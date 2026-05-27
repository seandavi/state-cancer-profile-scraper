"""Scraper for the State Cancer Profiles demographics endpoint.

Data source: ``https://statecancerprofiles.cancer.gov/demographics/index.php``

The endpoint serves ACS-derived demographic indicators (crowding, education,
poverty, SVI, etc.). As with the risk endpoint, the demographic-variable
dropdown is populated by JavaScript from ``/demographics/censusJSDefines.js``
keyed by topic, so we parse that file alongside the HTML select options.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable, Iterator
from typing import Any

import httpx
import pandas as pd
from bs4 import BeautifulSoup

from scps.scraper import column_text_replace

logger = logging.getLogger("scps.demographics")

DEMO_BASE_URL = "https://statecancerprofiles.cancer.gov/demographics/index.php"
DEMO_DEFINES_URL = (
    "https://statecancerprofiles.cancer.gov/demographics/censusJSDefines.js"
)

_PLACEHOLDER_VALUES = {"*", "**", "***", "****", "*****"}

# Matches lines like:  ed_array['00004']="Less than 9th grade";
#                       population_ages_array['00002'] = "Ages under 18";
# Backreferenced quotes (\2 and \4) so apostrophes inside double-quoted
# labels (e.g. "bachelor's degree") aren't treated as terminators.
_DEMO_LINE_RE = re.compile(
    r"""^\s*(?P<array>[a-z_]+_array)\[(['"])(?P<id>[^'"]+)\2\]\s*=\s*"""
    r"""(['"])(?P<label>.*?)\4\s*;""",
    re.MULTILINE,
)


# Matches /* ... */ block comments (non-greedy, multi-line).
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)

# Arrays in the JS file that look like topic definitions but aren't —
# they're the picker-label lookups, not demo-id mappings.
_NON_TOPIC_ARRAYS = {"topic_box"}


def parse_census_defines(js_text: str) -> dict[str, dict[str, str]]:
    """Parse ``censusJSDefines.js`` into ``{topic: {demo_id: label}}``.

    The ``pop`` topic is a special case: its ids live in two sibling arrays
    (``population_ages_array``, ``population_races_array``) that are
    re-exported by ``pop_array['Ages']`` / ``pop_array['Races']`` at runtime.
    We merge both into the ``pop`` mapping here.
    """
    # Strip block comments first so commented-out array definitions
    # (e.g. ur_array) don't get parsed as live topics.
    js_text = _BLOCK_COMMENT_RE.sub("", js_text)

    flat: dict[str, dict[str, str]] = {}
    for raw_line in js_text.splitlines():
        if raw_line.lstrip().startswith("//"):
            continue
        match = _DEMO_LINE_RE.match(raw_line)
        if not match:
            continue
        array = match.group("array")
        demo_id = match.group("id")
        if demo_id in _PLACEHOLDER_VALUES:
            continue
        flat.setdefault(array, {})[demo_id] = match.group("label")

    result: dict[str, dict[str, str]] = {}
    for array_name, mapping in flat.items():
        if not array_name.endswith("_array"):
            continue
        topic = array_name[: -len("_array")]
        if topic.startswith("population_") or topic in _NON_TOPIC_ARRAYS:
            # Folded into pop_array below, or not a real topic.
            continue
        result[topic] = dict(mapping)

    pop_merged: dict[str, str] = {}
    pop_merged.update(flat.get("population_ages_array", {}))
    pop_merged.update(flat.get("population_races_array", {}))
    if pop_merged:
        result["pop"] = pop_merged

    return result


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


def get_demographics_options() -> dict[str, Any]:
    """Discover demographics select options from the live website."""
    html = httpx.get(DEMO_BASE_URL).text
    select_opts = _parse_select_options(html)

    js_text = httpx.get(DEMO_DEFINES_URL).text
    demo_by_topic = parse_census_defines(js_text)

    return {
        "topic": select_opts.get("topic", {}),
        "demo_by_topic": demo_by_topic,
        "areatype": select_opts.get("areatype", {}),
        "race": select_opts.get("race", {}),
        "sex": select_opts.get("sex", {}),
        "age": select_opts.get("age", {}),
        "statefips": select_opts.get("statefips", {}),
    }


def _label(options: dict[str, str], key: str) -> str:
    return options.get(key, key)


def get_demographics_table(
    topic: str,
    demo: str,
    areatype: str = "county",
    statefips: str = "00",
    race: str = "00",
    sex: str = "0",
    age: str = "001",
    options: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Fetch a single demographics CSV and return it as a normalized DataFrame.

    Column shape varies by ``areatype``: state/county use ``State``/``County``
    + ``FIPS``, HSA uses ``Health Service Area`` + ``HSA_Code``. We rename
    both to ``reported_locale`` + ``area_code`` so downstream code doesn't
    have to branch.
    """
    url = (
        f"{DEMO_BASE_URL}?statefips={statefips}&areatype={areatype}"
        f"&topic={topic}&demo={demo}&race={race}&sex={sex}&age={age}"
        f"&type=manyareacensus&sortVariableName=value&sortOrder=default&output=1"
    )
    logger.debug(url)

    df = pd.read_csv(
        url,
        skiprows=6,
        low_memory=False,
        na_values=["*", "N/A", " N/A", "N/A ", " N/A "],
        skipinitialspace=True,
        dtype={"FIPS": str, "HSA_Code": str},
    )
    df.columns = [column_text_replace(c) for c in df.columns]

    # Normalize locale column (varies by areatype).
    locale_renames = {
        "state": "reported_locale",
        "county": "reported_locale",
        "health_service_area": "reported_locale",
        "hsa_code": "area_code",
        "fips": "area_code",
    }
    df = df.rename(columns={k: v for k, v in locale_renames.items() if k in df.columns})

    # Rename percent column. The raw-count column name varies with the demo
    # (e.g. "Households (with >1 Person Per Room)" vs "People (Male)") so we
    # don't try to rename it — callers can look it up via demo_label.
    if "value_percent" in df.columns:
        df = df.rename(columns={"value_percent": "percent"})
    if "rank_within_us" in df.columns:
        df = df.rename(columns={"rank_within_us": "rank"})

    opts = options or {}
    df["topic"] = topic
    df["topic_label"] = _label(opts.get("topic", {}), topic)
    df["demo"] = demo
    df["demo_label"] = _label(opts.get("demo_by_topic", {}).get(topic, {}), demo)
    df["areatype"] = _label(opts.get("areatype", {}), areatype)
    df["race"] = _label(opts.get("race", {}), race)
    df["sex"] = _label(opts.get("sex", {}), sex)
    df["age"] = _label(opts.get("age", {}), age)

    df.loc[df["area_code"].isna(), "area_code"] = ""
    df["state_fips"] = df["area_code"].str[:2]
    df["locale_type"] = "other"
    df.loc[df["area_code"].str.startswith("00"), "locale_type"] = "national"
    if areatype == "state":
        df.loc[df["area_code"].str.endswith("000") & ~df["area_code"].str.startswith("00"), "locale_type"] = "state"
    elif areatype == "county":
        df.loc[
            df["area_code"].str.len().eq(5) & ~df["area_code"].str.endswith("000"),
            "locale_type",
        ] = "county"
    elif areatype == "hsa":
        df.loc[~df["area_code"].str.startswith("00"), "locale_type"] = "hsa"

    df["_extracted_at"] = pd.Timestamp.now().isoformat()
    df["url"] = url.replace("&output=1", "")

    if "percent" in df.columns:
        df["percent"] = pd.to_numeric(df["percent"], errors="coerce")

    return df


def iter_demographics_combos(
    options: dict[str, Any],
    areatypes: Iterable[str],
) -> Iterator[dict]:
    """Yield every ``(areatype, topic, demo, race, sex, age)`` combo."""
    topics = options["topic"]
    demo_by_topic = options["demo_by_topic"]
    races = options["race"]
    sexes = options["sex"]
    ages = options["age"]
    for areatype in areatypes:
        for topic_id in topics:
            demos = demo_by_topic.get(topic_id, {})
            if not demos:
                continue
            for demo_id in demos:
                for race_id in races:
                    for sex_id in sexes:
                        for age_id in ages:
                            yield {
                                "topic": topic_id,
                                "demo": demo_id,
                                "areatype": areatype,
                                "race": race_id,
                                "sex": sex_id,
                                "age": age_id,
                            }


def demographics_master_table(
    areatypes: Iterable[str] = ("county", "state"),
    options: dict[str, Any] | None = None,
    combos: Iterable[dict] | None = None,
    on_success: Callable[[dict, int], None] | None = None,
) -> pd.DataFrame:
    """Iterate over every ``(topic, demo, areatype, race, sex, age)`` combo.

    Parameters
    ----------
    areatypes : iterable of str
        Defaults to ``("county", "state")``. The website also supports
        ``"hsa"`` (health service area) but it's omitted by default since
        HSA codes don't slot into FIPS-keyed downstream joins.
    combos : iterable of dict, optional
        Catalog-driven override of the cartesian iteration.
    on_success : callable, optional
        Called as ``on_success(combo, n_rows)`` after each successful fetch.
    """
    opts = options or get_demographics_options()

    if combos is None:
        logger.info(
            "Demographics scrape: %d topics, areatypes=%s",
            len(opts["topic"]), list(areatypes),
        )
        combos = iter_demographics_combos(opts, areatypes)

    dflist: list[pd.DataFrame] = []
    for combo in combos:
        try:
            df = get_demographics_table(options=opts, **combo)
            dflist.append(df)
            if on_success is not None:
                on_success(combo, len(df))
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            logger.debug("Skipped %s: %s", combo, exc)

    if not dflist:
        return pd.DataFrame()
    return pd.concat(dflist, ignore_index=True)
