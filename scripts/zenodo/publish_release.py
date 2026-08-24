"""Per-release Zenodo publisher, used by CI (SPEC M4).

Same code path as the backfill — ``scps.zenodo`` — not a parallel
implementation. Given a fresh scrape output directory and its release tag:
build the manifest, assign a vintage against ``data/vintages.json``; if the
vintage is new, publish a new version on the data concept and print the
updated vintages.json for the caller to commit. If the vintage is already
deposited, exit 0 without touching Zenodo.

    uv run python scripts/zenodo/publish_release.py \
        --release-dir . --tag 2026-09-01 [--sandbox --base-record ID] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scps import manifest as manifest_mod  # noqa: E402
from scps import zenodo  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--release-dir", type=Path, required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--vintages", type=Path, default=Path("data/vintages.json"))
    ap.add_argument("--sandbox", action="store_true")
    ap.add_argument("--base-record", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--assume-vintage",
        default=None,
        metavar="VID",
        help=(
            "Assign this release to an existing vintage id, overriding the "
            "content-hash comparison. Required when the SCRAPER's output "
            "format changed (new columns, row-filter changes): hashes then "
            "differ even if upstream data didn't, and only a value-level "
            "comparison on common strata (docs/releases.md §1.1) can decide. "
            "The release's hashes are learned into the vintage so future "
            "same-format releases compare normally."
        ),
    )
    args = ap.parse_args()

    m = manifest_mod.build_manifest(args.release_dir, args.tag)
    (args.release_dir / "manifest.json").write_text(json.dumps(m, indent=1) + "\n")

    vintages = manifest_mod.load_vintages(args.vintages)
    if args.assume_vintage:
        if args.assume_vintage not in vintages["vintages"]:
            ap.error(f"--assume-vintage {args.assume_vintage} not in {args.vintages}")
        vid, is_new = args.assume_vintage, False
        info = vintages["vintages"][vid]
        for topic, h in m["content_hashes"].items():
            hashes = info["content_sha256"].setdefault(topic, [])
            if h not in hashes:
                hashes.append(h)
    else:
        vid, is_new = manifest_mod.assign_vintage(m, vintages)

    # NLM-style deposit documentation; regenerated every release.
    readme_vintages = dict(vintages)
    if is_new:
        readme_vintages = {**vintages, "vintages": {**vintages["vintages"], vid: {
            "releases": [args.tag], "first_capture": args.tag, "best_capture": args.tag,
        }}}
    (args.release_dir / "00_README.txt").write_text(
        manifest_mod.render_readme(m, vid, readme_vintages)
    )

    if not is_new:
        # Record the tag under its vintage so the mapping stays complete.
        info = vintages["vintages"][vid]
        if args.tag not in info["releases"]:
            info["releases"].append(args.tag)
            info["best_capture"] = args.tag
            if not args.dry_run:
                args.vintages.write_text(json.dumps(vintages, indent=1) + "\n")
        logging.info("%s is vintage %s (already deposited) — nothing to publish.", args.tag, vid)
        return 0

    logging.info("%s is NEW vintage %s — publishing.", args.tag, vid)
    vintages["vintages"][vid] = {
        "releases": [args.tag],
        "first_capture": args.tag,
        "best_capture": args.tag,
        "defective_releases": [],
        "content_sha256": {t: [h] for t, h in m["content_hashes"].items()
                           if t in manifest_mod.VINTAGE_TOPICS},
    }

    dep = zenodo.VintageDeposit(
        vintage_id=vid,
        tags=[args.tag],
        publication_date=args.tag,
        best_capture=args.tag,
        files=manifest_mod.release_files(args.release_dir)
        + [args.release_dir / "manifest.json", args.release_dir / "00_README.txt"],
    )

    if args.sandbox:
        base_url, secret = zenodo.SANDBOX, "cdsci-zenodo-sandbox-api-token"
        base_record = args.base_record
    else:
        base_url, secret = zenodo.PRODUCTION, "cdsci-zenodo-api-token"
        base_record = args.base_record or zenodo.PRODUCTION_CONCEPT_RECORD

    if not args.dry_run:
        token = os.environ.get("ZENODO_TOKEN") or zenodo.token_from_gsm(secret)
        client = zenodo.ZenodoClient(base_url, token)
        versions = client.concept_versions(base_record)
        if args.tag in zenodo.deposited_tags(versions):
            logging.info("Tag already in a deposited version — idempotent no-op.")
            return 0
        latest = versions[-1]["id"] if versions else base_record
        zenodo.run_deposit(client, str(latest), dep, dry_run=False, manifest=m)
    else:
        zenodo.run_deposit(zenodo.ZenodoClient(zenodo.SANDBOX, "dry"), "0", dep, dry_run=True)
        # Dry runs record nothing: a vintages.json entry without a deposit
        # behind it would make the next real run skip the publish.
        return 0

    args.vintages.write_text(json.dumps(vintages, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
