# API Research Summary: 14 Data Sources

> Compiled: 2026-10-13 · Test environment: Python 3.12, egress IP in Singapore
> Chinese version: [SUMMARY_zh.md](SUMMARY_zh.md)

**About sources**: anything not marked comes from official documentation. Marks in parentheses mean:
- (tested): observed in live calls, not in the docs
- (semi-official): from vendor-partner open-source code or docs
- (unconfirmed): not found in official docs and not tested

---

## 1. Overall status

| Status | Sources |
|---|---|
| **Verified with real requests, usable** | USAspending, Grants.gov, GovInfo, CourtListener, SAM.gov, OSHA, UCC Filings (Colorado + Connecticut) |
| **Usable, but the API itself is limited** | DOJ (title match and single-day lookup only); api.ftc.gov (HSR notices only) |
| **Not usable** | FTC press releases: this machine's IP is blocked by the site, needs a US IP<br>USPTO: key requires ID.me, which needs a US ID; dropped |
| **Paid, awaiting credentials** | D&B Direct+, Moody's Orbis, Quartr (earnings calls), LexisNexis: code written per docs, never run with real credentials |

**Credentials**:
- Configured (all in `.env`): api.data.gov key (shared by GovInfo and api.ftc.gov), CourtListener token, SAM.gov key, DOL key (OSHA).
- Everything else: not configured.

---

## 2. Quick reference

| Source | Available | Country coverage | What you get | Auth / cost | Keyword search | Date filter | Timestamp precision | Rate / quota | Suggested schedule |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **USAspending** | Yes | US federal contracts and grants; recipients and places of performance can be abroad (215 countries/areas) | Federal contracts/grants: IDs, recipient, amount, agency, industry codes, competition, performance period | No key, free | Yes: `keywords` | Yes: `time_period`, 4 date types | last-modified to the second | Unpublished; max 50k results per query | Daily |
| **Grants.gov** | Yes | Grant opportunities from US federal agencies | Grant opportunities: title, agency, funding amounts, eligibility, deadlines, contacts, attachments | No key, free | Yes: `keyword` | No; sort then filter locally | list: date only; detail: to the second (with TZ) | Unpublished | Daily |
| **GovInfo** | Yes | US federal publications only | Federal Register, regulations, bills, Congressional Record, court opinions, etc.: metadata + PDF/XML full text | Free api.data.gov key | Yes: full text | Yes: publish-date range + ingest-time incremental | ingest time to the second | 36,000/hr | Daily |
| **CourtListener** | Yes | US federal, state, territorial and tribal courts (plus 3 historical English courts) | Court opinions (with full-text links), federal dockets, parties, attorneys, judges | Free token (search works anonymously) | Yes: boolean syntax | Yes: filed-date range + modified-time incremental | ingest time to the microsecond | **5/min, 50/hr, 125/day** | Every 1–2 h |
| **SAM.gov** | Yes (only 10 calls/day) | US federal procurement; registrants can be foreign companies | Contract opportunities (incl. awards), vendor registrations, procurement exclusion list | Free SAM key | Partial: title only | Yes: posted-date range (required, ≤ 1 yr) | date only | **10/day** | Daily |
| **DOJ** | Yes (title match and single-day lookup only) | US Department of Justice; defendants can be foreign nationals | DOJ press releases: title, full HTML text, issuing office, topic | No key, free | Partial: title match only | Partial: single day only | created/changed to the second | ≤ 4 req/s | Every 2–4 h |
| **api.ftc.gov** | Yes (HSR notices only, no press releases) | Mergers affecting US commerce; parties can be foreign | HSR early terminations: acquirer, acquired party, transaction number, date | Free api.data.gov key | Yes: field filters | Yes: field filters | to the second | 20,000/hr | Weekly |
| **OSHA** | Yes | 50 US states and territories | Safety inspections, violations and penalties, workplace accidents (11 tables, joined on inspection number) | Free DOL key | Yes: `like` matching | Yes: `gt`/`lt` | load time `load_dt` to the second | 10k records / 5 MB per request; bursts trigger 429 in testing | Daily |
| **UCC Filings** (CO / CT) | Yes (Colorado and Connecticut only) | Filings in Colorado and Connecticut only | Liens: debtors, secured parties, collateral (CO), filing date, lapse date | No key, free | Yes: `$where like` / `$q` | Yes: `$where between` | date only | IP-throttled without token; effectively unlimited with one | Daily |
| FTC press releases | No: this machine's IP is blocked by the FTC site; needs a US IP | US FTC | Press-release title, link, summary, publish time (full text needs the web page) | No API; RSS and web pages only | web page search only | RSS holds only the latest 10–30 items | `pubDate` with TZ | Site firewall blocks by IP | Daily (after an IP change) |
| USPTO | No: key requires ID.me identity verification, which needs a US ID | US patents and trademarks; applicants can be from any country | Patent applications: title, filing/grant dates, inventors, applicants, CPC, prosecution documents | Free key, but needs ID.me | Yes | Yes | ingest time to the second | 5M/week; no concurrency per key | — (dropped) |
| D&B Direct+ | No: paid, credentials not purchased | Global: 190+ countries, nearly 600M organizations | Company profiles: DUNS, address, industry, employees, financials, corporate linkage | Paid | Yes: `searchTerm` | No (change-notification subscription only) | transaction timestamp | per contract | — |
| Moody's Orbis | No: paid, credentials not purchased | Global: 635M+ companies (no official country count) | Global companies: firmographics, financials (by year), employees, ownership | Paid | name match / criteria | Unknown | must be requested in the query | per contract (semi-official: typically 1–10 concurrent) | — |
| Quartr | No: paid, credentials not purchased | Global: 16,000+ listed companies across 65+ markets | Listed-company earnings calls: events, transcripts, audio, slides, AI summaries | Paid | No: filter by ticker etc. only | Yes: event date + updated-time incremental | Unknown | default 50 req/s | — |
| LexisNexis | No: paid, credentials not purchased | Global: news sources from 170+ countries, 51 languages | News and legal documents: title, date, source + full text | Paid | Yes: boolean syntax | Yes: `Date ge/le` | publication date | per contract; ≤ 50 per page | — |

