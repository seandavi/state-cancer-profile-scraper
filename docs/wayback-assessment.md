# Wayback coverage assessment — can pre-2023 captures reconstruct retrospective vintages?

Issue #34. Assessed 2026-08-23 against `scrape_catalog.jsonl` from release `2026-06-01`.

**Verdict: no-go for vintage reconstruction. Go for a small, separately-framed
"vintage timeline" evidence product.** Best per-vintage county coverage is 1.25%
(mortality 2015-2019) and 0.48% (incidence 2014-2018). No pre-2023 vintage is
reconstructible at any defensible completeness bar. What the captures *do*
support is dating eleven distinct pre-2023 incidence vintages, which is a
citable fact for the manuscript's revision argument and costs nothing more to
produce than what is already in this directory.

---

## 1. What the audit count actually measured

`docs/audit.md` §6 reported 18,971 distinct pre-2023 CSV urlkeys and called the
yield "high, not low". That count is correct but it counts the wrong thing. A
urlkey is distinct if any query parameter differs — including `sortVariableName`,
`sortOrder`, and `graph`, none of which change the data returned. It also counts
each **state page separately**, and the modern scraper fetches a national slice
with `stateFIPS=00` in one request.

Re-counted on the axes that matter:

| topic | captures (200, text/csv, ≤2022) | distinct **strata** | strata matching live catalog |
|---|---|---|---|
| incidencerates | 15,837 | 201 | 91 |
| deathrates | 17,049 | 84 | 57 |
| demographics | 2,351 | 13 (77 incl. topic/demo) | 28 |
| risk | 405 | 8 (96 incl. topic/risk) | 25 |

The stratum space collapses by roughly two orders of magnitude once sort-order
noise and per-state fan-out are removed. 15,837 incidence captures are 201
distinct data slices crawled repeatedly.

## 2. Captures per year (all four topics, `caps/strata`)

| year | incidence | mortality | demographics | risk | total |
|---|---|---|---|---|---|
| 2008 | 1/1 | – | – | – | 1 |
| 2009 | 184/5 | – | – | – | 184 |
| 2010 | 258/6 | – | – | – | 258 |
| 2011 | 1883/7 | – | – | 48/2 | 1,931 |
| 2012 | 1/1 | – | – | – | 1 |
| 2013 | 137/6 | – | – | 22/2 | 159 |
| 2014 | – | – | – | – | 0 |
| 2015 | 158/28 | – | 18/5 | 49/5 | 225 |
| 2016 | 53/10 | – | 1/1 | 15/4 | 69 |
| 2017 | 3/3 | – | – | 9/3 | 12 |
| 2018 | – | – | – | – | 0 |
| 2019 | 401/29 | 317/18 | 161/4 | 90/3 | 969 |
| 2020 | 46/23 | 274/27 | 11/1 | 14/5 | 345 |
| 2021 | 3951/124 | 7275/60 | 413/7 | 133/8 | 11,772 |
| 2022 | 8761/146 | 9183/67 | 1747/7 | 25/6 | 19,716 |
| **all** | **15837/201** | **17049/84** | **2351/13** | **405/8** | **35,642** |

2021–2022 hold 88% of all captures. 2014 and 2018 are empty. Mortality has no
CSV capture at all before 2019.

## 3. Vintages identifiable from sampled captures

