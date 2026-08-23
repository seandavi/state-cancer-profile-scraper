# State Cancer Profiles archive — build spec

**Repo:** `seandavi/state-cancer-profile-scraper`
**Deliverables:** (1) versioned Zenodo archive with per-vintage DOIs, (2) medRxiv data descriptor, (3) cleaned-up pipeline with CI that keeps both current.
**Explicitly out of scope:** the public county-profile website, MIR/exceedance/access analytics, tract-level anything. Those are a separate repo and a separate paper. Do not start them.

**Do not build an R client.** `cancerprof` (getwilds) wraps SCP's per-query CSV export. Audit correction (2026-08-23, `docs/landscape.md`): it was submitted to rOpenSci review but the review closed without acceptance; it was never on CRAN; the authors label it "Concept – Not useable"; and county-level calls for three of four topics have been broken since SCP added the 2023 RUCC column. Cite it accurately, not as "rOpenSci-reviewed." The directive stands: this project is complementary — it archives vintages, which a live query client structurally cannot do — and any client interface belongs upstream, not here.

---

## 0. Governing principle

This repo's product is a **longitudinal record of published estimates**, not a copy of the current ones. State Cancer Profiles has no API, no bulk download, and no release archive — it overwrites. Everything below follows from that.

The hard rule: **published release bytes are immutable.** Never regenerate, reformat, or "fix" a historical release. If an old release lacks Parquet, it lacks Parquet forever; document the format change, don't retrofit it. Corrections are new releases with an errata note, never edits.

---

## Task 0 — audit before building

Do not write pipeline code until all of these are answered and written to `docs/audit.md`. Several change the plan materially.

1. **Release inventory and vintage grouping.** `gh release list --limit 100`. For each: tag, date, asset filenames, sizes. Then group releases into distinct SCP vintages by comparing content — two releases scraped a week apart with identical data are one vintage. The repo has ~20 releases on a monthly cadence; the vintage count is likely much smaller. **Decision rule, fixed now:** Zenodo versions are keyed on distinct vintage, not on release. A vintage's Zenodo record lists every GitHub release tag that captured it in `related_identifiers`. Twenty near-identical DOIs is inflation, not preservation.
2. **Format coverage.** Which releases have Parquet, which are CSV-only? Record the first release where Parquet appears.
3. **Zenodo state — resolved 2026-08-23.** The webhook IS active: all releases since 2024-08 are archived as source-code zips under concept `10.5281/zenodo.13174526`. A separate data concept `10.5281/zenodo.11098814` (CC-BY-4.0, May 2024 incidence+mortality extract) also exists. Decision: the two roles stay separate — see M3. Details in `docs/audit.md` §3.
4. **Schema drift.** Load every release's four tables. Diff column names, dtypes, and category vocabularies (cancer site labels, race/ethnicity labels, stage codes) across vintages. Produce a matrix in `docs/schema-drift.md`. Expect real drift: SEER submission year, staging recodes, RUCC vintage moving from 2013 to 2023, NCI population denominator re-basing.
5. **Coverage drift.** Per release, count rows and count suppressed cells by state. Kansas should be absent at county level throughout; Indiana should drop out of some years. Confirm and record which.
6. **Wayback yield.** Probe `web.archive.org` for pre-2023 captures of SCP incidence/mortality table URLs. Expect low yield — these are query-string-generated tables crawlers don't systematically hit. Report hit count. This determines the manuscript framing (see §5).
7. **Credentials.** Confirm a Zenodo personal access token exists with `deposit:write` and `deposit:actions` scopes. Sandbox token too (`sandbox.zenodo.org`) — the backfill gets rehearsed there first.
8. **Prior art — blocking for the manuscript.** Install and exercise `cancerprof`. Determine precisely what it does and does not do: does it retrieve all four data topics? Can it produce a complete national county-level extract in one call, or only per-query slices? Does it cache, version, or archive anything? Write the answer in `docs/landscape.md` as a feature matrix against this archive. Every novelty claim in the manuscript must survive this comparison.
9. **Confirm the no-bulk-download claim, dated.** Verify against `statecancerprofiles.cancer.gov` today that there is no API and no bulk download endpoint. Record the access date. This is a factual claim in the paper and needs a timestamp, not an assumption.
10. **Distribution endpoints — test, don't assume.** This gates the "queryable in-browser" claim in the manuscript, so it runs now even though mirror publishing is deferred (M6). For each candidate host, deposit a test Parquet and check whether it serves (a) CORS headers permitting cross-origin fetch and (b) HTTP range requests, since DuckDB-WASM needs both to query a remote file from a browser.
    - **Zenodo** (sandbox first).
    - **Hugging Face datasets.** Also confirm that `duckdb` resolves `hf://` paths against a public dataset repo without auth. HF DOI behavior is not in scope — no DOI will be minted there.
    - **Cloudflare R2**, as fallback if neither of the above works in-browser.
    Report which targets support which access modes. This determines whether "queryable in-browser" can be claimed about the deposited artifacts themselves or only about a mirror.
