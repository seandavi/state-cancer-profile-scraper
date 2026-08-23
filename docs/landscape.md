# Prior art: `cancerprof` vs. this archive

SPEC.md Task 0, item 8. Prepared 2026-08-23.

## Provenance of this assessment: LIVE, not static

This was a **live exercise**, not a source read. Specifics, so the caveat is auditable:

- R 4.6.1 (2026-06-24) on the working host.
- `cancerprof` is **not on CRAN** — `https://cran.r-project.org/web/packages/cancerprof/index.html`
  returns 404 and `.../src/contrib/Archive/cancerprof/` also returns 404 (never published,
  never archived), despite `NEWS.md` reading "Initial CRAN submission."
- Installed from GitHub source: `getwilds/cancerprof` `main` tarball, `DESCRIPTION` Version 0.1.0.
  Last commit on `main` is **2024-04-17**.
- **One deviation from a stock install, disclosed:** the hard dependency `cdlTools` could not be
  built on this host (it pulls `raster` → `terra`, which needs system GDAL/PROJ; absent here).
  `cdlTools` is used by `cancerprof` for exactly one call — `fips()`, converting a state name or
  abbreviation to a numeric FIPS code (`R/fips-scp.R`, the only `cdlTools` reference in the
  package). I installed a 20-line local shim package exporting only `fips()`. **No line of
  `cancerprof` was modified.** This shim cannot influence any finding below: every finding
  concerns response parsing downstream of a successful, correctly-parameterised HTTP request,
  and the request URLs were independently verified by hand (see the recorded URL below).
- All HTTP requests below went to the live `statecancerprofiles.cancer.gov` on 2026-08-23.

Scripts and captured output are alongside this file: `exercise.R`, `exercise2.R`, `exercise3.R`,
`exercise4.R`, `diag.R`, `diag2.R`, `natl.R`, `supp.R`, `p1.R` and the corresponding `*-out.txt`.

## What `cancerprof` is

19 exported functions wrapping the State Cancer Profiles website's own per-query CSV export
endpoint. `R/create-request.R` builds `https://statecancerprofiles.cancer.gov/{topic}/index.php`
and the callers append query parameters plus `output=1`. There is no NCI API behind this: the
`DESCRIPTION` title, "API Client for State Cancer Profiles", names an API that does not exist
(see `no-bulk-access.md`). `output=1` is the same URL the site's own "Export Data" link emits —
I confirmed byte-for-byte that the link on a live table page carries `output=1`.

### Maturity — relevant to how the manuscript should cite it

Two premises in the task brief need correcting before anything is written down:

