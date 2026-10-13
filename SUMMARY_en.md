# API Research Summary: 12 Data Sources

> Compiled: 2026-10-13 · Test environment: Python 3.12, egress IP in Singapore
> Chinese version: [SUMMARY_zh.md](SUMMARY_zh.md)

**Source labels** (every fact is tagged):
- ✅ official docs
- 🔶 semi-official: vendor-partner open-source code or docs
- 🧪 observed in live testing
- ❓ unconfirmed

---

## 1. Overall status

| Status | Sources |
|---|---|
| ✅ **Verified with real requests, usable** | USAspending, Grants.gov, GovInfo, CourtListener, SAM.gov |
| 🟡 **Usable, but the API itself is limited** | DOJ (title match and single-day lookup only); api.ftc.gov (HSR notices only) |
| ⛔ **Not usable** | FTC press releases: this machine's IP is blocked by the site, needs a US IP<br>USPTO: key requires ID.me, which needs a US ID; dropped |
| 🔑 **Paid, awaiting credentials** | D&B Direct+, Moody's Orbis, Quartr, LexisNexis: code written per docs, never run with real credentials |

**Credentials**:
- Configured (all in `.env`): api.data.gov key (shared by GovInfo and api.ftc.gov), CourtListener token, SAM.gov key.
- Everything else: not configured.

---

## 2. Quick reference

| Source | Auth / cost | Keyword search | Date filter | Timestamp precision | Rate / quota | Suggested schedule |
|---|---|---|---|---|---|---|
| **USAspending** | No key, free | ✅ `keywords` | ✅ `time_period`, 4 date types | last-modified to the second | Unpublished; max 50k results per query | Daily |
| **Grants.gov** | No key, free | ✅ `keyword` | ❌ none; sort then filter locally | list: date only; detail: to the second (with TZ) | Unpublished | Daily |
| **GovInfo** | Free api.data.gov key | ✅ full text | ✅ publish-date range + ingest-time incremental | ingest time to the second | 36,000/hr | Daily |
| **CourtListener** | Free token (search works anonymously) | ✅ boolean syntax | ✅ filed-date range + modified-time incremental | ingest time to the microsecond | **5/min, 50/hr, 125/day** | Every 1–2 h |
| **SAM.gov** | Free SAM key | 🟡 title only | ✅ posted-date range (required, ≤ 1 yr) | date only | **10/day** | Daily |
| **DOJ** | No key, free | 🟡 title match only | 🟡 single day only | created/changed to the second | ≤ 4 req/s | Every 2–4 h |
| **api.ftc.gov** | Free api.data.gov key | ✅ field filters | ✅ field filters | to the second | 20,000/hr | Weekly |
| FTC press releases | No API; RSS and web pages only | web page search only | RSS holds only the latest 10–30 items | `pubDate` with TZ | Site firewall blocks by IP | Daily (after an IP change) |
| USPTO | Free key, but needs ID.me | ✅ | ✅ | ingest time to the second | 5M/week; no concurrency per key | — (dropped) |
| D&B Direct+ | 💰 paid | ✅ `searchTerm` | ❌ (change-notification subscription only) | transaction timestamp | per contract | — |
| Moody's Orbis | 💰 paid | name match / criteria | ❓ | must be requested in the query | per contract (🔶 typically 1–10 concurrent) | — |
| Quartr | 💰 paid | ❌ filter by ticker etc. only | ✅ event date + updated-time incremental | ❓ | default 50 req/s | — |
| LexisNexis | 💰 paid | ✅ boolean syntax | ✅ `Date ge/le` | publication date | per contract; ≤ 50 per page | — |

---

## 3. Source-by-source details

### 3.1 USAspending.gov: federal contract and grant spending
- **How to call**: REST JSON. Search endpoints are all **POST**, with conditions in a JSON body.
  - Search: `POST /api/v2/search/spending_by_award/`
  - Count: `POST /api/v2/search/spending_by_award_count/`
  - Detail: `GET /api/v2/awards/{generated_internal_id}/`
  - Last update date: `GET /api/v2/awards/last_updated/`
  - Bulk download: `POST /api/v2/bulk_download/awards/` (generates a zip asynchronously)
