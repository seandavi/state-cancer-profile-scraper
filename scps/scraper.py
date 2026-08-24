"""This script scrapes the state cancer profiles website
and saves the results as csv files.

The website is not designed as an API, so this script does
some nasty html scraping that makes it somewhat fragile.
It requires scraping the select options from the website
and then iterating over all the possible combinations of
select options to get the data.

The script is designed to be run from the command line
with the following command:

```
python scrape_statecancerprofiles.py
```

The script will create two csv files, one for incidence
and one for death. Each of these files is about 700k lines.

The script will also print out the url for each request
it makes. Note that the script will make a lot of requests
and take a long time to run (about 30 minutes or so, depending
on bandwidth). We use a messy try-except block a lot
because the website is not very robust and some of the
options are not valid for some of the other options.

"""

import csv
import functools
import re
import io
from collections.abc import Callable, Iterable, Iterator

import httpx
import pandas as pd
from bs4 import BeautifulSoup
import logging

logging.getLogger("httpx").setLevel(logging.WARNING)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scps.scraper")


def get_select_options() -> dict:
    """Get the select options from the state cancer profiles website"""
    soup = BeautifulSoup(
        get_with_retry(
            "https://statecancerprofiles.cancer.gov/incidencerates/index.php"
        ).text,
        "html.parser",
    )
    select_dict = {}
    for s in soup.find_all("select"):
        option_dict = {}
        field = s.attrs.get("id")  # age, stage, ....
        for o in s.find_all("option"):
            txt = o.get_text()
            if not txt.startswith("---"):
                option_dict[o.attrs.get("value")] = o.get_text()
        if field == "age":
            # website is missing some age groups
            # since the developers tried to be clever
            # with javascript, apparently.

            # This is a hack to add the missing age groups
            # to the select options for pediatrics.
            option_dict["016"] = "Age < 15"
            option_dict["015"] = "Age < 20"
        select_dict[s.attrs.get("id")] = option_dict
    return select_dict


def column_text_replace(txt: str) -> str:
    """Replace text in column names to make them more pythonic."""
    return (
        txt.strip()
        .replace("[", "")
        .replace("]", "")
        .replace("(", "")
        .replace(")", "")
        .replace("*", "_")
        .replace(" ", "_")
        .replace("%", "pct")
        .replace("-", "_")
        .replace(",", "_")
        .replace(".", "_")
        .replace("?", "")
        .lower()
    )


@functools.lru_cache(maxsize=1)
def select_options() -> dict:
    """Cached select-option vocabulary, fetched on first use.

    Importing this module must not perform network I/O (#37); anything that
    needs the vocabulary calls this instead of a module-level constant.
    """
    return get_select_options()


# "*" is deliberately NOT treated as NA at read time: it marks a suppressed
# cell and is decoded into `suppression_reason` before numeric coercion (#35).
NA_VALUES = ["N/A", " N/A", "N/A ", " N/A "]

# Every SCP export names its area-code column one of these; the header line
# is located by content, not by a fixed offset (#36).
_KEY_FIELDS = {"FIPS", "HSA_Code"}


_DEFINES_SRC_RE = re.compile(r'src="([^"]*[Dd]efines\.js[^"]*)"')
_CONST_BLOCK_RE = re.compile(r"const\s+(\w+)\s*=\s*\[(.*?)\];", re.S)
_PAIR_RE = re.compile(r'\[\s*"([^"]+)"\s*,\s*"([^"]*)"\s*\]')

SCP_HOST = "https://statecancerprofiles.cancer.gov"


def find_defines_url(html: str, host: str = SCP_HOST) -> str:
    """Locate the topic-defines script referenced by a page.

    Upstream renamed riskJSDefines.js -> /j/riskDefines.js (and the
    demographics equivalent) in a 2026-08 front-end refresh; discovering
    the URL from the page's own script tag survives the next rename.
    """
    m = _DEFINES_SRC_RE.search(html)
    if m is None:
        raise ValueError("no *Defines.js script tag found in page")
    src = m.group(1)
    return src if src.startswith("http") else host + src


def parse_defines(js_text: str, prefix: str) -> dict[str, dict[str, str]]:
    """Parse 2026-08-format defines: ``const <prefix><topic> = [["id","label"], ...]``.

    Unquoted first elements (OPTION_GROUP_START markers) and ``*_arrays``
    lookup tables are skipped; ``//`` line comments are ignored.
    """
    js_text = "\n".join(
        line for line in js_text.splitlines()
        if not line.lstrip().startswith("//")
    )
    out: dict[str, dict[str, str]] = {}
    for name, body in _CONST_BLOCK_RE.findall(js_text):
        if not name.startswith(prefix) or name.endswith("_arrays"):
            continue
        entries = {i: label for i, label in _PAIR_RE.findall(body)}
        if entries:
            out[name[len(prefix):]] = entries
    return out


