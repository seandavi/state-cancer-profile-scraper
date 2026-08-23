"""Tests for the scps.risk module."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from scps import risk


# ---------------------------------------------------------------------------
# parse_risk_defines
# ---------------------------------------------------------------------------

SAMPLE_RISK_JS = """
var alcohol_array = new Array();
alcohol_array['**']=CHOOSE_BEGINNING + "choose screening or risk factor" + CHOOSE_END;
alcohol_array['v505']="Binge drinking, ages 21+";
//alcohol_array['v501']="Mean number of alcoholic drinks per day, ages 21+";

var smoke_array = new Array();
smoke_array['**']=CHOOSE_BEGINNING + "choose screening or risk factor" + CHOOSE_END;
smoke_array["v19"]="Current Smoking; Ages 18+";
smoke_array["v28"]="Smokers (Ever); Ages 18+";

var topic_arrays = new Array();
topic_arrays["alcohol"] = alcohol_array;
topic_arrays["smoke"] = smoke_array;
"""


def test_parse_risk_defines_returns_topic_to_risk_mapping():
    result = risk.parse_risk_defines(SAMPLE_RISK_JS)
    assert result == {
        "alcohol": {"v505": "Binge drinking, ages 21+"},
        "smoke": {
            "v19": "Current Smoking; Ages 18+",
            "v28": "Smokers (Ever); Ages 18+",
        },
    }


def test_parse_risk_defines_skips_commented_lines():
    result = risk.parse_risk_defines(SAMPLE_RISK_JS)
    # v501 is commented out and must not appear.
    assert "v501" not in result.get("alcohol", {})


def test_parse_risk_defines_skips_placeholder_choice_entries():
    result = risk.parse_risk_defines(SAMPLE_RISK_JS)
    assert "**" not in result.get("alcohol", {})
    assert "**" not in result.get("smoke", {})


# ---------------------------------------------------------------------------
# get_risk_table URL construction & metadata enrichment
# ---------------------------------------------------------------------------

_RISK_HEADER = (
    "State,FIPS,Percent2,"
    '"Lower 95% Confidence Interval","Upper 95% Confidence Interval",'
    '"Number of Respondents (with Screening or Risk Factor)"'
)


def _risk_report(header=_RISK_HEADER, rows=None):
    rows = rows or [
        '"United States",00000,15.6,N/A,N/A,N/A',
        '"District of Columbia",11001,25.5,23.5,27.6,536',
        '"Montana",30000,20.3,18.9,21.6,946',
    ]
    return "\n".join(
        [
            "Screening and Risk Factors Report",
            "",
            '"Binge Drinking, 2020-2022"',
            "",
            header,
            *rows,
            "",
            "Created by statecancerprofiles.cancer.gov on 08/23/2026 11:35 am.",
        ]
    )


def test_get_risk_table_builds_expected_url():
    captured = []

    def fake_fetch(url):
        captured.append(url)
        return _risk_report()

    with patch.object(risk, "fetch_report", side_effect=fake_fetch):
        risk.get_risk_table(topic="alcohol", risk="v505", statefips="00")

    assert len(captured) == 1
    url = captured[0]
    assert "topic=alcohol" in url
    assert "risk=v505" in url
    assert "statefips=00" in url
    assert "type=risk" in url
    assert "output=1" in url


def test_get_risk_table_normalizes_columns_and_adds_metadata():
    options = {
        "topic": {"alcohol": "Alcohol"},
        "risk_by_topic": {"alcohol": {"v505": "Binge drinking"}},
        "race": {"00": "All Races"},
        "sex": {"0": "Both Sexes"},
        "datatype": {"0": "Direct Estimates"},
    }
    with patch.object(risk, "fetch_report", return_value=_risk_report()):
        df = risk.get_risk_table(
            topic="alcohol", risk="v505", statefips="00", options=options
        )

    # Locale column renamed.
    assert "reported_locale" in df.columns
    # Percent column normalized.
    assert "percent" in df.columns
    # Metadata columns attached.
    assert (df["topic_label"] == "Alcohol").all()
    assert (df["risk_label"] == "Binge drinking").all()
    assert (df["race"] == "All Races").all()
    # locale_type derived from FIPS pattern.
    locale_types = dict(zip(df["fips"], df["locale_type"]))
    assert locale_types["00000"] == "national"
    assert locale_types["30000"] == "state"  # ends in 000, not in 00


def test_get_risk_table_county_breakdown_uses_county_column():
    payload = _risk_report(
        header=_RISK_HEADER.replace("State,FIPS", "County,FIPS"),
        rows=['"Some County, TX",48001,10.0,9.0,11.0,42'],
    )
    with patch.object(risk, "fetch_report", return_value=payload):
        df = risk.get_risk_table(topic="alcohol", risk="v505", statefips="99")

    assert "reported_locale" in df.columns
    assert df["locale_type"].iloc[0] == "county"


def test_get_risk_table_decodes_suppression():
    payload = _risk_report(
        rows=[
            '"Montana",30000,20.3,18.9,21.6,946',
            '"Wyoming",56000,* ,*, *,*',
        ]
    )
    with patch.object(risk, "fetch_report", return_value=payload):
        df = risk.get_risk_table(topic="alcohol", risk="v505", statefips="00")

    by_fips = df.set_index("fips")
    assert by_fips.loc["30000", "percent"] == 20.3
    assert pd.isna(by_fips.loc["30000", "suppression_reason"])
    assert pd.isna(by_fips.loc["56000", "percent"])
    assert by_fips.loc["56000", "suppression_reason"] == "suppressed_small_count"


# ---------------------------------------------------------------------------
# risk_master_table iteration
# ---------------------------------------------------------------------------

def _tiny_risk_options():
    return {
        "topic": {"alcohol": "Alcohol", "smoke": "Smoking"},
        "risk_by_topic": {
            "alcohol": {"v505": "Binge drinking"},
            "smoke": {"v19": "Current smoking"},
        },
        "race": {"00": "All Races"},
        "sex": {"0": "Both Sexes"},
        "statefips": {"00": "US by State", "99": "US by County"},
        "datatype": {"0": "Direct Estimates"},
    }


def test_risk_master_table_iterates_full_cartesian():
    seen = []

    def fake_get_risk_table(**kwargs):
        seen.append(
            (kwargs["topic"], kwargs["risk"], kwargs["statefips"])
        )
        return pd.DataFrame({"reported_locale": ["X"], "fips": ["00000"]})

    with patch.object(risk, "get_risk_table", side_effect=fake_get_risk_table):
        risk.risk_master_table(
            statefipses=("00", "99"), options=_tiny_risk_options()
        )

    # 2 statefips × 2 topics × 1 risk-per-topic × 1 race × 1 sex = 4 calls
    assert len(seen) == 4
    assert set(seen) == {
        ("alcohol", "v505", "00"),
        ("smoke", "v19", "00"),
        ("alcohol", "v505", "99"),
        ("smoke", "v19", "99"),
    }


def test_risk_master_table_swallows_invalid_combinations():
    """Exceptions from a single combo should not abort the run."""
    def fake_get_risk_table(**kwargs):
        if kwargs["topic"] == "smoke":
            raise ValueError("simulated invalid combo")
        return pd.DataFrame({"reported_locale": ["X"], "fips": ["00000"]})

    with patch.object(risk, "get_risk_table", side_effect=fake_get_risk_table):
        df = risk.risk_master_table(
            statefipses=("00",), options=_tiny_risk_options()
        )

    # Only the alcohol row survives; smoke raised and was swallowed.
    assert len(df) == 1


def test_risk_master_table_propagates_keyboard_interrupt():
    def fake_get_risk_table(**_kwargs):
        raise KeyboardInterrupt

    with patch.object(risk, "get_risk_table", side_effect=fake_get_risk_table):
        with pytest.raises(KeyboardInterrupt):
            risk.risk_master_table(
                statefipses=("00",), options=_tiny_risk_options()
            )


# ---------------------------------------------------------------------------
# get_risk_options (live discovery)
# ---------------------------------------------------------------------------

def test_get_risk_options_combines_html_and_js():
    html_response = MagicMock()
    html_response.text = """
    <html><body>
      <select id="topic">
        <option value="alcohol">Alcohol</option>
      </select>
      <select id="race">
        <option value="00">All Races</option>
      </select>
      <select id="sex">
        <option value="0">Both Sexes</option>
      </select>
      <select id="statefips">
        <option value="00">US by State</option>
      </select>
      <select id="datatype">
        <option value="0">Direct Estimates</option>
      </select>
    </body></html>
    """
    js_response = MagicMock()
    js_response.text = SAMPLE_RISK_JS

    def fake_get(url, *_a, **_k):
        if url.endswith(".js"):
            return js_response
        return html_response

    with patch("scps.risk.httpx.get", side_effect=fake_get):
        opts = risk.get_risk_options()

    assert opts["topic"] == {"alcohol": "Alcohol"}
    assert "alcohol" in opts["risk_by_topic"]
    assert "v505" in opts["risk_by_topic"]["alcohol"]
