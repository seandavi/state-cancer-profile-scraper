# Verification: no API and no bulk-download endpoint at State Cancer Profiles

SPEC.md Task 0, item 9. This is the evidence behind a dated factual claim in the manuscript.

**Host checked:** `https://statecancerprofiles.cancer.gov`
**Access date:** **2026-08-23** (checks ran 15:27–15:38 UTC)
**Method:** `curl` from a Linux host, with browser User-Agent
`Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36`.
Saved responses are in `site/`, `tablepage.html`, and `raw2.csv` alongside this file.

## Verdict

As of 2026-08-23 the State Cancer Profiles website exposes **no public API and no bulk-download
endpoint**. The only machine-readable data export is a **per-query CSV** returned by appending
`output=1` to a table URL — the same URL the site's own "Export Data" link emits. It returns
exactly one statistical stratum per request.

The claim is supported by the site's own documentation, not only by probing: the FAQ describes
per-table export as *the* method, and the words "API" and "bulk" appear nowhere on any page checked.

## What was checked, and what was found

### 1. Site documentation — the strongest evidence

The FAQ (`/faq.html`, retrieved 2026-08-23) answers "How do I export or copy the data from a
graph, map or table?" with:

> Data is easily exported to a comma-separated value (CSV) file using the **"Export Data" link
> located to the right of most tables, graphs, and maps** on the Web site. […] For sections of the
> Web site that do not have an "Export Data" link, use the "Make Table" link instead. Select the
> data you want to copy from the data table, then **copy and paste** the data into your
> spreadsheet program.

Per-table export and manual copy-paste are presented as the complete set of options. No
alternative for whole-dataset retrieval is offered anywhere.

### 2. Word-level scan of all reachable documentation pages

Eleven pages fetched (all HTTP 200): `/index.html`, `/about/`, `/faq.html`,
`/dataUseRestrictions.html`, `/resources/`, `/data-topics/incidence.html`,
`/data-topics/mortality.html`, `/data-topics/demographics.html`,
`/data-topics/screening-risk-factors.html`, `/help/about/`, `/help/quick_ref/`.

- The string **"API" does not appear on any of them** (case-insensitive).
- The string **"bulk" does not appear on any of them**.
- Every occurrence of "download" refers to either a **PNG image** of a graph or the **Java
  Virtual Machine**. None refers to downloading data.

### 3. Site navigation

Top-level navigation is Home / About / Help & Resources / Contact. The data sections are
`/data-topics/{incidence,mortality,demographics,screening-risk-factors}.html`, plus a
`cancer-knowledge.html` link on the homepage that is **itself a dead link (HTTP 404)**. There is
no "Data", "Downloads", "Developers", or "API" section. `/resources/` is a link list of external
organisations (CDC USCS, NPCR, etc.), not a data-distribution page.

### 4. Path probing

| Path | Status |
|---|---|
| `/robots.txt` | **403 Forbidden** |
| `/` | 200 |
| `/api`, `/api/`, `/api/v1` | 404 |
| `/rest`, `/services`, `/ws`, `/graphql` | 404 |
| `/data`, `/datasets`, `/data.json` | 404 |
| `/download`, `/downloads`, `/downloads/all.zip` | 404 |
| `/export`, `/export/all`, `/alldata.zip` | 404 |
| `/sitemap.xml`, `/sitemap_index.xml` | 404 |
| `/swagger.json`, `/openapi.json` | 404 |
| `/.well-known/` | 404 |
| `/incidencerates/`, `/incidencerates/index.php` | 200 (the query-driven table UI) |

Note on `robots.txt`: it returns **403, not 404** — the server refuses it rather than reporting it
absent. This held with both a default `curl` User-Agent and a browser User-Agent. **No crawl
directives could be read**, so this exercise establishes nothing about the site's stated crawl
policy in either direction. Do not characterise the site as permitting or forbidding automated
access on this basis.

### 5. Client-side behaviour — is there an undocumented JSON backend?

