"""Scraper for the State Cancer Profiles screening & risk-factor endpoint.

Data source: ``https://statecancerprofiles.cancer.gov/risk/index.php``

The risk endpoint exposes BRFSS-derived prevalence of screening behaviors
(mammograms, colonoscopy, HPV vaccination) and risk factors (binge drinking,
smoking, obesity). The dropdown that picks the actual risk factor is
populated by JavaScript from ``/risk/riskJSDefines.js``, keyed by topic, so
we parse that file alongside the HTML select options.
"""

from __future__ import annotations

import io
import logging
import re
from collections.abc import Callable, Iterable, Iterator
from typing import Any

import pandas as pd
from bs4 import BeautifulSoup

from scps.scraper import (
    NA_VALUES,
    find_defines_url,
    get_with_retry,
    parse_defines,
    column_text_replace,
    decode_suppression,
    fetch_report,
    parallel_fetch,
    split_report,
)

logger = logging.getLogger("scps.risk")

RISK_BASE_URL = "https://statecancerprofiles.cancer.gov/risk/index.php"

# These placeholder values appear in the HTML selects as "--- choose X ---"
# prompts and should never be used as real query parameters.
_PLACEHOLDER_VALUES = {"*", "**", "***", "****", "*****"}


def parse_risk_defines(js_text: str) -> dict[str, dict[str, str]]:
    """Parse the risk defines script into ``{topic: {risk_id: label}}``.

    2026-08 upstream format: ``const risk_<topic> = [["id", "label"], ...]``.
    """
    return parse_defines(js_text, "risk_")