### Country coverage

Two layers: **which country's institution produces the data**, and **which countries the companies or people in the records can be in**. Government sources cover only the US government's own business, but counterparties can be foreign. Figures come from live queries on 2026-10-14; the four paid vendors use their official published figures.

| Source | Data produced by | Countries of the records' subjects | Basis |
|---|---|---|---|
| **USAspending** | US federal government | Worldwide. Of 5.78M FY2025 contracts, 103,866 went to foreign recipients (about 1.8%) and 162,470 were performed abroad, across 215 countries or areas; the largest non-US amounts were Japan, Germany, Canada, the UK and South Korea | tested |
| **SAM.gov** | US federal government | Worldwide. Foreign companies can register; 5,176 entities are registered in the UK (e.g. Barclays) | tested |
| **Grants.gov** | US federal government | Grant opportunities from US federal agencies; whether foreign organizations may apply depends on each opportunity's eligibility | official docs |
| **GovInfo** | US federal government (GPO) | US federal publications only: Federal Register, regulations, congressional documents, federal court opinions | official docs |
| **CourtListener** | US (aggregated by Free Law Project) | Mainly US courts, 3,359 in total: federal courts, state courts for the 50 states plus DC (55 state supreme courts), territorial courts (Guam, Northern Mariana Islands, Puerto Rico, Virgin Islands, etc.) and tribal courts (e.g. Cherokee Nation Supreme Court); plus 3 historical English courts (House of Lords etc.) with very little data | tested |
| **DOJ** | US Department of Justice | DOJ press releases; defendants can be foreign nationals (a sample featured a Colombian national) | tested |
| **api.ftc.gov** (HSR) | US FTC | Mergers affecting US commerce; both parties can be foreign (sample: Swiss ABB acquiring UK Rotork) | tested |
| FTC press releases | US FTC | US FTC press releases | official docs |
| **OSHA** | US Department of Labor | Workplaces in the 50 states and US territories (Puerto Rico inspections confirmed) | tested |
| **UCC Filings** | Colorado and Connecticut state governments | **Only filings made in these two states.** Debtors are mostly in-state (93% of Connecticut debtors are in CT), with a few out of state or abroad (Colorado has Canadian and UK debtors, among others) | tested |
| USPTO | US Patent and Trademark Office | US patents and trademarks; applicants can be from any country (unconfirmed, not tested) | — |
| D&B Direct+ | Global | 190+ countries and markets, nearly 600M organizations (2024 annual report); a few countries have no data (legacy docs list Antarctica, Cuba, North Korea, etc.) and some data blocks cover only certain regions, so ask D&B for its data-block coverage matrix | official |
| Moody's Orbis | Global | 635M+ companies from 170+ sources; no official country count. Over 99% are private companies, and financial depth depends on each country's filing rules | official |
| Quartr | Global listed companies | 16,000+ listed companies across 65+ markets; no public list of exchanges or countries, so you'd enumerate them via the API | official |
| LexisNexis (news) | Global | 33,000+ licensed news sources from 170+ countries in 51 languages; about 23,000 of them are licensed for generative-AI use | official |

---

## 3. Source-by-source details

### 3.1 USAspending.gov: federal contract and grant spending
- **How to call**: REST JSON. Search endpoints are all **POST**, with conditions in a JSON body.
  - Search: `POST /api/v2/search/spending_by_award/`
  - Count: `POST /api/v2/search/spending_by_award_count/`
  - Detail: `GET /api/v2/awards/{generated_internal_id}/`
  - Last update date: `GET /api/v2/awards/last_updated/`
  - Bulk download: `POST /api/v2/bulk_download/awards/` (generates a zip asynchronously)
