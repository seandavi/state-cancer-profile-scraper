# Task 0 audit

Status: complete, 2026-08-23, except item 7 (Zenodo tokens — needs Sean).

## 1–2. Release inventory, vintage grouping, format coverage — complete

Full report: `docs/releases.md`. Headlines:

- **19 releases, 3 distinct vintages** (V1: 1 release, 2024-08; V2: 13 releases,
  2025-02→2026-02; V3: 5 releases, 2026-04→2026-06). Vintage boundaries show ~98% of
  estimate values revised; within-vintage releases are byte-identical modulo scrape
  timestamp. The per-vintage DOI decision means 3 version DOIs, not 19.
- Two releases (`2025-05-01`, `2025-09-01`) are defective partial scrapes (one failed
  query slice each), not vintages — exactly the failure class the new catalog regression
  oracle (#38) now catches.
- **No release has ever shipped Parquet** (the Parquet commit postdates the last release)
  and 17 of 19 releases carry only incidence+mortality. The manuscript's "typed columnar
  Parquet" framing describes no published artifact until a new release is cut.
- The `Created by` vintage-string extraction assumed by M2 is impossible for historical
  releases (the old scraper discarded the notes); vintage must be derived by content
  hash. From the next release forward, `notes_<endpoint>.txt` (PR #39) carries the notes.
- Vintage boundaries are bracketed, not dated: V1→V2 spans a six-month release gap,
  V2→V3 spans the missing 2026-03 release. The manuscript must not claim every upstream
  vintage since 2024 was captured.
- **Open decision for M3:** for V2 and V3 the *first* capture is not the *best* capture
  (V3's first capture lacks demographics/risk/By-State). Recommended: deposit best-capture
  bytes, set `publication_date` to first capture, state the distinction in the version
  description.

## 3. Zenodo state — FINDING: existing records, decision required

The SPEC's assumption that no Zenodo integration exists is **wrong on both counts**.

**The GitHub–Zenodo webhook is active on this repo** (hook id 493690531) and has been since
at least August 2024. Every release from `release-2024-08-02` through `release-2026-06-01`
(19 versions) is archived under concept DOI **10.5281/zenodo.13174526**. These records
contain only the **source-code zip** (~76 KB, `isSupplementTo` the git tree), not the data
assets. License MIT; creators Sean Davis, Faisal Alquaddoomi.

**A separate data deposit also exists**: concept DOI **10.5281/zenodo.11098814**
("United States State Cancer Profiles data extract", CC-BY-4.0, creator Davis, Sean), with
two versions dated 2024-05-01 and 2024-05-02 containing
`state_cancer_profiles_incidence.csv.gz` (34 MB), `state_cancer_profiles_mortality.csv.gz`
(27 MB), and `select_options.json`. This captures a **May 2024 vintage that falls in the
gap between the 2024-08 and 2025-02 GitHub releases** — it may be a vintage the release
archive does not hold.

Implications, per the SPEC's own stop rule:

- The backfill as specified (new concept DOI, oldest-first) would create a **third**
  parallel archive. Do not run it as written.
- The clean division available: 13174526 remains the *software* record (webhook keeps
  maintaining it); the *data* archive continues the existing 11098814 concept via the REST
  API, backfilling per-vintage versions from the GitHub release assets. The May 2024
  deposit becomes the first vintage instead of a conflict, and the concept already carries
  the right license (CC-BY) and the right shape (data files, not zips).
- Whatever is decided, M4's CI must not fight the webhook: webhook keeps archiving code;
  `publish_release.py` writes data versions to the data concept only on a new vintage.

**Decision needed before M3.** Recommended: adopt 11098814 as the data concept.

## 4–5. Schema drift, coverage drift — complete

Full reports: `docs/schema-drift.md`, `docs/coverage-drift.md`. Headlines:

- **Almost no schema drift.** Category vocabularies are identical across all three
  vintages; exactly one column was ever added (the 2023 RUCC note column at V1→V2 — and
  it carries only Urban/Rural, not the 1–9 codes; the anticipated RUCC 2013→2023
  crosswalk does not exist in the archive). Drift shows up as *value* drift (~98%
  revised per vintage) and *coverage* drift instead. The M2 crosswalk file is nearly
  empty; schema stability is a finding, not a gap.
- **Suppression is invisible in all historical releases** — no glyphs, no nulls: the old
  scraper's `rate.notna()` filter dropped suppressed rows (confirmed by live
  reconciliation in `docs/landscape.md`). PR #39 retains them with reason codes from the
  next release forward; historical releases can only expose suppression via expected
  cross-product differencing.
- Kansas: **zero incidence rows of any kind** in 17/19 releases (state-level rows appear
  only from 2026-05-28); county mortality present throughout — an asymmetry that breaks
  naive incidence×mortality joins. Indiana county incidence is absent through V1+V2 and
  returns complete (92 counties) exactly at V3. V1 additionally lacks MN, NV, VA.
- Derived-view (normalize.py) work list: `locale_type` misclassifies 30–55k county rows
  per release before 2026-05-28 (filter on `areatype` instead); ~30k footnote-prose rows
  leaked into demographics/risk (the new content-based parser prevents this going
  forward); demographics race labels carry undecoded escapes and don't match the
  incidence vocabulary (blocks the advertised cross-topic join until normalized);
  `(1)`/`(2)`/`(7)` source markers embedded in `reported_locale` should be parsed to a
  column.

## 6. Wayback yield — FINDING: high, not low

The SPEC expected low yield. Pre-2023 captures of `index.php` query outputs with
`mimetype: text/csv` (i.e., actual data exports, not HTML shells), distinct URL keys:

| path | distinct pre-2023 CSV captures |
|---|---|
| incidencerates | 4,438 |
| deathrates | 12,075 |
| demographics | 2,203 |
| risk | 255 |
| **total** | **18,971** |

Incidence alone also shows ~65k HTTP-200 captures of any mimetype. Retrospective vintage
reconstruction is plausible, not a bonus footnote. Coverage per vintage (which
site/sex/stage/area combinations were captured) still needs assessment before the
manuscript claims anything — captures are query-slice-shaped, not full extracts.

## 7. Credentials

No Zenodo API token found in the environment, `~/.config`, or GSM. **Needed from Sean:**
a production token (`deposit:write` + `deposit:actions`) and a sandbox.zenodo.org token.
The webhook's existence confirms the Zenodo account link is healthy.

## 10. Distribution endpoints — tested 2026-08-23

| target | HTTP range | CORS | notes |
|---|---|---|---|
| Zenodo (`zenodo.org/records/.../files/...`) | yes (206) | **no** | no `Access-Control-Allow-Origin` header |
| Hugging Face (`/resolve/main/...`) | yes (206) | **yes** | ACAO echoes origin; range/etag headers exposed |
| Cloudflare R2 | not tested | — | unnecessary given HF result |

`duckdb` (CLI, local) resolves `hf://datasets/...` paths against a public dataset repo
without authentication.

**Consequence for the manuscript:** "queryable in-browser" is claimable for the Hugging
Face **mirror**, not for the Zenodo deposit itself. Phrase it that way. R2 is not needed;
M6 skips it.

## 11. Repository policy

Springer Nature's recommended generalist repositories list (linked from Scientific Data's
repositories policy): Dryad, figshare, Harvard Dataverse, OSF, Science Data Bank,
**Zenodo**. Hugging Face is **not** listed. Zenodo satisfies journal policy; HF is a
mirror only — as the SPEC assumed. Checked 2026-08-23.

## 8–9. Prior art, no-bulk-download confirmation — complete 2026-08-23

Full reports: `docs/landscape.md` (cancerprof, live exercise) and `docs/no-bulk-access.md`
(dated verification). Headlines:

- `cancerprof` was never on CRAN; its rOpenSci review closed 2026-07-23 without acceptance;
  the authors label it "Concept – Not useable." County-level calls fail for three of four
  topics because SCP added a 2023 RUCC column and the package parses columns by fixed
  position (their issue #131, open since 2025-03-14). No cache, no versioning, no vintage
  in output. A full extract via cancerprof ≈ **18,852 sequential requests** (one per
  stratum — geography is NOT the limiting axis; `stateFIPS=00` returns all counties).
- **Archive defect found:** `scps/scraper.py` drops suppressed rows outright
  (`rate.notna()` filter) — 346/3,144 rows in the sampled stratum (241 `*` small-count,
  105 Kansas `[P1 note]`). The manuscript's suppression-decoding claim is false until the
  M2 scraper fix ships. cancerprof preserves suppressed rows (as untyped NA) — currently
  better than us on this axis.
- No API, no bulk download at statecancerprofiles.cancer.gov as of 2026-08-23: FAQ
  documents per-table export as the only method; "API"/"bulk" appear on none of 11 doc
  pages; conventional endpoints 404; UI is fully server-rendered. Suggested dated
  manuscript wording is in `docs/no-bulk-access.md`; re-verify before submission.
