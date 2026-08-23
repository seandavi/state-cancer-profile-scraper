# Release inventory, vintage grouping, format coverage

Covers SPEC Task 0 items 1, 2 (and item 4/5 live in `schema-drift.md` / `coverage-drift.md`).
Audit performed 2026-08-23 against `seandavi/state-cancer-profile-scraper`. All 19 releases
downloaded and analysed in full.

## Headline

| Question | Answer |
|---|---|
| Releases | **19** (not ~20; no `2026-03-01`) |
| Distinct upstream vintages | **3** |
| Releases with Parquet | **0** — Parquet has never shipped |
| Topics per release | 2 (incidence, mortality) for 17 releases; 4 only for the last 2 |
| Total downloaded | 1.4 GB |

## 1. Inventory and release → vintage mapping

Vintage assignment is derived from content, not from dates: for every release the CSV is
hashed after dropping `_extracted_at` (the only scrape-time-varying column). Releases sharing
a content hash captured the same upstream bytes.

| Release tag | Published | Vintage | Topics | Incidence rows | Mortality rows | Assets | inc hash | mort hash |
|---|---|---|---|---|---|---|---|---|
| `2024-08-02-1` | 2024-08-02 | **V1** | incidence+mortality | 934,287 | 774,770 | 60.3 MB | 18c222f6 | b9a13248 |
| `2025-02-10` | 2025-02-10 | **V2** | incidence+mortality | 1,014,762 | 782,632 | 61.7 MB | bcaaeea2 | ca9e335d |
| `2025-03-01` | 2025-03-01 | **V2** | incidence+mortality | 1,014,762 | 782,632 | 61.7 MB | bcaaeea2 | ca9e335d |
| `2025-04-01` | 2025-04-01 | **V2** | incidence+mortality | 1,014,762 | 782,632 | 61.7 MB | bcaaeea2 | ca9e335d |
| `2025-05-01` | 2025-05-01 | **V2** ⚠ | incidence+mortality | 1,013,440 | 782,632 | 61.7 MB | b5ac3034 | ca9e335d |
| `2025-06-01` | 2025-06-01 | **V2** | incidence+mortality | 1,014,762 | 782,632 | 61.7 MB | bcaaeea2 | ca9e335d |
| `2025-07-01` | 2025-07-01 | **V2** | incidence+mortality | 1,014,762 | 782,632 | 61.7 MB | bcaaeea2 | ca9e335d |
| `2025-08-01` | 2025-08-01 | **V2** | incidence+mortality | 1,014,762 | 782,632 | 61.7 MB | bcaaeea2 | ca9e335d |
| `2025-09-01` | 2025-09-01 | **V2** ⚠ | incidence+mortality | 1,014,762 | 782,628 | 61.7 MB | bcaaeea2 | 939da27b |
| `2025-10-01` | 2025-10-01 | **V2** | incidence+mortality | 1,014,762 | 782,632 | 61.7 MB | bcaaeea2 | ca9e335d |
| `2025-11-01` | 2025-11-01 | **V2** | incidence+mortality | 1,014,762 | 782,632 | 61.7 MB | bcaaeea2 | ca9e335d |
| `2025-12-01` | 2025-12-01 | **V2** | incidence+mortality | 1,014,762 | 782,632 | 61.7 MB | bcaaeea2 | ca9e335d |
| `2026-01-01` | 2026-01-01 | **V2** | incidence+mortality | 1,014,762 | 782,632 | 61.7 MB | bcaaeea2 | ca9e335d |
| `2026-02-01` | 2026-02-01 | **V2** | incidence+mortality | 1,014,762 | 782,632 | 61.7 MB | bcaaeea2 | ca9e335d |
| `2026-04-01` | 2026-04-01 | **V3** | incidence+mortality | 1,354,812 | 928,958 | 79.0 MB | 34cdefec | bf605a95 |
| `2026-05-01` | 2026-05-01 | **V3** | incidence+mortality | 1,354,812 | 928,958 | 79.0 MB | 34cdefec | bf605a95 |
| `2026-05-27` | 2026-05-27 | **V3** | incidence+mortality | 1,354,812 | 928,958 | 79.0 MB | 34cdefec | bf605a95 |
| `2026-05-28` | 2026-05-28 | **V3** † | +demographics +risk | 1,476,853 | 1,034,042 | 151.3 MB | 4cf8a414 | ab3c881c |
| `2026-06-01` | 2026-06-01 | **V3** † | +demographics +risk | 1,476,853 | 1,034,042 | 151.3 MB | 4cf8a414 | ab3c881c |