45 incidence and 16 mortality captures were downloaded via
`https://web.archive.org/web/<ts>id_/<original>`, stratified across capture
years and evenly spaced within each year (`sample_captures.py`), plus a 14-point
monthly boundary probe on the headline incidence stratum
(`boundary_probe.csv`). Every capture's `Created by statecancerprofiles.cancer.gov
on <date>` footer matched its capture date, so these are live renders, not stale
caches — the capture date is a trustworthy vintage timestamp.

**Incidence — 11 distinct data windows:**

| data window | observed in captures |
|---|---|
| 2001-2004 | Jan–Feb 2009 |
| 2002-2006 | May 2010 |
| 2003-2007 | Jun 2010 |
| 2004-2008 | Oct 2011 |
| 2005-2009 | Dec 2012 – Mar 2013 |
| 2008-2012 | Sep 2015 – Jan 2016 |
| 2010-2014 | Jul 2017 |
| 2011-2015 | Jul 2019 |
| 2013-2017 | Aug 2020 – Jul 2021 |
| 2014-2018 | Sep 2021 – Oct 2022 |
| 2015-2019 | Nov 2022 – Dec 2022 |

**Mortality — 4 distinct data windows:** 2011-2015 (Jul 2019), 2013-2017 (Aug
2020), 2014-2018 (Oct 2020 – Jun 2021), 2015-2019 (Oct 2021 – Aug 2022).

Two incidental findings worth keeping:

- **Refresh is not annual and not spring.** The incidence 2014-2018 → 2015-2019
  cut fell between 2022-10-01 and 2022-11-26 — a 14-month vintage. Calendar year
  is therefore the wrong bucket for coverage accounting, which is why §4 uses
  observed vintage windows instead.
- **No "submission year" footnote exists in this era.** The SPEC expected a
  "Based on the YYYY submission" string; pre-2023 exports don't carry one. The
  data window in the title plus the `Created by` date are the only vintage
  markers, and they are sufficient.

## 4. Per-vintage coverage against the live catalog

Denominator is `scrape_catalog.jsonl` (release `2026-06-01`): the combos that
actually return data. Incidence: 3,546 county slices. Mortality: **1,836** county
slices, not 3,672 — deathrates URLs carry no `stage` parameter, so the catalog's
211/999 split double-counts the mortality space; both sides of the ratio collapse
it.

A county-areatype national slice requires ~51 state pages. `cty≥45` counts strata
where captures cover at least 45 states within that vintage's capture window.

**Incidence** (of 3,546 county / 3,546 state slices):

| vintage | captures | strata | in catalog | cty ≥45 st | **cty %** | cty ≥25 st | state-level | state % |
|---|---|---|---|---|---|---|---|---|
| 2008-2012 | 206 | 31 | 0 | 0 | 0.00% | 0 | 0 | 0.00% |
| 2010-2014 | 1 | 1 | 0 | 0 | 0.00% | 0 | 0 | 0.00% |
| 2011-2015 | 399 | 27 | 0 | 0 | 0.00% | 0 | 0 | 0.00% |
| 2013-2017 | 2,729 | 89 | 45 | 5 | 0.14% | 5 | 8 | 0.23% |
| **2014-2018** | 7,502 | 150 | 86 | **17** | **0.48%** | 27 | 36 | 1.02% |
| 2015-2019 | 2,138 | 78 | 65 | 5 | 0.14% | 16 | 28 | 0.79% |

**Mortality** (of 1,836 county / 1,836 state slices):

| vintage | captures | strata | in catalog | cty ≥45 st | **cty %** | cty ≥25 st | state-level | state % |
|---|---|---|---|---|---|---|---|---|
| 2011-2015 | 330 | 24 | 21 | 0 | 0.00% | 4 | 3 | 0.16% |
| 2013-2017 | 8 | 5 | 5 | 0 | 0.00% | 0 | 0 | 0.00% |
| 2014-2018 | 5,231 | 55 | 47 | 10 | 0.54% | 11 | 17 | 0.93% |
| **2015-2019** | 11,116 | 67 | 56 | **23** | **1.25%** | 25 | 26 | 1.42% |

**Demographics:** 28 of 3,816 catalog combos appear; 2 reach ≥45 states. ~0.1% of
1,911 county slices.

**Risk:** risk is national/state-only (`stateFIPS` ∈ {00, 99}), so one capture is
a complete slice — the one topic where captures aren't fragmentary. But only 25
of 600 catalog combos were ever captured: **4.2%**, the highest completeness of
any topic and still far below any usable bar.

### Why coverage is this low

The captured strata are the site's default landing-page slices. Every incidence
stratum reaching ≥45 states is `race=00` (All Races) and all but three are
`age=001`/`sex=0`. Crawlers follow default links; they never enumerate the
race × age × sex × stage grid, which is where 97% of the stratum space lives.

Two structural blockers on top of that:

1. **Pre-2017 captures use the old site's URL grammar** — no `areatype`, no
   `stage`, frequently blank `stateFIPS` and blank `cancer`. Of 2,675 pre-2017
   incidence captures, 2,650 are two default URL shapes crawled repeatedly. Zero
   map onto the modern stratum key. The 2008–2016 rows in the table are not
   sampling noise; that era is unmappable without a hand-built crosswalk.
2. **The race vocabulary changed.** Captures use race codes `01`–`07`; the
   current site uses `00, 05, 07, 28, 38, 48`. Only `00`, `05`, `07` overlap by
   code, and code overlap does not imply label equivalence — this needs
   verification before any old race-stratified capture is trusted.

### Temporal coherence — the one thing that isn't a problem

For the well-covered strata, stitching 45+ states inside a single vintage is
feasible: the minimum span needed to collect 45 states is 2–12 days for 8 of the
19 incidence strata and under 60 days for 13 of 19 (`wellcovered.txt`). The
binding constraint is stratum breadth, not vintage smearing.

## 5. Recommendation

### Minimum coverage bar

A reconstructed vintage should ship only if it clears **all** of:

1. ≥80% of the catalog's county slices for that topic, with
2. ≥48 of 51 state pages per slice, all captured inside one vintage window, and
3. a verified label crosswalk for every race/age/stage code used.

80% is already generous — it admits an artifact a user must check per-slice
rather than trust wholesale. Nothing observed comes within a factor of 60 of it.
The best vintage on offer is mortality 2015-2019 at 1.25%. Lowering the bar to
admit it would mean publishing an artifact that is ~99% absent while carrying a
DOI and a vintage label, which is worse than publishing nothing: it invites
exactly the misreading that a version DOI is supposed to prevent.

### Verdict per topic

| topic | best vintage | coverage | verdict |
|---|---|---|---|
| incidence | 2014-2018 | 0.48% | **no-go** |
| mortality | 2015-2019 | 1.25% | **no-go** |
| demographics | 2022-era | ~0.1% | **no-go** |
| risk | 2021-era | 4.2% | **no-go** (complete slices, but 25 of 600) |

### What to do instead

Ship the **vintage timeline** (§3) as a manuscript figure and a small CSV, not as
a data release. It costs nothing beyond `sample_incidence.csv` and
`boundary_probe.csv`, and it directly supports the paper's revision argument:
eleven distinct incidence vintages between 2009 and 2022, each of which SCP
overwrote and none of which is retrievable today. That is a stronger and more
honest use of the Wayback evidence than a 1%-complete reconstruction, and it
converts the retrospective gap from a weakness into the motivation.

Keep the CDX indexes in this directory. If Wayback coverage is ever revisited,
the expensive part is already done.

### Provenance marking, if this is ever revisited

Should the bar be met later, wayback-derived rows must carry, per row:
`provenance='wayback'`, `wayback_timestamp` (14-digit), `source_url` (the
original SCP URL), `scp_created_date` (from the export footer), and
`data_window`. They must ship as a **separate artifact with its own DOI**, never
merged into a prospectively-scraped vintage — a mixed-provenance table with 1%
archival rows is not reproducible by the pipeline that produced the other 99%.

## 6. Method and files

All in this directory. Requests to `web.archive.org` were sequential with a 1.2 s
delay, 60 s timeout, and up to 3 retries; 2 of 61 sample fetches failed on
connection reset and are excluded.

| file | what |
|---|---|
| `cdx_{incidencerates,deathrates,demographics,risk}.tsv` | raw CDX, `filter=mimetype:text/csv&filter=statuscode:200&to=20221231`, uncollapsed |
| `cdx_*.parsed.csv` | one row per capture with query string split into dimensions |
| `parse_cdx.py` → `summary_cdx.txt` | per-year captures / strata / state-coverage |
| `coverage.py` → `coverage.txt` | calendar-year coverage vs catalog |
| `vintage_coverage.py` → `vintage_coverage.txt` | **per-vintage coverage (headline table)** |
| `wellcovered.py` → `wellcovered.txt` | which strata are well covered, and stitch-window spans |
| `sample_captures.py` → `sample_incidence.csv`, `sample_deathrates.csv` | 61 downloaded captures with window, created date, row count, data hash |
| `boundary_probe.csv` | monthly probe locating the 2014-2018 → 2015-2019 incidence cut |
| `vintage_map.txt`, `captures_per_year.txt` | tables in §2, §3 |
| `scrape_catalog.jsonl`, `select_options.json` | denominator and labels, from release `2026-06-01` |

### Caveat on the denominator

Coverage is measured against the **2026** catalog. The true 2018-era stratum
space differed — fewer cancer sites, the old race vocabulary. The percentages are
therefore approximate for older vintages. They are not approximate enough to
matter: at 0.5–1.25%, a denominator off by even a factor of two does not change
the verdict.

---

## 7. Unrelated bug found while establishing the denominator — mortality is 50% duplicated

Working out the mortality denominator surfaced a data-correctness defect in the
released tables. It has nothing to do with Wayback; it is recorded here because
this is where it was found. **Not fixed — reporting only.**

**Mortality has no stage dimension, but the scraper iterates stage anyway.**
`scps/scraper.py:get_table` interpolates `&stage={stage}` into every URL
regardless of `_type`, and `_run_incidence_or_mortality` (`scps/cli.py:179`)
drives mortality through the same `iter_incidence_combos` that iterates
`stage ∈ {211, 999}`.

Verified against the live site, 2026-08-23 — two `deathrates` URLs differing only
in `stage`:

```
stage=999  324239 bytes  sha256:4f58eb4f3a283dd9…
stage=211  324239 bytes  sha256:4f58eb4f3a283dd9…
```

Byte-identical, including the per-request render timestamp. The site ignores
`stage` on `deathrates` entirely.

**Consequence in the published data** (`state_cancer_profiles_mortality.csv.gz`,
release `2026-06-01`, 1,034,042 rows):

- Dropping `stage`, `url`, `_extracted_at`, exactly **517,021 rows (50.0%) are
  duplicates**. The `stage=999` and `stage=211` subframes are `.equals()`-identical.
- `stage` value counts are exactly balanced: 517,021 "All Stages" and 517,021
  "Late Stage (Regional & Distant)".
- So **every row labelled "Late Stage (Regional & Distant)" in the mortality
  table is wrong.** It is an all-stages mortality rate carrying a late-stage
  label. This is not merely redundant — a user filtering mortality to late stage
  gets all-stage rates and no indication anything is off.

Incidence is **not** affected: stage is a real dimension there (1,007,444 All
Stages vs 469,409 Late Stage, zero duplicates).

Three things follow:

1. Mortality should not iterate stage, and the mortality table should not carry a
   `stage` column. That halves mortality requests (3,672 → 1,836 per areatype)
   and the mortality file size.
2. The immutability rule means historical releases keep these rows. The fix is a
   new vintage plus an erratum, and the manuscript must not report mortality row
   counts from affected releases without noting the duplication.
3. Any Technical Validation chunk counting mortality rows is currently counting
   each measurement twice.

Suggested handling: its own issue, owned by whoever holds scraper-hardening.

### Correction to fold back into `docs/audit.md` §6

The mortality county denominator is 1,836, not 3,672 — for the reason above.
