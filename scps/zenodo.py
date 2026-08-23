"""Zenodo REST client and deposit planning for the vintage archive.

Importable core so the logic is testable without a token; the runnable
entry points are ``scripts/zenodo/backfill.py`` and
``scripts/zenodo/publish_release.py``. API gotchas and the
sandbox-first rule live in ``scripts/zenodo/CLAUDE.md``.
"""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from scps.manifest import release_files

logger = logging.getLogger("scps.zenodo")

PRODUCTION = "https://zenodo.org"
SANDBOX = "https://sandbox.zenodo.org"

# The data concept (docs/audit.md §3). The webhook-maintained software
# concept 13174526 must never be written to by this code.
PRODUCTION_CONCEPT_RECORD = "11098814"

CREATORS = [{"name": "Davis, Sean", "orcid": "0000-0002-8991-6458"}]

_RETRY_STATUSES = {429, 500, 502, 503, 504}


def token_from_gsm(secret_name: str) -> str:
    """Fetch a token from GCP Secret Manager via the gcloud CLI."""
    return subprocess.run(
        [
            "gcloud", "secrets", "versions", "access", "latest",
            f"--secret={secret_name}", "--project=cdsci-infra",
        ],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


class ZenodoClient:
    """Minimal deposit client. Sequential, with retry/backoff (rate limits
    are modest — never upload concurrently)."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self._params = {"access_token": token}

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        if url.startswith("/"):
            url = self.base_url + url
        params = {**self._params, **kwargs.pop("params", {})}
        for attempt in range(6):
            resp = httpx.request(
                method, url, params=params, timeout=120.0, **kwargs
            )
            if resp.status_code not in _RETRY_STATUSES:
                resp.raise_for_status()
                return resp
            wait = 2**attempt
            logger.warning("%s %s -> %s; retrying in %ss", method, url, resp.status_code, wait)
            time.sleep(wait)
        resp.raise_for_status()
        return resp

    # -- read side -----------------------------------------------------
    def concept_versions(self, concept_record_id: str) -> list[dict]:
        """All published versions under a concept, oldest first."""
        out: list[dict] = []
        page = 1
        while True:
            resp = self._request(
                "GET",
                f"/api/records/{concept_record_id}/versions",
                params={"page": page, "size": 25},  # 25 = unauthenticated page cap
            ).json()
            hits = resp.get("hits", {}).get("hits", [])
            out.extend(hits)
            total = resp.get("hits", {}).get("total", len(out))
            if len(out) >= total or not hits:
                break
            page += 1
        out.sort(key=lambda h: h.get("metadata", {}).get("publication_date", ""))
        return out

    # -- write side ----------------------------------------------------
    def new_version_draft(self, record_id: str) -> dict:
        """POST newversion, then return the draft deposition (work against
        links.latest_draft, never the original id)."""
        resp = self._request(
            "POST", f"/api/deposit/depositions/{record_id}/actions/newversion"
        ).json()
        draft_url = resp["links"]["latest_draft"]
        return self._request("GET", draft_url).json()

    def clear_files(self, draft: dict) -> None:
        """Files do not carry over usefully to a new version — remove all."""
        for f in self._request("GET", draft["links"]["files"]).json():
            self._request("DELETE", f["links"]["self"])

    def upload_file(self, draft: dict, path: Path) -> None:
        bucket = draft["links"]["bucket"]
        with path.open("rb") as fh:
            self._request("PUT", f"{bucket}/{path.name}", content=fh.read())

    def set_metadata(self, draft: dict, metadata: dict) -> None:
        self._request(
            "PUT", draft["links"]["self"], json={"metadata": metadata}
        )

    def publish(self, draft: dict) -> dict:
        return self._request("POST", draft["links"]["publish"]).json()


# ---------------------------------------------------------------------------
# Deposit planning — pure functions, unit-tested
# ---------------------------------------------------------------------------

@dataclass
class VintageDeposit:
    vintage_id: str
    tags: list[str]
    publication_date: str
    best_capture: str
    files: list[Path]


def vintage_metadata(dep: VintageDeposit, repo: str = "seandavi/state-cancer-profile-scraper") -> dict:
    """Deposit metadata for one vintage version.

    ``related_identifiers`` carries every GitHub tag that captured the
    vintage — this is also the idempotency key.
    """
    # Git tags are bare dates ("2026-06-01"); "release-" is only in the title.
    tag_urls = [f"https://github.com/{repo}/releases/tag/{t}" for t in dep.tags]
    description = (
        f"<p>State Cancer Profiles data extract — vintage {dep.vintage_id}. "
        f"Complete national county- and state-level extract scraped from "
        f"statecancerprofiles.cancer.gov, which offers no API, bulk download, "
        f"or archive of prior estimates.</p>"
        f"<p>This vintage was first captured on {dep.publication_date} and was "
        f"served unchanged by the upstream site across {len(dep.tags)} scrape "
        f"release(s): {', '.join(dep.tags)}. The deposited files are the most "
        f"complete capture of the vintage (release {dep.best_capture}), which "
        f"is not necessarily the first; the publication date reflects first "
        f"capture. Vintage grouping method and release-level provenance: "
        f"https://github.com/{repo}/blob/main/docs/releases.md</p>"
    )
    return {
        "title": f"United States State Cancer Profiles data extract — vintage {dep.vintage_id}",
        "upload_type": "dataset",
        "publication_date": dep.publication_date,
        "creators": CREATORS,
        "license": "cc-by-4.0",
        "description": description,
        "keywords": ["cancer", "surveillance", "State Cancer Profiles", "SEER", "NPCR", "county", "incidence", "mortality"],
        "related_identifiers": [
            {"identifier": u, "relation": "isSupplementTo", "scheme": "url"}
            for u in tag_urls
        ],
    }


def deposited_tags(versions: list[dict]) -> set[str]:
    """GitHub release tags already present across a concept's versions."""
    tags: set[str] = set()
    for v in versions:
        for rel in v.get("metadata", {}).get("related_identifiers", []):
            ident = rel.get("identifier", "")
            if "/releases/tag/" in ident:
                tags.add(ident.rsplit("/releases/tag/", 1)[-1])
    return tags


def plan_backfill(
    vintages: dict, release_root: Path, existing_versions: list[dict]
) -> list[VintageDeposit]:
    """Deposits still needed, oldest first. Already-deposited vintages
    (any of their tags present in existing metadata) are skipped —
    re-running never duplicates."""
    done = deposited_tags(existing_versions)
    plan: list[VintageDeposit] = []
    ordered = sorted(
        vintages["vintages"].items(), key=lambda kv: kv[1]["first_capture"]
    )
    for vid, info in ordered:
        if set(info["releases"]) & done:
            logger.info("%s already deposited — skipping", vid)
            continue
        best_dir = release_root / info["best_capture"]
        files = release_files(best_dir)
        plan.append(
            VintageDeposit(
                vintage_id=vid,
                tags=info["releases"],
                publication_date=info["first_capture"],
                best_capture=info["best_capture"],
                files=files,
            )
        )
    return plan


def run_deposit(client: ZenodoClient, base_record_id: str, dep: VintageDeposit, dry_run: bool = False) -> str | None:
    """Execute one vintage deposit as a new version of ``base_record_id``.
    Returns the new record id (or None on dry run)."""
    logger.info(
        "%s: %d files from %s, publication_date=%s%s",
        dep.vintage_id, len(dep.files), dep.best_capture, dep.publication_date,
        " [dry-run]" if dry_run else "",
    )
    if dry_run:
        return None
    draft = client.new_version_draft(base_record_id)
    client.clear_files(draft)
    for path in dep.files:
        logger.info("  upload %s (%d bytes)", path.name, path.stat().st_size)
        client.upload_file(draft, path)
    client.set_metadata(draft, vintage_metadata(dep))
    published = client.publish(draft)
    logger.info("  published %s -> %s", dep.vintage_id, published.get("doi"))
    return str(published.get("id"))
