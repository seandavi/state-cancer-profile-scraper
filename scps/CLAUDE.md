# scps/ — scraper conventions

- **Parse payloads by content, never by position.** SCP CSV exports are reports
  (title block / data / footnotes); `scraper.split_report` locates the data block by its
  header line. Never reintroduce `skiprows=N` or blank-line counting — that's the failure
  class that broke cancerprof for 17 months (docs/landscape.md appendix).
- **The notes blocks are data.** Title + footnotes carry the vintage string, submission
  year, and suppression definitions; they're preserved via `df.attrs["scp_notes"]` and
  written as `notes_<endpoint>.txt` per run. Don't discard them.
- **Suppressed rows are kept, not dropped.** `*` → rate null +
  `suppression_reason="suppressed_small_count"`; `[P1 note]` (Kansas) →
  `"withheld_state_law"`. Plain `N/A` (not available) rows drop. `decode_suppression` in
  `scraper.py` is the single implementation — reuse it.
- **No network I/O at import time.** Vocabulary comes from cached `select_options()` /
  per-run option fetches. Tests prime the cache in `tests/conftest.py`.
- **The catalog is a regression oracle.** `scrape_catalog.jsonl` records every combo that
  ever returned data. In catalog-driven runs, a known-good combo that fails must fail the
  run loudly (`cli._fail_on_regressions`); only never-seen combos may fail quietly.
- **Filter on `areatype`, not `locale_type`,** when selecting county/state tiers —
  `locale_type` misclassifies county-equivalents in releases before 2026-05-28
  (docs/coverage-drift.md).
- Every non-trivial change lands with a test that feeds a realistic raw SCP payload
  (see the `_report(...)` builders in `tests/`), not a pre-parsed DataFrame.
