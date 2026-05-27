"""Smoke tests for the click CLI."""

import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from click.testing import CliRunner

from scps import cli


def _fake_master_table(*_args, on_success=None, **_kwargs):
    if on_success is not None:
        on_success(
            {"cancer": "001", "age": "001", "sex": "0", "race": "00", "stage": "999", "areatype": "county"},
            1,
        )
    return pd.DataFrame({"reported_locale": ["X"], "fips": ["00000"]})


def _fake_risk_table(*_args, on_success=None, **_kwargs):
    if on_success is not None:
        on_success(
            {"topic": "alcohol", "risk": "v505", "race": "00", "sex": "0", "statefips": "00"},
            1,
        )
    return pd.DataFrame({"reported_locale": ["X"], "fips": ["00000"]})


def _fake_demo_table(*_args, on_success=None, **_kwargs):
    if on_success is not None:
        on_success(
            {"topic": "crowd", "demo": "00027", "areatype": "county", "race": "00", "sex": "0", "age": "001"},
            1,
        )
    return pd.DataFrame({"reported_locale": ["X"], "area_code": ["00000"]})


def test_cli_help_runs():
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["--help"])
    assert result.exit_code == 0
    assert "scrape" in result.output


def test_scrape_writes_each_dataset(tmp_path):
    runner = CliRunner()
    with (
        patch("scps.cli.scraper.master_table", side_effect=_fake_master_table),
        patch("scps.cli.risk.risk_master_table", side_effect=_fake_risk_table),
        patch(
            "scps.cli.demographics.demographics_master_table",
            side_effect=_fake_demo_table,
        ),
        patch("scps.cli.scraper.get_select_options", return_value={"cancer": {}}),
    ):
        result = runner.invoke(
            cli.cli, ["scrape", "-o", str(tmp_path)]
        )

    assert result.exit_code == 0, result.output
    expected_files = {
        "state_cancer_profiles_incidence.csv.gz",
        "state_cancer_profiles_mortality.csv.gz",
        "state_cancer_profiles_risk.csv.gz",
        "state_cancer_profiles_demographics.csv.gz",
        "select_options.json",
    }
    written = {p.name for p in tmp_path.iterdir()}
    assert expected_files <= written


def test_scrape_filters_by_dataset(tmp_path):
    runner = CliRunner()
    with (
        patch("scps.cli.scraper.master_table", side_effect=_fake_master_table),
        patch("scps.cli.risk.risk_master_table", side_effect=_fake_risk_table) as risk_mock,
        patch(
            "scps.cli.demographics.demographics_master_table",
            side_effect=_fake_demo_table,
        ) as demo_mock,
        patch("scps.cli.scraper.get_select_options", return_value={"cancer": {}}),
        patch("scps.cli.risk.get_risk_options", return_value={"topic": {}}),
        patch("scps.cli.demographics.get_demographics_options", return_value={"topic": {}}),
    ):
        result = runner.invoke(
            cli.cli, ["scrape", "-d", "risk", "-o", str(tmp_path)]
        )

    assert result.exit_code == 0, result.output
    risk_mock.assert_called_once()
    demo_mock.assert_not_called()
    assert (tmp_path / "state_cancer_profiles_risk.csv.gz").exists()
    assert not (tmp_path / "state_cancer_profiles_incidence.csv.gz").exists()


def test_scrape_writes_catalog_in_discovery_mode(tmp_path):
    """First-run / no-catalog → write a fresh catalog from successful combos."""
    runner = CliRunner()
    with (
        patch("scps.cli.scraper.master_table", side_effect=_fake_master_table),
        patch("scps.cli.risk.risk_master_table", side_effect=_fake_risk_table),
        patch(
            "scps.cli.demographics.demographics_master_table",
            side_effect=_fake_demo_table,
        ),
        patch("scps.cli.scraper.get_select_options", return_value={"cancer": {}}),
        patch("scps.cli.risk.get_risk_options", return_value={"topic": {}}),
        patch("scps.cli.demographics.get_demographics_options", return_value={"topic": {}}),
    ):
        result = runner.invoke(cli.cli, ["scrape", "-o", str(tmp_path)])

    assert result.exit_code == 0, result.output
    catalog_path = tmp_path / "scrape_catalog.jsonl"
    assert catalog_path.exists()
    lines = [json.loads(line) for line in catalog_path.read_text().splitlines() if line.strip()]
    endpoints_seen = {entry["endpoint"] for entry in lines}
    assert endpoints_seen == {"incidence", "mortality", "risk", "demographics"}


