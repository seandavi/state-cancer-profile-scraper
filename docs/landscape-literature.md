# Landscape literature — State Cancer Profiles archive

SPEC.md §5, literature strands (issue #30). Prepared 2026-08-23.
Companion to `docs/landscape.md`, which holds the `cancerprof` feature matrix. That matrix
is **not** repeated here; this document covers everything else §5 asks for.

Citation keys below refer to `refs.bib` in this directory. Every entry there was pulled from
PubMed (via the PubMed MCP) or Crossref during this session; nothing is reconstructed from
memory. Sources I could not verify are listed as comments at the bottom of `refs.bib` and are
named in this document where they matter.

---

## Strand 1 — Other software and data prior art

**Provenance.** Registry sweeps were run through APIs rather than JS-gated web UIs: the GitHub
Search API for repositories and code, Zenodo/figshare/Dryad/Dataverse REST search, and a
full-text code search of the `github.com/cran` mirror org, which is a true full-text sweep of
every CRAN package's `R/` and `man/`. Every hit reported below was opened and read. Bioconductor
and PyPI null results were each established by more than one method.

### 1a. Software clients, scrapers, extracts

`cancerprof` is not the only other SCP client, and one of the others matters.

**The find: `CIOData/CIFTools_update`.** A public Python repository belonging to the University
of Kentucky Markey Cancer Center's Community Impact Office — the Cancer InFocus team — contains
`src/cancer_in_focus_data/state_cancer_profile.py`, roughly 590 lines that do a genuine
**national** SCP sweep: `stateFIPS=00&areatype=county`, looped over cancer site × race/ethnicity
× sex, parallelised with `joblib`, with retry and backoff, CSV block parsing, and even a
hardcoded fix for the Bedford VA FIPS change (51917 → 51019). Architecturally it is much closer
to `scps` than `cancerprof` is, and **the manuscript must not claim that no other national
SCP sweep exists.** It escaped name-based searching because nothing in the repo or path says
"State Cancer Profiles."

What keeps it from being a substitute for this archive, stated precisely so the claim survives
a reviewer opening the repo: it is not on PyPI, has no releases or tags, no versioned data
artifact and no DOI; it is undocumented as a standalone library (1 star); it produces the input
to a dashboard rather than a citable dataset; and the current pipeline path in fact reads
**USCS incidence from a manually placed CSV** while retaining SCP only for mortality. So it is
a live-query ETL step inside someone else's product, with no archive and nothing to cite. The
honest framing is: *another team independently built a national SCP sweep, which is evidence
the need is real; nobody has published the output as a versioned, citable dataset.* One
caution — attribution to the Cancer InFocus team is inferred from the GitHub org identity and
author overlap, and is not stated on the repository. Verify before writing it down.

**`SilentSpringInstitute/RStateCancerProfiles`** [`silentspring_rscp`] is the earliest known SCP client — an R package
building live URLs against `incidencerates/index.php` and the death-rates CGI endpoint,
Apache-2.0, 15 commits, **last commit 3 January 2017**, never on CRAN. It predates `cancerprof`
by about seven years. Worth exactly one sentence, and it makes a useful point: people keep
re-implementing this because the endpoint is undocumented, and the re-implementations keep
being abandoned.

Two further live clients exist and are **not** competitors: a Rust source file inside a
personal knowledge-graph experiment (`somethingelseentirely/sci-graph`, 0 stars, created April
2026) and a commercial data-platform connector (`subsetsio/connectors`, 0 stars, June 2026).
Beyond those, everything found was a consumer of hand-downloaded SCP exports or a class
project — including `SatcherInstitute/health-equity-tracker`, which is a serious funded
platform whose code says outright that source files are *"manually saved in
data/nci_cancer/"*. That is another datapoint for the motivation section: a well-resourced
health-equity platform ingests SCP by hand.

**The CRAN result is a null on clients and a gift on motivation.** A full-text sweep of all
CRAN sources for `statecancerprofiles` / "State Cancer Profiles" returns four files in three
packages, and **not one is a client**. All three ship *frozen one-off manual exports* as example
data: `latticeExtra` carries county all-cancer death rates for **1999–2003**
[`sarkar_latticeextra`]; `SeerMapper` carries all-site mortality for **2009–2013**, hand-exported
on **2 September 2016**, for four states only [`pearson_seermapper`]; `spGARCH` carries prostate
incidence for **2008–2012**, nine southeastern states, spatially imputed [`otto_spgarch`].

Three independent authors each needed SCP data, each hand-exported a different narrow slice,
each froze it into a package, and one of them recorded the specific afternoon they did it. That
is the strongest single illustration available of the gap this archive fills, and it costs
three `@Manual` citations. Use it in Background & Summary.

**Explicit null results, each worth stating:** no CRAN package is an SCP client; **Bioconductor
has nothing** SCP-related; **PyPI has no SCP package at all** (established three ways, since
PyPI's search UI is behind a JS challenge); and **NCI still publishes no API, web service, or
bulk download** for SCP — the site exposes only Home / About / Help & Resources / Contact plus
the four data topics, confirming `docs/no-bulk-access.md` as of this check.

### 1b. Deposited SCP-derived datasets

**No full national SCP extract has ever been deposited by anyone other than this author.** That
null result is clean, and it was checked properly:

- **Zenodo** — a full-text query for "State Cancer Profiles" returns one record, and it is the
  author's own. See the correction below, because the details differ from what `docs/landscape.md`
  currently says.
- **Dryad** — zero. The API returns `total: 0`.
- **figshare** — no standalone deposits. The 21 hits are AACR auto-deposited journal
  supplementary files: 20 figures and summary tables from `[joseph2022pesticides]`-adjacent work
  (the longitudinal-position/daylight-saving paper) plus one zoning-code audit tool. Figure
  images and summary tables, not the underlying extract.
- **Harvard Dataverse** — one genuinely SCP-derived deposit: *Air Quality–Lung Cancer Data*
  [`acharjee2020airquality`], county-level lung cancer incidence 2010–2014 abstracted from SCP
  and joined to air-quality data. It is the textbook example of the pattern: **one cancer site,
  one measure, one five-year window, no demographic stratification.** A second hit was a pointer
  record about SEER and is not SCP-derived. Cite `acharjee2020airquality` as the sole prior
  deposit and characterise it accurately — a single analysis slice — rather than dismissing it.

**Correction needed to `docs/landscape.md`.** That document's feature matrix says the archive's
DOI is "**Not yet** — Zenodo backfill is M3." The Zenodo sweep found otherwise: the 2024 deposit
is **`10.5281/zenodo.11102940`** (*United States State Cancer Profiles data extract*, Davis,
2024-05-02) — not the `10.5281/zenodo.11098814` given in the task brief — and it is marked
superseded, pointing to **`10.5281/zenodo.18446185`** under concept DOI
**`10.5281/zenodo.13174526`** (*seandavi/state-cancer-profile-scraper: release-2026-02-01*,
Davis & Alquaddoomi). So a concept DOI and at least one versioned release DOI already exist.
Someone should reconcile this against M3's scope before the matrix or the manuscript repeats
"DOI pending." Flagged, not acted on — I did not edit the repo.

**One item to watch, unverified.** An OSF project titled *"Erased at the margins: suppression
bias in cancer disparities"* (https://osf.io/bjzr5, created 2026-06-04) analyses SCP suppression
under the `count < 16` rule and explicitly reasons about *"the bulk data"* in which "suppressed
county–site–stratum cells are absent entirely." If that is a paper in progress on SCP suppression
bias, it is the nearest thing to a competitor on the archive's headline claim, and it may be
downstream use of a bulk extract. The page is JS-rendered, so **contributors and DOI could not
be verified** — this is a lead to check by hand, not a finding.

### 1c. Cancer InFocus and catchment-area surveillance tooling

Adjacent, not competing — but SPEC.md §5 is right that reviewers in this space will know it,
and an unacknowledged Cancer InFocus is a credibility hole. The good news is that this
literature *supports* the archive's case rather than undercutting it.

**Cancer InFocus** [`burus2023cancerinfocus`] is the primary citation: Markey Cancer Center
(University of Kentucky) software that gathers and transforms publicly available data from
multiple sources into interactive county-level maps of cancer incidence, mortality, social
determinants and risk factors, for a defined cancer-center catchment area. It exists because
the NCI's 2017 Community Outreach and Engagement requirement obliges every NCI-designated
center to characterise the cancer burden in its catchment area, and the authors describe doing
that by hand as "tedious and inefficient."

**Read the relationship carefully, because it cuts both ways.** Cancer InFocus is a *data
collection and visualization* layer that sits on top of sources including State Cancer
Profiles — it is a consumer of the upstream this archive mirrors, not an alternative source of
it. It ships a dashboard for a chosen county set, not a national bulk extract, and it has no
vintage archive: like every live-query tool it shows whatever upstream serves today. So it is
complementary in the same way `cancerprof` is, and the manuscript should say that in the same
plain terms SPEC.md §6 already uses.

**The adoption numbers are the most useful thing here, and they are an argument for the
archive.** Burus et al. report that as of October 2024, **35 institutions including 26
NCI-designated cancer centers** had licensed Cancer InFocus, and among adopters 91.7% said
they were gathering more data and 72.0% less effort to disseminate it than under their
previous methods [`burus2025cifimpact`]. That is a quantified, peer-reviewed measure of
institutional demand for exactly this data in exactly this shape — and it is 26 organisations
whose pipelines currently re-fetch from a live, unversioned, silently-drifting upstream. Use
it in Background & Summary as the demand evidence; it is far better than asserting that
county-level cancer data is useful.

The surrounding tool literature, for the acknowledgment paragraph: **CHANA** (North Carolina /
UNC Lineberger), which compiles public sources, linked registry–claims data, and primary survey
work into county profiles and dashboards [`spees2024chana`]; a HIPAA-compliant geographic
aggregation method for folding clinical-trial accrual data into Cancer InFocus
[`antonio2024deidentification`]; the MUSC Hollings stakeholder-engaged dashboard [`sonawane2024dashboards`]; and **CancerClarity**, which consumes Cancer InFocus data to
generate LLM-written narratives of county cancer statistics [`munoz2024cancerclarity`]. That
last one is a second-order consumer — a tool built on a tool built on State Cancer Profiles —
which is a compact illustration of how far downstream the reproducibility problem propagates
when the bottom of the stack is unversioned.

**ECCO (Exploring Cancer in Colorado)** [`lowery2026ecco`] is a published
county- and tract-level cancer data platform that names **Cancer InFocus and State Cancer
Profiles as its two upstream sources**, alongside the Colorado state health department. Two
things follow. First, it is direct published evidence that catchment-area platforms consume
SCP as an input and would benefit from a bulk, versioned form of it — which is the reuse-value
argument, made by a third party. Second, **Sean Davis is an author on it**, so it must be
declared as a self-citation and framed as related prior work by the same group, not as
independent corroboration. Todd Burus, a Cancer InFocus author, is also on the ECCO paper.

---

## Strand 2 — Methodological literature

### 2a. Data vintage and estimate revision in official statistics

The argument the manuscript needs to make is that *a statistical agency's published estimate
for a fixed reference period is not a constant*, and that discarding superseded values destroys
information. That argument has a mature literature — it just isn't in health.

**The economics lineage.** Croushore and Stark built the Federal Reserve Bank of Philadelphia's
*Real-Time Data Set for Macroeconomists*: a set of quarterly **vintages**, each a snapshot of
what the major macroeconomic series looked like *as published on that date*
[`croushore2001realtime`]. Their companion paper asks the question this archive is implicitly
asking — *does the data vintage matter?* — and answers it empirically, showing that
published econometric results can fail to replicate when re-run on the vintage actually
available at the time versus the latest revised vintage [`croushore2003vintage`]. This is the
strongest available citation for the framing, and it also supplies the vocabulary: **vintage**
is a term of art in that literature, which is a point in favour of SPEC.md's decision to
declare "vintage" as the preferred term. Two cautions when citing it: it is not a health
paper, so introduce it explicitly as an analogy rather than dropping it in as if it were a
surveillance reference; and their vintages are *reconstructed retrospectively* from archived
agency publications, whereas this archive is prospective — say which one you are doing.

**The health-surveillance analogue exists and is a cancer paper.** Clegg, Feuer, Midthune, Fay
and Hankey quantified how much SEER cancer incidence counts are revised *after* first
publication [`clegg2002reportingdelay`]. Their numbers are directly quotable: initial case
counts, taken after the standard two-year delay, captured only **88–97% of the eventual final
counts**, and reaching 99% completeness took **4 to 17 years** depending on the site. Adjusting
for reporting delay changed 1998 incidence rates by 3% (colorectal) to 14% (melanoma in
whites, prostate in Black men) — and, critically, **flipped trend conclusions**: reporting-
adjusted melanoma incidence in white men rose significantly (EAPC +4.1%) where the unadjusted
series looked flat-to-declining (EAPC −4.2%) after 1996. That is a health-domain demonstration
that the same reference period, restated later, yields a different and sometimes
opposite-signed answer.

This is the single most useful citation in the whole literature review, because it converts
"vintages matter" from an assertion into a cancer-surveillance finding by NCI's own
statisticians. Do note the mechanism is *reporting delay*, i.e. late case ascertainment; SCP
vintage-to-vintage change also arises from denominator revisions, registry re-certification,
methodological changes and the moving five-year window. Do not claim `clegg2002reportingdelay`
explains all SCP drift — cite it as evidence that revision of published cancer estimates is
real, routine, and consequential. Registry-completeness assessment is the adjacent machinery
[`das2008completeness`].

**Data versioning as research infrastructure.** For the "why does an archive need immutable
tagged releases" argument, Klump et al. give a conceptual framework and a set of principles
for versioning data, and make the point that versioning is not just revision tracking but
identification and citability [`klump2021versioning`]. A Scientific Data paper proposes a
`major.minor.patch` scheme for datasets with drift metrics [`gonzalezcebrian2024versioning`] —
useful mainly as evidence that the target journal already publishes on this problem, which is
a small but real desk-rejection defence.

### 2b. Small-area suppression and its downstream effects

**Where SCP's suppression rules come from.** The relevant NCHS standards documents are
citable and current: Klein et al. set out the Healthy People 2010 suppression criteria
[`klein2002suppression`]; Parker et al. give the NCHS Data Presentation Standards for
Proportions, built on a minimum denominator and Clopper–Pearson confidence-interval width
[`parker2017proportions`]; Talih et al. evaluate the corresponding standards for rates from
vital statistics and surveys, including what fraction of estimates get flagged unreliable
[`talih2023ratesstandards`]. Note for the descriptor: neither Klein nor Parker has a DOI, and
both are NCHS series reports — cite with report number.

**The best cancer-specific citation is NCI's own.** Tatalovich et al. state the problem this
archive's suppression handling addresses, in NCI's words [`tatalovich2022zonedesign`]: counties
are a poor unit for cancer reporting because "sparsely populated counties [have] less reliable
estimates of cancer rates that are often suppressed due to confidentiality concerns," and they
built alternative zone-design geographies specifically to "substantially reduc[e] the need to
suppress data." This is an NCI Surveillance Research Program team (Feuer is senior author)
conceding that county-level suppression materially degrades the utility of exactly the data
SCP serves. Cite it as the authoritative statement that suppression is a recognised
limitation, not a nuisance.

**How much analysis suppression actually blocks — with published, quantified examples.**
Three independent 2026 papers using SCP report suppression as a binding constraint:

- Jacobson et al. set out to describe pediatric cancer incidence in rural US counties and
  found publicly available data for **29 non-metropolitan counties, about 2% of rural
  counties** [`jacobson2026pediatric`]. Their own framing: geographic disparities in pediatric
  cancer incidence are "poorly characterized… partly due to suppression of data for small
  populations," and they close on "the limitations of publicly available surveillance data for
  pediatric cancers in rural areas." A 98% loss rate, published, in a peer-reviewed journal.
- Ladas and Towery could not compare melanoma mortality across five southwest Missouri
  counties because it was suppressed in all but one [`ladas2026melanoma`].
- Kasheri et al. list "HSAs with low case counts were censored" among the stated limitations of
  a 557-area national analysis [`kasheri2026dermatologist`].

These are worth more to the manuscript than any methodological citation, because they are
independent researchers documenting the exact failure mode the archive's suppression-reason
columns address. They also carry a warning: **they demonstrate that suppression removes cells,
not that any tool recovers them.** The archive does not un-suppress anything. What it can
claim, from PR #39 forward, is that a suppressed cell is *representable and labelled* rather
than silently absent — the user can count what is missing and why, which is precisely what
Jacobson et al. had to reconstruct by hand.

**Downstream-analysis effects of disclosure control.** The closest well-developed literature is
the census differential-privacy debate, which is methodologically adjacent (noise injection
rather than cell suppression) but asks the same question: what does disclosure protection do
to health estimates? Santos-Lozada et al. found that differential privacy applied to census
denominators biases mortality rate estimates more for Black and Hispanic populations and more
in less-urban, smaller areas [`santoslozada2020dp`]. Krieger et al. and Li et al. reached
more reassuring conclusions for census-tract inequity monitoring under later DAS versions
[`krieger2021dp`, `li2023dpmapping`]; Kurz et al. found up to 10% county-level error in
Medicaid participation rates [`kurz2022dpmedicaid`]. **Cite this cluster carefully.** It is
genuinely adjacent, not identical, and a reviewer who knows it will notice if you elide the
difference. Its honest use is one sentence: disclosure-protection choices made upstream
propagate into small-area health estimates in ways that fall unevenly on smaller and
minoritised populations, and are therefore worth recording rather than silently absorbing.
Rushton et al. remains the standard review for the geographic-confidentiality tradeoff in
cancer research specifically [`rushton2006geocoding`].

**Gap, stated honestly:** I did not find a paper that quantifies the bias introduced into a
downstream regression by *cell suppression specifically* in county cancer rates. If the
manuscript wants to claim such bias, it must either demonstrate it from the archive's own data
or state it as a plausible concern rather than a cited finding.

### 2c. Joinpoint and AAPC methodology, as SCP applies it

SCP reports trend statistics (annual percent change and its confidence interval) computed with
NCI's Joinpoint methodology. The canonical chain, all verified:

- **The founding paper.** Kim, Fay, Feuer and Midthune, permutation tests for joinpoint
  regression, applied to US prostate cancer incidence and mortality [`kim2000permutation`].
  This is the citation for "how the joinpoints are chosen."
- **AAPC.** Clegg, Hankey, Tiwari, Feuer and Edwards define the average annual percent change
  as a weighted summary of segment-specific APCs over a fixed window, and show why the
  conventional single-slope APC misleads when the trend has transitions [`clegg2009aapc`].
  This is the citation for the number SCP actually displays.
- **What changed since.** Kim et al. document two substantive enhancements to Joinpoint since
  1998 — data-driven model selection replacing the permutation test as default, and empirical-
  quantile confidence intervals replacing parametric ones — and describe their impact on NCI's
  published trend analyses [`kim2022twentyyears`], with the model-selection method developed in
  [`kim2023modelselection`].

**Why `kim2022twentyyears` earns its place in a data descriptor.** It is evidence that the
trend columns SCP publishes are the output of *a versioned piece of software whose defaults
have changed*. Two SCP vintages can therefore differ in their trend statistics for reasons
that have nothing to do with new cases being reported. That is a dataset property, it belongs
in Technical Validation or Usage Notes, and it strengthens the vintage argument without
requiring any new analysis. It also implies a concrete Usage Note: **do not compare AAPC values
across vintages without checking which Joinpoint version produced them.**

### 2d. Bonus finding — SCP's screening and risk-factor numbers are modelled, not observed

Not in the SPEC brief, but it is a dataset property the descriptor must state and it was
sitting in the same searches. SCP's county-level screening and risk-factor estimates are
**model-based small-area estimates** that combine BRFSS with NHIS in a multilevel model,
not direct survey estimates. The methodology paper is Raghunathan et al.
[`raghunathan2007combining`]; the operational description covering 11 smoking and screening
outcomes for 3,112 counties is Liu et al. [`liu2019smallarea`]; the most recent extension
(PSA testing, 3,142 counties) is Liu et al. [`liu2025psa`].

This matters for two reasons. It means the risk/screening topic has a different epistemic
status from incidence and mortality — modelled versus registry-observed — and a data descriptor
that presents all four topics in one harmonized schema is obliged to say so. And it means
those columns can change between vintages because *the model was refit*, independent of any
new data. Both are Usage Notes, and both are cheap to state.

---

## Strand 3 — Genre precedent

Six Scientific Data descriptors built on scraped or re-extracted public/government data. All
verified via PubMed. For each I note **how it framed novelty relative to the upstream source**,
because that is what §5 asks for and what determines whether this manuscript survives triage.

**1. Hasell et al., cross-country database of COVID-19 testing** [`hasell2020testing`].
*The closest analogue in the set, and the model to copy.* Every number in it came from official
government sources that were already public. The novelty claim is built on four things, none of
which is the data itself: (i) the sources are scattered across 94 countries and not
comparable as published; (ii) the descriptor ships **metadata describing data quality and
comparability issues needed for interpretation** — i.e. the caveats are a deliverable, not a
limitations paragraph; (iii) the collection is **"entirely replicable, with sources provided
for each observation"** — per-row provenance; (iv) it is a maintained time series, updated by
"automated scraping and manual collection and verification." Read that list against this
archive: per-row `url` and `_extracted_at`, a documented suppression vocabulary, a machine-
readable `scrape_catalog.jsonl`, and monthly automated releases. The mapping is close to
one-to-one, and it is the strongest evidence that the genre accepts this kind of contribution.

**2. Xu et al., COVID-19 real-time case information** [`xu2020covidcases`]. Individual-level
records curated from "national, provincial, and municipal health reports, as well as additional
information from online reports." Novelty framed almost entirely as **assembly plus
geocoding**: scattered official reports become one geo-coded, harmonized, machine-readable
table. Notably it makes no methodological claim at all. Useful as the floor — this cleared
Scientific Data on aggregation and timeliness alone.

**3. van Heusden et al., FAIR Dutch Freedom of Information Act documents**
[`vanheusden2025foia`]. The framing sentence is worth lifting almost verbatim: the material is
already public, but "the current publication landscape is very scattered, with many
organizations publishing on their own websites, with little to no coordination on document
structure, (meta)data quality, and without a standardized metadata format." Novelty = metadata
standardization + quality checks + FAIR deposition in a repository. This is the "the data is
public but not usable" argument in its purest published form, and it is a 2025 acceptance, so
it reflects current editorial practice rather than 2020 pandemic latitude.

**4. Ocagli et al., JECFA portal** [`ocagli2024jecfa`]. R scripts scrape a WHO/FAO
intergovernmental database; the result is 6,552 records. The authors are conspicuously modest —
they call it "primarily… an automated indexing tool" and state plainly that manual work is
still needed to extract detailed data. Their validation is a systematic comparison against a
manually collected subset. Two lessons: **understating the claim did not sink it**, and
**validate against a hand-built subset** — which for this archive means reconciling a sample of
released rows against fresh live SCP pulls, an executable-chunk-sized piece of work that would
directly serve Technical Validation.

**5. Karnik et al., nature-based carbon offset project boundaries** [`karnik2025offsets`].
Scraped from carbon project registries (75% of entries) plus manual georeferencing (22%).
Novelty framed as **enabling an analysis the upstream form blocks**: verifying offset efficacy
"is complicated by a lack of readily available geospatial boundary data." The reusable move is
naming the downstream question the upstream format prevents. For this archive that question is
the cross-topic county join — incidence × mortality × screening × demographics — which is
prohibitive one query at a time and trivial against four files.

**6. Zhang et al., 2022 election advertising from Meta and Google**
[`zhang2025adtransparency`]. Collected from platform ad-transparency libraries — i.e. from
sources whose entire purpose is public disclosure. Novelty framed as **comparability
engineering**: two providers' disclosures made comparable through added labels, plus derived
features. Closest to this archive's decoded-label columns, where the contribution is a
consistent vocabulary across slices that upstream never reconciles.

### What the six have in common

None claims to have generated new observations. Every one claims some combination of:
**scattered → assembled**, **inconsistent → harmonized**, **undocumented → documented with
quality metadata**, **ephemeral → deposited and citable**, **inaccessible → enabling a
specific named downstream analysis**. Not one leads with "we scraped a website."

The one thing none of them has is the vintage argument. Hasell et al. maintain a live series;
they do not preserve superseded values as first-class retrievable objects. That is where this
archive is doing something the genre has not already absorbed — which is exactly why SPEC.md's
ordering (reuse value leads, vintage differentiates) is the right way round: the first argument
gets you past triage on established precedent, the second is what makes the resource
non-substitutable.

---

## Does anything found here threaten the differentiation claims in `docs/landscape.md`?

Taking the four surviving claims in turn.

**Bulk access — survives, but one sentence has to be rewritten.** No bulk SCP *dataset* exists
anywhere: not on Zenodo, Dryad, figshare or Dataverse, and NCI publishes no API or bulk
download. That claim is intact. What is **not** intact is any claim that nobody else has built
a national sweep — `[ciodata_ciftools]` is one, and a competent one. The correction is small
and it makes the argument better rather than worse: the differentiator is not the sweep, it is
the *published, versioned, citable artifact*. Another team built the same machinery and it
lives inside a dashboard pipeline with no release, no tag and no DOI. Write it that way and a
reviewer who finds the repo finds you already said so.

The published SCP-using papers reinforce the point from the other side: they are almost all
single-slice analyses (one cancer, one window, one geography tier), which is what the per-query
interface makes cheap — and the three CRAN packages carrying frozen 2016-vintage exports show
what people do when they need the data to sit still. Crowley et al. is a partial exception — a
national county-level analysis that also confirms, incidentally, that the **2023 RUCC vintage
is now what SCP county data carries** [`crowley2026oncologists`], corroborating the schema-drift
finding in `docs/landscape.md` from an independent published source.

**Historical vintages — unthreatened, and strengthened.** No SCP vintage archive exists, and
`clegg2002reportingdelay` supplies the citable reason why one should. If anything the
literature raises the ceiling on this claim: revision of published cancer estimates is
documented, quantified, and capable of reversing trend conclusions. Two constraints on how it
is stated. The vintage count must be reported honestly however small it is (SPEC.md §6 already
requires this). And `kim2022twentyyears` means part of vintage-to-vintage difference in the
trend columns is a **software version change**, not a data revision — the manuscript should say
so rather than let a reviewer discover it.

**Analysis-ready shape — unthreatened, but this is where the genre bar actually sits.** Every
precedent in Strand 3 rests on it, so it is well-trodden ground, which cuts both ways: it is
accepted, and it is therefore expected to be done well. Two specific exposures. First, SPEC.md
§6 already flags that demographics race labels carry undecoded escapes and a different
vocabulary from incidence/mortality — the "consistent vocabulary" claim is the one
`zhang2025adtransparency` makes, and it is falsifiable by inspection, so `normalize.py` must
land before the claim is written. Second, the four topics do not have uniform epistemic status:
risk/screening is modelled small-area estimation [`liu2019smallarea`], incidence and mortality
are registry-derived. Presenting them in one harmonized schema without saying so would be a
fair reviewer complaint.

**Reproducibility — unthreatened.** Standard, well-supported by `klump2021versioning`.

**The real threat is not on this list.** It is the suppression claim, and `docs/landscape.md`
already identified it: through the 19 historical releases the archive drops suppressed rows
outright, which is worse than `cancerprof`'s behaviour. The literature makes that gap more
costly, not less, because `tatalovich2022zonedesign` and the three 2026 SCP-user papers
establish that suppression is *the* recognised limitation of county cancer data. A descriptor
that leads its Methods with suppression decoding, as SPEC.md §6 directs, is claiming exactly
the axis the field cares most about — so the PR #39 scoping ("true only of releases from #39
forward, historical vintages expose suppression only by cross-product differencing") is not a
minor footnote. It is the sentence a methodological-skeptic reviewer will go looking for, and
it needs to appear before they have to.

Net: no claim has to be dropped, one has to be reworded. The bulk-access claim must shift from
"nobody else does this" to "nobody else has published the result" — `[ciodata_ciftools]` makes
the stronger version false. The vintage claim got stronger and gained a cancer-domain citation
[`clegg2002reportingdelay`]. Analysis-ready shape turns out to be the genre's price of entry
rather than a differentiator. Suppression is the exposed flank, and the literature is precisely
why it is exposed.

---

## Loose ends someone should close by hand

Listed so they don't get silently absorbed as findings.

1. **`10.5281/zenodo.13174526` / `10.5281/zenodo.18446185` exist.** Reconcile against `docs/landscape.md`'s
   "DOI pending" and against SPEC.md M3's scope before either is repeated. Also note the brief's
   `10.5281/zenodo.11098814` did not match what the Zenodo API returned (`…11102940`); one of the two
   is wrong and it should be settled before anything cites it.
2. **OSF `bjzr5`, "Erased at the margins: suppression bias in cancer disparities."** Contributors
   and DOI unverified (JS-rendered). Nearest thing to a competitor on the headline claim.
3. **`10.1200/CCI.24.00099`** ("Interinstitutional Approach to Advancing Geospatial…", JCO CCI)
   surfaced in catchment-area searching but could not be verified — ASCO returned 403, Ovid 402,
   and it is not indexed in PubMed. Title and DOI come from a search snippet only. **Do not cite.**
4. **Simeonov & Himmelstein (PeerJ)**, the elevation/lung-cancer paper behind `dhimmel/elevcan`.
   PMID 25648772 is confirmed to exist, but volume/pages/DOI were taken from a repository README,
   not an opened record. Verify if you want it.
5. **`CIOData/CIFTools_update` attribution.** That it is the Cancer InFocus team's code is inferred
   from GitHub org identity and author overlap, not stated anywhere. Confirm before asserting it
   in print, since it names a specific group.
6. **Cancer InFocus pagination.** PubMed still carries the ahead-of-print form (OF1–OF5). Crossref
   gives **32(7):889–893**, which is what `refs.bib` uses.
7. **No citation exists for State Cancer Profiles itself.** There is no descriptor paper. Cite it
   as a web resource with an access date. The same applies to Cancer InFocus, which has no software
   DOI and no public canonical repository — its citable form is `[burus2023cancerinfocus]`.
8. **`refs.bib` carries more than this document cites.** Six further verified entries for
   published SCP reuse are in there unreferenced, for the manuscript's Background & Summary to
   draw on: `[drake2025community]`, `[crowley2026oncologists]`, `[zhang2024oncologydensity]`,
   `[wei2025tanning]`, `[joseph2022pesticides]`, `[shalowitz2015geographic]`. They span 2015
   to 2026 and cover oncology workforce, environmental exposure, screening and access —
   useful for showing breadth of reuse rather than a single niche.
9. **Gap, not a finding:** no paper was found that quantifies bias introduced into a downstream
   regression by *cell suppression specifically* in county cancer rates. If the manuscript wants
   that, it must demonstrate it from the archive's own data.
