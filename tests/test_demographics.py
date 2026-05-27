"""Tests for the scps.demographics module."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from scps import demographics


# ---------------------------------------------------------------------------
# parse_census_defines
# ---------------------------------------------------------------------------

SAMPLE_CENSUS_JS = """
var population_ages_array = new Array();
population_ages_array['00002'] = "Ages under 18";
population_ages_array['00003'] = "Ages 65 and over";

var population_races_array = new Array();
population_races_array['00014'] = "Foreign born";
population_races_array['00022'] = "Black";

var pop_array = new Array();
pop_array['Ages'] = population_ages_array;
pop_array['Races'] = population_races_array;

var ed_array = new Array();
ed_array['*****']=CHOOSE_BEGINNING + "choose demographic variable" + CHOOSE_END;
ed_array['00004']="Less than 9th grade";
//ed_array['00005']="Less than high school";
ed_array['00006']="At least bachelor's degree";

var crowd_array = new Array();
crowd_array['*****']=CHOOSE_BEGINNING + "choose demographic variable" + CHOOSE_END;
crowd_array['00027']="Households with >1 person per room";
"""


def test_parse_census_defines_returns_topic_to_demo_mapping():
    result = demographics.parse_census_defines(SAMPLE_CENSUS_JS)
    assert result["ed"] == {
        "00004": "Less than 9th grade",
        "00006": "At least bachelor's degree",
    }
    assert result["crowd"] == {"00027": "Households with >1 person per room"}


def test_parse_census_defines_merges_population_subarrays_into_pop():
    """pop_array re-exports population_ages_array + population_races_array."""
    result = demographics.parse_census_defines(SAMPLE_CENSUS_JS)
    assert result["pop"] == {
        "00002": "Ages under 18",
        "00003": "Ages 65 and over",
        "00014": "Foreign born",
        "00022": "Black",
    }


def test_parse_census_defines_skips_comments_and_placeholders():
    result = demographics.parse_census_defines(SAMPLE_CENSUS_JS)
    # Commented "00005" line excluded.
    assert "00005" not in result.get("ed", {})
    # Placeholder "*****" excluded.
    assert "*****" not in result.get("ed", {})


def test_parse_census_defines_skips_block_commented_arrays():
    """The live JS has `var ur_array = ...` inside /* ... */; must be skipped."""
    js_with_block_comment = SAMPLE_CENSUS_JS + """
/*
var ur_array = new Array();
ur_array['*****']=CHOOSE_BEGINNING + "choose demographic variable" + CHOOSE_END;
ur_array['00001']="Continuum Code";
*/
"""
    result = demographics.parse_census_defines(js_with_block_comment)
    assert "ur" not in result


def test_parse_census_defines_excludes_topic_box_array():
    """`topic_box_array` is the topic-label lookup, not a topic definition."""
    js_with_topic_box = SAMPLE_CENSUS_JS + """