- **What you get** (tested, actual responses):
  - **Search results** (13 fields each): `Award ID`, `Recipient Name`, `Description`, `Award Amount`, `Awarding Agency`, start/end dates, last-modified time, base obligation date, internal IDs.
  - **Detail** (167 fields):
    - Basics: PIID, type, `date_signed`, `total_obligation`, subaward count and amount, parent award.
    - Solicitation and competition: solicitation ID, solicitation procedure, number of offers received, extent competed, small-business set-aside type.
    - Classification: NAICS industry code, product/service code (PSC).
    - Compliance attributes: commercial item, multi-year contract, labor standards, foreign funding, etc.
    - Defense: DoD program codes.
    - Funding: outlays and obligations broken down by Disaster Emergency Fund Code (DEFC).
    - Performance period: start, end, potential end dates.
- **Timestamps**:
  - Search results: `Start Date` / `End Date` (dates), `Last Modified Date` (to the second), `Base Obligation Date`.
  - Detail: `date_signed`, `period_of_performance.*`.
- **Keyword** (supported): `filters.keywords: ["..."]`. Tested: "cybersecurity" narrowed 72M awards to 3,645.
- **Date** (supported): `filters.time_period: [{start_date, end_date, date_type}]`; `date_type` is one of `action_date` / `date_signed` / `last_modified_date` / `new_awards_only`. Tested: Filtering by signing date for Jan 2025 works.
- **Limits**:
  - No rate limit published (unconfirmed).
  - Max 100 per page (tested), default 10.
  - A single query can page through at most 50,000 results.
  - Search data starts 2007-10-01.
- **Updates**: nightly; DoD and USACE contract data is published with a 90-day delay.
- **Gotchas**:
  - `award_type_codes` must not mix groups (contracts A/B/C/D, grants 02–05, loans 07/08); mixing returns 400 (tested). The official example actually mixes them.
  - `Start Date` in search results is not the signing date.
- **Sources**: api.usaspending.gov/docs/endpoints; GitHub `usaspending-api/.../api_contracts` (spending_by_award.md, search_filters.md, etc.); usaspending.gov data PDFs. Official confidence: **high**.

### 3.2 Grants.gov: federal grant opportunities
- **How to call**:
  - Search: `POST https://api.grants.gov/v1/api/search2`
  - Detail: `POST /v1/api/fetchOpportunity {"opportunityId": ...}`
- **What you get** (tested, actual responses):
  - **Search results** (10 fields each): ID, opportunity number, title, agency code and name, open date, close date, status (forecasted/posted/closed/archived), document type, program numbers (CFDA/ALN).
  - **Detail** (140 fields):
    - Basics: title, number, revision, category, owning agency and parent agency.
    - Funding: estimated total, award ceiling and floor, expected number of awards, cost-sharing requirement.
    - Application: eligible applicant types, funding instruments (e.g. grant, cooperative agreement), funding activity categories.
    - Contact: name, phone, email.
    - Milestones: estimated posting, application due, award and project start dates.
    - Attachments and history: attachment folders, document URLs, history of every revision.
- **Timestamps**:
  - Search results: `openDate` / `closeDate` as `MM/DD/YYYY`, no time zone.
  - Detail: `postingDate`, `lastUpdatedDate`, etc., to the second with time zone (e.g. EDT).
- **Keyword** (supported): `keyword`. Tested: "cybersecurity" narrowed 1,462 to 192. You can also filter by `agencies` / `fundingCategories` / `eligibilities` / `aln` (program number) / `oppNum`.
- **Date** (not supported): **no date-range parameter**. Sort with `sortBy=openDate|desc` and filter locally (tested), or download the daily full XML extract.
- **History**: by default only forecasted and posted opportunities come back; add `oppStatuses=forecasted|posted|closed|archived` for history (tested: 192 → 2,126).
- **Limits**: no published rate or page-size limit (unconfirmed). Tested: `rows=5000` works; `rows=20000` fails.
- **Sources**: grants.gov/api/api-guide, /api/common/search2, /api/common/fetchopportunity, /xml-extract. Official confidence: **high**.

### 3.3 GovInfo (GPO): Federal Register, regulations, congressional documents, court opinions
- **Auth**: free api.data.gov key, passed as `api_key=`.
- **How to call**:
  - Full-text search: `POST /search`
  - Incremental by ingest time: `GET /collections/{code}/{lastModified start}`
  - By publish date: `GET /published/{date}`
  - Detail: `GET /packages/{id}/summary`, with PDF/XML/ZIP/MODS download links
- **What you get** (tested, actual responses):
  - **Coverage**: 42 collections, e.g. FR (Federal Register, 1M+ documents), CFR (federal regulations), USCOURTS (federal court opinions), BILLS (bills), CREC (Congressional Record), PLAW (public laws), BUDGET (budget).
  - **Search results** (15 fields): title, package ID, granule ID, collection code, government author, issue date, ingest date, last-modified time, plus PDF / TXT / ZIP / MODS download links.
  - **Incremental listing** (7 fields): package ID, title, document class, issue date, last-modified time, Congress number, detail link.
  - **Detail** (28 fields):
    - Publication info: volume, issue, page count, publisher, government authors, SuDoc class number.
    - Other identifiers: ISSN, etc.
    - Downloads: PDF / XML / ZIP / MODS / PREMIS links.
    - Granules: link to the list of granules (e.g. individual notices).
  - **Full text**: via the download links above (PDF / XML / TXT).