- **What you get**: award ID, recipient, description, amount, awarding agency, start/end dates, last-modified time, etc. The detail endpoint has 167 fields.
- **Timestamps**:
  - Search results: `Start Date` / `End Date` (dates), `Last Modified Date` (to the second), `Base Obligation Date`.
  - Detail: `date_signed`, `period_of_performance.*`.
- **Keyword** ✅: `filters.keywords: ["..."]`. 🧪 "cybersecurity" narrowed 72M awards to 3,645.
- **Date** ✅: `filters.time_period: [{start_date, end_date, date_type}]`; `date_type` is one of `action_date` / `date_signed` / `last_modified_date` / `new_awards_only`. 🧪 Filtering by signing date for Jan 2025 works.
- **Limits**:
  - No rate limit published ❓.
  - Max 100 per page 🧪, default 10 ✅.
  - A single query can page through at most 50,000 results ✅.
  - Search data starts 2007-10-01 ✅.
- **Updates**: nightly ✅; DoD and USACE contract data is published with a 90-day delay ✅.
- **Gotchas**:
  - `award_type_codes` must not mix groups (contracts A/B/C/D, grants 02–05, loans 07/08); mixing returns 400 🧪. The official example actually mixes them.
  - `Start Date` in search results is not the signing date.
- **Sources**: api.usaspending.gov/docs/endpoints; GitHub `usaspending-api/.../api_contracts` (spending_by_award.md, search_filters.md, etc.); usaspending.gov data PDFs. Official confidence: **high**.

### 3.2 Grants.gov: federal grant opportunities
- **How to call**:
  - Search: `POST https://api.grants.gov/v1/api/search2`
  - Detail: `POST /v1/api/fetchOpportunity {"opportunityId": ...}`
- **What you get**: opportunity number, title, agency, open date, close date, status. The detail endpoint has 140 fields (funding, eligibility, revision history, etc.).
- **Timestamps**:
  - Search results: `openDate` / `closeDate` as `MM/DD/YYYY`, no time zone.
  - Detail: `postingDate`, `lastUpdatedDate`, etc., to the second with time zone (e.g. EDT) ✅.
- **Keyword** ✅: `keyword`. 🧪 "cybersecurity" narrowed 1,462 to 192. You can also filter by `agencies` / `fundingCategories` / `eligibilities` / `aln` (program number) / `oppNum`.
- **Date** ❌: **no date-range parameter**. Sort with `sortBy=openDate|desc` and filter locally 🧪, or download the daily full XML extract ✅.
- **History**: by default only forecasted and posted opportunities come back; add `oppStatuses=forecasted|posted|closed|archived` for history 🧪 (192 → 2,126).
- **Limits**: no published rate or page-size limit ❓. 🧪 `rows=5000` works; `rows=20000` fails.
- **Sources**: grants.gov/api/api-guide, /api/common/search2, /api/common/fetchopportunity, /xml-extract. Official confidence: **high**.

### 3.3 GovInfo (GPO): Federal Register, regulations, congressional documents, court opinions
- **Auth**: free api.data.gov key ✅, passed as `api_key=`.
- **How to call**:
  - Full-text search: `POST /search`
  - Incremental by ingest time: `GET /collections/{code}/{lastModified start}`
  - By publish date: `GET /published/{date}`
  - Detail: `GET /packages/{id}/summary`, with PDF/XML/ZIP/MODS download links
- **What you get**: 42 collections, e.g. FR (Federal Register), CFR, USCOURTS (court opinions), BILLS, CREC, PLAW.
- **Timestamps**: `dateIssued` (publish date), `lastModified` (GovInfo ingest/update time, ISO 8601 to the second ✅), `dateIngested`.
- **Keyword** ✅: `{"query": "antitrust collection:(FR)"}`. 🧪 Federal Register total 1.027M → 14,650.
- **Date** ✅: add `publishdate:range(2025-01-01,2025-03-31)` to the query. 🧪 14,650 → 101, and 10/10 sampled records fell in range.
- **Limits**:
  - Personal key: 36,000/hr, 1,200/min, 40/s ✅ (🧪 response headers match).
  - DEMO_KEY: docs say 30/hr and 50/day; 🧪 only 10 were granted, then a ~18-hour wait.
  - Max 1,000 per page ✅; paginate with the `offsetMark=*` cursor (the old `offset` parameter is being deprecated) ✅.
