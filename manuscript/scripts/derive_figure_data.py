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
    ap.add_argument("--v3-dir", help="directory holding all four V3 topic "
                    "parquet files; enables data/topic_universe.csv")
    ap.add_argument("--catalog", help="deposited scrape_catalog.jsonl; "
                    "enables data/catalog_counts.csv")
    ap.add_argument("--v1-dir", help="V1 best-capture release files; with "
                    "--v2-dir and --v3-dir enables the validation CSVs")
    ap.add_argument("--v2-dir")
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

    if args.v3_dir:
        rows = []
        for topic in ["incidence", "mortality", "demographics", "risk"]:
            df = pd.read_parquet(
                f"{args.v3_dir}/state_cancer_profiles_{topic}.parquet")
            code = df["fips"] if "fips" in df.columns else df["area_code"]
            county_codes = code[(code.str.len() == 5) & (code != "00000")]
            rows.append({
                "topic": topic,
                "rows": len(df),
                "county_level_codes": county_codes.nunique(),
                "state_rows": int((df.locale_type == "state").sum()),
                "national_rows": int((df.locale_type == "national").sum()),
                "includes_pr": bool(code.str[:2].eq("72").any()),
                "tier_column": "areatype" if "areatype" in df.columns
                               else "statefips_query",
            })
        pd.DataFrame(rows).to_csv(OUT / "topic_universe.csv", index=False)

    if args.catalog:
        import json as _json
        recs = [_json.loads(l) for l in open(args.catalog)]
        latest = max(r["last_seen"] for r in recs)
        cur = pd.DataFrame(r for r in recs if r["last_seen"] == latest)
        counts = cur.groupby("endpoint").size().rename("query_slices")
        counts.to_frame().assign(catalog_total=len(recs),
                                 as_of=latest).to_csv(
            OUT / "catalog_counts.csv")

    if args.v1_dir and args.v2_dir and args.v3_dir:
        validation(args)

    for f in sorted(OUT.glob("*.csv")):
        print(f.name, f.stat().st_size, "bytes")


KEY = ["cancer", "race", "sex", "age", "stage", "areatype", "fips"]
RATE = "age_adjusted_rate_per_100_000"


def _read(path, columns=None):
    if str(path).endswith(".parquet"):
        import pyarrow.parquet as _pq
        have = set(_pq.ParquetFile(path).schema_arrow.names)
        df = pd.read_parquet(path, columns=[c for c in columns if c in have])
    else:
        df = pd.read_csv(path, dtype={"fips": str},
                         usecols=lambda c: c in set(columns))
    df["fips"] = df["fips"].astype(str)
    return df


def _decompose(a, b, key):
    m = a.merge(b, on=key, suffixes=("_a", "_b"))
    changed = (m[f"{RATE}_a"] != m[f"{RATE}_b"]).sum()
    return len(m), int(changed)


