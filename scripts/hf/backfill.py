"""One-time, idempotent HF backfill: one commit + tag per vintage (SPEC M6).

Downloads each vintage's best-capture release assets via ``gh release
download``, rebuilds the manifest from those bytes and checks it against
the manifest already committed at ``manifests/<tag>.json`` (the same
content sha256 that ``data/vintages.json`` is keyed on), then mirrors
oldest vintage first so HF's commit history matches Zenodo's version order.

    uv run python scripts/hf/backfill.py --release-root /path/to/rel [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scps import hf  # noqa: E402
from scps import manifest as manifest_mod  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")

REPO = "seandavi/state-cancer-profile-scraper"


def _ensure_downloaded(tag: str, release_root: Path) -> Path:
    d = release_root / tag
    if not d.exists() or not any(d.iterdir()):
        d.mkdir(parents=True, exist_ok=True)
        logging.info("Downloading release assets for %s...", tag)
        subprocess.run(
            ["gh", "release", "download", tag, "--dir", str(d), "--clobber",
             "--repo", REPO],
            check=True,
        )
    return d


def _verify(tag: str, release_dir: Path, committed_manifest: Path) -> dict:
    """Rebuild the manifest from downloaded bytes and check every sha256
    matches the manifest already committed for that release tag."""
    built = manifest_mod.build_manifest(release_dir, tag)
    committed = json.loads(committed_manifest.read_text())
    built_hashes = {f["filename"]: f["sha256"] for f in built["files"]}
    committed_hashes = {f["filename"]: f["sha256"] for f in committed["files"]}
    mismatches = {
        name: (committed_hashes[name], built_hashes.get(name))
        for name in committed_hashes
        if built_hashes.get(name) != committed_hashes[name]
    }
    if mismatches:
        raise SystemExit(f"{tag}: sha256 mismatch vs committed manifest: {mismatches}")
    return built


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--release-root", type=Path, required=True)
    ap.add_argument("--vintages", type=Path, default=Path("data/vintages.json"))
    ap.add_argument("--manifests-dir", type=Path, default=Path("manifests"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    vintages = json.loads(args.vintages.read_text())
    args.release_root.mkdir(parents=True, exist_ok=True)

    for vid in sorted(vintages["vintages"], key=lambda v: int(v.lstrip("V"))):
        info = vintages["vintages"][vid]
        tag = info["best_capture"]
        release_dir = _ensure_downloaded(tag, args.release_root)
        built = _verify(tag, release_dir, args.manifests_dir / f"{tag}.json")
        (release_dir / "manifest.json").write_text(json.dumps(built, indent=1) + "\n")

        files = manifest_mod.release_files(release_dir) + [release_dir / "manifest.json"]
        readme = release_dir / "00_README.md"
        if readme.exists():
            files.append(readme)

        if args.dry_run:
            logging.info("[dry-run] would mirror %s (%s) — %d files", vid, tag, len(files))
            continue

        tag_name = hf.mirror_vintage(release_dir, files, vid, vintages, built)
        logging.info("Mirrored %s (%s) -> tag %s", vid, tag, tag_name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
