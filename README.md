## State cancer profiles scraper

[![](https://img.shields.io/github/v/release/seandavi/state-cancer-profile-scraper)](https://github.com/seandavi/state-cancer-profile-scraper/release/latest)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/seandavi/state-cancer-profile-scraper/total)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/seandavi/state-cancer-profile-scraper/.github%2Fworkflows%2Frun-scrape.yaml?label=Scrape%20status)

For the TLDR, the data for _incidence_ and _mortality_ are available for download from:

- <https://github.com/seandavi/state-cancer-profile-scraper/releases/latest>


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