"""Click-based command-line interface for the state cancer profiles scraper.

Installed as the ``scps-scraper`` console script via ``pyproject.toml``::

    scps-scraper scrape                 # all datasets
    scps-scraper scrape --datasets risk # one dataset
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import click

from scps import demographics, risk, scraper

logger = logging.getLogger("scps.cli")

DATASET_CHOICES = ("incidence", "mortality", "risk", "demographics")

OUTPUT_FILES = {
    "incidence": "state_cancer_profiles_incidence.csv.gz",
    "mortality": "state_cancer_profiles_mortality.csv.gz",
    "risk": "state_cancer_profiles_risk.csv.gz",
    "demographics": "state_cancer_profiles_demographics.csv.gz",
}


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    show_default=True,
)
def cli(log_level: str) -> None:
    """Scrape data from the State Cancer Profiles website."""
    logging.basicConfig(level=getattr(logging, log_level.upper()))
    logging.getLogger("httpx").setLevel(logging.WARNING)


@cli.command()
@click.option(
    "--datasets",
    "-d",
    multiple=True,
    type=click.Choice(DATASET_CHOICES, case_sensitive=False),
    help=(
        "Dataset(s) to scrape. Repeat the flag for multiple datasets. "
        "Defaults to all four."
    ),
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Directory to write the gzipped CSVs into.",
)
@click.option(
    "--areatypes",
    multiple=True,
    type=click.Choice(["county", "state", "hsa"], case_sensitive=False),
    help=(
        "Areatypes to iterate for incidence/mortality/demographics. "
        "Defaults to ('county', 'state')."
    ),
)
def scrape(
    datasets: tuple[str, ...],
    output_dir: Path,
    areatypes: tuple[str, ...],
) -> None:
    """Run the scraper and write gzipped CSVs to ``--output-dir``."""
    selected = tuple(d.lower() for d in datasets) or DATASET_CHOICES
    output_dir.mkdir(parents=True, exist_ok=True)
    areas = tuple(a.lower() for a in areatypes) or ("county", "state")

    if "incidence" in selected or "mortality" in selected:
        # Re-export the live select options alongside the data so anyone
        # consuming the release can decode metadata IDs without re-scraping.
        logger.info("Fetching incidence/mortality select options")
        options_path = output_dir / "select_options.json"
        with options_path.open("w") as fh:
            json.dump(scraper.get_select_options(), fh)

    if "incidence" in selected:
        _run_incidence_or_mortality("incd", areas, output_dir)
    if "mortality" in selected:
        _run_incidence_or_mortality("death", areas, output_dir)
    if "risk" in selected:
        _run_risk(output_dir)
    if "demographics" in selected:
        _run_demographics(areas, output_dir)


def _run_incidence_or_mortality(
    type_code: str, areatypes: tuple[str, ...], output_dir: Path
) -> None:
    label = "incidence" if type_code == "incd" else "mortality"
    logger.info("Scraping %s (areatypes=%s)", label, areatypes)
    df = scraper.master_table(_type=type_code, areatypes=areatypes)
    out = output_dir / OUTPUT_FILES[label]
    logger.info("Writing %s (shape=%s)", out, df.shape)
    df.to_csv(out, index=False, compression="gzip")


def _run_risk(output_dir: Path) -> None:
    logger.info("Scraping risk factors")
    df = risk.risk_master_table()
    out = output_dir / OUTPUT_FILES["risk"]
    logger.info("Writing %s (shape=%s)", out, df.shape)
    df.to_csv(out, index=False, compression="gzip")


def _run_demographics(areatypes: tuple[str, ...], output_dir: Path) -> None:
    # The demographics endpoint doesn't accept all the same areatypes as
    # incidence/mortality; filter to those it supports.
    demo_areatypes = tuple(a for a in areatypes if a in ("county", "state", "hsa"))
    if not demo_areatypes:
        demo_areatypes = ("county", "state")
    logger.info("Scraping demographics (areatypes=%s)", demo_areatypes)
    df = demographics.demographics_master_table(areatypes=demo_areatypes)
    out = output_dir / OUTPUT_FILES["demographics"]
    logger.info("Writing %s (shape=%s)", out, df.shape)
    df.to_csv(out, index=False, compression="gzip")


if __name__ == "__main__":
    cli()