A rendered county-level incidence table page (178 KB) was retrieved and its markup and script
references inspected. Findings:

- **No `fetch(`, `$.ajax`, `$.getJSON`, `$.get`, or `$.post` call appears in the page.**
- Every data-bearing URL in the page is a **server-rendered PHP query-string URL** —
  `/incidencerates/index.php?…`, `/incidencerates/graph.php?…`, `/map/index.php?…`,
  `/historicaltrend/index.php?…`. Sorting, graphing and mapping are all full page loads with
  different parameters, not API calls.
- Scripts loaded are jQuery, jQuery-UI, Bootstrap and site-specific presentation files
  (`incidencerates.js`, `freeze-table.min.js`, `NiceScale.js`). The only third-party endpoint is
  `matomo.php` / `static.cancer.gov/webanalytics/…`, i.e. web analytics.

So there is no private JSON API behind the UI that a client could be pointed at. The application
is entirely server-rendered.

### 6. The one machine-readable export, characterised

The "Export Data" link on the live table page resolves to:

```
/incidencerates/index.php?areatype=county&cancer=047&race=00&age=001&stage=999
  &year=0&type=incd&statefips=53&datatype=01&sex=0&ruralurban=0
  &sortVariableName=rate&sortOrder=desc&output=1
```

Confirmed live: returns HTTP 200 with `Content-Type: text/csv`. The payload is a report, not a
clean data file — a title block, then the data rows, then a footnotes block, separated by blank
lines (this layout is why `cancerprof`'s parser is fragile; see `landscape-cancerprof.md`).

Scope of a single request:

- **Geography is not the limiting axis.** `stateFIPS=00&areatype=county` returns **all 3,143 US
  counties plus the national aggregate in one response** (3,144 rows).
- **The stratum is the limiting axis.** One request returns exactly one
  (cancer site × race × sex × age × stage × year) combination. Every parameter takes a single
  enumerated code; the site's own form controls offer no "all" option for these dimensions.
- Reproducing one release of this archive took **18,852 such requests** (from
  `scrape_catalog.jsonl` in release `2026-06-01`).

## Precise scope — what this does and does not establish

Stated conservatively, because it goes into a paper.

**Established for 2026-08-23:** the site publishes no API and documents none; its own FAQ presents
per-table CSV export and copy-paste as the available methods; the words "API" and "bulk" appear on
none of the eleven documentation pages checked; a list of common API and bulk-download paths all
404; the UI makes no client-side data API calls; and the sole machine-readable export returns one
stratum per request.

**Not established / explicitly out of scope:**

- Pages were fetched as static HTML; **no JavaScript was executed and no headless browser was
  driven**. The conclusion about client-side API calls rests on reading the served markup and
  script references, not on observing runtime network traffic.
- Only the eleven documentation pages listed were scanned. This is not an exhaustive crawl of
  every URL on the host — and no sitemap or readable `robots.txt` was available to enumerate one.
- `robots.txt` returned 403, so **no statement is made about the site's crawl policy.**
- Path probing tests a finite list of conventional names. It cannot prove that no
  differently-named endpoint exists; it shows that no conventional one does and that none is
  documented.
- **Only `statecancerprofiles.cancer.gov` was checked.** Nothing here speaks to whether the same
  underlying statistics are obtainable in bulk from other NCI/CDC systems (SEER*Stat, CDC WONDER,
  US Cancer Statistics, data.gov). The manuscript should confine the claim to the State Cancer
  Profiles site specifically and not imply these statistics are unavailable in bulk anywhere.

## Suggested manuscript wording

> As of 23 August 2026, the State Cancer Profiles website provided no public API and no
> bulk-download facility. Its documentation describes per-table CSV export as the available
> method for obtaining data, and the site's sole machine-readable export returns a single
> statistical stratum per HTTP request; assembling a complete national county-level extract
> required 18,852 such requests.

Every element of that sentence is supported above. Re-verify and update the date before
submission, and again at revision — this is a live site and the finding is perishable.
