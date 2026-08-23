# Schema drift across vintages

SPEC Task 0 item 4. Derived from all 19 releases; vintage grouping per `audit-inventory.md`.
Ready to drop into `docs/schema-drift.md`.

## Summary — there is almost no schema drift

The SPEC expects "real drift: SEER submission year, staging recodes, RUCC vintage moving from
2013 to 2023, NCI population denominator re-basing." Measured against the artifacts, **the
category vocabularies are completely stable across all three vintages** and exactly one column
was ever added. What the SPEC anticipated as schema drift shows up instead as *value* drift
(~98% of estimates revised at each vintage boundary) and *coverage* drift (see
`coverage-drift.md`).

This is good news for `normalize.py` — the crosswalk file M2 calls for is close to empty — but
it removes a talking point from the manuscript. Schema stability should be reported as a
finding, not padded.

## Drift matrix — incidence

| Property | V1 (`2024-08-02-1`) | V2 (`2025-02-10`…`2026-02-01`) | V3 (`2026-04-01`…`2026-06-01`) |
|---|---|---|---|
| Column count | 28 | 29 | 29 |
| `2023_rural_urban_continuum_codes…` | **absent** | present | present |
| Cancer site labels | 23, stable | 23, identical | 23, identical |
| Race/ethnicity labels | 6, stable | 6, identical | 6, identical |
| Stage codes | 2, stable | 2, identical | 2, identical |
| Sex | 3, stable | 3, identical | 3, identical |
| Age groups | 7, stable | 7, identical | 7, identical |
| `year` | `Latest 5-year average` | identical | identical |
| `areatype` | `By County` | `By County` | `By County`; **`By State` added at `2026-05-28`** |
| `locale_type` | county/national/**other** | county/national/**other** | **other** dropped, `state` added at `2026-05-28` |
| `ci_rank` family | all-NULL | all-NULL | populated for state rows only (`2026-05-28`+) |

## Drift matrix — mortality

Identical pattern, one column fewer (no `percent_of_cases_with_late_stage`):
27 columns in V1, 28 from V2 onward, same single added column, same stable vocabularies.

## The one real column change

`2023_rural_urban_continuum_codesrural_urban_note` is added in **`2025-02-10`** (V1 → V2) to
both incidence and mortality, and never changes again.

Two caveats:

1. **The name is a header-parsing bug.** It is two SCP header cells concatenated without a
   separator: `2023 Rural-Urban Continuum Codes` + `Rural-Urban Note`. `normalize.py` should
   rename it; the release bytes keep the mangled name.
2. **It does not carry RUCC codes.** Its only values are `Urban` (901,906), `Rural` (449,365)
   and NULL (125,582) in `2026-06-01` — the note column's binary collapse, not the 1–9 RUCC
   scale. The actual continuum code was never captured.

**The anticipated RUCC 2013 → 2023 transition is not in the archive.** V1 has no RUCC column at
all; every release that has one has the 2023 vintage. There is no crosswalk to write.

## Non-drift: dtype changes are inference artifacts

DuckDB's sniffer reports `lower_ci_rank` / `upper_ci_rank` flipping DOUBLE → VARCHAR at
`2025-02-10` and VARCHAR → DOUBLE at `2026-05-28`. Both are consequences of column emptiness,
not of a schema change: the columns are all-NULL throughout V2 and only become populated at
`2026-05-28`, when the By-State tier arrives (117,759 non-null of 1,476,853 — essentially the
118,500 state rows). Rank is a state-level-only field. Read every column as VARCHAR and cast
explicitly; do not trust sniffed types across releases.

## Column completeness, by vintage (incidence)

| Column | V1 | V2 | V3 (`2026-06-01`) |
|---|---|---|---|
| `ci_rank` | all-NULL | all-NULL | 117,759 / 1,476,853 |
| `lower_ci_rank` / `upper_ci_rank` | 907,641 / 934,287 | all-NULL | 117,759 / 1,476,853 |
| `recent_trend` (+3 trend cols) | 531,877 / 934,287 | 570,012 / 1,014,762 | 808,870 / 1,476,853 |
| `percent_of_cases_with_late_stage` | 284,809 / 934,287 | 307,825 / 1,014,762 | 469,409 / 1,476,853 |
| `state` | 929,700 / 934,287 | 1,010,162 / 1,014,762 | 1,349,093 / 1,476,853 |
| `2023_rural_urban_continuum_codes…` | — | 1,011,882 / 1,014,762 | 1,351,271 / 1,476,853 |

`recent_trend` is NULL for ~45% of rows in every vintage. That is a genuine missingness signal
(trend not fitted / statistically unstable) and it is the largest real missingness in the data,
but **no reason code is preserved** — see below.

## Suppression is not represented at all — blocking for the manuscript

This is the most consequential finding in the schema audit.

SPEC §6 framing point 1 says: "SCP encodes suppressed and statistically unstable cells as
asterisks and footnote glyphs inside otherwise-numeric columns. Here they become typed nulls
with an explicit suppression-reason column. This is a semantic transformation, and it is the
core claim to having produced a new dataset rather than a reformatting of an existing one."

Measured against the artifacts:

- **There are no asterisks or footnote glyphs anywhere.** Scanning every column of
  `2026-06-01` incidence for `*` or `suppress` returns zero rows.
- **There are no nulls in the rate columns.** `age_adjusted_rate_per_100_000`,
  `average_annual_count` and the CI bounds are 100% populated in every release. Every row that
  exists has a number.
- **Suppressed cells are absent rows, not marked cells.** SCP omits them upstream and the
  scraper keeps only what it is served. Suppression is invisible in these files unless you
  construct the full expected cross-product of geography × site × sex × race × stage × age and
  diff against it.
- **There is no suppression-reason column** and no reason information survives anywhere.

So the transformation the manuscript describes as its core novelty claim has not been performed,
and the input it assumes (glyph-bearing numeric columns) does not exist in these artifacts. Two
options, both requiring a decision before the abstract is written:

1. **Build it for real.** Materialise the expected cross-product, mark absent cells as
   suppressed nulls, and derive a reason where one is inferable. This is genuine added value and
   would support the claim — but it is new work not currently in M2, and reason codes may only
   be recoverable by re-scraping the footnote text the scraper currently discards.
2. **Re-frame.** Drop the suppression-decoding claim and lead Methods with the vintage archive
   plus the cross-topic-join and reproducibility arguments.

Related: the footnote markers SCP appends to locality names *are* preserved, in
`reported_locale` — `(1)`, `(2)`, `(7)` with 10,135 / 921,305 / 545,413 rows in `2026-06-01`.
These are the closest surviving signal to a per-cell caveat and are currently un-parsed. The
`locale` column has them stripped. Parsing these into a typed footnote column is cheap and would
partially support option 1.

## Data-quality defects to fix in `normalize.py`

The release bytes stay untouched; these belong in the derived harmonized view.

| Defect | Where | Detail |
|---|---|---|
| `locale_type` misclassification | V1, V2, V3 up to `2026-05-27` | 30,472–55,197 rows/release binned `other`. All are real counties whose names lack the literal word "County": Louisiana parishes, Alaska boroughs, independent cities (Baltimore City, St. Louis City, Virginia Beach City), and DC. Fixed upstream at `2026-05-28`. Any analysis filtering `locale_type='county'` silently drops them — **filter on `areatype='By County'` instead.** |
| Notes leaked in as data rows | demographics, risk (both releases) | 29,689 rows in `2026-06-01` demographics carry footnote prose in `reported_locale` ("Notes:", "Data not available … for this combination", "For more information about Insurance … see the dictionary at …", "Created by statecancerprofiles.cancer.gov on …"). They have NULL keys. Incidence and mortality are clean (0 such rows). |
| Undecoded escapes | demographics | `race` values appear as literal `   White Non-Hispanic` — the non-breaking-space escapes were never decoded, so demographics race labels do not match the incidence/mortality vocabulary. Blocks the cross-topic join the manuscript advertises. |
| Mangled column name | all releases from V2 | `2023_rural_urban_continuum_codesrural_urban_note`, two headers concatenated. |
| Footnote markers inside `reported_locale` | all releases | `(1)`/`(2)`/`(7)` suffixes; parse to their own column. |

The demographics race-label defect is worth flagging on its own: SPEC §6 claims "Cross-topic
joins are single queries. Incidence × mortality × screening × demographics on shared FIPS keys."
The FIPS keys do join, but the race dimension does not, because demographics carries a different
and un-decoded label vocabulary. Verify each advertised join actually runs before claiming it.

## Method

Column lists, sniffed dtypes and row counts per release/topic: `content.json` (from
`hashcols.py`). Vocabulary and completeness queries: `drift.py`, `dead.py`, `supp.py`,
`supp2.py`. Defect characterisation: `other.py`, `nullkey.py`, `whichcol.py`.
