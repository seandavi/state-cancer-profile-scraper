"""Tests for scps.normalize — the audit's defect list, one test each."""

import pandas as pd
import pytest

from scps import normalize


CROSSWALKS = normalize.load_crosswalks()


def test_locale_type_rederived_from_areatype():
    """Parishes/boroughs/cities binned `other` upstream become `county`."""
    df = pd.DataFrame(
        {
            "fips": ["00000", "06000", "22047", "51640", "11001"],
            "areatype": ["By County"] * 4 + ["By State"],
            "reported_locale": ["US", "California", "Iberville Parish(2)", "Galax City(1)", "DC"],
            "locale_type": ["national", "state", "other", "other", "state"],
        }
    )
    out, dropped = normalize.harmonize(df, "incidence", "V2", "t", CROSSWALKS)
    by_fips = dict(zip(out["fips"], out["locale_type"]))
    assert by_fips == {
        "00000": "national",
        "06000": "state",
        "22047": "county",
        "51640": "county",
        "11001": "state",
    }
    assert dropped == 0


def test_leaked_note_rows_dropped_and_counted():
    df = pd.DataFrame(
        {
            "area_code": ["00000", None, None],
            "areatype": ["By County"] * 3,
            "reported_locale": ["US", "Notes:", "Created by statecancerprofiles..."],
        }
    )
    out, dropped = normalize.harmonize(df, "demographics", "V3", "t", CROSSWALKS)
    assert len(out) == 1
    assert dropped == 2


def test_race_labels_cleaned_and_canonicalized():
    df = pd.DataFrame(
        {
            "area_code": ["00000"] * 4,
            "race": [
                "\\u00A0\\u00A0\\u00A0White Non-Hispanic",
                "White (includes Hispanic",
                "Asian Non-Hispanic",
                "All Races (includes Hispanic)",
            ],
        }
    )
    out, _ = normalize.harmonize(df, "demographics", "V3", "t", CROSSWALKS)
    assert list(out["race"]) == [
        "White Non-Hispanic",
        "White (includes Hispanic)",
        "Asian Non-Hispanic",
        "All Races (includes Hispanic)",
    ]
    # Canonical only where populations are identical; Asian NH has no
    # incidence equivalent (A/PI is a different population) and stays null.
    assert out["race_canonical"].tolist()[0] == "White (Non-Hispanic)"
    assert pd.isna(out["race_canonical"].tolist()[2])
    assert out["race_canonical"].tolist()[3] == "All Races (includes Hispanic)"


def test_risk_typo_canonicalized():
    df = pd.DataFrame(
        {
            "fips": ["00000"],
            "race": ["Asian / Pacifice Islander (Non-Hispanic)"],
        }
    )
    out, _ = normalize.harmonize(df, "risk", "V3", "t", CROSSWALKS)
    assert out["race_canonical"].iloc[0] == "Asian / Pacific Islander (Non-Hispanic)"


def test_source_note_extracted_and_rucc_renamed():
    df = pd.DataFrame(
        {
            "fips": ["53045", "53000"],
            "areatype": ["By County"] * 2,
            "reported_locale": ["Mason County(7)", "Washington(1)"],
            "2023_rural_urban_continuum_codesrural_urban_note": ["Rural", None],
        }
    )
    out, _ = normalize.harmonize(df, "incidence", "V3", "tag-x", CROSSWALKS)
    assert list(out["source_note"]) == ["7", "1"]
    assert "rural_urban" in out.columns
    assert list(out["vintage"]) == ["V3", "V3"]
    assert list(out["release_tag"]) == ["tag-x", "tag-x"]


def test_accounting_is_strict():
    df = pd.DataFrame({"fips": ["01001", None], "areatype": ["By County"] * 2})
    out, dropped = normalize.harmonize(df, "incidence", "V1", "t", CROSSWALKS)
    assert len(out) + dropped == 2