def validation(args):
    import json as _json
    topic = "state_cancer_profiles_{}.{}".format
    rows = []
    cols = KEY + [RATE]

    v1i = _read(f"{args.v1_dir}/{topic('incidence', 'csv.gz')}", cols)
    v2i = _read(f"{args.v2_dir}/{topic('incidence', 'csv.gz')}", cols)
    v3i = _read(f"{args.v3_dir}/{topic('incidence', 'parquet')}",
                cols + ["state", "suppression_reason"])
    v1m = _read(f"{args.v1_dir}/{topic('mortality', 'csv.gz')}", cols)
    v2m = _read(f"{args.v2_dir}/{topic('mortality', 'csv.gz')}", cols)
    v3m = _read(f"{args.v3_dir}/{topic('mortality', 'parquet')}", cols)

    # audit method: raw rows, stage included (historical mortality carries
    # the phantom stage duplication on both sides of V1->V2)
    for name, a, b in [("V1->V2 incidence", v1i, v2i),
                       ("V1->V2 mortality", v1m, v2m)]:
        n, ch = _decompose(a, b, KEY)
        rows.append({"transition": name, "common_rows": n, "changed": ch})
    # V2->V3: V3 is post-hardening, so compare published values only and
    # collapse the phantom stage for mortality (V3 iterates none)
    v3i_pub = v3i[v3i[RATE].notna()]
    n, ch = _decompose(v2i, v3i_pub, KEY)
    rows.append({"transition": "V2->V3 incidence (published-in-both)",
                 "common_rows": n, "changed": ch})
    key_ns = [k for k in KEY if k != "stage"]
    v2m_all = v2m[v2m.stage == "All Stages"]
    n, ch = _decompose(v2m_all, v3m[v3m[RATE].notna()], key_ns)
    rows.append({"transition": "V2->V3 mortality (deduped, published)",
                 "common_rows": n, "changed": ch})
    bd = pd.DataFrame(rows)
    bd["pct_changed"] = (bd.changed / bd.common_rows).round(4)
    bd.to_csv(OUT / "boundary_decomposition.csv", index=False)

    # suppression census (V3 incidence, per state x reason)
    cen = (v3i.assign(reason=v3i.suppression_reason.fillna("published"),
                      state=v3i.state.fillna("(no state: national tier)"))
           .groupby(["state", "reason"]).size().rename("cells").reset_index())
    cen.to_csv(OUT / "suppression_census.csv", index=False)

    # county coverage (published county rows) per vintage and topic
    cov = []
    for vid, inc, mort in [("V1", v1i, v1m), ("V2", v2i, v2m),
                           ("V3", v3i_pub, v3m[v3m[RATE].notna()])]:
        for tname, df in [("incidence", inc), ("mortality", mort)]:
            c = df[(df.areatype == "By County") & df[RATE].notna()
                   & (df.fips.str.len() == 5) & (df.fips != "00000")]
            cov.append({"vintage": vid, "topic": tname,
                        "counties": c.fips.nunique(),
                        "kansas": c[c.fips.str[:2] == "20"].fips.nunique(),
                        "indiana": c[c.fips.str[:2] == "18"].fips.nunique()})
    pd.DataFrame(cov).to_csv(OUT / "coverage_by_vintage.csv", index=False)

    # cross-topic join check (V3): all-sites county strata + race crosswalk
    def stratum_fips(df, cancer):
        s = df[(df.cancer == cancer) & (df.sex == "Both Sexes")
               & (df.race == "All Races (includes Hispanic)")
               & (df.age == "All Ages") & (df.areatype == "By County")
               & df[RATE].notna()
               & (df.fips.str.len() == 5) & (df.fips != "00000")]
        if "stage" in s.columns and (s.stage == "All Stages").any():
            s = s[s.stage == "All Stages"]
        return set(s.fips)

    inc_f = stratum_fips(v3i, "All Cancer Sites")
    mort_f = stratum_fips(v3m, "All Cancer Sites")
    xw = _json.loads(
        (pathlib.Path(__file__).resolve().parents[2] / "data" /
         "crosswalks.json").read_text())
    demo = pd.read_parquet(f"{args.v3_dir}/{topic('demographics', 'parquet')}",
                           columns=["race"])
    labels = {str(x).replace("\\u00A0", " ").replace("\xa0", " ").strip()
              for x in demo.race.dropna().unique()}
    labels = {xw["race_label_fixes"].get(x, x) for x in labels}
    mapped = {x for x in labels if x in xw["race_canonical"]}
    pd.DataFrame([{
        "inc_counties": len(inc_f), "mort_counties": len(mort_f),
        "joined_counties": len(inc_f & mort_f),
        "mort_only": len(mort_f - inc_f),
        "demo_race_labels": len(labels),
        "demo_race_mapped": len(mapped),
        "unmapped_labels": "; ".join(sorted(labels - mapped)),
    }]).to_csv(OUT / "join_check.csv", index=False)


if __name__ == "__main__":
    main()
