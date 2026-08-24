"""Derive the small figure/table inputs in manuscript/data/ from release artifacts.

Inputs are the published release files themselves, so every number in the
manuscript's figures traces to deposited bytes:

    python derive_figure_data.py \
        --v2-incidence .../2026-02-01/state_cancer_profiles_incidence.csv.gz \
        --v3-incidence .../2026-08-24/state_cancer_profiles_incidence.parquet

Outputs (committed alongside the manuscript; small, diffable):
    data/schema_incidence.csv       column name + type from the V3 parquet
    data/fig_revision_scatter.csv   per-county all-sites rate, V2 vs V3
    data/fig_map_rate.csv           per-county all-sites rate, V3
    data/fig_map_suppression.csv    per-county cell status, lung & bronchus, V3
"""

import argparse
import pathlib
import urllib.request

import pandas as pd
import pyarrow.parquet as pq

OUT = pathlib.Path(__file__).resolve().parent.parent / "data"
GEOJSON = OUT / "geo" / "counties.geojson"
GEOJSON_URL = ("https://raw.githubusercontent.com/plotly/datasets/master/"
               "geojson-counties-fips.json")  # 2010 Census county boundaries

ALL_SITES = dict(cancer="All Cancer Sites", sex="Both Sexes",
                 race="All Races (includes Hispanic)", age="All Ages",
                 stage="All Stages", areatype="By County")
# The stratum audited in docs/landscape.md (241 suppressed, 105 withheld).
LUNG = {**ALL_SITES, "cancer": "Lung & Bronchus"}


def stratum(df, spec):
    m = pd.Series(True, index=df.index)
    for col, val in spec.items():
        m &= df[col] == val
    out = df[m]
    assert len(out), f"empty stratum {spec}"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2-incidence", required=True)
    ap.add_argument("--v3-incidence", required=True)
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    if not GEOJSON.exists():
        GEOJSON.parent.mkdir(exist_ok=True)
        urllib.request.urlretrieve(GEOJSON_URL, GEOJSON)

    schema = pq.ParquetFile(args.v3_incidence).schema_arrow
    pd.DataFrame(
        {"column": schema.names, "type": [str(t) for t in schema.types]}
    ).to_csv(OUT / "schema_incidence.csv", index=False)

    cols = list(ALL_SITES) + ["fips", "age_adjusted_rate_per_100_000",
                              "locale_type", "suppression_reason"]
    v3 = pd.read_parquet(args.v3_incidence, columns=cols)
    v2 = pd.read_csv(args.v2_incidence, usecols=[c for c in cols
                                                 if c != "suppression_reason"],
                     dtype={"fips": str})

    def counties_only(s):
        # areatype, not locale_type: pre-2026-05-28 files mislabel parishes,
        # boroughs, independent cities and DC as 'other' (docs/coverage-drift.md)
        return s[(s.fips.str.len() == 5) & (s.fips != "00000")]

    def county_rates(df, spec):
        s = counties_only(stratum(df, spec))
        return s.set_index("fips")["age_adjusted_rate_per_100_000"]

    r2, r3 = county_rates(v2, ALL_SITES), county_rates(v3, ALL_SITES)
    both = pd.DataFrame({"rate_v2": r2, "rate_v3": r3}).dropna()
    both.to_csv(OUT / "fig_revision_scatter.csv")

    r3.dropna().rename("rate").to_csv(OUT / "fig_map_rate.csv")

    lung = counties_only(stratum(v3, LUNG))
    status = lung.suppression_reason.fillna("published")
    pd.DataFrame({"fips": lung.fips, "status": status}).to_csv(
        OUT / "fig_map_suppression.csv", index=False)

    for f in sorted(OUT.glob("*.csv")):
        print(f.name, f.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