- **Timestamps**: `dateIssued` (publish date), `lastModified` (GovInfo ingest/update time, ISO 8601 to the second), `dateIngested`.
- **Keyword** (supported): `{"query": "antitrust collection:(FR)"}`. Tested: Federal Register total 1.027M → 14,650.
- **Date** (supported): add `publishdate:range(2025-01-01,2025-03-31)` to the query. Tested: 14,650 → 101, and 10/10 sampled records fell in range.
- **Limits**:
  - Personal key: 36,000/hr, 1,200/min, 40/s (tested: response headers match).
  - DEMO_KEY: docs say 30/hr and 50/day; tested: only 10 were granted, then a ~18-hour wait.
  - Max 1,000 per page; paginate with the `offsetMark=*` cursor (the old `offset` parameter is being deprecated).
- **Updates**: the Federal Register publishes on business days only; ingest times mostly fall between 06:00 and 15:00 UTC (tested).
- **Sources**: github.com/usgpo/api (README), api.govinfo.gov/api-docs (OpenAPI spec), govinfo.gov/help/finding-info, api.data.gov developer manual. Official confidence: **high**.

### 3.4 CourtListener (Free Law Project): opinions, PACER/RECAP dockets
- **Auth**: `Authorization: Token xxx`. `/search/` works anonymously (tested); other endpoints (e.g. `/dockets/`) return 401 without a token (tested).
- **How to call**: REST v4.
  - Search: `/api/rest/v4/search/?type=o|r|rd|d|oa|p` (opinions / RECAP dockets / RECAP documents / dockets only / oral arguments / judges)
  - Others: `/dockets/`, `/opinions/`, `/clusters/`
- **What you get** (tested, actual responses):
  - **Opinion search results** (47 fields):
    - Case: case name (short/full), docket number, court and jurisdiction, decision date, argued date, status, nature of suit.
    - Citations: citation, cite count, Lexis cite, neutral cite.
    - People: judges, panel, attorneys.
    - Content: procedural history, syllabus; per-opinion author, type, full-text download URL and matching snippet.
  - **RECAP docket search results** (50 fields):
    - Case: case name, docket number, court, date filed, date terminated, cause, jury demand, jurisdiction type.
    - People: assigned and referred judges, parties, attorneys, law firms, bankruptcy trustee.
    - Documents: per-document number, description, entry date filed, page count, availability, PACER document ID.
  - **Docket detail (REST, token required)** (60 fields):
    - Numbering: full docket number and its parsed components, PACER case ID.
    - Dates: filed, terminated, last filing, cert granted/denied.
    - Case info: nature of suit, appeal-from court, MDL status, bankruptcy info, linked opinions and oral-argument audio.
    - Record times: created, modified.
  - **Full text**: opinions have download URLs; RECAP documents have PDFs only if someone has purchased them.
- **Timestamps**:
  - `dateFiled`: decision date, date only.
  - `meta.timestamp` / `date_created` / `date_modified`: ingest or modification time, **to the microsecond** (tested).
- **Keyword** (supported): `q=` with AND/OR, "phrases" and field syntax (e.g. `caseName:xxx`). Tested: "antitrust" narrowed 8.33M to 44,907.
- **Date**:
  - `filed_after` / `filed_before` (tested) work (152 results for H1 2025, all in range), but the docs don't list these parameter names. The documented form is `q=dateFiled:[2025-01-01 TO 2025-06-30]`.
  - Incremental: `/dockets/?date_modified__gte=<ISO time>` (tested); 20/20 results were after the given time.
- **Limits**:
  - With a token, the default is **5/min, 50/hr, 125/day**; a 429 "5/min" was hit in testing.
  - Membership or a commercial agreement raises the limits. Anonymous traffic is throttled too, but no figure is published.
  - Non-search endpoints page through at most 100 pages.
