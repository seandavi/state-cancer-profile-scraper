"""Click-based command-line interface for the state cancer profiles scraper.

Installed as the ``scps-scraper`` console script via ``pyproject.toml``::

    scps-scraper scrape                 # all datasets
    scps-scraper scrape --datasets risk # one dataset

Catalog-driven runs::

    scps-scraper scrape                          # uses ./scrape_catalog.jsonl if present
    scps-scraper scrape --refresh-catalog        # full cartesian, rewrite catalog
    scps-scraper scrape --catalog-path /tmp/c.jsonl
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

import click

from scps import catalog as catalog_mod
from scps import demographics, risk, scraper

logger = logging.getLogger("scps.cli")

DATASET_CHOICES = ("incidence", "mortality", "risk", "demographics")

OUTPUT_FILES = {
    "incidence": "state_cancer_profiles_incidence.csv.gz",
    "mortality": "state_cancer_profiles_mortality.csv.gz",
    "risk": "state_cancer_profiles_risk.csv.gz",
    "demographics": "state_cancer_profiles_demographics.csv.gz",
}

PARQUET_FILES = {
    "incidence": "state_cancer_profiles_incidence.parquet",
    "mortality": "state_cancer_profiles_mortality.parquet",
    "risk": "state_cancer_profiles_risk.parquet",
    "demographics": "state_cancer_profiles_demographics.parquet",
}

DEFAULT_CATALOG_FILENAME = "scrape_catalog.jsonl"


def _write_notes(df, endpoint: str, output_dir: Path) -> None:
    """Persist the SCP report notes (title + footnotes) for one endpoint.

    The notes carry the "Created by statecancerprofiles.cancer.gov on DATE"
    vintage string and the submission year — the provenance manifest.py
    extracts rather than infers (#36). One file per endpoint per run.
    """
    notes = df.attrs.get("scp_notes")
    if notes:
        (output_dir / f"notes_{endpoint}.txt").write_text(notes + "\n")


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
@click.option(
    "--catalog-path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help=(
        f"Path to the scrape catalog (default: <output-dir>/{DEFAULT_CATALOG_FILENAME}). "
        "If the file exists and --refresh-catalog is not set, only the "
        "combinations recorded in it will be re-fetched."
    ),
)
@click.option(
    "--refresh-catalog",
    is_flag=True,
    default=False,
    help=(
        "Ignore any existing catalog and run the full cartesian iteration, "
        "rewriting the catalog from the surviving combinations. Use this on "
        "a quarterly cadence (or after a known upstream schema change)."
    ),
)
def scrape(
    datasets: tuple[str, ...],
    output_dir: Path,
    areatypes: tuple[str, ...],
    catalog_path: Path | None,
    refresh_catalog: bool,
) -> None:
    """Run the scraper and write gzipped CSVs to ``--output-dir``."""
    selected = tuple(d.lower() for d in datasets) or DATASET_CHOICES
    run_date = date.today().isoformat()
    output_dir.mkdir(parents=True, exist_ok=True)
    areas = tuple(a.lower() for a in areatypes) or ("county", "state")
    catalog_path = catalog_path or (output_dir / DEFAULT_CATALOG_FILENAME)

    catalog = catalog_mod.Catalog.load(catalog_path)
    if refresh_catalog:
        # Refresh only the *selected* endpoints' entries — preserve others so a
        # targeted refresh (e.g. -d risk --refresh-catalog) doesn't wipe the
        # full-cartesian discoveries for the datasets we're not touching.
        before = len(catalog.entries)
        catalog.entries = [e for e in catalog.entries if e.endpoint not in selected]
        removed = before - len(catalog.entries)
        if removed:
            logger.info(
                "Refresh mode: dropped %d existing entries for %s; preserving the rest.",
                removed, list(selected),
            )
        # Rewrite the on-disk file from the preserved entries so subsequent
        # per-success append_disk() calls don't double up.
        catalog.save()
    catalog_driven = not refresh_catalog and len(catalog.entries) > 0
    if catalog_driven:
        logger.info(
            "Catalog-driven mode: %d entries loaded from %s",
            len(catalog.entries), catalog_path,
        )
    else:
        logger.info(
            "Discovery mode: full cartesian iteration. Catalog will be (re)written at %s",
            catalog_path,
        )

    if "incidence" in selected or "mortality" in selected:
        logger.info("Fetching incidence/mortality select options")
        options_path = output_dir / "select_options.json"
        with options_path.open("w") as fh:
            json.dump(scraper.get_select_options(), fh)

    risk_options = None
    demo_options = None

    if "incidence" in selected:
        _run_incidence_or_mortality(
            "incd", "incidence", areas, output_dir, catalog, catalog_driven
        )
    if "mortality" in selected:
        _run_incidence_or_mortality(
            "death", "mortality", areas, output_dir, catalog, catalog_driven
        )
    if "risk" in selected:
        risk_options = _run_risk(output_dir, catalog, catalog_driven)
    if "demographics" in selected:
        demo_options = _run_demographics(
            areas, output_dir, catalog, catalog_driven
        )

    catalog.save()

    if catalog_driven:
        _probe_new_ids(catalog, selected, risk_options, demo_options)
        _fail_on_regressions(catalog, selected, run_date)


def _fail_on_regressions(
    catalog: catalog_mod.Catalog,
    selected: tuple[str, ...],
    run_date: str,
) -> None:
    """Exit non-zero if any known-good combo stopped returning data.

    The catalog is the regression oracle: in a catalog-driven run every
    recorded combo is attempted, so one that fails used to work — most
    likely an upstream schema change (see docs/landscape.md on how exactly
    this failure mode sat undetected in cancerprof for 17 months). Only
    never-recorded combos may fail quietly.
    """
    regressed: dict[str, int] = {}
    for endpoint in selected:
        missing = catalog.unseen_since(endpoint, run_date)
        if not missing:
            continue
        regressed[endpoint] = len(missing)
        for entry in missing[:5]:
            logger.error(
                "Regression: known-good %s combo returned no data: %s",
                endpoint,
                entry.combo,
            )
        if len(missing) > 5:
            logger.error(
                "... and %d more failed %s combos", len(missing) - 5, endpoint
            )
    if regressed:
        raise click.ClickException(
            f"known-good combos stopped returning data: {regressed}. "
            "Upstream layout may have changed; investigate before releasing "
            "(or re-run with --refresh-catalog after confirming the loss is real)."
        )


def _run_incidence_or_mortality(
    type_code: str,
    endpoint: str,
    areatypes: tuple[str, ...],
    output_dir: Path,
    catalog: catalog_mod.Catalog,
    catalog_driven: bool,
) -> None:
    logger.info("Scraping %s (areatypes=%s)", endpoint, areatypes)
    combos = list(catalog.combos_for(endpoint)) if catalog_driven else None
    if catalog_driven and not combos:
        logger.warning(
            "Catalog has no entries for %s; falling back to discovery", endpoint
        )
        combos = None
    df = scraper.master_table(
        _type=type_code,
        areatypes=areatypes,
        combos=combos,
        on_success=catalog_mod.make_recorder(catalog, endpoint),
    )
    out = output_dir / OUTPUT_FILES[endpoint]
    logger.info("Writing %s (shape=%s)", out, df.shape)
    df.to_csv(out, index=False, compression="gzip")
    parquet_out = output_dir / PARQUET_FILES[endpoint]
    logger.info("Writing %s", parquet_out)
    df.to_parquet(parquet_out, index=False)
    _write_notes(df, endpoint, output_dir)


def _run_risk(
    output_dir: Path,
    catalog: catalog_mod.Catalog,
    catalog_driven: bool,
) -> dict | None:
    logger.info("Scraping risk factors")
    options = risk.get_risk_options()
    combos = list(catalog.combos_for("risk")) if catalog_driven else None
    if catalog_driven and not combos:
        logger.warning("Catalog has no entries for risk; falling back to discovery")
        combos = None
    df = risk.risk_master_table(
        options=options,
        combos=combos,
        on_success=catalog_mod.make_recorder(catalog, "risk"),
    )
    out = output_dir / OUTPUT_FILES["risk"]
    logger.info("Writing %s (shape=%s)", out, df.shape)
    df.to_csv(out, index=False, compression="gzip")
    parquet_out = output_dir / PARQUET_FILES["risk"]
    logger.info("Writing %s", parquet_out)
    df.to_parquet(parquet_out, index=False)
    _write_notes(df, "risk", output_dir)
    return options


def _run_demographics(
    areatypes: tuple[str, ...],
    output_dir: Path,
    catalog: catalog_mod.Catalog,
    catalog_driven: bool,
) -> dict | None:
    demo_areatypes = tuple(a for a in areatypes if a in ("county", "state", "hsa"))
    if not demo_areatypes:
        demo_areatypes = ("county", "state")
    logger.info("Scraping demographics (areatypes=%s)", demo_areatypes)
    options = demographics.get_demographics_options()
    combos = list(catalog.combos_for("demographics")) if catalog_driven else None
    if catalog_driven and not combos:
        logger.warning(
            "Catalog has no entries for demographics; falling back to discovery"
        )
        combos = None
    df = demographics.demographics_master_table(
        areatypes=demo_areatypes,
        options=options,
        combos=combos,
        on_success=catalog_mod.make_recorder(catalog, "demographics"),
    )
    out = output_dir / OUTPUT_FILES["demographics"]
    logger.info("Writing %s (shape=%s)", out, df.shape)
    df.to_csv(out, index=False, compression="gzip")
    parquet_out = output_dir / PARQUET_FILES["demographics"]
    logger.info("Writing %s", parquet_out)
    df.to_parquet(parquet_out, index=False)
    _write_notes(df, "demographics", output_dir)
    return options


def _probe_new_ids(
    catalog: catalog_mod.Catalog,
    selected: tuple[str, ...],
    risk_options: dict | None,
    demo_options: dict | None,
) -> None:
    """Warn if upstream has added new top-level IDs since the catalog was built."""
    if ("incidence" in selected or "mortality" in selected):
        live = scraper.get_select_options()
        for endpoint in ("incidence", "mortality"):
            if endpoint not in selected:
                continue
            new = catalog_mod.probe_new_ids(
                catalog, endpoint, live["cancer"].keys(), "cancer"
            )
            if new:
                logger.warning(
                    "Upstream has %d new cancer IDs not in catalog (%s): %s. "
                    "Consider re-running with --refresh-catalog.",
                    len(new), endpoint, sorted(new),
                )

    if "risk" in selected and risk_options is not None:
        new = catalog_mod.probe_new_ids(
            catalog, "risk", risk_options["topic"].keys(), "topic"
        )
        if new:
            logger.warning(
                "Upstream has %d new risk topics not in catalog: %s. "
                "Consider re-running with --refresh-catalog.",
                len(new), sorted(new),
            )

    if "demographics" in selected and demo_options is not None:
        new = catalog_mod.probe_new_ids(
            catalog, "demographics", demo_options["topic"].keys(), "topic"
        )
        if new:
            logger.warning(
                "Upstream has %d new demographics topics not in catalog: %s. "
                "Consider re-running with --refresh-catalog.",
                len(new), sorted(new),
            )


if __name__ == "__main__":
    cli()
