"""Basic tests for the scps.scraper module."""

import io
from unittest.mock import MagicMock, patch

import pytest

# Minimal HTML that mimics the state cancer profiles select options page.
# get_select_options() is called at module import time, so we must patch
# httpx.get *before* importing scps.scraper.
MOCK_SELECT_HTML = """
<html>
<body>
  <select id="cancer">
    <option value="001">All Cancer Sites</option>
    <option value="071">Bladder</option>
  </select>
  <select id="year">
    <option value="0">Latest 5-year average</option>
  </select>
  <select id="race">
    <option value="00">All Races (includes Hispanic)</option>
  </select>
  <select id="sex">
    <option value="0">Both Sexes</option>
    <option value="1">Male</option>
    <option value="2">Female</option>
  </select>
  <select id="age">
    <option value="001">All Ages</option>
  </select>
  <select id="stage">
    <option value="999">All Stages</option>
  </select>
  <select id="areatype">
    <option value="county">By County</option>
    <option value="state">By State/Registry/Division</option>
  </select>
</body>
</html>
"""

_mock_http_response = MagicMock()
_mock_http_response.text = MOCK_SELECT_HTML

with patch("httpx.get", return_value=_mock_http_response):
    from scps import scraper


# ---------------------------------------------------------------------------
# Tests for column_text_replace
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("Age Adjusted Rate", "age_adjusted_rate"),
        ("  leading and trailing  ", "leading_and_trailing"),
        ("CI Rank [note]", "ci_rank_note"),
        ("Rate (per 100,000)", "rate_per_100_000"),
        ("Recent 5-Year Trend", "recent_5_year_trend"),
        ("% of Cases", "pct_of_cases"),
        ("Lower 95% CI*", "lower_95pct_ci_"),
        ("Met?", "met"),
        ("col.name", "col_name"),
    ],
)
def test_column_text_replace(input_text, expected):
    assert scraper.column_text_replace(input_text) == expected


def test_column_text_replace_empty_string():
    assert scraper.column_text_replace("") == ""


# ---------------------------------------------------------------------------
# Tests for get_select_options
# ---------------------------------------------------------------------------

def test_get_select_options_returns_dict():
    mock_response = MagicMock()
    mock_response.text = MOCK_SELECT_HTML
    with patch("httpx.get", return_value=mock_response):
        result = scraper.get_select_options()

    assert isinstance(result, dict)


def test_get_select_options_expected_keys():
    mock_response = MagicMock()
    mock_response.text = MOCK_SELECT_HTML
    with patch("httpx.get", return_value=mock_response):
        result = scraper.get_select_options()

    for key in ("cancer", "year", "race", "sex", "age", "stage", "areatype"):
        assert key in result, f"Expected key '{key}' missing from select options"


def test_get_select_options_values_are_dicts():
    mock_response = MagicMock()
    mock_response.text = MOCK_SELECT_HTML
    with patch("httpx.get", return_value=mock_response):
        result = scraper.get_select_options()

    for key, value in result.items():
        assert isinstance(value, dict), f"Value for '{key}' should be a dict"


def test_get_select_options_cancer_values():
    mock_response = MagicMock()
    mock_response.text = MOCK_SELECT_HTML
    with patch("httpx.get", return_value=mock_response):
        result = scraper.get_select_options()

    assert result["cancer"]["001"] == "All Cancer Sites"
    assert result["cancer"]["071"] == "Bladder"


def test_get_select_options_age_has_pediatric_options():
    """Age groups for pediatrics (015, 016) are added as a workaround."""
    mock_response = MagicMock()
    mock_response.text = MOCK_SELECT_HTML
    with patch("httpx.get", return_value=mock_response):
        result = scraper.get_select_options()

    assert "015" in result["age"], "Pediatric age group '015' should be present"
    assert "016" in result["age"], "Pediatric age group '016' should be present"


# ---------------------------------------------------------------------------
# Tests for get_table URL construction
# ---------------------------------------------------------------------------

def _make_mock_dataframe_csv():
    """Return a minimal CSV string matching the expected structure."""
    header_rows = "\n" * 8  # scraper skips first 8 rows
    csv_content = (
        "County,FIPS,Rural Urban,Age Adjusted Incidence Rate(rate note) - Cases per 100,000,"
        "Lower 95% Confidence Interval,Upper 95% Confidence Interval,"
        "CI Rank(rank note),Lower CI (CI Rank),Upper CI (CI Rank),"
        "Average Annual Count,Recent Trend,Recent 5-Year Trend (trend note) in Incidence Rates,"
        "Lower 95% Confidence Interval,Upper 95% Confidence Interval\n"
        "Test County, Virginia,51000,Urban,100.0,90.0,110.0,1,1,5,50,stable,1.0,0.5,1.5\n"
    )
    return header_rows + csv_content


def test_get_table_uses_correct_url():
    """get_table should build a URL with the expected query parameters."""
    captured_urls = []

    def mock_read_csv(url, **kwargs):
        captured_urls.append(url)
        import pandas as pd
        # Return a minimal DataFrame with required columns
        data = {
            "county": ["Test County, Virginia"],
            "fips": ["51001"],
            "age_adjusted_incidence_raterate_note___cases_per_100_000": [100.0],
            "lower_95pct_confidence_interval": [90.0],
            "upper_95pct_confidence_interval": [110.0],
            "ci_rankrank_note": ["1"],
            "lower_ci_ci_rank": [1],
            "upper_ci_ci_rank": [5],
            "average_annual_count": [50],
            "recent_trend": ["stable"],
            "recent_5_year_trend_trend_note_in_incidence_rates": [1.0],
            "lower_95pct_confidence_interval_1": [0.5],
            "upper_95pct_confidence_interval_1": [1.5],
        }
        return pd.DataFrame(data)

    with patch("pandas.read_csv", side_effect=mock_read_csv):
        scraper.get_table(
            year="0",
            stateFIPS="00",
            sex="0",
            stage="999",
            race="00",
            cancer="001",
            areatype="county",
            age="001",
            _type="incd",
        )

    assert len(captured_urls) == 1
    url = captured_urls[0]
    assert "stateFIPS=00" in url
    assert "cancer=001" in url
    assert "areatype=county" in url
    assert "incidencerates" in url
    assert "output=1" in url


def test_get_table_death_url():
    """get_table with _type='death' should use the deathrates endpoint."""
    captured_urls = []

    def mock_read_csv(url, **kwargs):
        captured_urls.append(url)
        import pandas as pd
        data = {
            "county": ["Test County, Virginia"],
            "fips": ["51001"],
            "age_adjusted_death_raterate_note___deaths_per_100_000": [50.0],
            "lower_95pct_confidence_interval": [40.0],
            "upper_95pct_confidence_interval": [60.0],
            "ci_rankrank_note": ["2"],
            "lower_ci_ci_rank": [1],
            "upper_ci_ci_rank": [5],
            "average_annual_count": [20],
            "recent_trend": ["falling"],
            "recent_5_year_trend_trend_note_in_death_rates": [-1.0],
            "lower_95pct_confidence_interval_1": [-1.5],
            "upper_95pct_confidence_interval_1": [-0.5],
        }
        return pd.DataFrame(data)

    with patch("pandas.read_csv", side_effect=mock_read_csv):
        scraper.get_table(_type="death")

    assert len(captured_urls) == 1
    assert "deathrates" in captured_urls[0]