11. **Repository policy check.** Confirm which of these appear on Scientific Data's recommended-repository list. Zenodo almost certainly qualifies; do not assume Hugging Face does.

Report findings and wait for a decision before M1.

---

## 1. Repo structure

The existing `scps/` package stays where it is. It has a working CLI, tests, and CI wired to it; renaming it buys nothing and breaks three things. New modules land beside the existing ones.

```
state-cancer-profile-scraper/
  CLAUDE.md                  # root: repo purpose, immutability rule, conventions
  README.md                  # rewritten; leads with bulk-access framing
  scps/
    scraper.py               # existing, cleaned in place
    catalog.py, cli.py, demographics.py, risk.py   # existing
    normalize.py             # NEW: harmonization to stable schema
    manifest.py              # NEW: sha256 manifest generation
    CLAUDE.md                # pipeline-specific conventions
  scripts/zenodo/
    backfill.py              # one-time, idempotent
    publish_release.py       # per-release, used by CI
    CLAUDE.md                # Zenodo API gotchas live here
  manuscript/
    descriptor.qmd           # medRxiv data descriptor
    MANUSCRIPT_STATE.yaml    # scriptorium editorial state (see §6)
    refs.bib
    CLAUDE.md                # style: descriptor genre, no analysis/conclusions
  docs/
    audit.md
    schema-drift.md
    releases.md              # human-readable vintage table
  .claude/agents/
    data-provenance-reviewer.md
    manuscript-reviewer.md
  ledger/
    runs.ndjson              # append-only run ledger
```

Data artifacts are build outputs. Not committed.

---

## 2. Milestones

### M1 — CLAUDE.md hierarchy
Write the root CLAUDE.md stating the immutability rule in the first paragraph, plus the `scps/` and `scripts/zenodo/` CLAUDE.md files. No code moves, no behavior changes.

