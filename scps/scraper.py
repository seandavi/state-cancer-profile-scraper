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
        httpx.get(
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


select_opts = get_select_options()


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

    url = (
        f"https://statecancerprofiles.cancer.gov/{url_insert}/index.php?stateFIPS={stateFIPS}"
        f"&areatype={areatype}&cancer={cancer}&race={race}"
        f"&stage={stage}&year={year}"
        f"&sex={sex}&age={age}&type={_type}&output=1"
    )
    logger.debug(url)

    df = pd.read_csv(
        url,
        skiprows=8,
        low_memory=False,
        na_values=["*", "N/A", " N/A", "N/A ", " N/A "],
        skipinitialspace=True,
        dtype={"FIPS": str},
    )
    df.columns = [column_text_replace(c) for c in df.columns]

    def get_text_from_select_id(group, id):
        return select_opts[group][id]

    df["year"] = get_text_from_select_id("year", year)
    df["sex"] = get_text_from_select_id("sex", sex)
    df["stage"] = get_text_from_select_id("stage", stage)
    df["race"] = get_text_from_select_id("race", race)
    df["cancer"] = get_text_from_select_id("cancer", cancer)
    df["areatype"] = get_text_from_select_id("areatype", areatype)
    df["age"] = get_text_from_select_id("age", age)
    df["state_fips"] = df["fips"].str[:2]
    if _type == "incd":
        df["measurement"] = "incidence"
    else:
        df["measurement"] = "mortality"
    df["locale_type"] = "other"
    df.loc[df["fips"].isna(), "fips"] = ""
    df.loc[df["fips"].str.endswith("000"), "locale_type"] = "state"
    df.loc[df["fips"].str.startswith("00"), "locale_type"] = "national"
    df.loc[df["county"].str.contains("County"), "locale_type"] = "county"
    df["_extracted_at"] = pd.Timestamp.now().isoformat()
    # to allow for easy linkout to the website
    df["url"] = url.replace("&output=1", "")
    for numeric_column in [
        rate_col,
        "lower_95pct_confidence_interval",
        "upper_95pct_confidence_interval",
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
    return df[df[rate_col].notna()]


# This function uses argparse to collect the command line arguments
# and then calls get_table() with those arguments.
# use last five years of data (year=0), all states (stateFIPS=00)
def master_table(year: str = "0", stateFIPS="00", _type="incd"):
    select_options = get_select_options()
    logger.info(str(select_options))
    dflist = []
    cancers = list(select_options["cancer"].keys())
    logger.info(f"Number of cancers: {len(cancers)}")
    for cancer in list(select_options["cancer"].keys()):
        cancer_name = select_options["cancer"][cancer]
        logger.info(f"Getting data for cancer: {cancer_name}")

        # The state cancer profiles folks in their
        # decided to make the age
        # groups for cancer 515 and 516 (pediatrics) different
        # than the other cancers. So we have to
        # handle them separately.
        if cancer == "516":
            ages = ["016"]
        elif cancer == "515":
            ages = ["015"]
        else:
            ages = select_options["age"].keys()
        for age in ages:
            for sex in select_options["sex"].keys():
                for race in select_options["race"].keys():
                    for stage in select_options["stage"].keys():
                        try:
                            df = get_table(
                                cancer=cancer,
                                age=age,
                                sex=sex,
                                race=race,
                                stage=stage,
                                _type=_type,
                            )
                            logger.debug(
                                f"Got data for {cancer_name}, shape {df.shape}"
                            )
                            dflist.append(df)
                        except KeyboardInterrupt:
                            raise
                        except Exception as e:
                            logger.debug("Caught an exception, but ignoring it")
                            logger.debug(e)
                            pass
    df = pd.concat(dflist)
    df[["locale", "state"]] = df.county.str.replace(
        r"\(.*\)", "", regex=True
    ).str.split(", ", expand=True, n=1)
    if _type == "incd":
        column_translation = {
            "lower_95pct_confidence_interval_1": "lower_ci_trend_in_rate",
            "upper_95pct_confidence_interval_1": "upper_ci_trend_in_rate",
            "county": "reported_locale",
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
            "county": "reported_locale",
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
    return df


def main():
    import json

    logger.info("Getting select options")
    json.dump(get_select_options(), open("select_options.json", "w"))

    logger.info("Getting incidence data")
    df = master_table(_type="incd")
    logger.info("Saving incidence data with shape: %s", str(df.shape))
    df.to_csv("state_cancer_profiles_incidence.csv.gz", index=False, compression="gzip")
    logger.info("Getting death data")
    df = master_table(_type="death")
    logger.info("Saving mortality data with shape: %s", str(df.shape))
    df.to_csv("state_cancer_profiles_mortality.csv.gz", index=False, compression="gzip")


if __name__ == "__main__":
    print(main())
