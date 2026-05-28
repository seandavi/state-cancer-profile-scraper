"""Tests for scps.catalog."""

import json
from datetime import date
from pathlib import Path

import pandas as pd

from scps import catalog as catalog_mod


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# load / save round-trip
# ---------------------------------------------------------------------------

def test_catalog_load_empty_when_missing(tmp_path):
    cat = catalog_mod.Catalog.load(tmp_path / "missing.jsonl")
    assert cat.entries == []
    assert not cat.has_combos_for("incidence")


def test_catalog_record_and_save_roundtrip(tmp_path):
    path = tmp_path / "cat.jsonl"
    cat = catalog_mod.Catalog.load(path)
    cat.record_success(
        "risk",
        {"topic": "alcohol", "risk": "v505", "race": "00", "sex": "0", "statefips": "00"},
        rows=52,
    )
    cat.record_success(
        "incidence",
        {"cancer": "001", "age": "001", "sex": "0", "race": "00", "stage": "999", "areatype": "county"},
        rows=3142,
    )
    cat.save()

    reloaded = catalog_mod.Catalog.load(path)
    assert len(reloaded.entries) == 2
    risk_combos = list(reloaded.combos_for("risk"))
    assert risk_combos == [
        {"topic": "alcohol", "risk": "v505", "race": "00", "sex": "0", "statefips": "00"}
    ]
    assert reloaded.has_combos_for("incidence")
    assert reloaded.entries[0].discovered == date.today().isoformat()


def test_catalog_record_success_updates_existing_entry(tmp_path):
    cat = catalog_mod.Catalog(path=tmp_path / "cat.jsonl")
    combo = {"topic": "alcohol", "risk": "v505", "race": "00", "sex": "0", "statefips": "00"}
    cat.record_success("risk", combo, rows=10)
    cat.record_success("risk", combo, rows=20)  # rerun on same combo
    assert len(cat.entries) == 1
    assert cat.entries[0].rows == 20


def test_catalog_append_disk_is_crash_safe(tmp_path):
    """append_disk writes one entry immediately; survives process loss."""
    path = tmp_path / "cat.jsonl"
    cat = catalog_mod.Catalog(path=path)
    cat.append_disk("risk", {"topic": "alcohol", "risk": "v505"}, rows=42)
    cat.append_disk("risk", {"topic": "smoke", "risk": "v19"}, rows=13)

    written = _read_jsonl(path)
    assert len(written) == 2
    assert {w["topic"] for w in written} == {"alcohol", "smoke"}
    assert all(w["endpoint"] == "risk" for w in written)


# ---------------------------------------------------------------------------
# make_recorder + master_table integration
# ---------------------------------------------------------------------------

def test_make_recorder_writes_to_catalog_on_each_success(tmp_path):
    path = tmp_path / "cat.jsonl"
    cat = catalog_mod.Catalog(path=path)
    record = catalog_mod.make_recorder(cat, "risk")

    record({"topic": "alcohol", "risk": "v505"}, 50)
    record({"topic": "smoke", "risk": "v19"}, 100)

    # In-memory updated.
    assert len(cat.entries) == 2
    # On-disk file updated (crash safety).
    on_disk = _read_jsonl(path)
    assert len(on_disk) == 2


def test_master_table_uses_combo_iterator_and_calls_on_success(tmp_path):
    """master_table should iterate the provided combos, not a cartesian."""
    from unittest.mock import patch

    from scps import scraper as scraper_mod

    seen_combos = []
    recorded = []

    def fake_get_table(**kwargs):
        seen_combos.append(kwargs)
        return pd.DataFrame({"reported_locale": ["X, CO"], "fips": ["08001"]})

    combos = [
        {"cancer": "001", "age": "001", "sex": "0", "race": "00", "stage": "999", "areatype": "county"},
        {"cancer": "001", "age": "001", "sex": "0", "race": "00", "stage": "999", "areatype": "state"},
    ]

    def on_success(combo, rows):
        recorded.append((dict(combo), rows))

    with patch.object(scraper_mod, "get_table", side_effect=fake_get_table):
        scraper_mod.master_table(combos=combos, on_success=on_success)

    # Only the explicit combos ran (no cartesian).
    assert len(seen_combos) == 2
    assert all(c["_type"] == "incd" for c in seen_combos)
    assert len(recorded) == 2


# ---------------------------------------------------------------------------
# probe_new_ids
# ---------------------------------------------------------------------------

def test_probe_new_ids_returns_ids_not_in_catalog():
    cat = catalog_mod.Catalog(path=Path("/dev/null"))
    cat.record_success("risk", {"topic": "alcohol", "risk": "v505"}, rows=10)
    cat.record_success("risk", {"topic": "smoke", "risk": "v19"}, rows=10)

    live_topics = ["alcohol", "smoke", "vaccine"]  # vaccine is new
    new = catalog_mod.probe_new_ids(cat, "risk", live_topics, "topic")
    assert new == {"vaccine"}


def test_probe_new_ids_empty_when_catalog_covers_everything():
    cat = catalog_mod.Catalog(path=Path("/dev/null"))
    cat.record_success("risk", {"topic": "alcohol", "risk": "v505"}, rows=10)

    new = catalog_mod.probe_new_ids(cat, "risk", ["alcohol"], "topic")
    assert new == set()


def test_probe_new_ids_scoped_to_endpoint():
    """Only the requested endpoint's entries count toward 'known' IDs."""
    cat = catalog_mod.Catalog(path=Path("/dev/null"))
    cat.record_success("risk", {"topic": "alcohol", "risk": "v505"}, rows=10)
    cat.record_success("demographics", {"topic": "crowd", "demo": "00027"}, rows=10)

    # crowd is in the demographics catalog but should still count as "new"
    # if we're checking the risk endpoint.
    new = catalog_mod.probe_new_ids(cat, "risk", ["crowd"], "topic")
    assert new == {"crowd"}
