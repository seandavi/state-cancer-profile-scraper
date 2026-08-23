# Coverage drift

SPEC Task 0 item 5: per-release row counts, suppressed-cell counts by state, and the
Kansas / Indiana questions.

## Headline

| SPEC expectation | Finding |
|---|---|
| "Kansas should be absent at county level throughout" | **Half right.** Kansas has **zero** incidence rows of any kind in 18 of 19 releases — but its county *mortality* is present throughout (103–104 counties). The gap is incidence-only. |
| "Indiana should drop out of some years" | **Confirmed, and it is a clean break.** Indiana county incidence is absent from the first 14 releases (V1 and all of V2) and appears from `2026-04-01` (V3) onward with all 92 counties. Indiana mortality was never missing. |
| "count suppressed cells by state" | **Not possible as specified.** Suppressed cells are absent rows, not marked cells — there is nothing to count. See `schema-drift.md`. Row counts and geographic coverage are reported instead. |

**Important caveat on method:** coverage must be computed on `areatype='By County'`, not
`locale_type='county'`. The `locale_type` column misclassifies 30k–55k county rows per release
as `other` in every release up to `2026-05-27` (see `schema-drift.md`). Computing coverage on
`locale_type` produces a spurious result in which Alaska, DC, Louisiana and Puerto Rico appear
to have no county data and Virginia appears to gain 38 counties in May 2026. All figures below
use `areatype`.

## Rows per release

| Release | Vintage | Incidence total | county | state | national | Mortality total | county | state | national |
|---|---|---|---|---|---|---|---|---|---|
| `2024-08-02-1` | V1 | 934,287 | 900,937 | 0 | 2,878 | 774,770 | 740,488 | 0 | 3,028 |
| `2025-02-10` | V2 | 1,014,762 | 969,169 | 0 | 2,880 | 782,632 | 748,380 | 0 | 3,028 |
| `2025-05-01` ⚠ | V2 | 1,013,440 | 967,900 | 0 | 2,879 | 782,632 | 748,380 | 0 | 3,028 |
| `2025-09-01` ⚠ | V2 | 1,014,762 | 969,169 | 0 | 2,880 | 782,628 | 748,377 | 0 | 3,027 |
| `2026-02-01` | V2 | 1,014,762 | 969,169 | 0 | 2,880 | 782,632 | 748,380 | 0 | 3,028 |
| `2026-04-01` | V3 | 1,354,812 | 1,296,074 | 0 | 3,541 | 928,958 | 888,558 | 0 | 3,618 |
| `2026-05-27` | V3 | 1,354,812 | 1,296,074 | 0 | 3,541 | 928,958 | 888,558 | 0 | 3,618 |
| `2026-05-28` | V3 | 1,476,853 | 1,351,271 | 118,500 | 7,082 | 1,034,042 | 925,340 | 101,466 | 7,236 |
| `2026-06-01` | V3 | 1,476,853 | 1,351,271 | 118,500 | 7,082 | 1,034,042 | 925,340 | 101,466 | 7,236 |

Rows omitted from this table are identical to their vintage neighbours; full table in
`release_totals.csv`. The `county` column here is `locale_type='county'`, so it *undercounts*
by the `other` bucket (30,472–55,197 rows) in every release before `2026-05-28`; the `other`
column is dropped from the table for width and is in the CSV.

⚠ Defective partial scrapes — see `audit-inventory.md` §1.3.

## Distinct counties covered

| Release | Vintage | Incidence counties | Mortality counties |
|---|---|---|---|
| `2024-08-02-1` | V1 | 2,694 | 3,087 |
| `2025-02-10` … `2026-02-01` | V2 | 2,933 | 3,082 |
| `2026-04-01` … `2026-06-01` | V3 | 3,029 | 3,084 |

Incidence covers fewer counties than mortality in every release, and the gap narrows from 393
(V1) to 55 (V3). Mortality coverage is essentially complete and flat — it comes from NCHS vital
statistics, which have no registry-participation gaps. Incidence coverage depends on state
cancer registries agreeing to publish at county level, which is what drives everything below.

## Kansas — incidence absent throughout, mortality present throughout

Kansas is the **only** state with no county-level incidence in the current release.

| Release span | KS incidence rows (any areatype) | KS county mortality rows |
|---|---|---|
| `2024-08-02-1` … `2026-05-27` (17 releases) | **0** | 10,392 → 11,576 |
| `2026-05-28`, `2026-06-01` | 2,164 (state-level only) | 11,576 |

Kansas had *no incidence rows at all* — not merely no county rows — in 17 of 19 releases. The
2,164 rows appearing in the last two releases are entirely `areatype='By State'`, which only
exists from `2026-05-28`. County-level Kansas incidence has never been captured, in any release,
in any vintage.

Kansas county mortality is present in all 19 releases (103 counties, rising to 104 in V3).

The SPEC's phrasing "Kansas should be absent at county level throughout" is true but incomplete
in a way that matters for Usage Notes: a user joining incidence to mortality on FIPS will get
104 Kansas counties from one side and nothing from the other. State the asymmetry explicitly.

## Indiana — county incidence returns at the V2 → V3 boundary

| Release | Indiana county incidence | Indiana county mortality |
|---|---|---|
| `2024-08-02-1` (V1) | **0 rows / 0 counties** | 22,206 rows / 92 counties |
| `2025-02-10` … `2026-02-01` (V2, 13 releases) | **0 rows / 0 counties** | 22,656 rows / 92 counties |
| `2026-04-01` … `2026-06-01` (V3, 5 releases) | 41,268 rows / **92 counties** | 27,070 rows / 92 counties |

Indiana county incidence is missing from 14 consecutive releases spanning ~19 months, then
returns complete. The return coincides exactly with the V2 → V3 vintage boundary, so it is an
upstream registry-publication change, not a scraper change. Indiana mortality was never
affected.

Because the V2 → V3 boundary is bracketed by the missing `2026-03-01` release, the date Indiana
returned is only known to within the 2026-02-01 → 2026-04-01 window.

## Other states with a coverage gap

Only in the first release, and all restored by `2025-02-10`:

| State | `2024-08-02-1` | `2025-02-10` onward |
|---|---|---|
| Minnesota | absent | 87 counties |
| Nevada | absent | 17 counties |
| Virginia | absent | 133 counties (incl. independent cities) |

Full per-state-per-release county counts: `county_coverage_incidence.csv`,
`county_coverage_mortality.csv`.

Summary of states with **no** county incidence, by release:

- `2024-08-02-1`: Indiana, Kansas, Minnesota, Nevada, Virginia
- `2025-02-10` … `2026-02-01`: Indiana, Kansas
- `2026-04-01` … `2026-06-01`: Kansas

No state is ever missing from county-level mortality, in any release.

## For the manuscript's Usage Notes

Three coverage facts belong there alongside the three the SPEC already lists:

1. Kansas has no county-level incidence in any vintage, but does have county-level mortality.
   Incidence × mortality joins drop Kansas counties on the incidence side.
2. Indiana county incidence exists only in V3. Any cross-vintage comparison involving Indiana
   compares presence against absence, not a change in rates.
3. Before `2026-05-28` there is no state-level tier at all, and `locale_type` mislabels several
   thousand counties as `other`. Users must filter on `areatype`.

## Method

`coverage2.py` (per-state county counts on `areatype`), `ks2.py` (Kansas/Indiana verification),
`final.py` (per-release totals), `coverage.py` (superseded `locale_type` version, kept to show
the artifact), `supp.py` / `supp2.py` (suppression encoding).
