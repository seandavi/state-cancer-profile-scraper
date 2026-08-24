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
            import pyarrow.parquet as pq

            entry.update(format="parquet", rows=pq.ParquetFile(path).metadata.num_rows)
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


# ---------------------------------------------------------------------------
# 00_README.txt — NLM-style deposit documentation (generated, never hand-kept)
# ---------------------------------------------------------------------------

_FILE_BLURBS = (
    ("state_cancer_profiles_incidence", "Cancer incidence: age-adjusted rates per 100,000 with 95% CIs, trend statistics, and average annual counts, one row per statistical stratum (cancer site x race/ethnicity x sex x age x stage) x locale (county/state/US). From the first 2026-08-24 release onward, upstream-suppressed cells are retained as empty rate fields with an explicit suppression_reason column (suppressed_small_count = fewer than 16 cases; withheld_state_law = Kansas counties); in earlier releases suppressed rows are absent entirely. Source: SEER/NPCR registries via statecancerprofiles.cancer.gov."),
    ("state_cancer_profiles_mortality", "Cancer mortality: same layout as incidence, without the stage dimension (not applicable to death rates; releases before 2026-08-24 carry a spurious stage column that duplicates every row — see the repository's docs). Source: NCHS vital statistics via statecancerprofiles.cancer.gov."),
    ("state_cancer_profiles_risk", "Screening and risk-factor prevalence (e.g. smoking, binge drinking, mammography). These are MODEL-BASED small-area estimates built from BRFSS survey data, not registry observations, and refresh on their own cadence independent of the incidence/mortality vintage."),
    ("state_cancer_profiles_demographics", "Demographic and social-determinant indicators (poverty, education, insurance, SVI, population) from the American Community Survey and related sources, by county/state."),
    ("notes_", "Verbatim title and footnote blocks from the upstream CSV export for this topic: data windows, source registries, submission year, and suppression-rule definitions as stated by NCI at scrape time."),
    ("scrape_catalog.jsonl", "One JSON line per query combination known to return data; the exact request inventory this release was scraped from (provenance for every row's originating query)."),
    ("select_options.json", "The query vocabulary (cancer sites, race/ethnicity, ages, stages...) as served by the website's own form controls at scrape time."),
    ("gh_hash.txt", "Git commit of the scraper code that produced this release, in the repository below."),
    ("manifest.json", "Machine-readable inventory: sha256, byte size, row count, and content hash per file, plus provenance fields extracted from the notes."),
    ("release_note.txt", "Short human note attached to the GitHub release."),
    ("00_README.txt", "This file."),
)


def _blurb(filename: str) -> str:
    for prefix, text in _FILE_BLURBS:
        if filename.startswith(prefix):
            return text
    return ""


def render_readme(manifest: dict, vintage_id: str, vintages: dict) -> str:
    """NLM-style plain-text documentation of one deposit's files and provenance."""
    info = vintages["vintages"][vintage_id]
    tags = ", ".join(info["releases"])
    doi = info.get("doi", "(this version)")
    concept = vintages.get("concept_doi", "10.5281/zenodo.11098814")
    lines = [
        "00_README.txt",
        f"United States State Cancer Profiles data extract - vintage {vintage_id}",
        "=" * 72,
        "",
        "WHAT THIS IS",
        "",
        "A complete national county- and state-level extract of the NCI/CDC State",
        "Cancer Profiles website (statecancerprofiles.cancer.gov), which offers no",
        "API, bulk download, or archive of prior estimates. A VINTAGE is one",
        "edition of the upstream estimates: the complete set of values the site",
        "served during some period, bounded by NCI silently replacing them with",
        "revised values. Several dated scrapes that captured identical values",
        "belong to one vintage; this deposit preserves one such edition.",
        "",
        "PROVENANCE",
        "",
        f"  Vintage:            {vintage_id} (first captured {info['first_capture']})",
        f"  Deposited bytes:    GitHub release {info['best_capture']} (the vintage's most complete capture)",
        f"  All capturing tags: {tags}",
        f"  Version DOI:        {doi}",
        f"  Concept DOI:        {concept} (always resolves to the latest vintage)",
        "  Scraper:            https://github.com/seandavi/state-cancer-profile-scraper",
        "                      (commit in gh_hash.txt; methods in docs/releases.md)",
        "  License:            CC-BY-4.0",
        "",
        "FILES",
        "",
    ]
    for f in manifest["files"]:
        size = f"{f['bytes']:,} bytes"
        rows = f" | {f['rows']:,} rows" if "rows" in f else ""
        lines.append(f"  {f['filename']}  ({size}{rows})")
        lines.append(f"    sha256: {f['sha256']}")
        blurb = _blurb(f["filename"])
        if blurb:
            import textwrap
            lines.extend(textwrap.wrap(blurb, width=70, initial_indent="    ", subsequent_indent="    "))
        lines.append("")
    lines += [
        "CITATION",
        "",
        f"  Davis S. United States State Cancer Profiles data extract - vintage {vintage_id}.",
        f"  Zenodo. https://doi.org/{doi}" if doi != "(this version)" else "  Zenodo. (DOI of this version)",
        "",
    ]
    return "\n".join(lines) + "\n"