- **It is not an accepted rOpenSci package.** rOpenSci Software Peer Review issue
  [ropensci/software-review#637](https://github.com/ropensci/software-review/issues/637) was
  opened 2024-04-03 and **closed 2026-07-23 carrying the labels `holding` and
  `4/review(s)-in-awaiting-changes`** — closed while still awaiting author changes, not accepted.
  "Submitted to rOpenSci peer review; review closed without acceptance" is the defensible phrasing.
  "rOpenSci-reviewed package" invites a reviewer to check the badge and find otherwise.
- **The authors themselves label it unusable.** The repository README leads with the WILDS
  "Project Status: **Concept – Not useable, no support, not open to feedback, unstable API**" badge.

Also: 17 open issues, 2 stars, last commit 2024-04-17 (~2.3 years stale as of today).

## Answers to the four questions

### 1. Does it retrieve all four SCP data topics?

**Nominally yes; in practice, three of the four are broken at county level today.**

All four topics are wrapped: `incidence_cancer()`, `mortality_cancer()`, six `risk_*()` functions,
and eleven `demo_*()` functions.

But every **county-level** call to incidence, mortality, and demographics fails on the live site
as of 2026-08-23:

| Topic | `areatype = "state"` | `areatype = "county"` |
|---|---|---|
| Incidence | works (53 rows, 13 cols) | **fails** |
| Mortality | works (52 rows, 14 cols) | **fails** |
| Demographics | works (52 rows, 5 cols) | **fails** (all of poverty, income, education, population, SVI tested) |
| Risk / screening | works (52 rows, 6 cols) | works (39 rows, 5 cols) |

The error is `Can't transform a data frame with missing names.`

**Root cause, confirmed by inspecting the raw payload.** County-level SCP responses now carry a
column the package does not know about, in position 3:
`2023 Rural-Urban Continuum Codes([rural urban note])`. `cancerprof` renames columns by fixed
position with `setNames()` over a hard-coded vector — for all-stages incidence that vector is
`get_area(areatype)` (2) + 6 shared names + 5 more = **13 names for the 14 columns now returned**.
The surplus column gets an `NA` name and the following `dplyr::mutate(across(...))` aborts.
State-level responses have no RUCC column, which is exactly why state-level still works. Risk
county responses have no RUCC column either, which is why risk survives.

Verified column lists (live, 2026-08-23):

```
county incidence  → 14 cols, [3] = X2023.Rural.Urban.Continuum.Codes..rural.urban.note..
county mortality  → 15 cols, [3] = X2023.Rural.Urban.Continuum.Codes..rural.urban.note..
county demogr.    →  5 cols, [3] = X2023.Rural.Urban.Continuum.Codes..rural.urban.note..
```

This is *precisely* the drift SPEC.md item 4 anticipated ("RUCC vintage moving from 2013 to 2023").
It is a hard-coded-position parser meeting an upstream schema change.

Not my own misconfiguration: [getwilds/cancerprof#131](https://github.com/getwilds/cancerprof/issues/131),
"error running example code of `incidence_cancer`", reports the identical
`Can't transform a data frame with NA or "" names` traceback. It has been **open since
2025-03-14** — roughly 17 months. The failing call in that report is the package's own
documented example.

### 2. One national county-level extract, or per-query slices?

**Per-query slices — but the slicing axis is the stratum, not the state.** This distinction
matters and cuts against the archive, so state it correctly.

I initially assumed `cancerprof` was limited to one state per call. **It is not.**
`fips_scp("usa")` returns `"00"`, and `stateFIPS=00&areatype=county` is honoured by the endpoint:
a single request returned **3,144 rows — every US county plus the national aggregate**. So
geography is *not* the limiting axis; a user does not need 51 calls per stratum.

What a call *cannot* vary is the stratifying dimensions. One request fixes one
(cancer site × race × sex × age × stage × year) combination and returns all areas for it. A
complete extract therefore needs one call per stratum.

**Empirical call count, not a cartesian-product guess.** Each release ships
`scrape_catalog.jsonl`, one record per query this repo actually issued. For the current release
(tag `2026-06-01`) it holds **18,852 records, all with `last_seen = 2026-06-01`** (so this is the
live working set, not a cumulative historical union):

| Topic | Query slices | Rows retrieved |
|---|---:|---:|
| Incidence (county 3,546 + state 3,546) | 7,092 | 1,476,853 |
| Mortality (county 3,672 + state 3,672) | 7,344 | 1,034,042 |
| Demographics (county 1,911 + state 1,905) | 3,816 | 3,310,984 |
| Risk | 600 | 83,429 |
| **Total** | **18,852** | **~5.9 M** |

**So: ~18,900 sequential HTTP requests to reproduce one release via `cancerprof`** — and today
about 14,400 of them (the county-level incidence, mortality and demographics slices) would throw
before returning data.

Two aggravating factors:

- **The returned data frame does not identify its own stratum.** County incidence comes back as
  `County | FIPS | Age_Adjusted_Incidence_Rate | ... | Trend_Upper_95%_CI`. There is no `cancer`,
  `race`, `sex`, `age`, `stage`, or `year` column — those values exist only in the arguments the
  caller passed. Concatenating 18,852 results into an analysable table requires the user to
  re-attach six dimension columns per call themselves. The archive ships them as columns.
- **No throttling, retry, or backoff.** Every exported function is a bare `req_perform()`; there
  is no `req_throttle()` or `req_retry()` anywhere in `R/`. An 18,852-request sweep is entirely
  the user's problem to pace, and any transient failure is unhandled.

### 3. Does it cache, version, or archive anything?

**No, no, and no.** I grepped `R/` for `cache|memoise|version|vintage|etag|last-modified|Sys.Date|timestamp`.
The only hits are inside recorded `httptest2` test fixtures (`R/test-dput-resp-*.R`) — captured
HTTP responses used by the test suite, not a runtime cache.

Consequences:

- Every call is a fresh network round trip. Re-running an analysis re-downloads everything.
- **Nothing records which SCP vintage the numbers came from.** The response body contains the
  data period (my live pull carried `"Lung & Bronchus (All Stages^), 2018-2022"`), but
  `process_resp()` slices the payload down to the data block and **discards the header lines** that
  carry that string. The vintage is thrown away before the user sees it.
- When upstream data changes, the same script silently returns different numbers with no signal
  and no way to retrieve the previous values. There is no path to a superseded vintage:
  SCP serves only current data, and `cancerprof` keeps no copy. **An analysis run through
  `cancerprof` is not reproducible after the next SCP refresh.**

### 4. Output format: typed? suppression handling?

**Typed: yes, partially — better than a first read of the source suggests.** `process_resp()`
reads with `colClasses = "character"`, but each exported wrapper then applies
`mutate(across(<named columns>, as.numeric))`. Live state-level incidence returned
`character, character, numeric × 6, character × 2, numeric × 3`. So rates and CIs are numeric in
the returned data frame. It is an in-memory `data.frame` only — no columnar/on-disk format, no
Parquet, nothing to query without R.

**Suppression: neither tool decodes it, and the archive currently handles it *worse*. This must
not be claimed as an archive advantage.**

I pulled one stratum (lung & bronchus, all races, both sexes, all ages, all stages, latest 5-year,
all counties) live and reconciled all three representations exactly:

| | Rows |
|---|---:|
| Returned by SCP | 3,144 |
| — with a numeric rate | 2,798 |
| — suppressed, rate is `*` | 241 |
| — `[P1 note]`, rate withheld | 105 |

SCP's own footnotes define both markers:

> `*` Data has been suppressed to ensure confidentiality and stability of rate estimates. Counts
> are suppressed if fewer than 16 records were reported in a specific area-sex-race category.

> `[P1 note]` Data not available because of state legislation and regulations which prohibit the
> release of county level data to outside entities.

All 105 `[P1 note]` rows are **Kansas** counties — confirming the expectation in SPEC.md item 5.

How each tool treats those 346 non-numeric rows:

- **`cancerprof`** — `process_resp()` ends with `na_if(x, "*")`, plus `na_if` for `"N/A"` and
  `"data not available"`. The asterisk becomes `NA` and **the row is retained**. The reason for
  suppression is erased (an `NA` rate no longer says "suppressed" vs. "missing", and `[P1 note]`
  is not in the `na_if` list at all so it survives as a literal string). But the row's existence
  survives, and critically so does `Average Annual Count = "3 or fewer"` — genuine information
  about the suppressed cell.
- **This archive** — `scps/scraper.py` ends its per-response handler with
  `return df[df[rate_col].notna()]`. **Suppressed rows are dropped outright.** Confirmed against
  the shipped data: for that same stratum the release contains 2,797 county rows + 1 national row
  = 2,798, matching SCP's numeric-rate count exactly, and `age_adjusted_rate_per_100_000` has
  **zero** nulls across all 1,476,853 incidence rows.

So for this one stratum the archive silently omits 346 county observations, and across the corpus
the suppressed cells are simply absent. A user of the archive cannot distinguish "county was
suppressed for small counts", "county is Kansas and legally withheld", and "county was never
queried". `cancerprof` at least preserves the first two as rows. This is a **real defect in the
archive**, not a strength, and item 5's suppressed-cell counts cannot be computed from the
released files as they stand — only from `scrape_catalog.jsonl` row counts by subtraction.

## Feature matrix

Scored honestly. "Live site" = a user hand-driving the Export Data link.

| Capability | `cancerprof` 0.1.0 | Live SCP site | This archive |
|---|---|---|---|
| **Bulk extract in one operation** | No — 1 call per stratum; ~18,852 calls per full release | No — one manual export per table | **Yes** — 4 files per release |
| **All four data topics** | Wrapped, but **county-level broken for 3 of 4** since the 2023 RUCC column appeared | Yes, manually | **Yes**, all four, county + state + national |
| **Typed columnar output** | Partly — typed in-memory `data.frame`; no on-disk columnar format | No — raw CSV text | **Yes** — typed CSV; Parquet added at commit `c7a46cd` (not yet in the `2026-06-01` release, which is CSV-only) |
| **Stratum identified in the data** | **No** — user must re-attach cancer/race/sex/age/stage/year per call | No | **Yes** — as decoded label columns, not SCP numeric codes |
| **Suppression decoded** | **No** — `*` → `NA`, row kept, `"3 or fewer"` kept | Markers present but undocumented in the payload | **No — and worse: suppressed rows are dropped entirely** |
| **Historical vintages** | No — current data only | No — current data only | **Yes** — ~20 dated GitHub releases |
| **Vintage recorded in output** | No — header lines discarded by the parser | Present in the CSV header a user downloads | Partial — `_extracted_at` + source `url` per row; SCP's own vintage string not yet extracted (SPEC M2) |
| **Pinned, citable versions** | No — unversioned live queries, package not on CRAN | No | Partial — immutable release tags; **DOI pending (SPEC M3)** |
| **Offline / no-rate-limit querying** | No — every call is a live request; no cache, no throttle, no retry | No | **Yes** — download once, query locally |
| **DOI** | No | No | Partial — data concept 10.5281/zenodo.11098814 exists (May 2024 versions); per-vintage backfill is M3. (The record id 11102940 that surfaces in Zenodo search is that concept's 2024 version DOI — same deposit.) |
| **Maintained** | Last commit 2024-04-17; self-labelled "Concept – Not useable"; 17 open issues | N/A (NCI-operated) | Monthly automated releases |

## Bottom line for the manuscript

Claims that survive this comparison:

1. **Bulk access.** ~18,900 sequential per-stratum requests versus four files. This is a
   difference in kind, and it is the strongest claim. State the mechanism precisely — the site
   *can* return all counties in one call, so the correct framing is "one request per statistical
   stratum", **not** "one request per county" or "per state". An overstatement here is easy for a
   reviewer to falsify with a single URL. **Wording correction from the literature pass
   (docs/landscape-literature.md §1a):** another team has independently built a national SCP
   sweep — the Cancer InFocus data layer (CIOData/CIFTools_update), unpublished, unversioned, no
   DOI, feeding a dashboard. So the claim is "nobody else has *published* the result as a
   versioned, citable dataset", never "nobody else does this".
2. **Historical vintages.** SCP publishes only current data and `cancerprof` caches nothing, so
   before this archive there was no way to obtain a superseded SCP vintage at all. Nothing in the
   landscape competes on this axis. Given that upstream schema drift is demonstrable (the RUCC
   column), this is a substantive contribution, not a convenience.
3. **Analysis-ready shape.** The archive carries the six stratifying dimensions as decoded label
   columns; `cancerprof` returns them nowhere, so assembling a cross-stratum table from it is
   18,852 manual re-attachments.
4. **Reproducibility.** Immutable tagged releases against unversioned live queries.

Claims to **drop or fix before writing**:

- **Do not claim suppression is decoded, handled, or preserved.** The archive drops suppressed
  rows; `cancerprof` keeps them. If the manuscript wants this axis, fix the pipeline first —
  retain suppressed rows with an explicit reason code (`suppressed_small_count`,
  `withheld_state_law`) rather than filtering on `notna()`. That change would turn a current
  weakness into the strongest per-cell claim available, and it also unblocks SPEC item 5's
  suppressed-cell census.
- **Do not call `cancerprof` an rOpenSci package.** Its review closed without acceptance
  (2026-07-23, `4/review(s)-in-awaiting-changes`). Say "submitted to rOpenSci software peer
  review; closed without acceptance."
- **Do not say `cancerprof` is a CRAN package.** It has never been on CRAN.
- **Do not claim `cancerprof` covers only one state per call.** It does not; that would be a
  falsifiable error.
- Report the county-level breakage as **dated and reproducible** (2026-08-23, corroborated by
  issue #131 open since 2025-03-14), not as a permanent property — it is a fixable bug and could
  be patched before the paper appears. Its durable significance is as *evidence that upstream
  schema drift breaks position-dependent live clients*, which is an argument for archiving, not
  a criticism of the authors.

## Appendix: what the two codebases teach each other

Same upstream, same per-stratum CSV endpoint, two architectures. Comparing `cancerprof`'s
`R/` (~40 files) against `scps/` (~1,400 lines) explains why one broke and the other
didn't — and shows two of their failure modes latent in our code.

**Where the architectures diverge: who owns the vocabulary.** `cancerprof` hardcodes
everything a request needs: 30+ `handle-*.R` files map human labels to SCP numeric codes
by hand, and each wrapper re-implements the site's JavaScript constraint rules (female-only
cancers, childhood age locks) as R conditionals. `scps` scrapes the `<select>` options off
the live page at runtime (`get_select_options()`), so codes, labels, and (via the catalog)
valid combinations track upstream automatically. The 2023 RUCC column proved which design
survives drift — but the sharper example is vocabulary: a new cancer site or race category
appears in our next scrape untouched; in `cancerprof` it requires a source edit, a
constraint-rule review, and a release.

**Where both are the same, and fragile: positional structure assumptions.**
`cancerprof` finds the data block by counting blank lines ("the 4th blank line" for
incidence) and names columns by position with fixed-length `setNames()` vectors — the RUCC
column shifted every position and broke three topics for 17+ months. We are not entitled
to smugness: `scps` does `pd.read_csv(skiprows=8)`. If SCP adds one line to the title
block, we break identically. We name columns from the header instead of by position, which
is why the RUCC column passed through us harmlessly — but the block-location assumption is
the same class of bug, just unexercised so far.

**The shared blind spot: the header/footnote block is data, and both throw it away.**
`cancerprof` slices it off; `scps` skips it. That block carries the "Created by
statecancerprofiles.cancer.gov on DATE" vintage string, the suppression-rule definitions,
and the source notes — exactly what M2's manifest needs and what neither tool preserves.
One change fixes the fragility and the blindness together: locate the data block by
content (scan for the header line), and parse what surrounds it instead of skipping a
fixed number of rows.

**Suppression: their conservative choice beat our clever one.** `cancerprof` maps `*` to
`NA` and keeps the row (retaining `Average Annual Count = "3 or fewer"` — real
information); `scps` filters to `rate.notna()` and destroys the row. Tracked as #35.

**Silent failure is the common disease.** `cancerprof`'s county breakage sat in an open
issue for 17 months because nothing distinguished "invalid combination" from "regression."
Our `master_table` try/except swallowed every state-level combo for the same reason (the
old #11 bug). We hold the cure `cancerprof` structurally can't have: `scrape_catalog.jsonl`
knows which combos succeeded last release. A combo that worked at the previous release and
fails now is a regression and must fail the run loudly; only never-seen combos may fail
quietly. That check belongs in M4's validate step.

**Minor hygiene, same lesson smaller:** `scps/scraper.py` performs network I/O at import
time (`select_opts = get_select_options()` at module level). Harmless until the site
hiccups during an unrelated import (or a test run). Make it lazy when touching the file
for #35.