def _parse_select_options(html: str) -> dict[str, dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    result: dict[str, dict[str, str]] = {}
    for select in soup.find_all("select"):
        sid = select.attrs.get("id")
        if not sid:
            continue
        opts: dict[str, str] = {}
        for option in select.find_all("option"):
            value = option.attrs.get("value")
            if value is None or value in _PLACEHOLDER_VALUES:
                continue
            text = option.get_text().strip()
            if text.startswith("---"):
                continue
            opts[value] = text
        result[sid] = opts
    return result


def get_risk_options() -> dict[str, Any]:
    """Discover risk select options from the live website.

    Returns a dict with keys ``topic``, ``risk_by_topic``, ``race``, ``sex``,
    ``statefips``, and ``datatype``. The ``risk_by_topic`` value is a nested
    ``{topic: {risk_id: label}}`` mapping parsed from ``riskJSDefines.js``.
    """
    html = get_with_retry(RISK_BASE_URL).text
    select_opts = _parse_select_options(html)

    js_text = get_with_retry(find_defines_url(html)).text
    risk_by_topic = parse_risk_defines(js_text)

    return {
        "topic": select_opts.get("topic", {}),
        "risk_by_topic": risk_by_topic,
        "race": select_opts.get("race", {}),
        "sex": select_opts.get("sex", {}),
        "statefips": select_opts.get("statefips", {}),
        "datatype": select_opts.get("datatype", {}),
    }


def _label(options: dict[str, str], key: str) -> str:
    return options.get(key, key)


def get_risk_table(
    topic: str,
    risk: str,
    race: str = "00",
    sex: str = "0",
    statefips: str = "00",
    datatype: str = "0",
    options: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Fetch a single risk-factor CSV and return it as a normalized DataFrame.

    ``statefips="00"`` returns US-by-state, ``"99"`` returns US-by-county.
    Other values return the counties of a single state.
    """
    url = (
        f"{RISK_BASE_URL}?statefips={statefips}&topic={topic}&race={race}"
        f"&sex={sex}&risk={risk}&type=risk&datatype={datatype}"
        f"&sortVariableName=percent&sortOrder=desc&output=1"
    )
    logger.debug(url)

    data_csv, notes = split_report(fetch_report(url))
    df = pd.read_csv(
        io.StringIO(data_csv),
        low_memory=False,
        na_values=NA_VALUES,
        skipinitialspace=True,
        dtype={"FIPS": str},
    )
    df.columns = [column_text_replace(c) for c in df.columns]

    # Locale column is `state` for statefips=00, `county` for statefips=99 or
    # a specific state. Normalize to `reported_locale` so downstream consumers
    # don't have to branch.
    if "state" in df.columns:
        df = df.rename(columns={"state": "reported_locale"})
    elif "county" in df.columns:
        df = df.rename(columns={"county": "reported_locale"})

    df = df.rename(
        columns={
            "percent2": "percent",
            "lower_95pct_confidence_interval": "lower_ci_percent",
            "upper_95pct_confidence_interval": "upper_ci_percent",
            "number_of_respondents_with_screening_or_risk_factor": "respondents",
        }
    )

    opts = options or {}
    df["topic"] = topic
    df["topic_label"] = _label(opts.get("topic", {}), topic)
    df["risk"] = risk
    df["risk_label"] = _label(opts.get("risk_by_topic", {}).get(topic, {}), risk)
    df["race"] = _label(opts.get("race", {}), race)
    df["sex"] = _label(opts.get("sex", {}), sex)
    df["datatype"] = _label(opts.get("datatype", {}), datatype)
    df["statefips_query"] = statefips

    df.loc[df["fips"].isna(), "fips"] = ""
    df["state_fips"] = df["fips"].str[:2]
    df["locale_type"] = "other"
    df.loc[df["fips"].str.startswith("00"), "locale_type"] = "national"
    df.loc[df["fips"].str.endswith("000") & ~df["fips"].str.startswith("00"), "locale_type"] = "state"
    if statefips == "99" or statefips not in ("00", ""):
        # The county-level breakdown uses 5-digit county FIPS that don't end
        # in 000; mark them as county.
        df.loc[
            df["fips"].str.len().eq(5) & ~df["fips"].str.endswith("000"),
            "locale_type",
        ] = "county"

    df["_extracted_at"] = pd.Timestamp.now().isoformat()
    df["url"] = url.replace("&output=1", "")

    if "percent" in df.columns:
        df["suppression_reason"] = decode_suppression(df["percent"])
    for numeric_column in ("percent", "lower_ci_percent", "upper_ci_percent", "respondents"):
        if numeric_column in df.columns:
            df[numeric_column] = pd.to_numeric(df[numeric_column], errors="coerce")

    df.attrs["scp_notes"] = notes
    return df


def iter_risk_combos(
    options: dict[str, Any],
    statefipses: Iterable[str],
) -> Iterator[dict]:
    """Yield every ``(topic, risk, race, sex, statefips)`` combo."""
    topics = options["topic"]
    risk_by_topic = options["risk_by_topic"]
    races = options["race"]
    sexes = options["sex"]
    for statefips in statefipses:
        for topic_id in topics:
            risks = risk_by_topic.get(topic_id, {})
            if not risks:
                continue
            for risk_id in risks:
                for race_id in races:
                    for sex_id in sexes:
                        yield {
                            "topic": topic_id,
                            "risk": risk_id,
                            "race": race_id,
                            "sex": sex_id,
                            "statefips": statefips,
                        }


def risk_master_table(
    statefipses: Iterable[str] = ("00", "99"),
    options: dict[str, Any] | None = None,
    combos: Iterable[dict] | None = None,
    on_success: Callable[[dict, int], None] | None = None,
) -> pd.DataFrame:
    """Iterate over every ``(topic, risk, race, sex, statefips)`` combination.

    Parameters
    ----------
    statefipses : iterable of str
        Which statefips queries to run when ``combos`` is not provided.
        ``"00"`` returns the US-by-state breakdown and ``"99"`` returns
        US-by-county. Defaults to both.
    options : dict, optional
        Pre-fetched output of ``get_risk_options()``. Refetched if omitted.
    combos : iterable of dict, optional
        If provided, supersedes the cartesian iteration — typically used by
        the catalog to limit the run to known-good combos.
    on_success : callable, optional
        Called as ``on_success(combo, n_rows)`` after each successful fetch.
    """
    opts = options or get_risk_options()

    if combos is None:
        logger.info(
            "Risk scrape: %d topics, statefips=%s",
            len(opts["topic"]), list(statefipses),
        )
        combos = iter_risk_combos(opts, statefipses)

    dflist = [
        df
        for _combo, df in parallel_fetch(
            combos, lambda c: get_risk_table(options=opts, **c), on_success
        )
    ]

    if not dflist:
        return pd.DataFrame()
    notes = next(
        (d.attrs["scp_notes"] for d in dflist if d.attrs.get("scp_notes")), None
    )
    df = pd.concat(dflist, ignore_index=True)
    if notes:
        df.attrs["scp_notes"] = notes
    return df