def get_with_retry(url: str, attempts: int = 5) -> httpx.Response:
    """GET with exponential backoff on transient network/server errors.

    Long scrapes hit transient ConnectErrors and 5xx from the upstream CDN
    (#47); one blip must not kill a multi-hour run.
    """
    import time

    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            resp = httpx.get(url, timeout=60.0)
            if resp.status_code >= 500:
                raise httpx.HTTPStatusError(
                    f"server error {resp.status_code}", request=resp.request, response=resp
                )
            resp.raise_for_status()
            return resp
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                raise
            last_exc = exc
            wait = 2**attempt
            logger.warning("GET %s failed (%s); retry %d/%d in %ss",
                           url[:80], exc, attempt + 1, attempts, wait)
            time.sleep(wait)
    raise last_exc


def fetch_report(url: str) -> str:
    """GET one SCP CSV export and return the raw text."""
    return get_with_retry(url).text


def split_report(text: str) -> tuple[str, str]:
    """Split a raw SCP export into ``(data_csv, notes)``.

    The payload is a report: a title block, the CSV data block, then
    footnotes. The data block is located by finding the header line by
    content (it contains a FIPS/HSA_Code field) and reading until the next
    blank line — upstream can grow or shrink the title block without
    breaking us, which is what killed cancerprof's fixed-offset parser.
    ``notes`` is the title block plus the footnotes, verbatim: it carries
    the "Created by statecancerprofiles.cancer.gov on DATE" vintage string,
    the submission year, and the suppression-rule definitions.
    """
    lines = text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if "FIPS" not in line and "HSA_Code" not in line:
            continue
        fields = next(csv.reader([line]), [])
        if any(f.strip() in _KEY_FIELDS for f in fields):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("no data-block header line found in SCP payload")
    end = header_idx + 1
    while end < len(lines) and lines[end].strip():
        end += 1
    data_csv = "\n".join(lines[header_idx:end])
    notes = "\n".join(lines[:header_idx] + lines[end:]).strip()
    return data_csv, notes


def decode_suppression(raw: "pd.Series") -> "pd.Series":
    """Map raw value-column strings to a suppression-reason column.

    SCP marks small-count suppression with ``*`` and state-law withholding
    (Kansas counties) with ``[P1 note]``. Everything else → <NA>.
    """
    stripped = raw.astype("string").str.strip()
    reason = pd.Series(pd.NA, index=raw.index, dtype="string")
    reason[stripped == "*"] = "suppressed_small_count"
    reason[stripped.str.startswith("[P1", na=False)] = "withheld_state_law"
    return reason


