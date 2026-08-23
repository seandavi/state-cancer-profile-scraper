"""Basic tests for the scps.scraper module."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from scps import scraper
from tests.conftest import MOCK_SELECT_HTML


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

_INCD_RATE = '"Age-Adjusted Incidence Rate([rate note]) - cases per 100,000"'
_DEATH_RATE = '"Age-Adjusted Death Rate([rate note]) - deaths per 100,000"'

# Full county header as served live (2026-08), including the 2023 RUCC column
# that broke position-based parsers.
COUNTY_HEADER = (
    "County,FIPS,2023 Rural-Urban Continuum Codes([rural urban note]),"
    + _INCD_RATE
    + ',"Lower 95% Confidence Interval","Upper 95% Confidence Interval",'
    '"CI*Rank([rank note])","Lower CI (CI*Rank)","Upper CI (CI*Rank)",'
    "Average Annual Count,Recent Trend,"
    '"Recent 5-Year Trend ([trend note]) in Incidence Rates",'
    '"Lower 95% Confidence Interval","Upper 95% Confidence Interval"'
)


def _report(header, rows, title_lines=None):
    """Assemble a raw SCP export: title block, data block, footnotes."""
    title = title_lines or [
        "Incidence Rate Report for United States by County",
        "",
        '"All Cancer Sites (All Stages^), 2018-2022"',
        "",
        "Sorted by Rate",
        "",
    ]
    return "\n".join(
        [
            *title,
            header,
            *rows,
            "",
            "Created by statecancerprofiles.cancer.gov on 08/23/2026 11:30 am.",
            '"* Data has been suppressed to ensure confidentiality and stability of rate estimates."',
            '"(1) Source: NPCR and SEER. Based on the 2024 submission."',
        ]
    )


def test_get_table_uses_correct_url():
    """get_table should build a URL with the expected query parameters."""
    captured_urls = []

    def mock_fetch(url):
        captured_urls.append(url)
        return _report(
            "County,FIPS," + _INCD_RATE,
            ['"Test County, Virginia",51001,100.0'],
        )

    with patch.object(scraper, "fetch_report", side_effect=mock_fetch):
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


# ---------------------------------------------------------------------------
# split_report: content-based data-block location
# ---------------------------------------------------------------------------

def test_split_report_locates_data_by_content():
    """The data block is found by its header line, not by a fixed offset."""
    rows = ['"Test County, Virginia",51001,100.0']
    short = _report("County,FIPS," + _INCD_RATE, rows, title_lines=["Tiny", ""])
    long_title = ["Line %d" % i for i in range(12)] + [""]
    long = _report("County,FIPS," + _INCD_RATE, rows, title_lines=long_title)

    for payload in (short, long):
        data_csv, notes = scraper.split_report(payload)
        assert data_csv.splitlines()[0].startswith("County,FIPS")
        assert len(data_csv.splitlines()) == 2
        assert "Created by statecancerprofiles.cancer.gov" in notes
        assert "2024 submission" in notes


def test_split_report_raises_without_header():
    import pytest

    with pytest.raises(ValueError):
        scraper.split_report("Just a title\n\nNo data here\n")


# ---------------------------------------------------------------------------
# Suppression decoding (#35)
# ---------------------------------------------------------------------------

def test_get_table_keeps_suppressed_rows_with_reason():
    """Suppressed cells become typed nulls + a reason; N/A rows still drop."""
    rows = [
        '"Mason County(7)",53045,Rural,66.9 ,60, 74.5,1 , 1 , 6,74,falling,-1.5 ,-2.0, -0.9',
        '"Garfield County(2)",53023,Rural,* ,*, *,* , * , *,3 or fewer,*,*,*,*',
        '"Cheyenne County(2)",20023,Rural,[P1 note] ,N/A, N/A,N/A , N/A , N/A,N/A,N/A,N/A,N/A,N/A',
        '"Nowhere County(1)",99001,Rural,N/A ,N/A, N/A,N/A , N/A , N/A,N/A,N/A,N/A,N/A,N/A',
    ]
    payload = _report(COUNTY_HEADER, rows)

    with patch.object(scraper, "fetch_report", return_value=payload):
        df = scraper.get_table(areatype="county")

    rate_col = "age_adjusted_incidence_raterate_note___cases_per_100_000"
    by_fips = df.set_index("fips")
    # The N/A-rate row is dropped; numeric + both suppressed rows survive.
    assert set(by_fips.index) == {"53045", "53023", "20023"}
    assert by_fips.loc["53045", rate_col] == 66.9
    assert pd.isna(by_fips.loc["53045", "suppression_reason"])
    assert pd.isna(by_fips.loc["53023", rate_col])
    assert by_fips.loc["53023", "suppression_reason"] == "suppressed_small_count"
    assert pd.isna(by_fips.loc["20023", rate_col])
    assert by_fips.loc["20023", "suppression_reason"] == "withheld_state_law"
    # The RUCC column passes through under its normalized name.
    assert "2023_rural_urban_continuum_codesrural_urban_note" in df.columns


def test_get_table_attaches_notes():
    payload = _report(
        "County,FIPS," + _INCD_RATE, ['"Test County, Virginia",51001,100.0']
    )
    with patch.object(scraper, "fetch_report", return_value=payload):
        df = scraper.get_table(areatype="county")
    assert "Created by statecancerprofiles.cancer.gov" in df.attrs["scp_notes"]


def test_master_table_iterates_areatypes():
    """master_table passes each requested areatype through to get_table."""
    captured_areatypes = []

    def fake_get_table(**kwargs):
        captured_areatypes.append(kwargs.get("areatype"))
        import pandas as pd
        # master_table splits `county` on ", " into (locale, state) — use a
        # comma-bearing string so the split produces two columns.
        # master_table now expects `reported_locale` (get_table renames the
        # raw "county"/"state" column to this); replicate that here.
        return pd.DataFrame(
            {
                "reported_locale": ["Somewhere County, CO"],
                "fips": ["08001"],
                "age_adjusted_incidence_raterate_note___cases_per_100_000": [1.0],
            }
        )

    # Trim the select option universe so the run is fast.
    tiny_opts = {
        "cancer": {"001": "All Cancer Sites"},
        "age": {"001": "All Ages"},
        "sex": {"0": "Both Sexes"},
        "race": {"00": "All Races (includes Hispanic)"},
        "stage": {"999": "All Stages"},
        "year": {"0": "Latest 5-year average"},
        "areatype": {"county": "By County", "state": "By State"},
    }

    with patch.object(scraper, "get_select_options", return_value=tiny_opts), \
         patch.object(scraper, "get_table", side_effect=fake_get_table):
        scraper.master_table(areatypes=("county", "state"))

    assert captured_areatypes == ["county", "state"]


def test_master_table_default_areatype_is_county_only():
    """Backward-compat: default areatypes preserves county-only behaviour."""
    captured_areatypes = []

    def fake_get_table(**kwargs):
        captured_areatypes.append(kwargs.get("areatype"))
        import pandas as pd
        # master_table now expects `reported_locale` (get_table renames the
        # raw "county"/"state" column to this); replicate that here.
        return pd.DataFrame(
            {
                "reported_locale": ["Somewhere County, CO"],
                "fips": ["08001"],
                "age_adjusted_incidence_raterate_note___cases_per_100_000": [1.0],
            }
        )

    tiny_opts = {
        "cancer": {"001": "All Cancer Sites"},
        "age": {"001": "All Ages"},
        "sex": {"0": "Both Sexes"},
        "race": {"00": "All Races (includes Hispanic)"},
        "stage": {"999": "All Stages"},
        "year": {"0": "Latest 5-year average"},
        "areatype": {"county": "By County"},
    }

    with patch.object(scraper, "get_select_options", return_value=tiny_opts), \
         patch.object(scraper, "get_table", side_effect=fake_get_table):
        scraper.master_table()

    assert set(captured_areatypes) == {"county"}


def test_get_table_handles_state_areatype_response():
    """By-state responses have `State`+`FIPS` columns, not `County`+`FIPS`.

    Regression for the bug where state-areatype combos silently failed because
    df["county"] raised KeyError and master_table swallowed it.
    """
    # State-level responses carry no RUCC column (which is exactly why
    # cancerprof's state calls still work).
    payload = _report(
        "State,FIPS," + _INCD_RATE,
        [
            '"California",06000,400.0',
            '"Texas",48000,410.0',
            # 11001 — 5-char non-000 FIPS, still state
            '"District of Columbia",11001,420.0',
            # 02900 — aggregated registry, special FIPS
            '"Alaska",02900,430.0',
        ],
    )

    with patch.object(scraper, "fetch_report", return_value=payload):
        df = scraper.get_table(areatype="state")

    assert "reported_locale" in df.columns
    assert "county" not in df.columns
    assert "state" not in df.columns  # the source column got renamed
    # Every row in the by-state view classifies as "state", including the
    # 5-char-non-000 FIPS rows for DC and the Alaska aggregate.
    assert (df["locale_type"] == "state").all()


def test_get_table_locale_type_from_fips_shape():
    """For by-county runs, classification uses FIPS shape — not locale-string.

    Regression for county-equivalents (parishes, boroughs, independent cities)
    that don't have the word "County" in their name. Also verifies that a
    state-aggregate row (FIPS XX000) embedded in a county-view response is
    labeled "state".
    """
    payload = _report(
        "County,FIPS," + _INCD_RATE,
        [
            '"United States",00000,1.0',                   # 00000 → national
            '"California",06000,2.0',                      # state aggregate row
            '"Iberville Parish, Louisiana",22047,3.0',     # county-equivalent
            '"Lake and Peninsula Borough, AK",02164,4.0',  # county-equivalent
            '"Galax City, Virginia",51640,5.0',            # county-equivalent (city)
            '"Plain County, Anywhere",12345,6.0',          # traditional county
        ],
    )

    with patch.object(scraper, "fetch_report", return_value=payload):
        df = scraper.get_table(areatype="county")

    by_fips = dict(zip(df["fips"], df["locale_type"]))
    assert by_fips == {
        "00000": "national",
        "06000": "state",
        "22047": "county",
        "02164": "county",
        "51640": "county",
        "12345": "county",
    }


def test_get_table_death_url():
    """get_table with _type='death' should use the deathrates endpoint."""
    captured_urls = []

    def mock_fetch(url):
        captured_urls.append(url)
        return _report(
            "County,FIPS," + _DEATH_RATE,
            ['"Test County, Virginia",51001,50.0'],
        )

    with patch.object(scraper, "fetch_report", side_effect=mock_fetch):
        scraper.get_table(_type="death")

    assert len(captured_urls) == 1
    assert "deathrates" in captured_urls[0]