- **Advice**: use the official bulk data (full CSV snapshots on S3) for history; don't page through the API.
- **Note**: RECAP coverage is incomplete. It comes mainly from documents bought by users of the RECAP browser extension, plus email, RSS and other sources.
- **Sources**: wiki.free.law/c/courtlistener/help/api/rest/v4/* (the old courtlistener.com/help/api/rest/ redirects there). Official confidence: **high**.

### 3.5 SAM.gov: contract opportunities, entity registrations, exclusions
- **Auth**: the Public API Key generated in your SAM.gov account (Account Details page). A generic api.data.gov key does not work (tested).
- **How to call**: REST JSON GET.
  - Opportunities: `/opportunities/v2/search`
  - Entities: `/entity-information/v3/entities` (v4 also exists)
  - Exclusions: `/entity-information/v4/exclusions`
- **What you get** (tested, actual responses):
  - **Opportunities** (41 fields):
    - Basics: title, notice ID, solicitation number, type (solicitation, award, presolicitation, etc.), active flag.
    - Agency: full agency hierarchy, office address.
    - Classification: NAICS industry code, product classification code, small-business set-aside type.
    - Dates: posted, response deadline, archive date.
    - Award: award date, contract number, amount, awardee name and location.
    - Contacts: name, email, phone, fax.
    - Links: SAM web link, attachment links. `description` is only a link; you must request it again with your api_key to get the text.
  - **Entities** (132 fields):
    - Identity: UEI, CAGE code, legal business name, DBA name.
    - Registration: status, registration date, expiration date, last-update date, exclusion flag.
    - Addresses: physical address, mailing address, congressional district.
    - Organization: entity type, profit structure, state or country of incorporation, start date, fiscal-year end.
    - Capabilities: business types and SBA certifications, primary NAICS and all NAICS/PSC codes, credit-card acceptance.
    - Contacts: government business POC and electronic business POC.
  - **Exclusions** (46 fields):
    - Exclusion details: classification, exclusion type, excluding agency, exclusion program.
    - Excluded party: person or company name, UEI, CAGE, NPI (healthcare provider number), address.
    - Action history: create, update, activate and termination dates, termination type.
    - Other: additional comments, investigation status, other locations; for vessels, call sign, tonnage, flag and owner.
- **Timestamps**:
  - Opportunities: `postedDate`, `responseDeadLine`, `archiveDate`, `award.date`, date only.
  - Entities: `registrationDate`, `lastUpdateDate`, `registrationExpirationDate`.
  - Exclusions: `createDate` / `updateDate` etc., in **`MM-DD-YYYY`** format, unlike the other APIs (tested).
- **Keyword**:
  - Opportunities: `title=` (title only). Tested: "cybersecurity" narrowed 15,236 to 4.
  - Entities: `legalBusinessName` / `q` / `ueiSAM` / `cageCode`.
- **Date** (supported): `postedFrom` and `postedTo` are **required**, format `MM/dd/yyyy`, span ≤ 1 year. Tested: 10/10 sampled records in range. Entities accept `registrationDate=[from,to]`.
- **Limits**:
  - Personal key with no role: **10/day**; with a role: 1,000/day; federal system account: 10,000/day.
  - Responses carry no remaining-quota info (tested), so you must count calls yourself.
  - `limit` max 1,000.
  - The terms of use require rotating the key every 90 days.
- **Data tiers**: Public / FOUO (contact details etc., needs the Read FOUO role) / Sensitive (tax IDs, bank info; needs a federal system account).
- **Gotcha**: with an invalid key, **every path returns an empty-body 404**, not 401, which looks like a wrong URL (tested). With a valid key, access from Singapore works fine (tested).
- **Sources**: open.gsa.gov/api/get-opportunities-public-api, /entity-api, /exclusions-api; sam.gov/about/terms-of-use. Official confidence: **high**.

### 3.6 DOJ News
- **How to call**: `GET https://www.justice.gov/api/v1/press_releases.json`; there is also `blog_entries.json`. `speeches` and `videos` don't exist (404 in testing (tested)). Fallback: RSS `/news/rss?type=press_release` (tested).
- **What you get** (tested, actual responses, 19 fields each):
  - `title`, press-release `number` (e.g. 26-1168), `body` (full HTML), `teaser` (HTML), `url`, `uuid`.
  - `component` (issuing office, e.g. Criminal Division, Antitrust Division), `topic` (e.g. Homeland Security Task Force), images and attachments.
  - Times: `date` / `created` / `changed`.
  - 270k+ records since 2009. `blog_entries` (blog posts, 3,342) is also available.
- **Timestamps**:
  - `date`: Unix seconds; observed as 12:00 UTC on the publish day, so date precision only (tested).
  - `created` / `changed`: Unix seconds wrapped in an HTML `<time datetime="...">` tag, to the second.
- **Keyword** (partial): only `parameters[title]` for title matching (tested: "antitrust": 270k → 270). **`parameters[keyword]` is silently ignored**; the total doesn't change (tested).
- **Date** (partial): `parameters[date]` matches a single day only. The official example uses a Unix timestamp; tested: `YYYY-MM-DD` also works. No ranges.
- **Sorting**: `sort=date&direction=DESC`. Without it, results start from the oldest (2009) (tested).
- **Limits**: max 50 per page; **more than 4 requests per second may get you throttled or blocked**.
- **Gotchas**:
  - Unknown parameters don't raise errors; they return everything. Always check `resultset.count` (tested).
  - The developer page says component filtering is supported, but `parameters[component]` had no effect in testing.
- **Updates**: business days only, about 50 per day, which is exactly one page, so you need to paginate (tested).
- **Sources**: justice.gov/developer/api-documentation/api_v1 (updated 2025-12-18), justice.gov/developer, justice.gov/legalpolicies. Official confidence: **high**.

### 3.7 FTC (Federal Trade Commission)
- **What you get**:
  - **Press-release RSS** (standard RSS 2.0 fields, seen from another host): title, link, summary, `pubDate` with time zone (e.g. `Thu, 08 Oct 2026 08:00:00 -0400`). The full text requires fetching the web page.
  - **HSR early-termination notices** (api.ftc.gov, tested response, 8 fields):
    - Transaction: `transaction-number`, `title`.
    - Parties: `acquiring-party`, `acquired-party`, and the specific `acquired-entities`.
    - Times: early-termination `date`, record `created` / `updated` times.
- **Press releases**: no API; RSS and web pages only.
  - RSS URLs: `/feeds/press-release.xml`, `-competition.xml`, `-consumer-protection.xml`. Confirmed live from another host.
  - The web list supports keyword search via `?search_api_fulltext=` (tested).
  - RSS holds only the latest 10–30 items; `pubDate` includes a time zone (tested).
- **This machine's IP is blocked**: www.ftc.gov returns an "abusive automated request" page (a fake 404) for every path, homepage included (tested). Either run from a US machine or server, or email PWH-Alert@ftc.gov as the block page suggests.
- **api.ftc.gov** (usable): only two datasets, HSR early-termination notices and DNC complaints, **not press releases**.
  - Format: JSON:API.
  - Filtering: `filter[title][value]` + `[operator]=CONTAINS` (tested: works).
  - Paging: `page[limit]` / `page[offset]`, max 50 per page.
  - Sorting: `sort[x][path]=created&sort[x][direction]=DESC`.
  - Timestamps: `created` / `updated` (to the second), `date`.
  - Quota: tested 20,000/hr. HSR notices are released in weekly batches (tested).
- **Sources**: ftc.gov/developer, ftc.gov/developer/api/v0/endpoints/hsr-early-termination-notices, ftc.gov/news-events/stay-connected/ftc-rss-feeds. Official confidence: **high**.

### 3.8 USPTO (dropped)
- **What you could get** (per official docs, not tested):
  - Patent applications: application number, invention title, filing date, grant date, patent number, publication date, application status, inventors, applicants, CPC classification, ingest time.
  - Other: prosecution documents (`/documents` per application), plus sub-resources such as assignments and continuity.
  - Trademarks (TSDR): status and prosecution documents, looked up by case number.
- The patent API (Open Data Portal) requires `X-API-KEY`. Getting a key needs a USPTO.gov account + MFA + **ID.me identity verification (requires a US ID)**; the key page is data.uspto.gov/apikey. The trademark API (TSDR) needs a separate key. The bulk-data API also needs a key (tested).
- What the API can do (checked against official docs):
  - Search: `q`, OpenSearch syntax.
  - Date: `rangeFilters` on filingDate / grantDate etc.
  - Incremental: `lastIngestionDateTime` (ingest time).
  - Limits: 5M metadata calls/week, 4–15 req/s, no concurrent calls per key.
  - Trademarks: lookup by case number only, 60/min.
- PatentsView: migration began 2026-03-20. Bulk tables are on the new platform, but the API isn't there yet.
- Google Patents (BigQuery) was considered as a replacement; you chose not to use it, so it was not added.

### 3.9 Paid sources (code written per docs; not run with real credentials)

| | D&B Direct+ | Moody's Orbis | Quartr | LexisNexis |
|---|---|---|---|---|
| **Auth** | OAuth2: Basic(key:secret) → `POST /v3/token` (form-encoded) → Bearer, 24 h | `ApiToken` header (semi-official) | `x-api-key` header | OAuth2: `auth-api.lexisnexis.com/oauth/v2/token` → Bearer, 24 h |
| **What you get** (per docs/specs, not tested) | DUNS number, company name and trade-style names, address, phone, website, registration numbers, industry codes, employee counts, financials, legal entity type, control status, corporate linkage (parent/subsidiaries); more depends on which Data Blocks you buy | BvD ID, name, country, NACE industry, operating revenue (`OPRE`, per year), employees (`EMPL`); the partner code lists 496+ selectable fields, including ownership (semi-official) | Companies (name, tickers, ISIN, CIK, country), events such as earnings calls (title, date, fiscal year, fiscal period, type), file URLs for transcripts / audio / slides / reports, live transcripts, AI summaries | News: ResultId, title, date, source, location/jurisdiction, similar documents; `$expand=Document` returns the full text (raw XML) in the same call |
| **Main endpoints** | `cleanseMatch` (name → DUNS number), `search/criteria`, `data/duns/{duns}?blockIDs=` | `Companies/match`, `Companies/data` (WHERE + SELECT) (semi-official) | `/public/v3/companies`, `/events`, `/documents/transcripts`, etc. | `services-api.lexisnexis.com/v1/News` (OData) |
| **Keyword** | Yes: `searchTerm` | name match (semi-official) | No: ticker/ISIN/CIK only | Yes: `$search` (boolean search) |
| **Date** | No: Monitoring change notifications only | Unknown | Yes: `startDate/endDate`; `updatedAfter` for incremental | Yes: `$filter=Date ge ... and Date le ...` |
| **Limits** | per contract; 429 when exceeded; quotas reset daily at 00:00 UTC | semi-official: typically 1–10 concurrent | default 50 req/s; max 500 per page | per contract, 429 when exceeded; max 50 per page |
| **No-credential probe** | 401 (error code 00004) (tested) | 401 `error.token.rejected` (tested) | 401; v1/v2 retired (410) (tested) | token endpoint 401, data endpoint 498 (tested) |
| **Doc reliability** | Medium: docs now need a login; checked via 2024-11 archives | **Low: no public docs**; everything comes from partner open-source code | High: docs and OpenAPI are public | Medium-high: spec files on dev.lexisnexis.com are public |
| **When credentials arrive** | Confirm the v3 token works | **Adjust request bodies and field codes against the contract docs** | Run as is | Confirm dataset names (e.g. `News`, `CompanyAndFinancial`) |

---

### 3.10 OSHA (Occupational Safety and Health Administration): inspections, violations, accidents
- **Auth**: free DOL API key as `X-API-KEY`, issued after registering at dataportal.dol.gov; configured in `.env`. The dataset catalog `/v4/datasets` needs no key (tested).
- **How to call**: `GET https://apiprod.dol.gov/v4/get/OSHA/{table}/json?X-API-KEY=...`; field definitions at `/json/metadata` (name, description, type and linked tables per field) (tested); csv and xml formats are also supported.
- **What you get** (tested, actual responses):
  - **Inspections** `inspection` (36 fields): inspection number `activity_nr`; establishment name, site address, mailing address, employee count; owner type; NAICS and SIC industry codes; inspection type and scope (e.g. accident, complaint, planned); safety or health inspection; union status; open date `open_date`, case-modified date, close dates.
  - **Violations** `violation` (29 fields): inspection number, citation ID, cited `standard` (e.g. 1910.212), violation type (serious, willful, repeat, etc.), gravity, instances and people exposed, **initial and current penalty**, issuance date, abatement date, final order date, contest date, hazardous-substance codes.
  - **Accidents** `accident` (16 fields): summary number, event date, **event description** (e.g. "Three employees struck by vehicle"), keywords (e.g. Guardrail, Struck By), fatality flag, project type and cost, building stories. The injured-person table `accident_injury` and narrative table `accident_abstract` are separate.
  - Other tables: `violation_event` (violation history), `related_activity`, `emphasis_codes` (emphasis programs), `optional_code_info`, etc.
  - Tables join on `activity_nr` (tested): a violation can be traced back to the inspected establishment.
- **Timestamps**: business dates (open, issuance, event) are date-only; every table has a load time `load_dt` **to the second** (tested), suitable for incremental sync.
- **Keyword** (supported, tested): `filter_object={"field":"estab_name","operator":"like","value":"%WALMART%"}`; 20/20 results contained WALMART.
- **Date** (supported, tested): compare date fields with `gt` / `lt` inside `filter_object`, combinable with and/or. Tested `open_date` in Jan 2025: 20/20 in range; incremental `load_dt > 2026-10-01`: 20/20.
- **Limits**:
  - Max 10,000 records or 5 MB per request, whichever comes first; `limit` defaults to 10; paginate with `offset`.
  - No rate limit published, but **in testing, 429s started after about 20+ requests within ~10 minutes**, with no rate-limit headers and no `Retry-After`; access recovers on its own after a while (tested). The module spaces requests 3 seconds apart.
  - Filtered + sorted queries are occasionally very slow (over 40 seconds), so the module uses a 90-second timeout (tested).
  - **Sharing your key in public code repositories or forums is prohibited**.
- **Updates**: loaded daily; the latest `load_dt` seen was 2026-10-12 (tested).
- **Sources**: dataportal.dol.gov/api-guide and the user-guide PDF (2024-08-05 edition), apiprod.dol.gov/v4/datasets, `/json/metadata`. Official confidence: **high**.

### 3.11 UCC Filings (Uniform Commercial Code liens)
- **Background**: the US has **no federal UCC database**; each state's Secretary of State keeps its own records. The only free, live-queryable APIs are the open-data portals of **Colorado (CO)** and **Connecticut (CT)** (Socrata SODA API) (tested). Oregon publishes a monthly file of the previous month's filings.
- **Auth**: no key needed (tested). A Socrata app token (`X-App-Token` header) is optional and gives you your own quota.
- **How to call**: `GET https://data.colorado.gov/resource/{dataset id}.json` and `https://data.ct.gov/resource/xfev-8smz.json`, with SoQL parameters `$where` / `$q` / `$order` / `$select` / `$limit`.
- **What you get** (tested, actual responses):
  - **Colorado**: 2.6M filings back to 1966, in 4 tables joined on `fileid`:
    - Filings `wffy-3uut`: transaction ID, master document ID, transaction type (initial, amendment, continuation, termination), filing date, lapse date, document type, termination flag.
    - Debtors `8upq-58vz`: organization or individual name, organization type, jurisdiction, address.
    - Secured parties `ap62-sav4` (2.09M): organization or individual name, address, assignor flag.
    - Collateral `4am6-w6u4`: collateral description, farm-product flag, county.
  - **Connecticut**: 848k rows in one flat table: lien/UCC numbers, status, filing type, debtor name and address, secured-party name and address, accepted date `dt_accept`, lapse date `dt_lapse`, page count. **No collateral field.**
- **Timestamps**: filing, accepted and lapse dates as time-zone-less timestamps; date precision only (tested).
- **Keyword** (supported, tested): `$where=upper(organizationname) like '%BANK%'`. Colorado secured parties 2.09M → 608k; `$q=` full-text search also works.
- **Date** (supported, tested): `$where=filingdate between '2026-09-01T00:00:00' and '2026-09-30T23:59:59'`; Colorado 2.6M → 10,609, and 20/20 sampled records in range. Connecticut keyword + date combined: 848k → 2,023.
- **Limits**:
  - Without an app token, requests share an IP-based pool and too many get a 429; no figure is published.
  - With an app token, requests are "currently not throttled" unless deemed abusive.
- **Updates**: Colorado updates automatically "every day after midnight" (latest filing seen: 10/11); Connecticut updates daily (latest seen: 10/12) (tested).
- **Other states and national coverage** (research findings, not tested):
  - Most states sell bulk files only, e.g. Texas $65/day ($1,150 for the full master), Kentucky $1,500/month; Washington, Minnesota and Illinois offer weekly updates.
  - California and New York offer web search only, and California has anti-bot protection.
  - Commercial APIs: **Middesk** (50 states, includes collateral and lapse date, per-business lookup); **D&B UCC Filings** (the 10 most recent filings per DUNS, or name search with a date range; needs a separate entitlement, and Direct+ support must be confirmed).
  - LexisNexis's Web Services API showed no UCC content; its UCC data lives in its separate Public Records products.
- **Sources**: data.colorado.gov dataset metadata, catalog.data.gov (Connecticut), dev.socrata.com/docs/app-tokens.html; each state's bulk products on its Secretary of State site. Official confidence: **high** (CO/CT).

## 4. Cross-cutting notes

1. **Two kinds of time**:
   - "Business time": publish, sign or decision dates, mostly date-only.
   - "Ingest/update time": `lastModified`, `date_modified`, `updatedAfter`, `Last Modified Date`, to the second or even microsecond. **Use the latter for incremental sync.**
2. **Date formats vary**: ISO, `MM/DD/YYYY`, `MM-DD-YYYY`, Unix seconds, HTML `<time>` tags, `Aug 01, 2024 12:00:00 AM EDT`. `parse_any_date()` in `common.py` handles all of them.
3. **Invalid parameters are silently ignored**: DOJ does this. Always compare totals before and after filtering to confirm a filter works (the test framework does exactly that).
4. **Non-standard error codes**: SAM returns 404 for an invalid key, LexisNexis returns 498 for an expired token, and the FTC block page is a fake 404.
5. **api.data.gov key**: shared by GovInfo and api.ftc.gov. DEMO_KEY is only good for a quick trial.
6. **IP restrictions**: only the FTC website blocked this IP. All other sources, including SAM, work from Singapore.

---

## 5. Suggested schedule (Singapore/Beijing time, UTC+8)

| Frequency | Source | Time | Requests per run |
|---|---|---|---|
| Every 1–2 h | CourtListener (`date_modified__gte` incremental) | on the hour | ≤ 2 |
| Every 2–4 h | DOJ (newest first, stop at a known uuid) | 00/04/08/12/16/20 h | 1–3 |
| Daily | SAM.gov opportunities (`limit=1000`, postedFrom/To = yesterday) | 20:00 | 1–2 |
| Daily | USAspending (check `last_updated` first), Grants.gov | 20:00 | a few |
| Daily | GovInfo (`/collections/FR/{last run}`) | 00:00 | a few |
| Daily | UCC (CO/CT, `$where` filing date = yesterday) | 16:00 (US data refreshed after midnight) | 2–6 |
| Daily | OSHA inspections (`open_date` > last run) | 20:00 | 1–3 |
| Weekly | api.ftc.gov HSR notices | Thursday | 1 |

**The test script also uses quota**: one SAM run costs 4 calls (at most 2 test runs per day); one CourtListener run costs 5.

---

## 6. Project files and usage

```bash
pip install -r requirements.txt
cp .env.example .env              # add credentials (the 4 existing ones are already set)
python run_all.py                 # run all tests
python run_all.py sam doj         # run selected modules only
python run_all.py --render-only   # rebuild the report without making requests
```

| File | Contents |
|---|---|
| `apis/*.py` | One module per source: call examples + `META` (limits, sources) |
| `common.py` | Test framework: timestamp detection, filter verification, rate-limit header capture, automatic retry on 429 |
| `run_all.py` | Entry point; builds the report |
| `output/report.md` | Detailed test report: status, fields and sources for every request |
| `output/samples/` | Real response samples |
| `README.md` / `LIMITS.md` | Short summary / limits and schedule (Chinese) |
| `.env` | Credentials (**do not commit to git**) |

## 7. To-do

- [ ] UCC: for more states, decide between state bulk files and Middesk / D&B UCC
- [ ] FTC press releases: run `python run_all.py ftc` on a machine with a US IP
- [ ] Paid sources: test each once credentials arrive (adjust Orbis against the contract docs first)
- [ ] If SAM's 10/day is not enough: request a role in SAM (raises it to 1,000/day)
- [ ] If CourtListener's quota is not enough: consider membership, or switch to bulk data