⚠ = defective partial scrape (see §1.3). † = scraper scope expanded, upstream values unchanged (see §1.2).

Per-release asset filenames and byte sizes: `assets.json`. Per-release column lists, dtypes,
row counts and content hashes: `content.json`.

Every release carries the same asset set: `gh_hash.txt` (the repo commit the scrape ran from),
`select_options.json` (the SCP query vocabulary), and one `.csv.gz` per topic. `2026-05-28`
and `2026-06-01` add `scrape_catalog.jsonl`.

### 1.1 The three vintages

| Vintage | Releases | First capture | Best capture | Upstream change |
|---|---|---|---|---|
| **V1** | 1 (`2024-08-02-1`) | 2024-08-02 | `2024-08-02-1` | baseline |
| **V2** | 13 (`2025-02-10` … `2026-02-01`) | 2025-02-10 | `2026-02-01` | 98.3% of incidence values revised vs V1 |
| **V3** | 5 (`2026-04-01` … `2026-06-01`) | 2026-04-01 | `2026-06-01` | 98.2% of incidence values revised vs V2 |

"Best capture" is the most complete release of the vintage, which is not the first capture for
V2 or V3. This matters for M3 — see §1.5.

The vintage boundaries were established by decomposing each transition into *new query slices*
versus *changed values on slices common to both releases*:

| Transition | Rows | New slices | Dropped | Common slices | Values changed | Verdict |
|---|---|---|---|---|---|---|
| `2024-08-02-1` → `2025-02-10` (inc) | 934,287 → 1,014,762 | 112,034 | 31,559 | 902,728 | 887,553 (**98.3%**) | new vintage |
| `2026-02-01` → `2026-04-01` (inc) | 1,014,762 → 1,354,812 | 373,262 | 33,212 | 981,550 | 964,119 (**98.2%**) | new vintage |
| `2026-05-27` → `2026-05-28` (inc) | 1,354,812 → 1,476,853 | 177,238 | 55,197 | 1,299,615 | **0 (0.0%)** | same vintage |
| `2024-08-02-1` → `2025-02-10` (mort) | 774,770 → 782,632 | 49,460 | 41,598 | 733,172 | 722,620 (98.6%) | new vintage |
| `2026-02-01` → `2026-04-01` (mort) | 782,632 → 928,958 | 175,468 | 29,142 | 753,490 | 733,566 (97.4%) | new vintage |
| `2026-05-27` → `2026-05-28` (mort) | 928,958 → 1,034,042 | 141,866 | 36,782 | 892,176 | **0 (0.0%)** | same vintage |

Within V2 the eleven clean releases are byte-identical after dropping `_extracted_at`. There is
no intermediate vintage hiding inside V2.

### 1.2 The 2026-05-28 jump is not a vintage change

`2026-05-28` adds 122,041 incidence rows and two whole topics, but **not one value changed** on
any slice shared with `2026-05-27`. The added rows are a new `areatype='By State'` tier plus
demographics and risk topics — a scraper scope expansion, released the same week. Grouping this
as a fourth vintage would be wrong: the underlying SCP estimates are identical.

### 1.3 Two releases are defective scrapes, not vintages

Both are strict *subsets* of their neighbours and both revert on the next release, which upstream
revisions do not do.

- **`2025-05-01` incidence** is missing exactly 1,322 rows relative to `2025-04-01`, and every
  missing row is from a single query slice: Lung & Bronchus / Female / All Races / By County.
  Zero rows present that aren't in `2025-04-01`. One failed request.
- **`2025-09-01` mortality** is missing 4 rows, all Kidney & Renal Pelvis / Male / Asian-Pacific
  Islander (NH) / By County (United States, Orange CA, Los Angeles CA, Honolulu HI). Restored
  identically in `2025-10-01`.