def get_table(
    year: str = "0",
    stateFIPS: str = "00",  # 00 includes all states
    sex: str = "0",
    stage: str = "999",
    race: str = "00",
    cancer: str = "001",
    areatype: str = "county",
    age: str = "001",
    _type: str = "incd",
) -> pd.DataFrame:
    if _type == "incd":
        rate_col = "age_adjusted_incidence_raterate_note___cases_per_100_000"
        url_insert = "incidencerates"
    else:
        rate_col = "age_adjusted_death_raterate_note___deaths_per_100_000"
        url_insert = "deathrates"

    # stage is not a deathrates dimension — the site ignores the parameter
    # and returns byte-identical payloads (#43). Never send it for mortality.
    stage_param = "" if _type == "death" else f"&stage={stage}"
    url = (
        f"https://statecancerprofiles.cancer.gov/{url_insert}/index.php?stateFIPS={stateFIPS}"
        f"&areatype={areatype}&cancer={cancer}&race={race}"
        f"{stage_param}&year={year}"
        f"&sex={sex}&age={age}&type={_type}&output=1"
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

    # Upstream uses different locale-column headers per areatype: "County"
    # for by-county, "State" for by-state. Normalize to `reported_locale`
    # here so downstream code (and the later locale_type derivation) doesn't
    # KeyError on whichever flavor it didn't expect. Pre-fix, the by-state
    # branch raised and the master_table try/except swallowed every state
    # combo silently — see #11 follow-up.
    if "county" in df.columns:
        df = df.rename(columns={"county": "reported_locale"})
    elif "state" in df.columns:
        df = df.rename(columns={"state": "reported_locale"})

    def get_text_from_select_id(group, id):
        return select_options()[group][id]

    df["year"] = get_text_from_select_id("year", year)
    df["sex"] = get_text_from_select_id("sex", sex)
    if _type != "death":
        df["stage"] = get_text_from_select_id("stage", stage)
    df["race"] = get_text_from_select_id("race", race)
    df["cancer"] = get_text_from_select_id("cancer", cancer)
    df["areatype"] = get_text_from_select_id("areatype", areatype)
    df["age"] = get_text_from_select_id("age", age)
    df.loc[df["fips"].isna(), "fips"] = ""
    df["state_fips"] = df["fips"].str[:2]
    if _type == "incd":
        df["measurement"] = "incidence"
    else:
        df["measurement"] = "mortality"
    # locale_type derivation. The request `areatype` tells us which view of
    # the data the row came from, which is the source of truth for whether a
    # row is state-level or county-level. FIPS shape alone would mis-label
    # corner cases — DC (11001), Puerto Rico (72001), and the Alaska
    # aggregate (02900) come back from the by-state view with 5-char FIPS
    # that don't end in 000. So:
    #   - any row whose FIPS starts with "00" is the national aggregate;
    #   - otherwise the request areatype dictates state vs county.
    # For county-areatype runs, FIPS-shape still distinguishes the embedded
    # state-aggregate row (e.g. 06000) when one shows up.
    df["locale_type"] = "other"
    is_5char = df["fips"].str.len().eq(5)
    is_national = is_5char & df["fips"].str.startswith("00")
    df.loc[is_national, "locale_type"] = "national"
    if areatype == "state":
        df.loc[is_5char & ~is_national, "locale_type"] = "state"
    elif areatype == "county":
        df.loc[
            is_5char & ~is_national & df["fips"].str.endswith("000"),
            "locale_type",
        ] = "state"
        df.loc[
            is_5char & ~is_national & ~df["fips"].str.endswith("000"),
            "locale_type",
        ] = "county"
    df["_extracted_at"] = pd.Timestamp.now().isoformat()
    # to allow for easy linkout to the website
    df["url"] = url.replace("&output=1", "")
    df["suppression_reason"] = decode_suppression(df[rate_col])
    for numeric_column in [
        rate_col,
        "lower_95pct_confidence_interval",
        "upper_95pct_confidence_interval",
        "ci_rankrank_note",
        "lower_ci_ci_rank",
        "upper_ci_ci_rank",
        "average_annual_count",
        "recent_5_year_trend_trend_note_in_incidence_rates",
        "lower_95pct_confidence_interval_1",
        "upper_95pct_confidence_interval_1",
    ]:
        try:
            df[numeric_column] = pd.to_numeric(df[numeric_column], errors="coerce")
        except Exception as e:
            logger.debug("Caught an expected exception, so ignoring")
            logger.debug(e)
            pass
    # Keep suppressed rows (typed-null rate + reason); drop only rows that
    # are neither numeric nor suppressed — the "N/A" not-available cases the
    # old rate-notna filter existed for.
    df = df[df[rate_col].notna() | df["suppression_reason"].notna()]
    df.attrs["scp_notes"] = notes
    return df


def iter_incidence_combos(
    select_options: dict,
    areatypes: Iterable[str],
) -> Iterator[dict]:
    """Yield every ``(cancer × age × sex × race × stage × areatype)`` combo.

    Pediatric cancers 515 and 516 use restricted age ranges per the
    upstream site's javascript; that constraint is encoded here.
    """
    cancers = list(select_options["cancer"].keys())
    for areatype in areatypes:
        for cancer in cancers:
            if cancer == "516":
                ages: Iterable[str] = ["016"]
            elif cancer == "515":
                ages = ["015"]
            else:
                ages = list(select_options["age"].keys())
            for age in ages:
                for sex in select_options["sex"].keys():
                    for race in select_options["race"].keys():
                        for stage in select_options["stage"].keys():
                            yield {
                                "cancer": cancer,
                                "age": age,
                                "sex": sex,
                                "race": race,
                                "stage": stage,
                                "areatype": areatype,
                            }


def _dedupe_death_combos(combos: Iterable[dict]) -> Iterator[dict]:
    """Strip the stage dimension from mortality combos and dedupe.

    stage is not a deathrates dimension (#43); iterating it doubled every
    mortality request and mislabelled half the table as late-stage.
    """
    seen: set = set()
    for combo in combos:
        combo = {k: v for k, v in combo.items() if k != "stage"}
        key = tuple(sorted(combo.items()))
        if key not in seen:
            seen.add(key)
            yield combo


def parallel_fetch(combos, fetch_one, on_success=None, workers=None):
    """Fetch combos concurrently; yield (combo, df) in combo order.

    Bounded thread-pool concurrency so a full scrape fits inside CI's
    6-hour job limit (#45) while staying polite to the upstream site.
    Failures come back as (combo, None) — same swallow-invalid-combos
    semantics as the old sequential loop. Results are yielded in input
    order and the caller invokes ``on_success`` on its own thread, so
    catalog recording needs no locking.
    """
    import os
    from concurrent.futures import ThreadPoolExecutor

    if workers is None:
        workers = int(os.environ.get("SCPS_WORKERS", "6"))

    def _fetch(combo):
        try:
            return combo, fetch_one(combo)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            logger.debug("Skipped %s: %s", combo, exc)
            return combo, None

    failures = 0
    total = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for combo, df in pool.map(_fetch, combos):
            total += 1
            if df is None:
                failures += 1
                continue
            if on_success is not None:
                on_success(combo, len(df))
            yield combo, df
    if failures:
        logger.warning(
            "parallel_fetch: %d/%d combos returned no data "
            "(invalid combos in discovery mode are normal; in catalog-driven "
            "mode this is data loss and the regression check will fail).",
            failures, total,
        )


def master_table(
    year: str = "0",
    stateFIPS: str = "00",
    _type: str = "incd",
    areatypes: Iterable[str] = ("county",),
    combos: Iterable[dict] | None = None,
    on_success: Callable[[dict, int], None] | None = None,
):
    """Scrape every (cancer × age × sex × race × stage × areatype) combination.

    Parameters
    ----------
    areatypes : iterable of str
        Areatypes to iterate when ``combos`` is not provided. The website
        supports ``"county"``, ``"state"``, and ``"hsa"`` (health service
        area). Defaults to ``("county",)`` for backward compatibility.
    combos : iterable of dict, optional
        If provided, supersedes the cartesian iteration — typically used by
        the catalog to limit the run to known-good combos. Each dict's keys
        become ``get_table`` kwargs.
    on_success : callable, optional
        Called as ``on_success(combo, n_rows)`` after every successful
        fetch. The catalog uses this to record discoveries incrementally.
    """
    if combos is None:
        select_options = get_select_options()
        cancers = list(select_options["cancer"].keys())
        logger.info(f"Number of cancers: {len(cancers)}")
        combos = iter_incidence_combos(select_options, areatypes)

    if _type == "death":
        combos = _dedupe_death_combos(combos)

    dflist = [
        df
        for _combo, df in parallel_fetch(
            combos, lambda c: get_table(_type=_type, **c), on_success
        )
    ]
    # concat() drops .attrs; carry the first fetch's notes block forward so
    # the CLI can persist it (vintage string lives there — see #36).
    notes = next(
        (d.attrs["scp_notes"] for d in dflist if d.attrs.get("scp_notes")), None
    )
    df = pd.concat(dflist)
    # Split "Galax City, Virginia(2)" → ("Galax City", "Virginia") for county
    # rows. State-level rows have no comma (e.g. "California") and split into
    # ("California", None), which is the right shape.
    df[["locale", "state"]] = df.reported_locale.str.replace(
        r"\(.*\)", "", regex=True
    ).str.split(", ", expand=True, n=1)
    if _type == "incd":
        column_translation = {
            "lower_95pct_confidence_interval_1": "lower_ci_trend_in_rate",
            "upper_95pct_confidence_interval_1": "upper_ci_trend_in_rate",
            "age_adjusted_incidence_raterate_note___cases_per_100_000": "age_adjusted_rate_per_100_000",
            "ci_rankrank_note": "ci_rank",
            "lower_ci_ci_rank": "lower_ci_rank",
            "upper_ci_ci_rank": "upper_ci_rank",
            "recent_5_year_trend_trend_note_in_incidence_rates": "recent_5_year_trend_in_rate",
            "lower_95pct_confidence_interval": "lower_ci_rate",
            "upper_95pct_confidence_interval": "upper_ci_rate",
        }
    if _type == "death":
        column_translation = {
            "age_adjusted_death_raterate_note___deaths_per_100_000": "age_adjusted_rate_per_100_000",
            "ci_rankrank_note": "ci_rank",
            "lower_ci_ci_rank": "lower_ci_rank",
            "upper_ci_ci_rank": "upper_ci_rank",
            "recent_5_year_trend_trend_note_in_death_rates": "recent_5_year_trend_in_rate",
            "lower_95pct_confidence_interval": "lower_ci_trend_in_rate",
            "upper_95pct_confidence_interval": "upper_ci_trend_in_rate",
        }
    df.rename(
        columns=column_translation,
        inplace=True,
    )
    df = df.loc[:, ~df.columns.str.startswith("met_")]
    if notes:
        df.attrs["scp_notes"] = notes
    return df


def main():
    """Run the full scrape (incidence, mortality, risk, demographics).

    Kept as a thin wrapper around the click CLI so that
    ``python -m scps.scraper`` and ``scps-scraper scrape`` produce the same
    output set.
    """
    from scps.cli import cli

    cli(args=["scrape"], standalone_mode=False)


if __name__ == "__main__":
    main()