- **Updates**: the Federal Register publishes on business days only; ingest times mostly fall between 06:00 and 15:00 UTC 🧪.
- **Sources**: github.com/usgpo/api (README), api.govinfo.gov/api-docs (OpenAPI spec), govinfo.gov/help/finding-info, api.data.gov developer manual. Official confidence: **high**.

### 3.4 CourtListener (Free Law Project): opinions, PACER/RECAP dockets
- **Auth**: `Authorization: Token xxx` ✅. `/search/` works anonymously 🧪; other endpoints (e.g. `/dockets/`) return 401 without a token 🧪.
- **How to call**: REST v4.
  - Search: `/api/rest/v4/search/?type=o|r|rd|d|oa|p` (opinions / RECAP dockets / RECAP documents / dockets only / oral arguments / judges) ✅
  - Others: `/dockets/`, `/opinions/`, `/clusters/`
- **What you get**: opinions (8.33M), RECAP dockets (PACER filings), judge data.
- **Timestamps**:
  - `dateFiled`: decision date, date only.
  - `meta.timestamp` / `date_created` / `date_modified`: ingest or modification time, **to the microsecond** ✅🧪.
- **Keyword** ✅: `q=` with AND/OR, "phrases" and field syntax (e.g. `caseName:xxx`). 🧪 "antitrust" narrowed 8.33M to 44,907.
- **Date**:
  - `filed_after` / `filed_before` 🧪 work (152 results for H1 2025, all in range), but the docs don't list these parameter names. The documented form is `q=dateFiled:[2025-01-01 TO 2025-06-30]` ✅.
  - Incremental: `/dockets/?date_modified__gte=<ISO time>` 🧪; 20/20 results were after the given time.
- **Limits**:
  - With a token, the default is **5/min, 50/hr, 125/day** ✅; 🧪 a 429 "5/min" was hit in testing.
  - Membership or a commercial agreement raises the limits ✅. Anonymous traffic is throttled too, but no figure is published ✅.
  - Non-search endpoints page through at most 100 pages ✅.