var topic_box_array = new Array();
topic_box_array["crowd"] = "Crowding";
topic_box_array["ed"] = "Education";
"""
    result = demographics.parse_census_defines(js_with_topic_box)
    assert "topic_box" not in result


# ---------------------------------------------------------------------------
# get_demographics_table URL construction & normalization
# ---------------------------------------------------------------------------

def _fake_county_csv_dataframe():
    return pd.DataFrame(
        {
            "county": ["United States", "Some County, TX"],
            "fips": ["00000", "48001"],
            "2023_rural_urban_continuum_codesrural_urban_note": ["N/A", "Rural"],
            "value_percent": [3.4, 0.5],
            "households_with_1_person_per_room": [4449577, 12],
            "rank_within_us": ["N/A", "100 of 3143"],
        }
    )


def _fake_hsa_csv_dataframe():
    return pd.DataFrame(
        {
            "health_service_area": ["United States", "Jackson, CO"],
            "hsa_code": ["00000", "0771"],
            "value_percent": [3.4, 0.0],
            "households_with_1_person_per_room": [4449577, 0],
            "rank_within_us": ["N/A", "1 of 950"],
        }
    )


def test_get_demographics_table_builds_expected_url():
    captured = []

    def fake_read_csv(url, **_kwargs):
        captured.append(url)
        return _fake_county_csv_dataframe()

    with patch("pandas.read_csv", side_effect=fake_read_csv):
        demographics.get_demographics_table(
            topic="crowd", demo="00027", areatype="county"
        )

    assert len(captured) == 1
    url = captured[0]
    assert "topic=crowd" in url
    assert "demo=00027" in url
    assert "areatype=county" in url
    assert "type=manyareacensus" in url
    assert "output=1" in url


def test_get_demographics_table_normalizes_county_columns():
    with patch("pandas.read_csv", return_value=_fake_county_csv_dataframe()):
        df = demographics.get_demographics_table(
            topic="crowd", demo="00027", areatype="county"
        )

    assert "reported_locale" in df.columns
    assert "area_code" in df.columns
    assert "percent" in df.columns
    assert "rank" in df.columns
    # locale_type derived: 00000 is national, 5-digit county FIPS → county.
    locale_types = dict(zip(df["area_code"], df["locale_type"]))
    assert locale_types["00000"] == "national"
    assert locale_types["48001"] == "county"


def test_get_demographics_table_normalizes_hsa_columns():
    """HSA areatype uses ``Health Service Area`` / ``HSA_Code`` headers."""
    with patch("pandas.read_csv", return_value=_fake_hsa_csv_dataframe()):
        df = demographics.get_demographics_table(
            topic="crowd", demo="00027", areatype="hsa"
        )

    assert "reported_locale" in df.columns
    assert "area_code" in df.columns
    locale_types = dict(zip(df["area_code"], df["locale_type"]))
    assert locale_types["00000"] == "national"
    assert locale_types["0771"] == "hsa"


# ---------------------------------------------------------------------------
# demographics_master_table iteration
# ---------------------------------------------------------------------------

def _tiny_demo_options():
    return {
        "topic": {"crowd": "Crowding", "ed": "Education"},
        "demo_by_topic": {
            "crowd": {"00027": "Households with >1 person per room"},
            "ed": {"00004": "Less than 9th grade"},
        },
        "areatype": {"county": "By County", "state": "By State"},
        "race": {"00": "All Races"},
        "sex": {"0": "Both Sexes"},
        "age": {"001": "All Ages"},
        "statefips": {"00": "United States"},
    }


def test_demographics_master_table_iterates_areatypes():
    seen = []

    def fake_get_table(**kwargs):
        seen.append((kwargs["areatype"], kwargs["topic"], kwargs["demo"]))
        return pd.DataFrame({"reported_locale": ["X"], "area_code": ["00000"]})

    with patch.object(demographics, "get_demographics_table", side_effect=fake_get_table):
        demographics.demographics_master_table(
            areatypes=("county", "state"), options=_tiny_demo_options()
        )

    # 2 areatypes × 2 topics × 1 demo × 1 race × 1 sex × 1 age = 4 calls
    assert len(seen) == 4
    assert {a for a, _, _ in seen} == {"county", "state"}


def test_demographics_master_table_default_areatypes_are_county_and_state():
    """HSA is omitted by default — non-FIPS area code breaks downstream joins."""
    seen_areatypes = set()

    def fake_get_table(**kwargs):
        seen_areatypes.add(kwargs["areatype"])
        return pd.DataFrame({"reported_locale": ["X"], "area_code": ["00000"]})

    with patch.object(demographics, "get_demographics_table", side_effect=fake_get_table):
        demographics.demographics_master_table(options=_tiny_demo_options())

    assert seen_areatypes == {"county", "state"}


def test_demographics_master_table_swallows_failures():
    def fake_get_table(**kwargs):
        if kwargs["topic"] == "ed":
            raise ValueError("simulated")
        return pd.DataFrame({"reported_locale": ["X"], "area_code": ["00000"]})

    with patch.object(demographics, "get_demographics_table", side_effect=fake_get_table):
        df = demographics.demographics_master_table(
            areatypes=("county",), options=_tiny_demo_options()
        )

    # Only crowd survives.
    assert len(df) == 1


# ---------------------------------------------------------------------------
# get_demographics_options live discovery
# ---------------------------------------------------------------------------

def test_get_demographics_options_combines_html_and_js():
    html_response = MagicMock()
    html_response.text = """
    <html><body>
      <select id="topic"><option value="crowd">Crowding</option></select>
      <select id="areatype"><option value="county">By County</option></select>
      <select id="race"><option value="00">All Races</option></select>
      <select id="sex"><option value="0">Both Sexes</option></select>
      <select id="age"><option value="001">All Ages</option></select>
      <select id="statefips"><option value="00">United States</option></select>
    </body></html>
    """
    js_response = MagicMock()
    js_response.text = SAMPLE_CENSUS_JS

    def fake_get(url, *_a, **_k):
        if url.endswith(".js"):
            return js_response
        return html_response

    with patch("scps.demographics.httpx.get", side_effect=fake_get):
        opts = demographics.get_demographics_options()

    assert opts["topic"] == {"crowd": "Crowding"}
    assert opts["demo_by_topic"]["crowd"] == {
        "00027": "Households with >1 person per room"
    }
    assert opts["areatype"] == {"county": "By County"}