def test_scrape_uses_catalog_when_present(tmp_path):
    """Second run with a catalog passes combos through to master_table."""
    runner = CliRunner()
    catalog_path = tmp_path / "scrape_catalog.jsonl"
    catalog_path.write_text(
        json.dumps({
            "endpoint": "risk",
            "topic": "alcohol",
            "risk": "v505",
            "race": "00",
            "sex": "0",
            "statefips": "00",
            "rows": 52,
            "discovered": "2026-01-01",
            "last_seen": "2026-01-01",
        }) + "\n"
    )

    captured_combos = []

    def capture(*_args, combos=None, on_success=None, **_kw):
        captured_combos.append(list(combos) if combos is not None else None)
        return pd.DataFrame({"reported_locale": ["X"], "fips": ["00000"]})

    with (
        patch("scps.cli.risk.risk_master_table", side_effect=capture),
        patch("scps.cli.risk.get_risk_options", return_value={"topic": {}}),
    ):
        result = runner.invoke(
            cli.cli, ["scrape", "-d", "risk", "-o", str(tmp_path)]
        )

    assert result.exit_code == 0, result.output
    # combos were passed (not None) and contained the single catalog entry.
    assert captured_combos == [
        [{"topic": "alcohol", "risk": "v505", "race": "00", "sex": "0", "statefips": "00"}]
    ]


def test_refresh_catalog_truncates_existing(tmp_path):
    catalog_path = tmp_path / "scrape_catalog.jsonl"
    catalog_path.write_text(
        json.dumps({"endpoint": "risk", "topic": "old", "risk": "v0", "rows": 1,
                    "discovered": "2025-01-01", "last_seen": "2025-01-01"}) + "\n"
    )

    captured_combos = []

    def capture(*_args, combos=None, on_success=None, **_kw):
        captured_combos.append(combos)  # should be None in refresh mode
        if on_success:
            on_success({"topic": "new", "risk": "v1"}, 5)
        return pd.DataFrame({"reported_locale": ["X"], "fips": ["00000"]})

    runner = CliRunner()
    with (
        patch("scps.cli.risk.risk_master_table", side_effect=capture),
        patch("scps.cli.risk.get_risk_options", return_value={"topic": {}}),
    ):
        result = runner.invoke(
            cli.cli, ["scrape", "-d", "risk", "-o", str(tmp_path), "--refresh-catalog"]
        )

    assert result.exit_code == 0, result.output
    assert captured_combos == [None]  # discovery mode, no combo filter
    # The old "old/v0" entry is gone; only the new "new/v1" remains.
    lines = [json.loads(line) for line in catalog_path.read_text().splitlines() if line.strip()]
    topics_in_catalog = {entry["topic"] for entry in lines}
    assert topics_in_catalog == {"new"}


def test_refresh_preserves_other_endpoints_entries(tmp_path):
    """Refreshing only `risk` must not drop incidence/mortality/demographics."""
    catalog_path = tmp_path / "scrape_catalog.jsonl"
    catalog_path.write_text(
        "\n".join([
            json.dumps({"endpoint": "risk", "topic": "old", "risk": "v0", "rows": 1,
                        "discovered": "2025-01-01", "last_seen": "2025-01-01"}),
            json.dumps({"endpoint": "incidence", "cancer": "001", "age": "001",
                        "sex": "0", "race": "00", "stage": "999", "areatype": "county",
                        "rows": 3142, "discovered": "2025-01-01", "last_seen": "2025-01-01"}),
            json.dumps({"endpoint": "demographics", "topic": "crowd", "demo": "00027",
                        "areatype": "county", "race": "00", "sex": "0", "age": "001",
                        "rows": 3143, "discovered": "2025-01-01", "last_seen": "2025-01-01"}),
        ]) + "\n"
    )

    def fake_risk(*_args, on_success=None, **_kw):
        if on_success:
            on_success({"topic": "new", "risk": "v1", "race": "00", "sex": "0", "statefips": "00"}, 5)
        return pd.DataFrame({"reported_locale": ["X"], "fips": ["00000"]})

    runner = CliRunner()
    with (
        patch("scps.cli.risk.risk_master_table", side_effect=fake_risk),
        patch("scps.cli.risk.get_risk_options", return_value={"topic": {}}),
    ):
        result = runner.invoke(
            cli.cli, ["scrape", "-d", "risk", "-o", str(tmp_path), "--refresh-catalog"]
        )

    assert result.exit_code == 0, result.output
    lines = [json.loads(line) for line in catalog_path.read_text().splitlines() if line.strip()]
    by_endpoint = {entry["endpoint"]: entry for entry in lines}
    # risk entry replaced (old → new), incidence + demographics preserved.
    assert by_endpoint["risk"]["topic"] == "new"
    assert by_endpoint["incidence"]["cancer"] == "001"
    assert by_endpoint["demographics"]["topic"] == "crowd"