### M2 — manifest and schema harmonization
- `manifest.py` emits, per release: filename, sha256, byte size, row count, format, and the vintage assignment. **Audit correction (docs/releases.md §1.4):** historical release artifacts contain no vintage string and no submission year — the old scraper discarded the notes — so for the 19 existing releases the vintage is **derived by content hash** (the method in docs/releases.md §1.1: same content modulo `_extracted_at` = same vintage). From the next release forward, `notes_<endpoint>.txt` (PR #39) carries the submission-year footnotes and data windows, and the manifest records both the derived vintage id and the extracted notes fields.
- `normalize.py` produces a **derived** harmonized view across vintages. This is a new artifact, not a rewrite. Original per-release files stay untouched. Harmonization decisions (label crosswalks, RUCC vintage handling) are recorded as data in a crosswalk file, not hardcoded in the function.
- Assertion: for every release, harmonized row count + dropped row count == original row count. Fail loudly.
- **Scraper fix (from the audit): retain suppressed rows.** `scps/scraper.py` currently filters to `rate.notna()`, silently discarding suppressed (`*`) and state-withheld (`[P1 note]`, all Kansas) cells — 346 of 3,144 rows in the stratum sampled. Keep the rows, type the rate as null, add a suppression-reason column. Applies to future releases only; unblocks the coverage audit's suppressed-cell census and the manuscript's lead Methods claim.

### M3 — Zenodo backfill

**Decided (2026-08-23):** two concepts, two roles. `10.5281/zenodo.13174526` stays the *software* record — the webhook keeps archiving source zips per release, untouched. `10.5281/zenodo.11098814` is the *data* concept: the backfill adds per-vintage versions onto it via the **REST API**. Its existing May 2024 deposit becomes the earliest vintage, not a conflict. Do not create a third concept.

- One version DOI per **distinct vintage** — the audit found **3** (V1/V2/V3 across 19 releases, docs/releases.md). Each version's metadata lists all GitHub release tags that captured that vintage (1, 13, and 5 tags).
- **Deposit bytes: best capture per vintage** (recommended, confirm at sandbox review): for V2 and V3 the first capture is not the most complete one (V3's first capture lacks demographics, risk, and the By-State tier; two V2 releases are defective partial scrapes). Deposit the best capture, set `publication_date` to the first capture, and state the distinction in the version description.
- **Cut a fresh release before depositing.** No existing release has Parquet, decoded suppression, or notes files; all three land with the next release after PR #39 merges. That release becomes the current vintage's deposit and the artifact the manuscript's format claims describe.
- Upload **oldest first** so version ordering matches vintage chronology.
- Set `publication_date` to the date of the first release that captured the vintage. Zenodo stores the actual upload timestamp separately, so this reflects true chronology without misrepresentation.
- Metadata per version: title with vintage, creators with ORCID, license **CC-BY-4.0** (already set on the concept; apply uniformly), related identifiers pointing at the GitHub release tags, and a description stating which SCP data vintage the version captured.
- Idempotent: re-running must not create duplicates. Key on the GitHub tags in `related_identifiers`.
- **Rehearse the entire backfill on sandbox.zenodo.org first.** Sandbox is a separate instance, so the rehearsal runs against a throwaway sandbox concept — same code, base URL and concept id as config. Published Zenodo records cannot be deleted. Report the sandbox concept DOI and version list for review before touching production.

The data concept DOI is the identity the paper cites and what satisfies journal repository policy. No other host mints an identifier for these bytes; the software record is cited only as software, if at all.

### M4 — CI
GitHub Action on release publish: scrape → validate → manifest → detect whether the scrape is a new vintage → `publish_release.py` (new Zenodo version only when the vintage is new). Same code path as the backfill, not a parallel implementation. Append a run record to `ledger/runs.ndjson`.

### M5 — manuscript
See §6.

### M6 — Hugging Face mirror (after M5)
Deliberately last: the mirror is additive, and the three-way sync obligation shouldn't start until there is a published record worth mirroring. Skip Cloudflare R2 unless Task 0 item 10 showed neither Zenodo nor HF serves CORS + range.

The sha256 manifest binds hosts together: identical bytes at every location, provable, and any divergence is a build failure.

- HF's job is hosting and discovery: native `hf://` access from DuckDB, a dataset card as documentation, an ML audience that will never find a Zenodo record. No DOI minted here — a second identifier for the same bytes is a liability, not a convenience.
- HF git tags carry no citational meaning. Name them after the Zenodo version they mirror (`zenodo-v3`, not `v3`) so nobody mistakes a tag for a citable version.
- The dataset card leads with the concept DOI as the canonical citation, states plainly that HF is a mirror, and links the Zenodo record. Anyone landing on HF first should be able to cite correctly without leaving the page.
- Every mirrored file's sha256 is listed on the card, matching the manifest.
- Once the mirror exists, one publish routine writes all targets from the same built artifacts; there is no path that updates one host alone. Zenodo publishes first, then mirrors, so the DOI exists before anything references it.

---

## 3. Zenodo API gotchas (put these in `scripts/zenodo/CLAUDE.md`)

- New version = `POST /deposit/depositions/{id}/actions/newversion`, then work against the *draft* returned in `links.latest_draft`, not the original id.
- Files do not carry over usefully to a new version — clear and re-upload.
- `publication_date` is settable at any time before publish; after publish, metadata is editable but files are not.
- Rate limits are modest. Backfill sequentially with retry/backoff, not concurrently.
- Sandbox and production use different tokens and different base URLs. Make the base URL a single config value so the sandbox rehearsal and the production run differ by one variable.

---

## 4. Reviewer personas

**`data-provenance-reviewer`** — checks that no historical bytes were modified, that every claim in the manifest is derived from the file rather than assumed, that harmonization is reversible, and that sha256 values are computed over the exact published artifacts.

**`manuscript-reviewer`** — checks the descriptor against the genre: no analysis, no interpretation, no conclusions; every dataset property stated is verifiable from the deposited files; the NIH acknowledgment is explicit and names the P30 directly.

---

## 5. Landscape assessment

Runs in parallel with M2. Output: `docs/landscape.md` plus populated `manuscript/refs.bib`. Use the PubMed MCP for the literature strands.

**Software and data prior art**
- `cancerprof` — full feature matrix (see Task 0 item 8). This is the primary comparator and must be cited.
- Search CRAN, Bioconductor, PyPI, and GitHub for any other SCP client, scraper, or extract.
- Search Zenodo, Dryad, figshare, and Harvard Dataverse for existing deposited SCP-derived datasets.
- Cancer InFocus and the cancer center catchment-surveillance tooling literature — adjacent, not competing, but reviewers in this space will know it and expect it acknowledged.

**Methodological literature**
- Data vintage and estimate revision in official statistics. The economics literature on real-time macroeconomic data revision is the mature version of this idea and gives the framing a citable intellectual lineage; find the health-surveillance analogues.
- Small-area suppression methodology and its effects on downstream analysis.
- Joinpoint/AAPC methodology as SCP applies it.

**Genre precedent**
- Find 3–5 published data descriptors built on scraped or re-extracted public government data. Note how they framed novelty relative to the upstream source. This directly informs how to survive editorial triage.

**Deliverable:** a short comparative paragraph, not an essay, plus the feature matrix. The single question it must answer: what can a user do with this archive that they cannot do with `cancerprof` plus the live website? If that answer is thin, report it and stop before writing the manuscript.

---

## 6. Manuscript

**Venue:** medRxiv, then Scientific Data.

### Framing

Two arguments, ordered. **Reuse value leads; the archive differentiates.**

**1. Analysis-ready bulk access (the reuse-value argument, and the one Scientific Data's criteria actually reward).** SCP publishes HTML tables driven by a query GUI. This resource publishes the complete national county- and state-level extract of all four data topics as typed, columnar Parquet. Concretely:

- **Suppression is decoded, not carried through.** SCP encodes suppressed and statistically unstable cells as asterisks and footnote markers inside otherwise-numeric columns. Here they become typed nulls with an explicit suppression-reason column (`suppressed_small_count`, `withheld_state_law`). This is a semantic transformation, and it is the core claim to having produced a new dataset rather than a reformatting of an existing one. Lead the Methods with it — **scoped to releases from PR #39 forward.** The audit established that all 19 historical releases dropped suppressed rows entirely (no glyphs, no nulls — docs/schema-drift.md), so the claim is true only of new releases; historical vintages expose suppression only via expected-cross-product differencing, and the manuscript must say so. Historical bytes stay as-is per the immutability rule.
- **Verify the cross-topic join before advertising it.** FIPS keys join, but demographics race labels carry undecoded escapes and differ from the incidence/mortality vocabulary (docs/schema-drift.md); `normalize.py` must reconcile them, and each advertised join gets run in an executable chunk before the claim appears in prose.
- **Cross-topic joins are single queries.** Incidence × mortality × screening × demographics on shared FIPS keys — the analytically interesting operations, and the ones per-query access makes prohibitive.
- **Reproducible by construction.** A pinned version DOI returns identical bytes forever. A live query client returns whatever the upstream serves that day, so the same script can produce different results on different runs.
- **Queryable without infrastructure.** The full extract is small enough for DuckDB or DuckDB-WASM to query directly with predicate pushdown — including in a browser, subject to Task 0 item 10. No backend, no rate limits, no credentials.
- **FAIR and pipeline-ready.** Stable typed schema, FIPS geographic keys joinable to Census/TIGER, long-format rows suitable for direct ingestion into feature pipelines.

**2. The vintage archive (what makes it non-substitutable).** SCP overwrites; no archive of prior estimates exists, and a live query client structurally cannot preserve what the source has already replaced. This is what answers "why not just use `cancerprof`" — and the two are complementary, not competing, which the paper should say plainly.

Report the vintage count honestly, including if it is small, and describe the archive as establishing a prospective record. Wayback yield (Task 0 item 6) came back high — thousands of pre-2023 CSV captures — so retrospective reconstruction is plausible, but the captures are query slices, not full extracts. The paper may *mention* the retrospective potential; it does not depend on it, and no reconstructed vintage ships until its coverage is assessed (tracked as its own issue, outside the paper's critical path).

Do not write the abstract until Task 0 items 6, 8, and 10 are reported.

### Authoring

Quarto (`descriptor.qmd`) with `quartobot` for cite-by-identifier. One source renders the medRxiv PDF and, later, whatever Scientific Data wants.

**Numbers are computed, never typed.** Every figure in Technical Validation — row counts, suppression counts by state, vintage table, schema drift matrix — is produced by an executable chunk reading the deposited artifacts. Use Quarto `freeze` so renders are deterministic and the manuscript can't silently drift from the data. If a number appears in prose and isn't traceable to a chunk, that's a defect.

### Writing process — scriptorium + humanizer

Scriptorium (`seandavi/scriptorium`) is the revision harness. It critiques prose that already exists; it does not draft. The division of labor: drafting happens here (author plus agent, against this spec and the audit outputs), then scriptorium skills run against the draft, then the author disposes of the findings.

- **Bootstrap:** run `scriptorium:init` to create `manuscript/MANUSCRIPT_STATE.yaml` — core claims (the two framing arguments above, verbatim), known weaknesses (small vintage count, single-source dependency), terminology (declare "vintage", "release", "suppression", "harmonized view" as preferred terms; forbid casual synonyms), target venue (Scientific Data), audience.
- **Draft-phase loop, per section:** `gap-finder` (what's unsupported or unengaged), `citation-audit` (claim–support alignment against `refs.bib`), `terminology-normalization` (vintage/release drift is the likely offender), `argumentative-flow` on Background & Summary once it stabilizes.
- **Pre-submission, once, in order:** `figure-text-alignment`, `desk-rejection-risk`, then `reviewer-simulation` — its methodological-skeptic lens is the dry run for "why is this not just a scrape?", which the paper must survive.
- Skip `reporting-guideline-fit`/`compliance` (no EQUATOR checklist covers data descriptors) and `venue-fit` (venue is decided). `compression` only if a length limit forces it.

**Humanizer: heavy hand, throughout.** Every drafted or agent-revised passage gets a full humanizer pass before it is considered done — kill the AI tells (stock vocabulary, reflexive rule-of-three, uniform sentence rhythm, vague attributions, em-dash sprawl). Two rules of engagement, the second straight from scriptorium's own design notes:

1. Humanize at draft time, section by section — not once at the end, when the tells have compounded and the fix is a rewrite.
2. Never combine a humanizer pass with a scriptorium transformation pass (`argumentative-flow`, `compression`) in the same step. They pull on the same stylistic axis in different directions; run scriptorium first, humanize its output, and let the author read the diff of each separately.

The manuscript-reviewer persona (§4) checks genre; humanizer checks voice. Both run before anything is called done.

### Funding

Place in a `## Funding` section. **The P30 is the only NIH award acknowledged.** Do not list any other award — the P30 alone satisfies the preprint pilot, and this work is not attributable to the other grants. **Verify the award number and the mandated CCSG wording with the cancer center grants administrator before posting** — most CCSGs specify exact language and NLM's text-mining matches on it.

> Research reported in this publication was supported by the National Cancer Institute of the National Institutes of Health under Award Number P30CA046934. The content is solely the responsibility of the authors and does not necessarily represent the official views of the National Institutes of Health.

The Rifkin-Bennis endowment may be acknowledged alongside this.

### Posting requirements — not optional

- CC-BY license, not the medRxiv default. CC licensing is what enables full-text indexing in PMC.
- The NIH acknowledgment must be explicit and name the award directly; indirect or institutional support does not qualify and the preprint will be excluded.
- Both must be correct at posting time for the PMCID.

### Structure

Background & Summary / Methods / Data Records / Technical Validation / Usage Notes. Suppression counts, schema drift, and coverage gaps are dataset properties and belong in Technical Validation, not framed as findings.

**Usage Notes must state:** incidence and mortality tables cover different five-year windows; consecutive vintages share four of five years and are therefore not independent observations and must not be naively differenced; and SCP displays but excludes 2020 incidence from trend fits, so any downstream trend work must handle 2020 explicitly.

---

## 7. AI use disclosure

Two constraints govern everything here: LLMs are not authors under any journal policy in scope, and AI use is disclosed in Methods or Acknowledgments, never as authorship.

The deliverable is a **plain-language disclosure statement** in the manuscript describing how AI tools were used (drafting, revision, code) and how the output was reviewed and disposed of by the human author. That statement is what the journals require.

`ledger/ai-sessions.ndjson` supports the statement as a best-effort working record — one line per session with task, artifacts touched, and disposition (accepted / modified / rejected). Disposition is the field that matters: a log of what an agent produced is uninteresting; a log of what a human accepted, changed, or threw out is the actual provenance. But the ledger is an aid to writing an honest disclosure, not a compliance artifact — gaps in it don't block anything, and no supplemental table is generated from it unless a journal asks.

---

## 8. Definition of done

- Every distinct vintage has a version DOI, correct `publication_date`, and matching sha256 in the manifest; each version's metadata lists the GitHub release tags that captured it.
- Concept DOI resolves to latest.
- A fresh clone can reproduce the harmonized view from the deposited artifacts alone.
- CI publishes a new Zenodo version on the next new-vintage release with no manual step.
- `docs/landscape.md` contains the `cancerprof` feature matrix and answers the differentiation question directly.
- `descriptor.qmd` renders; every Technical Validation number traces to an executable chunk; the Funding section names P30CA046934 in the verified CCSG wording; the AI disclosure statement is present.
- The manuscript has been through the scriptorium pre-submission sequence (§6) and a full humanizer pass, with author sign-off on both.