- **Advice**: use the official bulk data (full CSV snapshots on S3) for history ✅; don't page through the API.
- **Note**: RECAP coverage is incomplete. It comes mainly from documents bought by users of the RECAP browser extension, plus email, RSS and other sources ✅.
- **Sources**: wiki.free.law/c/courtlistener/help/api/rest/v4/* (the old courtlistener.com/help/api/rest/ redirects there). Official confidence: **high**.

### 3.5 SAM.gov: contract opportunities, entity registrations, exclusions
- **Auth**: the Public API Key generated in your SAM.gov account ✅ (Account Details page). A generic api.data.gov key does not work 🧪.
- **How to call**: REST JSON GET.
  - Opportunities: `/opportunities/v2/search`
  - Entities: `/entity-information/v3/entities` (v4 also exists)
  - Exclusions: `/entity-information/v4/exclusions`
- **What you get**:
  - Opportunities: 41 fields (title, agency, NAICS, deadline, award info…). The `description` field is only a link that you must request again with your api_key ✅.
  - Entities: 132 fields.
  - Exclusions: people or companies barred from federal procurement.
- **Timestamps**:
  - Opportunities: `postedDate`, `responseDeadLine`, `archiveDate`, `award.date`, date only.
  - Entities: `registrationDate`, `lastUpdateDate`, `registrationExpirationDate`.
  - Exclusions: `createDate` / `updateDate` etc., in **`MM-DD-YYYY`** format, unlike the other APIs 🧪.
- **Keyword**:
  - Opportunities: `title=` (title only) ✅. 🧪 "cybersecurity" narrowed 15,236 to 4.
  - Entities: `legalBusinessName` / `q` / `ueiSAM` / `cageCode` ✅.
- **Date** ✅: `postedFrom` and `postedTo` are **required**, format `MM/dd/yyyy`, span ≤ 1 year. 🧪 10/10 sampled records in range. Entities accept `registrationDate=[from,to]`.
- **Limits**:
  - Personal key with no role: **10/day**; with a role: 1,000/day; federal system account: 10,000/day ✅.
  - Responses carry no remaining-quota info 🧪, so you must count calls yourself.
  - `limit` max 1,000 ✅.
  - The terms of use require rotating the key every 90 days ✅.
- **Data tiers** ✅: Public / FOUO (contact details etc., needs the Read FOUO role) / Sensitive (tax IDs, bank info; needs a federal system account).
- **Gotcha**: with an invalid key, **every path returns an empty-body 404**, not 401, which looks like a wrong URL 🧪. With a valid key, access from Singapore works fine 🧪.
- **Sources**: open.gsa.gov/api/get-opportunities-public-api, /entity-api, /exclusions-api; sam.gov/about/terms-of-use. Official confidence: **high**.

### 3.6 DOJ News
- **How to call**: `GET https://www.justice.gov/api/v1/press_releases.json`; there is also `blog_entries.json` ✅. `speeches` and `videos` don't exist (404 in testing 🧪). Fallback: RSS `/news/rss?type=press_release` 🧪.
- **What you get**: press-release title, body (HTML), teaser, component (issuing office), topic, number, URL. 270k+ records since 2009 🧪.
- **Timestamps**:
  - `date`: Unix seconds; observed as 12:00 UTC on the publish day, so date precision only 🧪.
  - `created` / `changed`: Unix seconds wrapped in an HTML `<time datetime="...">` tag, to the second ✅.
- **Keyword** 🟡: only `parameters[title]` for title matching ✅ (🧪 "antitrust": 270k → 270). **`parameters[keyword]` is silently ignored**; the total doesn't change 🧪.
- **Date** 🟡: `parameters[date]` matches a single day only. The official example uses a Unix timestamp ✅; 🧪 `YYYY-MM-DD` also works. No ranges.
- **Sorting**: `sort=date&direction=DESC` ✅. Without it, results start from the oldest (2009) 🧪.
- **Limits**: max 50 per page ✅; **more than 4 requests per second may get you throttled or blocked** ✅.
- **Gotchas**:
  - Unknown parameters don't raise errors; they return everything. Always check `resultset.count` 🧪.
  - The developer page says component filtering is supported, but `parameters[component]` had no effect in testing 🧪.
- **Updates**: business days only, about 50 per day, which is exactly one page, so you need to paginate 🧪.
- **Sources**: justice.gov/developer/api-documentation/api_v1 (updated 2025-12-18), justice.gov/developer, justice.gov/legalpolicies. Official confidence: **high**.

### 3.7 FTC (Federal Trade Commission)
- **Press releases**: no API ✅; RSS and web pages only.
  - RSS URLs: `/feeds/press-release.xml`, `-competition.xml`, `-consumer-protection.xml` ✅. Confirmed live from another host.
  - The web list supports keyword search via `?search_api_fulltext=` 🧪.
  - RSS holds only the latest 10–30 items; `pubDate` includes a time zone 🧪.
- ⛔ **This machine's IP is blocked**: www.ftc.gov returns an "abusive automated request" page (a fake 404) for every path, homepage included 🧪. Either run from a US machine or server, or email PWH-Alert@ftc.gov as the block page suggests.
- **api.ftc.gov** (usable): only two datasets, HSR early-termination notices and DNC complaints ✅, **not press releases**.
  - Format: JSON:API ✅.
  - Filtering: `filter[title][value]` + `[operator]=CONTAINS` ✅ (🧪 works).
  - Paging: `page[limit]` / `page[offset]`, max 50 per page ✅.
  - Sorting: `sort[x][path]=created&sort[x][direction]=DESC` ✅.
  - Timestamps: `created` / `updated` (to the second), `date`.
  - Quota: 🧪 20,000/hr. HSR notices are released in weekly batches 🧪.
- **Sources**: ftc.gov/developer, ftc.gov/developer/api/v0/endpoints/hsr-early-termination-notices, ftc.gov/news-events/stay-connected/ftc-rss-feeds. Official confidence: **high**.

### 3.8 USPTO (dropped)
- The patent API (Open Data Portal) requires `X-API-KEY`. Getting a key needs a USPTO.gov account + MFA + **ID.me identity verification (requires a US ID)**; the key page is data.uspto.gov/apikey ✅. The trademark API (TSDR) needs a separate key ✅. The bulk-data API also needs a key 🧪.
- What the API can do (✅ checked against official docs):
  - Search: `q`, OpenSearch syntax.
  - Date: `rangeFilters` on filingDate / grantDate etc.
  - Incremental: `lastIngestionDateTime` (ingest time).
  - Limits: 5M metadata calls/week, 4–15 req/s, no concurrent calls per key.
  - Trademarks: lookup by case number only, 60/min.
- PatentsView: migration began 2026-03-20. Bulk tables are on the new platform, but the API isn't there yet ✅.
- Google Patents (BigQuery) was considered as a replacement; you chose not to use it, so it was not added.

### 3.9 Paid sources (code written per docs; not run with real credentials)

| | D&B Direct+ | Moody's Orbis | Quartr | LexisNexis |
|---|---|---|---|---|
| **Auth** | OAuth2: Basic(key:secret) → `POST /v3/token` (form-encoded) → Bearer, 24 h ✅ | `ApiToken` header 🔶 | `x-api-key` header ✅ | OAuth2: `auth-api.lexisnexis.com/oauth/v2/token` → Bearer, 24 h ✅ |
| **Main endpoints** | `cleanseMatch` (name → DUNS number), `search/criteria`, `data/duns/{duns}?blockIDs=` ✅ | `Companies/match`, `Companies/data` (WHERE + SELECT) 🔶 | `/public/v3/companies`, `/events`, `/documents/transcripts`, etc. ✅ | `services-api.lexisnexis.com/v1/News` (OData) ✅ |
| **Keyword** | ✅ `searchTerm` | name match 🔶 | ❌ ticker/ISIN/CIK only | ✅ `$search` (boolean search) |
| **Date** | ❌ Monitoring change notifications only | ❓ | ✅ `startDate/endDate`; `updatedAfter` for incremental | ✅ `$filter=Date ge ... and Date le ...` |
| **Limits** | per contract; 429 when exceeded; quotas reset daily at 00:00 UTC ✅ | 🔶 typically 1–10 concurrent | default 50 req/s; max 500 per page ✅ | per contract, 429 when exceeded; max 50 per page ✅ |
| **No-credential probe** | 401 (error code 00004) 🧪 | 401 `error.token.rejected` 🧪 | 401; v1/v2 retired (410) 🧪 | token endpoint 401, data endpoint 498 🧪 |
| **Doc reliability** | Medium: docs now need a login; checked via 2024-11 archives | **Low: no public docs**; everything comes from partner open-source code | High: docs and OpenAPI are public | Medium-high: spec files on dev.lexisnexis.com are public |
| **When credentials arrive** | Confirm the v3 token works | **Adjust request bodies and field codes against the contract docs** | Run as is | Confirm dataset names (e.g. `News`, `CompanyAndFinancial`) |

---

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
| Weekly | api.ftc.gov HSR notices | Thursday | 1 |

**The test script also uses quota**: one SAM run costs 4 calls (at most 2 test runs per day); one CourtListener run costs 5.

---

## 6. Project files and usage

```bash
pip install -r requirements.txt
cp .env.example .env              # add credentials (the 3 existing ones are already set)
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

- [ ] FTC press releases: run `python run_all.py ftc` on a machine with a US IP
- [ ] Paid sources: test each once credentials arrive (adjust Orbis against the contract docs first)
- [ ] If SAM's 10/day is not enough: request a role in SAM (raises it to 1,000/day)
- [ ] If CourtListener's quota is not enough: consider membership, or switch to bulk data
