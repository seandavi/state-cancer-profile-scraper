## State cancer profiles scraper

[![](https://img.shields.io/github/v/release/seandavi/state-cancer-profile-scraper)](https://github.com/seandavi/state-cancer-profile-scraper/release/latest)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/seandavi/state-cancer-profile-scraper/total)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/seandavi/state-cancer-profile-scraper/.github%2Fworkflows%2Frun-scrape.yaml?label=Scrape%20status)
[![codecov](https://codecov.io/gh/seandavi/state-cancer-profile-scraper/branch/main/graph/badge.svg)](https://codecov.io/gh/seandavi/state-cancer-profile-scraper)
[![DOI](https://zenodo.org/badge/794255451.svg)](https://doi.org/10.5281/zenodo.13174526)


The [state cancer profiles website](https://statecancerprofiles.cancer.gov/) hosts visualization and data exploration tools for cancer incidence and mortality in the United States. For casual browsing, the website is great. However, if having access to the underlying data is the goal, the existing site does not have bulk downloads or an API. Therefore, **we provide bulk data scraped from the website for data science applications**. 

For the TLDR, the data for _incidence_ and _mortality_ are available for download from:

- <https://github.com/seandavi/state-cancer-profile-scraper/releases/latest>

A new release is **generated every month with the latest data**. 

## Contents

- [State cancer profiles scraper](#state-cancer-profiles-scraper)
- [Contents](#contents)
- [About the code](#about-the-code)
- [About the data](#about-the-data)
- [Using the data](#using-the-data)
  - [Download the data](#download-the-data)
  - [Data access in place](#data-access-in-place)
- [Example rows from the data](#example-rows-from-the-data)
  - [Incidence data](#incidence-data)
  - [Mortality data](#mortality-data)
- [Local scraper usage](#local-scraper-usage)
  - [Running the scraper](#running-the-scraper)
- [License](#license)
- [Contributing](#contributing)

## About the code

This is a simple web scraper that extracts cancer data from the [State Cancer Profiles](https://statecancerprofiles.cancer.gov/) website. The data is extracted for all states and saved in two CSV files: one for cancer incidence and one for cancer mortality.

## About the data

The data is extracted from the [State Cancer Profiles](https://statecancerprofiles.cancer.gov/) website, which is a part of the [National Cancer Institute](https://www.cancer.gov/). The website provides cancer statistics for all 50 states, the District of Columbia, and Puerto Rico. The data is available for cancer incidence and cancer mortality, and it is based on the [SEER](https://seer.cancer.gov/) and [NPCR](https://www.cdc.gov/cancer/npcr/index.htm) programs.

## Using the data

The data is saved in two CSV files: one for cancer incidence and one for cancer mortality. The data is saved in a long format, with each row representing a single observation (i.e., a single cancer type in a single state in a single year). 

### Download the data

The data are available for download from the [releases](https://github.com/seandavi/state-cancer-profile-scraper/releases) page, with a link to the latest release [here](https://github.com/seandavi/state-cancer-profile-scraper/releases/latest).

Note that R, python, and many other languages can read CSV files directly without the need for downloading the data which might a fast and easy way to access the data. 

### Data access in place

For those who simply want to query the data in place, both [duckdb](https://duckdb.org/) and [clickhouse](https://clickhouse.tech/) databases can query csv files directly.  For example, using duckdb, you can run the following code to query the data:

```
install httpfs;
load
select 
  * 
from 
read_csv('https://github.com/seandavi/state-cancer-profile-scraper/releases/download/2025-02-10/state_cancer_profiles_incidence.csv.gz') 
limit 10;
```

Or, using [clickhouse-local](https://clickhouse.com/blog/extracting-converting-querying-local-files-with-sql-clickhouse-local#working-with-files-over-http-and-s3), start up clickhouse local and run the following query:

```
select 
  * 
from url('https://github.com/seandavi/state-cancer-profile-scraper/releases/download/2025-02-10/state_cancer_profiles_incidence.csv.gz') 
limit 10 
settings max_http_get_redirects = 10;
```

## Example rows from the data

### Incidence data

| reported_locale | fips | 2023_rural_urban_continuum_codesrural_urban_note | age_adjusted_rate_per_100_000 | lower_ci_rate | upper_ci_rate | ci_rank | lower_ci_rank | upper_ci_rank | average_annual_count | recent_trend | recent_5_year_trend_in_rate | lower_ci_trend_in_rate | upper_ci_trend_in_rate | year | sex | stage | race | cancer | areatype | age | state_fips | measurement | locale_type | _extracted_at | url | percent_of_cases_with_late_stage | locale | state |
|:-|-:|:-|-:|-:|-:|:-|:-|:-|-:|:-|-:|-:|-:|:-|:-|:-|:-|:-|:-|:-|-:|:-|:-|-:|:-|:-|:-|:-|
| Harrison County, Kentucky(7) | 21097 | Rural | 601.1 | 537.6 | 670.6 | \N | \N | \N | 71 | stable | -0.6000000000000001 | -1.7000000000000002 | 0.5 | Latest 5-year average | Male | All Stages | All Races (includes Hispanic) | All Cancer Sites | By County | All Ages | 21 | incidence | county | 2025-02-10 19:36:38.120091000 | https://statecancerprofiles.cancer.gov/incidencerates/index.php?stateFIPS=00&areatype=county&cancer=001&race=00&stage=999&year=0&sex=1&age=001&type=incd | \N | Harrison County | Kentucky |
| Metcalfe County, Kentucky(7) | 21169 | Rural | 601 | 519 | 693.4 | \N | \N | \N | 41 | stable | -0.1 | -1.4 | 1.2 | Latest 5-year average | Male | All Stages | All Races (includes Hispanic) | All Cancer Sites | By County | All Ages | 21 | incidence | county | 2025-02-10 19:36:38.120091000 | https://statecancerprofiles.cancer.gov/incidencerates/index.php?stateFIPS=00&areatype=county&cancer=001&race=00&stage=999&year=0&sex=1&age=001&type=incd | \N | Metcalfe County | Kentucky |
| Lumpkin County, Georgia(7) | 13187 | Urban | 600.1 | 550.7 | 653.2 | \N | \N | \N | 121 | stable | -0.2 | -1.4 | 1.2 | Latest 5-year average | Male | All Stages | All Races (includes Hispanic) | All Cancer Sites | By County | All Ages | 13 | incidence | county | 2025-02-10 19:36:38.120091000 | https://statecancerprofiles.cancer.gov/incidencerates/index.php?stateFIPS=00&areatype=county&cancer=001&race=00&stage=999&year=0&sex=1&age=001&type=incd | \N | Lumpkin County | Georgia |
| Boyd County, Kentucky(7) | 21019 | Urban | 600.1 | 561.7 | 640.7 | \N | \N | \N | 192 | stable | 0.1 | -0.5 | 1.7000000000000002 | Latest 5-year average | Male | All Stages | All Races (includes Hispanic) | All Cancer Sites | By County | All Ages | 21 | incidence | county | 2025-02-10 19:36:38.120091000 | https://statecancerprofiles.cancer.gov/incidencerates/index.php?stateFIPS=00&areatype=county&cancer=001&race=00&stage=999&year=0&sex=1&age=001&type=incd | \N | Boyd County | Kentucky |
| Greene County, Illinois(7) | 17061 | Rural | 599.8 | 525.6 | 682.5 | \N | \N | \N | 50 | stable | -0.4 | -1.7000000000000002 | 0.9 | Latest 5-year average | Male | All Stages | All Races (includes Hispanic) | All Cancer Sites | By County | All Ages | 17 | incidence | county | 2025-02-10 19:36:38.120091000 | https://statecancerprofiles.cancer.gov/incidencerates/index.php?stateFIPS=00&areatype=county&cancer=001&race=00&stage=999&year=0&sex=1&age=001&type=incd | \N | Greene County | Illinois |
| Washington County, Maine(6) | 23029 | Rural | 599.3 | 554.3 | 647.6 | \N | \N | \N | 152 | stable | 5.4 | -0.6000000000000001 | 9.6 | Latest 5-year average | Male | All Stages | All Races (includes Hispanic) | All Cancer Sites | By County | All Ages | 23 | incidence | county | 2025-02-10 19:36:38.120091000 | https://statecancerprofiles.cancer.gov/incidencerates/index.php?stateFIPS=00&areatype=county&cancer=001&race=00&stage=999&year=0&sex=1&age=001&type=incd | \N | Washington County | Maine |
| Jones County, North Carolina(6) | 37103 | Rural | 599 | 516.3 | 692.9 | \N | \N | \N | 43 | stable | -0.8 | -2.8 | 1.2 | Latest 5-year average | Male | All Stages | All Races (includes Hispanic) | All Cancer Sites | By County | All Ages | 37 | incidence | county | 2025-02-10 19:36:38.120091000 | https://statecancerprofiles.cancer.gov/incidencerates/index.php?stateFIPS=00&areatype=county&cancer=001&race=00&stage=999&year=0&sex=1&age=001&type=incd | \N | Jones County | North Carolina |
| Butler County, Kentucky(7) | 21031 | Urban | 598.8 | 522.9 | 683.2 | \N | \N | \N | 49 | stable | -0.7000000000000001 | -2.5 | 1.1 | Latest 5-year average | Male | All Stages | All Races (includes Hispanic) | All Cancer Sites | By County | All Ages | 21 | incidence | county | 2025-02-10 19:36:38.120091000 | https://statecancerprofiles.cancer.gov/incidencerates/index.php?stateFIPS=00&areatype=county&cancer=001&race=00&stage=999&year=0&sex=1&age=001&type=incd | \N | Butler County | Kentucky |
| Rolette County, North Dakota(6) | 38079 | Rural | 598.7 | 509 | 699.4 | \N | \N | \N | 35 | stable | 0.30000000000000004 | -1.6 | 2.2 | Latest 5-year average | Male | All Stages | All Races (includes Hispanic) | All Cancer Sites | By County | All Ages | 38 | incidence | county | 2025-02-10 19:36:38.120091000 | https://statecancerprofiles.cancer.gov/incidencerates/index.php?stateFIPS=00&areatype=county&cancer=001&race=00&stage=999&year=0&sex=1&age=001&type=incd | \N | Rolette County | North Dakota |
| Kalkaska County, Michigan(6) | 26079 | Urban | 598.7 | 536.1 | 667.2 | \N | \N | \N | 77 | stable | -0.4 | -2 | 1.2 | Latest 5-year average | Male | All Stages | All Races (includes Hispanic) | All Cancer Sites | By County | All Ages | 26 | incidence | county | 2025-02-10 19:36:38.120091000 | https://statecancerprofiles.cancer.gov/incidencerates/index.php?stateFIPS=00&areatype=county&cancer=001&race=00&stage=999&year=0&sex=1&age=001&type=incd | \N | Kalkaska County | Michigan |

### Mortality data

| reported_locale | fips | 2023_rural_urban_continuum_codesrural_urban_note | age_adjusted_rate_per_100_000 | lower_ci_rate | upper_ci_rate | ci_rank | lower_ci_rank | upper_ci_rank | average_annual_count | recent_trend | recent_5_year_trend_in_rate | lower_ci_trend_in_rate | upper_ci_trend_in_rate | year | sex | stage | race | cancer | areatype | age | state_fips | measurement | locale_type | _extracted_at | url | locale | state |
|:-|-:|:-|-:|-:|-:|:-|-:|-:|-:|:-|-:|-:|-:|:-|:-|:-|:-|:-|:-|:-|-:|:-|:-|-:|:-|:-|:-|
| Greenwood County, Kansas | 20073 | Rural | 182 | 144.9 | 228.2 | \N | 3 | 96 | 19 | stable | -0.9 | -1.9 | 0 | Latest 5-year average | Both Sexes | Late Stage (Regional & Distant) | White (Non-Hispanic) | All Cancer Sites | By County | All Ages | 20 | mortality | county | 2025-02-10 19:58:25.293785000 | https://statecancerprofiles.cancer.gov/deathrates/index.php?stateFIPS=00&areatype=county&cancer=001&race=07&stage=211&year=0&sex=0&age=001&type=death | Greenwood County | Kansas |
| Geneva County, Alabama | 1061 | Urban | 182 | 162.1 | 204 | \N | 2 | 54 | 64 | stable | -0.4 | -1.1 | 0.30000000000000004 | Latest 5-year average | Both Sexes | Late Stage (Regional & Distant) | White (Non-Hispanic) | All Cancer Sites | By County | All Ages | 1 | mortality | county | 2025-02-10 19:58:25.293785000 | https://statecancerprofiles.cancer.gov/deathrates/index.php?stateFIPS=00&areatype=county&cancer=001&race=07&stage=211&year=0&sex=0&age=001&type=death | Geneva County | Alabama |
| Robertson County, Texas | 48395 | Urban | 182 | 152.5 | 216.6 | \N | 13 | 204 | 31 | falling | -0.9 | -1.7000000000000002 | -0.2 | Latest 5-year average | Both Sexes | Late Stage (Regional & Distant) | White (Non-Hispanic) | All Cancer Sites | By County | All Ages | 48 | mortality | county | 2025-02-10 19:58:25.293785000 | https://statecancerprofiles.cancer.gov/deathrates/index.php?stateFIPS=00&areatype=county&cancer=001&race=07&stage=211&year=0&sex=0&age=001&type=death | Robertson County | Texas |
| Van Buren County, Arkansas | 5141 | Rural | 182 | 159.5 | 207.6 | \N | 8 | 73 | 51 | falling | -0.7000000000000001 | -1.2 | -0.1 | Latest 5-year average | Both Sexes | Late Stage (Regional & Distant) | White (Non-Hispanic) | All Cancer Sites | By County | All Ages | 5 | mortality | county | 2025-02-10 19:58:25.293785000 | https://statecancerprofiles.cancer.gov/deathrates/index.php?stateFIPS=00&areatype=county&cancer=001&race=07&stage=211&year=0&sex=0&age=001&type=death | Van Buren County | Arkansas |
| Perry County, Missouri | 29157 | Rural | 182 | 159.1 | 207.6 | \N | 8 | 107 | 48 | stable | -0.5 | -1.2 | 0.30000000000000004 | Latest 5-year average | Both Sexes | Late Stage (Regional & Distant) | White (Non-Hispanic) | All Cancer Sites | By County | All Ages | 29 | mortality | county | 2025-02-10 19:58:25.293785000 | https://statecancerprofiles.cancer.gov/deathrates/index.php?stateFIPS=00&areatype=county&cancer=001&race=07&stage=211&year=0&sex=0&age=001&type=death | Perry County | Missouri |
| Elbert County, Georgia | 13105 | Rural | 181.9 | 157 | 210.4 | \N | 6 | 137 | 41 | stable | -0.7000000000000001 | -1.4 | 0 | Latest 5-year average | Both Sexes | Late Stage (Regional & Distant) | White (Non-Hispanic) | All Cancer Sites | By County | All Ages | 13 | mortality | county | 2025-02-10 19:58:25.293785000 | https://statecancerprofiles.cancer.gov/deathrates/index.php?stateFIPS=00&areatype=county&cancer=001&race=07&stage=211&year=0&sex=0&age=001&type=death | Elbert County | Georgia |
| Ware County, Georgia | 13299 | Rural | 181.8 | 161.7 | 204.1 | \N | 7 | 121 | 62 | stable | -0.5 | -1 | 0 | Latest 5-year average | Both Sexes | Late Stage (Regional & Distant) | White (Non-Hispanic) | All Cancer Sites | By County | All Ages | 13 | mortality | county | 2025-02-10 19:58:25.293785000 | https://statecancerprofiles.cancer.gov/deathrates/index.php?stateFIPS=00&areatype=county&cancer=001&race=07&stage=211&year=0&sex=0&age=001&type=death | Ware County | Georgia |
| Nemaha County, Kansas | 20131 | Rural | 181.8 | 151 | 217.8 | \N | 4 | 85 | 28 | stable | 1.7000000000000002 | -0.5 | 12.2 | Latest 5-year average | Both Sexes | Late Stage (Regional & Distant) | White (Non-Hispanic) | All Cancer Sites | By County | All Ages | 20 | mortality | county | 2025-02-10 19:58:25.293785000 | https://statecancerprofiles.cancer.gov/deathrates/index.php?stateFIPS=00&areatype=county&cancer=001&race=07&stage=211&year=0&sex=0&age=001&type=death | Nemaha County | Kansas |
| Bryan County, Oklahoma (6, 7) | 40013 | Rural | 181.8 | 165.1 | 199.9 | \N | 18 | 69 | 93 | falling | -1.4 | -2.4 | -0.5 | Latest 5-year average | Both Sexes | Late Stage (Regional & Distant) | White (Non-Hispanic) | All Cancer Sites | By County | All Ages | 40 | mortality | county | 2025-02-10 19:58:25.293785000 | https://statecancerprofiles.cancer.gov/deathrates/index.php?stateFIPS=00&areatype=county&cancer=001&race=07&stage=211&year=0&sex=0&age=001&type=death | Bryan County | Oklahoma |
| Cherokee County, Alabama | 1019 | Rural | 181.7 | 162.6 | 202.9 | \N | 2 | 53 | 71 | stable | -0.30000000000000004 | -0.8 | 0.30000000000000004 | Latest 5-year average | Both Sexes | Late Stage (Regional & Distant) | White (Non-Hispanic) | All Cancer Sites | By County | All Ages | 1 | mortality | county | 2025-02-10 19:58:25.293785000 | https://statecancerprofiles.cancer.gov/deathrates/index.php?stateFIPS=00&areatype=county&cancer=001&race=07&stage=211&year=0&sex=0&age=001&type=death | Cherokee County | Alabama |



## Local scraper usage

While most users will simply want to download the data, the scraper is available for those who want to run it themselves.

To install the required packages, run the following command:

```bash
pip install git+https://github.com/seandavi/state-cancer-profiles-scraper.git
```

### Running the scraper

To run the scraper, use the following command:

```bash
python -m scps.scraper
```

The scraper will save the data in current working directory.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us. 
