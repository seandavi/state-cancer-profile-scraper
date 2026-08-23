"""Persistent catalog of (endpoint, dimension-combo) tuples that returned data.

Why: the full cartesian iteration across cancer × age × sex × race × stage ×
areatype (and the equivalents for risk/demographics) attempts ~5x more
combinations than actually exist in the data — pediatric cancers don't
exist for adult ages, mammograms don't exist for males, BRFSS suppresses
small cells, and so on. Memoizing the surviving combinations lets monthly
re-runs skip the dead space.

Format: append-only JSONL, one line per known-good combination. Released
alongside the gzipped CSVs so a future run can fetch the previous release's
catalog and skip straight to fetching real data.

Refresh policy: discovery (full cartesian + rewrite catalog) on the first
run after a schema change and on a quarterly cadence; catalog-driven on the
other 8 monthly runs.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger("scps.catalog")

ENDPOINTS = ("incidence", "mortality", "risk", "demographics")


@dataclass
class CatalogEntry:
    endpoint: str
    combo: dict[str, Any]
    rows: int
    discovered: str
    last_seen: str


@dataclass
class Catalog:
    """In-memory view of a scrape catalog backed by a JSONL file.

    Use :meth:`load` to read from disk and :meth:`save` to rewrite the file.
    During a live scrape, :meth:`record_success` updates an in-memory entry
    and :meth:`append_disk` writes a single line to the file immediately so
    a mid-run crash doesn't lose discovered combinations.
    """

    path: Path
    entries: list[CatalogEntry] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> Catalog:
        cat = cls(path=path)
        if not path.exists():
            return cat
        with path.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                endpoint = payload.pop("endpoint")
                rows = payload.pop("rows", 0)
                discovered = payload.pop("discovered", "")
                last_seen = payload.pop("last_seen", discovered)
                cat.entries.append(
                    CatalogEntry(
                        endpoint=endpoint,
                        combo=payload,
                        rows=rows,
                        discovered=discovered,
                        last_seen=last_seen,
                    )
                )
        logger.info("Loaded %d catalog entries from %s", len(cat.entries), path)
        return cat

    def combos_for(self, endpoint: str) -> Iterator[dict[str, Any]]:
        """Yield combo kwargs for every catalog entry of ``endpoint``."""
        for entry in self.entries:
            if entry.endpoint == endpoint:
                yield dict(entry.combo)

    def has_combos_for(self, endpoint: str) -> bool:
        return any(e.endpoint == endpoint for e in self.entries)

    def record_success(
        self, endpoint: str, combo: dict[str, Any], rows: int
    ) -> None:
        """Update in-memory entry (or add a new one) after a successful fetch."""
        today = date.today().isoformat()
        for entry in self.entries:
            if entry.endpoint == endpoint and entry.combo == combo:
                entry.last_seen = today
                entry.rows = rows
                return
        self.entries.append(
            CatalogEntry(
                endpoint=endpoint,
                combo=dict(combo),
                rows=rows,
                discovered=today,
                last_seen=today,
            )
        )

    def append_disk(
        self, endpoint: str, combo: dict[str, Any], rows: int
    ) -> None:
        """Append one entry to the on-disk file immediately (crash-safe)."""
        today = date.today().isoformat()
        payload = {
            "endpoint": endpoint,
            **combo,
            "rows": rows,
            "discovered": today,
            "last_seen": today,
        }
        with self.path.open("a") as fh:
            fh.write(json.dumps(payload) + "\n")

    def save(self) -> None:
        """Rewrite the catalog file from the in-memory state."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w") as fh:
            for entry in self.entries:
                payload = {
                    "endpoint": entry.endpoint,
                    **entry.combo,
                    "rows": entry.rows,
                    "discovered": entry.discovered,
                    "last_seen": entry.last_seen,
                }
                fh.write(json.dumps(payload) + "\n")
        logger.info("Wrote %d catalog entries to %s", len(self.entries), self.path)

    def unseen_since(self, endpoint: str, run_date: str) -> list[CatalogEntry]:
        """Entries for ``endpoint`` not re-confirmed on/after ``run_date``.

        In a catalog-driven run every recorded combo is attempted, so an
        entry whose ``last_seen`` predates the run is a combo that returned
        data last time and failed this time — a regression, not dead space
        (#38). ISO dates compare lexicographically.
        """
        return [
            e
            for e in self.entries
            if e.endpoint == endpoint and e.last_seen < run_date
        ]

    def truncate(self) -> None:
        """Empty the in-memory entries and the on-disk file (used by refresh)."""
        self.entries = []
        if self.path.exists():
            self.path.unlink()


def make_recorder(
    catalog: Catalog, endpoint: str
) -> "Callable[[dict, int], None]":  # noqa: F821 (forward ref)
    """Return a callback suited for ``master_table(on_success=...)``."""

    def record(combo: dict[str, Any], rows: int) -> None:
        catalog.record_success(endpoint, combo, rows)
        catalog.append_disk(endpoint, combo, rows)

    return record


def probe_new_ids(
    catalog: Catalog,
    endpoint: str,
    live_ids: Iterable[str],
    field_name: str,
) -> set[str]:
    """Return live ``field_name`` IDs that aren't represented in the catalog.

    Used after a catalog-driven scrape to warn when the upstream site has
    added a new cancer / topic / risk / demo that the catalog would silently
    miss. The caller decides what to do with the result (log a warning,
    exit non-zero, queue a refresh).
    """
    catalog_ids = {
        entry.combo.get(field_name)
        for entry in catalog.entries
        if entry.endpoint == endpoint and field_name in entry.combo
    }
    return {live_id for live_id in live_ids if live_id not in catalog_ids}
