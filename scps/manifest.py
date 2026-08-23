"""Per-release provenance manifest: sha256, sizes, row counts, vintage.

A *vintage* is a distinct set of upstream SCP estimates. Historical release
artifacts carry no upstream vintage string (the pre-#39 scraper discarded
the report notes), so vintage identity is derived from content: two releases
whose files are identical after dropping the scrape-time ``_extracted_at``
column captured the same upstream data. See ``docs/releases.md`` for the
audit that established the method and the V1-V3 grouping.

The release-tag → vintage mapping is data, not code: ``data/vintages.json``.
``assign_vintage`` extends it for a new release by comparing content hashes
against the latest known vintage.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path

import pandas as pd

TOPICS = ("incidence", "mortality", "risk", "demographics")

# Topics whose content hash defines vintage identity. risk/demographics only
# exist from 2026-05-28 and their arrival was a scraper scope change, not a
# vintage change (docs/releases.md §1.2), so they don't participate.
VINTAGE_TOPICS = ("incidence", "mortality")

# Release artifacts, by name. build_manifest and the Zenodo deposit paths
# operate on directories that may contain other files (in CI the scrape
# writes into the repo checkout root) — only these are release outputs.
RELEASE_FILE_RE = re.compile(
    r"^(state_cancer_profiles_\w+\.(csv\.gz|parquet)"
    r"|select_options\.json|scrape_catalog\.jsonl|gh_hash\.txt"
    r"|notes_\w+\.txt|release_note\.txt)$"
)


def release_files(release_dir: Path) -> list[Path]:
    """The release artifacts present in a directory, sorted by name."""
    return sorted(
        p for p in release_dir.iterdir()
        if p.is_file() and RELEASE_FILE_RE.match(p.name)
    )


_CREATED_RE = re.compile(
    r"Created by statecancerprofiles\.cancer\.gov on ([0-9/]+)"
)
_SUBMISSION_RE = re.compile(r"[Bb]ased on the (\d{4}) submission")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def content_hash(csv_gz: Path) -> tuple[str, int]:
    """Return (sha256 of content minus ``_extracted_at``, row count).

    The scrape timestamp is the only column that varies between captures of
    the same upstream data; hashing without it makes byte-level vintage
    comparison possible.
    """
    df = pd.read_csv(csv_gz, dtype=str, low_memory=False)
    df = df.drop(columns=["_extracted_at"], errors="ignore")
    payload = df.to_csv(index=False).encode()
    return hashlib.sha256(payload).hexdigest(), len(df)


def extract_notes_fields(notes_text: str) -> dict:
    """Pull provenance fields from a ``notes_<endpoint>.txt`` block.

    Only available for releases made after PR #39; historical releases have
    no notes and their manifests carry ``notes: null``.
    """
    created = _CREATED_RE.search(notes_text)
    submissions = sorted(set(_SUBMISSION_RE.findall(notes_text)))
    return {
        "created_on": created.group(1) if created else None,
        "submission_years": submissions,
    }


def build_manifest(release_dir: Path, tag: str) -> dict:
    """Manifest for one release directory (downloaded GitHub release assets)."""
    files = []
    content_hashes: dict[str, str] = {}
    for path in release_files(release_dir):
        entry: dict = {
            "filename": path.name,
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        topic = next(
            (t for t in TOPICS if path.name == f"state_cancer_profiles_{t}.csv.gz"),
            None,
        )
        if topic:
            chash, rows = content_hash(path)
            entry.update(format="csv.gz", topic=topic, rows=rows, content_sha256=chash)
            content_hashes[topic] = chash
        elif path.suffix == ".parquet":
            entry.update(format="parquet", rows=len(pd.read_parquet(path, columns=[])))
        notes_match = re.fullmatch(r"notes_(\w+)\.txt", path.name)
        if notes_match:
            entry["notes"] = extract_notes_fields(path.read_text())
        files.append(entry)
    return {"tag": tag, "files": files, "content_hashes": content_hashes}


def load_vintages(path: Path) -> dict:
    return json.loads(path.read_text())


def assign_vintage(manifest: dict, vintages: dict) -> tuple[str, bool]:
    """Return (vintage_id, is_new) for a release manifest.

    Same incidence+mortality content hashes as the latest vintage → that
    vintage. Any difference → a new vintage id. Defective partial scrapes
    can't reach this path anymore (the catalog regression oracle fails the
    run first), so hash inequality means upstream really changed.
    """
    hashes = {t: manifest["content_hashes"].get(t) for t in VINTAGE_TOPICS}
    for vid, vinfo in vintages["vintages"].items():
        if all(hashes.get(t) in vinfo["content_sha256"].get(t, []) for t in VINTAGE_TOPICS):
            return vid, False
    latest = max(vintages["vintages"], key=lambda v: int(v.lstrip("V")))
    return f"V{int(latest.lstrip('V')) + 1}", True
