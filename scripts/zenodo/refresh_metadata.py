"""Re-apply current vintage_metadata() to already-published versions.

Metadata (not files) is editable after publish: edit -> PUT -> publish.
Used to propagate description/wording changes (e.g. the plain-language
definition of "vintage") to versions deposited before the change.

    ZENODO_TOKEN=... uv run python scripts/zenodo/refresh_metadata.py \
        --release-root <staging-dir> [--vintages data/vintages.json] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scps import zenodo  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--release-root", type=Path, required=True)
    ap.add_argument("--vintages", type=Path, default=Path("data/vintages.json"))
    ap.add_argument("--base-record", default=zenodo.PRODUCTION_CONCEPT_RECORD)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    vintages = json.loads(args.vintages.read_text())
    token = os.environ.get("ZENODO_TOKEN") or zenodo.token_from_gsm("cdsci-zenodo-api-token")
    client = zenodo.ZenodoClient(zenodo.PRODUCTION, token)

    deposits = {
        d.vintage_id: d
        for d in zenodo.plan_backfill(vintages, args.release_root, existing_versions=[])
    }
    for version in client.concept_versions(args.base_record):
        title = version.get("metadata", {}).get("title", "")
        vid = title.rsplit("vintage ", 1)[-1] if "vintage " in title else None
        if vid not in deposits:
            logging.info("skip %s (%s) — not a vintage version", version["doi"], title[:50])
            continue
        manifest_path = Path("manifests") / f"{deposits[vid].best_capture}.json"
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
        md = zenodo.vintage_metadata(deposits[vid], manifest=manifest)
        logging.info("refresh %s (%s)%s", version["doi"], vid, " [dry-run]" if args.dry_run else "")
        if args.dry_run:
            continue
        dep_url = f"/api/deposit/depositions/{version['id']}"
        client._request("POST", dep_url + "/actions/edit")
        client._request("PUT", dep_url, json={"metadata": md})
        client._request("POST", dep_url + "/actions/publish")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
