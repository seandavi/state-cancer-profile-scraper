# state-cancer-profile-scraper

**Published release bytes are immutable.** Never regenerate, reformat, or "fix" a
historical release or its Zenodo deposit. If an old release lacks Parquet or suppression
decoding, it lacks them forever; document format changes, don't retrofit them. Corrections
are new releases with an errata note, never edits.

## What this repo is

A longitudinal archive of State Cancer Profiles (statecancerprofiles.cancer.gov)
estimates. SCP has no API, no bulk download, and no release archive — it overwrites. This
repo scrapes the complete national county- and state-level extract monthly and publishes
it as GitHub releases; distinct upstream *vintages* (not releases) get Zenodo version
DOIs. The product is the record of published estimates over time, not a copy of the
current ones.

The plan of record is `SPEC.md`. Audit ground truth about the existing releases lives in
`docs/` (`releases.md` for the release→vintage mapping, `schema-drift.md`,
`coverage-drift.md`, `audit.md`).

## Conventions

- A **vintage** is a distinct set of upstream SCP estimates; releases capturing identical
  content (modulo `_extracted_at`) belong to one vintage. Vintage assignment is derived by
  content comparison for historical releases; from PR #39 forward the scraped
  `notes_<endpoint>.txt` files carry the submission-year provenance.
- Zenodo: concept `10.5281/zenodo.11098814` is the **data** archive (one version per
  vintage, REST API). Concept `10.5281/zenodo.13174526` is the webhook-maintained
  **software** archive — leave it alone.
- Data artifacts are build outputs, never committed. Tests must not touch the network.
- `cancerprof` (getwilds) is the adjacent R client — complementary, not competing. Do not
  build a query client here; contribute upstream instead.
