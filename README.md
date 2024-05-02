## State cancer profiles scraper

This is a simple web scraper that extracts cancer data from the [State Cancer Profiles](https://statecancerprofiles.cancer.gov/) website. The data is extracted for all states and saved in two CSV files: one for cancer incidence and one for cancer mortality.

### Where are the data?

If you are looking for the pre-scraped data, you can find them on Zenodo at the following link:
    
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.11102940.svg)](https://doi.org/10.5281/zenodo.11102940)

### Installation

To install the required packages, run the following command:

```bash
pip install git+https://github.com/seandavi/state-cancer-profiles-scraper.git
```

### Usage

To run the scraper, use the following command:

```bash
python -m scps.scraper
```

The scraper will save the data in current working directory.

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
