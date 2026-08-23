"""One-time, idempotent Zenodo backfill: one version per vintage.

Rehearse on sandbox FIRST (scripts/zenodo/CLAUDE.md). Sandbox is a separate
instance, so the first sandbox run must create a throwaway base deposit
there and pass its record id via --base-record.

    # sandbox rehearsal (after creating a throwaway record there)
    uv run python scripts/zenodo/backfill.py --sandbox \
        --base-record <sandbox-record-id> --release-root /path/to/rel

    # production, only after the sandbox output is reviewed
    uv run python scripts/zenodo/backfill.py --release-root /path/to/rel

``--release-root`` is a directory of downloaded release assets,
one subdirectory per release tag (as produced by ``gh release download``).
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
    ap.add_argument("--sandbox", action="store_true")
    ap.add_argument("--base-record", default=None,
                    help="Record id to branch versions from (required for --sandbox)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.sandbox:
        base_url, secret = zenodo.SANDBOX, "cdsci-zenodo-sandbox-api-token"
        if not args.base_record and not args.dry_run:
            ap.error("--sandbox requires --base-record (create a throwaway deposit there first)")
        base_record = args.base_record
    else:
        base_url, secret = zenodo.PRODUCTION, "cdsci-zenodo-api-token"
        base_record = args.base_record or zenodo.PRODUCTION_CONCEPT_RECORD

    if args.dry_run:
        client = zenodo.ZenodoClient(base_url, "dry-run")
        existing = []
    else:
        token = os.environ.get("ZENODO_TOKEN") or zenodo.token_from_gsm(secret)
        client = zenodo.ZenodoClient(base_url, token)
        existing = client.concept_versions(base_record)

    vintages = json.loads(args.vintages.read_text())
    plan = zenodo.plan_backfill(vintages, args.release_root, existing)
    if not plan:
        logging.info("Nothing to do — all vintages already deposited.")
        return 0

    # Each deposit becomes the base for the next version, keeping order.
    current = base_record
    for dep in plan:
        new_id = zenodo.run_deposit(client, current, dep, dry_run=args.dry_run)
        if new_id:
            current = new_id
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
