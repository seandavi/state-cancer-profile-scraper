# manuscript/ — data descriptor conventions

Genre: **data descriptor** (medRxiv → Scientific Data). No analysis, no interpretation,
no conclusions. Structure: Background & Summary / Methods / Data Records / Technical
Validation / Usage Notes. Dataset properties (suppression counts, schema drift, coverage
gaps) go in Technical Validation as properties, never framed as findings.

- **Numbers are computed, never typed.** Every figure traces to an executable Quarto
  chunk reading the deposited artifacts; `freeze` keeps renders deterministic. A number
  in prose without a chunk behind it is a defect.
- **Claims are scoped honestly.** Suppression decoding and Parquet are true of releases
  from PR #39 forward only; historical vintages are CSV captures with suppressed rows
  dropped. Vintage boundaries are bracketed, not dated. Never claim every upstream
  vintage since 2024 was captured. Bulk framing is "one request per statistical stratum"
  (~18,900 per release), never "per county". Verify the cross-topic join in a chunk
  before advertising it.
- **cancerprof is cited accurately:** submitted to rOpenSci software peer review, closed
  without acceptance; never on CRAN. Complementary, not competing — say so plainly.
- Funding: P30CA046934 only, in the CCSG-verified wording. CC-BY at posting. Plain-language
  AI-use disclosure in Methods/Acknowledgments; LLMs are never authors.
- Revision loop: scriptorium skills against `MANUSCRIPT_STATE.yaml` (see SPEC §6), with a
  heavy humanizer pass per section at draft time — never combined with a scriptorium
  transformation pass in the same step.
