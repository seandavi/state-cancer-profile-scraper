"""Smoke tests for the click CLI."""

from pathlib import Path
from unittest.mock import patch

import pandas as pd
from click.testing import CliRunner

from scps import cli


def _fake_master_table(*_args, **_kwargs):
    return pd.DataFrame({"reported_locale": ["X"], "fips": ["00000"]})


def _fake_risk_table(*_args, **_kwargs):
    return pd.DataFrame({"reported_locale": ["X"], "fips": ["00000"]})


def _fake_demo_table(*_args, **_kwargs):
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
    ):
        result = runner.invoke(
            cli.cli, ["scrape", "-d", "risk", "-o", str(tmp_path)]
        )

    assert result.exit_code == 0, result.output
    risk_mock.assert_called_once()
    demo_mock.assert_not_called()
    assert (tmp_path / "state_cancer_profiles_risk.csv.gz").exists()
    assert not (tmp_path / "state_cancer_profiles_incidence.csv.gz").exists()