Assign both to V2 and record the defect. Do not treat either as a separate vintage.

### 1.4 The vintage-string extraction in SPEC M2 is not possible — blocking

SPEC M2 states the vintage is recoverable from "the `Created by statecancerprofiles.cancer.gov
on DATE` string and the underlying submission year, both of which are in the scraped notes —
extract them, don't infer them." Neither is true of these artifacts:

- **The `Created by` string exists only in demographics and risk**, i.e. in 2 of 19 releases.
  Incidence and mortality never contain it (`grep -c` = 0 in all 19).
- **Where it exists it is a page-generation timestamp equal to the scrape time**, carrying no
  vintage information: `2026-05-28` reads `on 05/28/2026 6:10 pm`, `2026-06-01` reads
  `on 05/31/2026 11:57 pm`. It tracks when the scraper hit the page, nothing about the data.
- **The SEER/NPCR submission year appears nowhere** in any artifact of any release.
- The scraper has no notes/footer handling at all — `grep -rn -i "created by|notes|footer|submission|vintage" scps/` returns nothing.

Vintage therefore **must** be inferred by content comparison. The method in §1.1 does this
cleanly and should be what `manifest.py` implements. M2's wording needs to change from "extract"
to "derive by content hash", and the manifest field should be a derived vintage id (V1/V2/V3)
plus the content hash, not a parsed upstream date.

### 1.5 Consequences for M3 (Zenodo backfill)

- Three version DOIs, not nineteen. Concept DOI + V1/V2/V3.
- `related_identifiers` per version lists the tags in §1.1 — 1, 13, and 5 tags respectively.
- `publication_date` per SPEC = first capture: 2024-08-02, 2025-02-10, 2026-04-01.
- **Unresolved tension:** SPEC says deposit by vintage and date by first capture, but for V2 and
  V3 the first capture is not the most complete capture. V3's first capture (`2026-04-01`) lacks
  demographics, risk and the By-State tier that `2026-06-01` has, and V2's first capture is fine
  but `2025-05-01`/`2025-09-01` are not. Recommend depositing the **best capture** bytes while
  keeping `publication_date` at first capture, and stating the distinction in the version
  description. Needs a decision before M3.
- **Vintage boundaries are only bracketed, not dated.** V1→V2 is bounded by a six-month gap with
  no releases (2024-08-02 → 2025-02-10) and V2→V3 by the missing March 2026 release
  (2026-02-01 → 2026-04-01). An upstream vintage could have come and gone inside either window
  uncaptured. The manuscript must not claim the archive captures every vintage since 2024.

## 2. Format coverage — no release has Parquet

Every one of the 19 releases is CSV-only (`.csv.gz`). There is no first-Parquet release.

The Parquet work exists in the repo but has never produced a release artifact: commit `c7a46cd`
("Add parquet release artifacts alongside gzipped CSVs", merged via PR #17) is dated
**2026-06-25**, which is after the most recent release (`2026-06-01`). No release has been cut
since it merged.

Consequences:

- SPEC item 2's "record the first release where Parquet appears" has the answer "none yet".
- The immutability rule means the 19 historical releases stay CSV-only permanently. Every
  Zenodo version backfilled for V1–V3 will be CSV-gz.
- **The manuscript's "typed, columnar Parquet" framing describes no published artifact today.**
  It becomes true only from the next release forward. Either cut a fresh release before
  depositing so at least the current vintage has Parquet, or generate Parquet as a *derived*
  artifact at deposit time (which the immutability rule permits for a new derived view but not
  as a replacement for release bytes). This needs a decision — it is load-bearing for §6
  framing point 1.

## Files in this work area

| File | Contents |
|---|---|
| `releases.json` | tag + publish date, 19 releases |
| `assets.json` | per-release asset filenames and byte sizes |
| `content.json` | per-release/topic column list, sniffed dtypes, row count, content MD5 |
| `county_coverage_{incidence,mortality}.csv` | distinct county FIPS per state per release |
| `release_totals.csv` | rows per release per topic per locale_type |
| `rel/<tag>/` | the downloaded assets themselves |
