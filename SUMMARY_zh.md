# 16 个数据源 API 调研汇总

> 整理日期：2026-10-13 · 测试环境：Python 3.12，出口 IP 在新加坡
> 英文版：[SUMMARY_en.md](SUMMARY_en.md)

**来源说明**：没有特别标注的信息都来自官方文档。括号里的标注表示：
-（实测）：实际调用时观察到的，文档里没写
-（半官方）：来自厂商合作方的开源代码或文档
-（未确认）：官方没找到，也没实测

---

## 1. 总体结论

| 状态 | 数据源 |
|---|---|
| **已用真实请求验证，可以用** | USAspending、Grants.gov、GovInfo、CourtListener、SAM.gov、OSHA、UCC Filings（科罗拉多 + 康涅狄格）、Alpha Vantage（财报电话会文字稿） |
| **能用，但接口本身功能有限** | DOJ（只能按标题搜、只能查某一天）；api.ftc.gov（只有并购审查 HSR 公告） |
| **调用不了** | FTC 新闻稿：本机 IP 被网站拦截，要换美国 IP<br>USPTO：key 要 ID.me 实名，需要美国证件，已放弃 |
| **免费演示可用，正式使用要付费** | EarningsCall（财报电话会；演示 key 只能查 AAPL、MSFT） |
| **付费，等凭证** | D&B Direct+、Moody's Orbis、Quartr（财报电话会）、LexisNexis：代码已按文档写好，没用真实凭证跑过 |

**凭证情况**：
- 已配置（都在 `.env` 里）：api.data.gov key（GovInfo 和 api.ftc.gov 共用）、CourtListener token、SAM.gov key、DOL key（OSHA）、Alpha Vantage key。
- 其他都没有。

---

## 2. 速查总表

| 数据源 | 是否可用 | 国家覆盖 | 拿到什么 | 认证 / 费用 | 关键词搜索 | 时间过滤 | 时间戳精度 | 频率/额度限制 | 建议多久跑一次 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **USAspending** | 可用 | 美国 + 国际：美国联邦合同和拨款；收款方和履约地点可以在国外（215 个国家/地区） | 联邦合同/拨款：编号、收款方、金额、机构、行业代码、竞争方式、履约期 | 不需要 key，免费 | 支持 `keywords` | 支持 `time_period`，可选 4 种日期口径 | 最后修改时间到秒 | 未公布；单次查询最多拿 5 万条 | 每天 1 次 |
| **Grants.gov** | 可用 | 仅美国：美国联邦机构发布的拨款机会 | 拨款机会：标题、机构、资金额度、申请资格、截止日、联系人、附件 | 不需要 key，免费 | 支持 `keyword` | 不支持，只能排序后自己筛 | 列表只有日期；详情到秒（带时区） | 未公布 | 每天 1 次 |
| **GovInfo** | 可用 | 仅美国：美国联邦政府出版物 | 联邦公报、法规、法案、国会记录、法院意见等：元数据 + PDF/XML 全文 | 免费 api.data.gov key | 支持，全文 | 支持，发布日期区间 + 按入库时间增量 | 入库时间到秒 | 36,000 次/小时 | 每天 1 次 |
| **CourtListener** | 可用 | 美国 + 国际：美国联邦、州、属地、部落法院；国际部分只有 3 个英国历史法院，数据很少 | 判决意见（含全文链接）、联邦法院案卷、当事人、律师、法官 | 免费 token（搜索可匿名） | 支持，布尔语法 | 支持，判决日期区间 + 按修改时间增量 | 入库时间到微秒 | **5 次/分钟、50 次/小时、125 次/天** | 每 1～2 小时 1 次 |
| **SAM.gov** | 可用（每天只有 10 次） | 美国 + 国际：美国联邦采购；注册实体包括外国公司（英国就有 5,176 家） | 合同机会（含授标）、供应商注册信息、禁止参与采购的名单 | 免费 SAM key | 部分支持：只搜标题 | 支持，发布日期区间（必填，≤1 年） | 只有日期 | **10 次/天** | 每天 1 次 |
| **DOJ** | 可用（只能按标题搜、只能查某一天） | 美国 + 国际：美国司法部新闻稿；涉案人可以是外国人 | 司法部新闻稿：标题、HTML 全文、发布部门、主题 | 不需要 key，免费 | 部分支持：只匹配标题 | 部分支持：只能查某一天 | 创建/修改时间到秒 | ≤ 4 次/秒 | 每 2～4 小时 1 次 |
| **api.ftc.gov** | 可用（只有并购审查公告，没有新闻稿） | 美国 + 国际：影响美国市场的并购；交易双方可以都是外国公司 | 并购审查提前终止：收购方、被收购方、交易编号、日期 | 免费 api.data.gov key | 支持，按字段过滤 | 支持，按字段过滤 | 到秒 | 20,000 次/小时 | 每周 1 次 |
| **OSHA** | 可用 | 仅美国：50 州及海外属地 | 安全检查、违规与罚款、工伤事故（11 张表，按检查编号关联） | 免费 DOL key | 支持 `like` 模糊匹配 | 支持 `gt`/`lt` | 入库时间 `load_dt` 到秒 | 单次 1 万条 / 5MB；实测连续请求会 429 | 每天 1 次 |
| **UCC Filings**（CO / CT） | 可用（只覆盖科罗拉多、康涅狄格两州） | 美国 + 国际：只有科罗拉多、康涅狄格两州的登记；债务人少量在国外（如加拿大、英国） | 担保登记：债务人、担保权人、担保物（CO）、申报日、失效日 | 不需要 key，免费 | 支持 `$where like` / `$q` | 支持 `$where between` | 只有日期 | 无 token 按 IP 限流；有 token 基本不限 | 每天 1 次 |
| FTC 新闻稿 | 不可用：本机 IP 被 FTC 网站拦截，需要换美国 IP | 仅美国：美国 FTC 新闻稿 | 新闻稿标题、链接、摘要、发布时间（全文要抓网页） | 没有 API，只有 RSS 和网页 | 只有网页能搜 | RSS 只有最近 10～30 条 | `pubDate` 带时区 | 网站防火墙按 IP 拦截 | 每天 1 次（换 IP 后） |
| USPTO | 不可用：key 需要 ID.me 实名验证，没有美国证件 | 美国 + 国际：美国专利和商标；申请人可以来自任何国家（未确认） | 专利申请：名称、申请/授权日、发明人、申请人、CPC、审查文件 | 免费 key，但要 ID.me 实名 | 支持， | 支持， | 入库时间到秒 | 每周 500 万次，同一 key 不能并发 | —（已放弃） |
| D&B Direct+ | 不可用：付费，还没买凭证 | 美国 + 国际：190 多个国家，近 6 亿家机构 | 企业档案：DUNS、地址、行业、员工、财务、母子公司关系 | 付费 | 支持 `searchTerm` | 不支持（只能订阅变更推送） | 调用时间戳 | 按合同 | — |
| Moody's Orbis | 不可用：付费，还没买凭证 | 美国 + 国际：6.35 亿家以上公司（官方没给国家数） | 全球企业：工商信息、财务（按年）、员工、股权结构 | 付费 | 名称匹配 / 条件筛选 | 未知 | 要在查询里指定 | 按合同（半官方：一般 1～10 个并发） | — |
| Quartr | 不可用：付费，还没买凭证 | 美国 + 国际：65 个以上市场的 16,000 多家上市公司 | 上市公司财报会：事件、文字稿、音频、PPT、AI 摘要 | 付费 | 不支持，只能按股票代码等过滤 | 支持，事件日期 + 按更新时间增量 | 未知 | 默认 50 次/秒 | — |
| **EarningsCall** | 部分可用：演示 key 只能查 AAPL、MSFT；正式使用要付费（$60/月起） | 美国 + 国际：9,000+ 家上市公司，主要美国，加拿大、欧洲、澳洲较少 | 电话会文字稿（全文、按发言人分段、逐词时间）、音频、PPT、财报日历 | 付费；演示 key 免注册 | 不支持，只能按公司名或代码搜公司 | 支持，按年份 + 季度；日历按日期 | 电话会时间到分钟（带时区）；逐词时间到毫秒 | 套餐 10 次/分钟起 | 财报季每天 1 次 |
| **Alpha Vantage**（财报电话会） | 可用（免费 key 每天 25 次） | 仅美国：美国上市股票（含在美上市的外国公司，如台积电、SAP）；伦敦、多伦多等交易所没有 | 电话会文字稿（按发言人分段、职位、情绪分）、历史财报发布日和 EPS、财报日历 | 免费 key（邮箱注册） | 不支持，只能按代码 + 季度 | 支持，按季度（2010Q1 起）；日历按范围 | 文字稿没有时间；财报发布日只有日期 | **25 次/天、1 次/秒** | 财报季每天 1 次 |
| LexisNexis | 不可用：付费，还没买凭证 | 美国 + 国际：170 多个国家的新闻源，51 种语言 | 新闻及法律文献：标题、日期、来源 + 全文 | 付费 | 支持，布尔语法 | 支持 `Date ge/le` | 出版日期 | 按合同；每页 ≤ 50 条 | — |

### 国家覆盖范围

分两层看：**数据出自哪个国家的机构**，以及**记录里的公司或个人可以在哪些国家**。政府数据源都只覆盖美国政府自己的业务，但交易对象可以是外国公司。数字来自 2026-10-14 的实测查询，付费的 4 家用的是厂商官方公布的数字。

| 数据源 | 数据出自 | 记录里的对象可以在哪些国家 | 依据 |
|---|---|---|---|
| **USAspending** | 美国联邦政府 | 全球。2025 财年 578 万份合同里，外国收款方 103,866 份（约 1.8%），海外履约地点 162,470 份，履约地点共涉及 215 个国家或地区；美国以外金额最多的是日本、德国、加拿大、英国、韩国 | 实测 |
| **SAM.gov** | 美国联邦政府 | 全球。外国公司也可以注册，注册地在英国的实体有 5,176 家（如巴克莱银行） | 实测 |
| **Grants.gov** | 美国联邦政府 | 美国联邦机构发布的拨款机会；外国机构能否申请看每个机会的资格要求 | 官方文档 |
| **GovInfo** | 美国联邦政府（GPO） | 只有美国联邦政府的出版物：联邦公报、法规、国会文件、联邦法院意见 | 官方文档 |
| **CourtListener** | 美国（Free Law Project 汇总） | 美国法院为主，共 3,359 个：联邦法院、50 州加华盛顿特区的州法院（州最高法院 55 个）、属地法院（关岛、北马里亚纳、波多黎各、维尔京群岛等）、部落法院（如切罗基族最高法院）；另有 3 个英国历史法院（House of Lords 等），量很少 | 实测 |
| **DOJ** | 美国司法部 | 美国司法部的新闻稿；涉案人可以是外国人（样例里有哥伦比亚籍被告） | 实测 |
| **api.ftc.gov**（HSR） | 美国 FTC | 影响美国市场的并购；交易双方可以都是外国公司（样例：瑞士 ABB 收购英国 Rotork） | 实测 |
| FTC 新闻稿 | 美国 FTC | 美国 FTC 的新闻稿 | 官方文档 |
| **OSHA** | 美国劳工部 | 美国 50 州及海外属地的工作场所（已查到波多黎各的检查记录） | 实测 |
| **UCC Filings** | 科罗拉多州、康涅狄格州政府 | **只有这两个州登记的申报**。债务人主要在本州（康涅狄格 93% 在 CT），少量在外州和外国（科罗拉多有加拿大、英国等） | 实测 |
| USPTO | 美国专利商标局 | 美国专利和商标；申请人可以来自任何国家（未确认，未实测） | — |
| D&B Direct+ | 全球 | 190 多个国家和市场，近 6 亿家机构（2024 年报）；个别国家没有数据（旧文档列出南极洲、古巴、朝鲜等），部分数据块只覆盖特定地区，具体要向 D&B 要数据块覆盖表 | 官方 |
| Moody's Orbis | 全球 | 6.35 亿家以上公司，来自 170 多个数据源；官方没给国家数。99% 以上是私营公司，财务数据的详细程度取决于各国的申报要求 | 官方 |
| Quartr | 全球上市公司 | 65 个以上市场的 16,000 多家上市公司；没有公开交易所或国家清单，要用 API 列出 | 官方 |
| EarningsCall | 商业数据商 | 9,000+ 家上市公司，主要美国，加拿大、欧洲、澳洲较少；多数公司 2020 年起 | 官方 |
| Alpha Vantage | 商业数据商 | 美国上市股票，包括在美国上市的外国公司（台积电、SAP、丰田）；伦敦、多伦多等非美国交易所的代码查不到 | 实测 |
| LexisNexis（新闻） | 全球 | 170 多个国家的 33,000 多个授权新闻源，51 种语言；其中可用于生成式 AI 的约 23,000 个 | 官方 |

---

## 3. 逐个说明

### 3.1 USAspending.gov：联邦合同、拨款支出
- **怎么调用**：REST JSON。搜索类接口都是 **POST**，条件放在 JSON body 里。
  - 搜索：`POST /api/v2/search/spending_by_award/`
  - 总数：`POST /api/v2/search/spending_by_award_count/`
  - 详情：`GET /api/v2/awards/{generated_internal_id}/`
  - 最近更新日期：`GET /api/v2/awards/last_updated/`
  - 批量下载：`POST /api/v2/bulk_download/awards/`（异步生成 zip）
- **拿到的信息**（实测，实际返回）：
  - **搜索结果**（每条 13 个字段）：合同编号 `Award ID`、收款方 `Recipient Name`、描述 `Description`、金额 `Award Amount`、授予机构 `Awarding Agency`、起止日期、最后修改时间、首次拨付日期、内部 ID。
  - **详情**（167 个字段）：
    - 基本信息：合同号 PIID、类型、签约日期 `date_signed`、总拨付 `total_obligation`、子合同数量和金额、上级合同。
    - 招标与竞争：招标编号、招标方式、收到几份报价、竞争程度、小企业预留类型。
    - 分类：NAICS 行业代码、产品服务代码（PSC）。
    - 合规属性：是否商业采购、多年期合同、劳工标准、是否外国资金等。
    - 国防相关：国防项目代码。
    - 资金：按应急资金代码（DEFC）拆分的支出和拨付。
    - 履约期：开始、结束、潜在结束日期。
- **时间戳**：
  - 搜索结果：`Start Date` / `End Date`（日期）、`Last Modified Date`（到秒）、`Base Obligation Date`。
  - 详情：`date_signed`、`period_of_performance.*`。
- **关键词**（支持）：`filters.keywords: ["..."]`。实测 "cybersecurity" 把结果从 7,200 万条缩到 3,645 条。
- **时间**（支持）：`filters.time_period: [{start_date, end_date, date_type}]`，`date_type` 可选 `action_date` / `date_signed` / `last_modified_date` / `new_awards_only`。实测按签约日期筛 2025 年 1 月有效。
- **限制**：
  - 频率限制官方没有公布（未确认）。
  - 每页最多 100 条（实测），默认 10 条。
  - 单次查询最多翻到 5 万条。
  - 搜索数据从 2007-10-01 开始。
- **更新**：每天夜间更新一次；国防部和陆军工程兵团的合同数据晚 90 天发布。
- **注意**：
  - `award_type_codes` 不能跨类别混用（合同 A/B/C/D、拨款 02–05、贷款 07/08），混用会报 400（实测）。官方示例里反而是混用的。
  - 搜索结果里的 `Start Date` 不是签约日期。
- **来源**：api.usaspending.gov/docs/endpoints；GitHub `usaspending-api/.../api_contracts`（spending_by_award.md、search_filters.md 等）；usaspending.gov 的数据说明 PDF。官方确认程度：**高**。

### 3.2 Grants.gov：联邦拨款机会
- **怎么调用**：
  - 搜索：`POST https://api.grants.gov/v1/api/search2`
  - 详情：`POST /v1/api/fetchOpportunity {"opportunityId": ...}`
- **拿到的信息**（实测，实际返回）：
  - **搜索结果**（每条 10 个字段）：ID、机会编号、标题、机构代码和名称、开放日期、截止日期、状态（forecasted/posted/closed/archived）、文档类型、项目编号（CFDA/ALN）。
  - **详情**（140 个字段）：
    - 基本信息：标题、编号、版本号、类别、发布机构及其上级机构。
    - 资金：预估总额、奖励金额上下限、预计资助数量、是否需要配套资金。
    - 申请：可申请的主体类型、资助方式（如赠款、合作协议）、资助领域。
    - 联系人：姓名、电话、邮箱。
    - 时间节点：预计公告日、申请截止日、授予日、项目开始日。
    - 附件与历史：附件文件夹、文档链接、每个版本的历史记录。
- **时间戳**：
  - 搜索结果：`openDate` / `closeDate`，格式 `MM/DD/YYYY`，不带时区。
  - 详情：`postingDate`、`lastUpdatedDate` 等，精确到秒，带时区（如 EDT）。
- **关键词**（支持）：`keyword`。实测 "cybersecurity" 从 1,462 条缩到 192 条。还能按 `agencies` / `fundingCategories` / `eligibilities` / `aln`（项目编号）/ `oppNum` 过滤。
- **时间**（不支持）：**没有日期区间参数**。只能用 `sortBy=openDate|desc` 排序后在本地筛（实测），或者下载每天一份的 XML 全量文件。
- **历史数据**：默认只返回预告中和开放中的机会；要查历史得加 `oppStatuses=forecasted|posted|closed|archived`（实测 192 → 2,126 条）。
- **限制**：官方没有公布频率和单页上限（未确认）。实测 `rows=5000` 正常，`rows=20000` 失败。
- **来源**：grants.gov/api/api-guide、/api/common/search2、/api/common/fetchopportunity、/xml-extract。官方确认程度：**高**。

### 3.3 GovInfo（美国政府出版局 GPO）：联邦公报、法规、国会文件、法院意见
- **认证**：api.data.gov 免费 key，放在 `api_key=` 参数里。
- **怎么调用**：
  - 全文搜索：`POST /search`
  - 按入库时间增量：`GET /collections/{集合代码}/{lastModified 起始时间}`
  - 按发布日期：`GET /published/{日期}`
  - 详情：`GET /packages/{id}/summary`，提供 PDF/XML/ZIP/MODS 下载链接
- **拿到的信息**（实测，实际返回）：
  - **覆盖范围**：42 个文件集合，如 FR（联邦公报，102 万多份）、CFR（联邦法规）、USCOURTS（联邦法院意见）、BILLS（法案）、CREC（国会记录）、PLAW（公法）、BUDGET（预算）。
  - **搜索结果**（15 个字段）：标题、文件 ID、分卷 ID、集合代码、作者机构、发布日、入库日、最后修改时间，以及 PDF / TXT / ZIP / MODS 下载链接。
  - **增量列表**（7 个字段）：文件 ID、标题、类别、发布日、最后修改时间、所属国会届次、详情链接。
  - **详情**（28 个字段）：
    - 出版信息：卷、期、页数、出版方、作者机构、政府分类号。
    - 其他编号：ISSN 等。
    - 下载：PDF / XML / ZIP / MODS / PREMIS 链接。
    - 分卷：分卷（如单条公告）列表的链接。
  - **全文**：通过上面的下载链接获取（PDF / XML / TXT）。
- **时间戳**：`dateIssued`（发布日）、`lastModified`（GovInfo 入库或更新时间，格式 ISO8601，到秒）、`dateIngested`。
- **关键词**（支持）：`{"query": "antitrust collection:(FR)"}`。实测：联邦公报总数 102.7 万 → 1.46 万。
- **时间**（支持）：在查询里加 `publishdate:range(2025-01-01,2025-03-31)`。实测：1.46 万 → 101 条，抽查 10/10 在区间内。
- **限制**：
  - 个人 key：36,000 次/小时、1,200 次/分钟、40 次/秒（实测：响应头一致）。
  - DEMO_KEY：官方写 30 次/小时、50 次/天，实测只给 10 次，用完要等约 18 小时。
  - 每页最多 1000 条；翻页用 `offsetMark=*` 游标，旧的 `offset` 参数在逐步废弃。
- **更新**：联邦公报只在工作日出版；入库时间多在 UTC 06:00～15:00（实测）。
- **来源**：github.com/usgpo/api（README）、api.govinfo.gov/api-docs（OpenAPI 规格）、govinfo.gov/help/finding-info、api.data.gov 开发者手册。官方确认程度：**高**。

### 3.4 CourtListener（Free Law Project）：判决意见、PACER/RECAP 案卷
- **认证**：`Authorization: Token xxx`。`/search/` 可以匿名用（实测），其他接口（如 `/dockets/`）没 token 返回 401（实测）。
- **怎么调用**：REST v4。
  - 搜索：`/api/rest/v4/search/?type=o|r|rd|d|oa|p`（判决意见 / RECAP 案卷 / RECAP 文件 / 只看案卷 / 口头辩论 / 法官）
  - 其他：`/dockets/`、`/opinions/`、`/clusters/`
- **拿到的信息**（实测，实际返回）：
  - **判决意见搜索结果**（47 个字段）：
    - 案件：案名（简称/全称）、案号、法院及管辖、判决日、辩论日、案件状态、诉由性质。
    - 引用：引注、被引次数、Lexis 引注、中立引注。
    - 人员：法官、合议庭、律师。
    - 内容：程序历史、摘要；每份意见的作者、类型、全文下载链接和匹配片段。
  - **RECAP 案卷搜索结果**（50 个字段）：
    - 案件：案名、案号、法院、立案日、结案日、诉因、是否陪审团审理、管辖类型。
    - 人员：主审和移交法官、当事人、律师、律所、破产受托人。
    - 文件：每份文件的编号、描述、立案日、页数、是否可下载、PACER 文件 ID。
  - **案卷详情（REST，需 token）**（60 个字段）：
    - 编号：完整案号及其拆分字段、PACER 案件 ID。
    - 日期：立案、结案、最后一次提交、调卷令批准/驳回。
    - 案件信息：诉由性质、上诉来源、多地区诉讼（MDL）状态、破产信息、关联的判决和庭审音频。
    - 记录时间：创建时间、修改时间。
  - **全文**：判决意见有下载链接；RECAP 文件只有被人买过的才有 PDF。
- **时间戳**：
  - `dateFiled`：判决日，只有日期。
  - `meta.timestamp` / `date_created` / `date_modified`：入库或修改时间，**精确到微秒**（实测）。
- **关键词**（支持）：`q=`，支持 AND/OR、"短语"、字段语法（如 `caseName:xxx`）。实测："antitrust" 从 833 万条缩到 44,907 条。
- **时间**：
  - `filed_after` / `filed_before` 实测有效（2025 上半年 152 条，全部在区间内），但文档没有列出参数名。官方写法是 `q=dateFiled:[2025-01-01 TO 2025-06-30]`。
  - 增量：`/dockets/?date_modified__gte=ISO时间` 实测 20/20 条都在指定时间之后。
- **限制**：
  - 有 token 默认 **5 次/分钟、50 次/小时、125 次/天**；实测撞到过 429 "5/min"。
  - 会员或商业协议可以提额。匿名也有限流，但没公布数字。
  - 非搜索接口最多翻 100 页。
- **建议**：历史全量用官方批量数据（S3 上的 CSV 全量快照），不要用 API 一页页翻。
- **注意**：RECAP 的覆盖不完整，主要来自 RECAP 浏览器插件用户购买过的文件，另有邮件、RSS 等来源。
- **来源**：wiki.free.law/c/courtlistener/help/api/rest/v4/*（旧地址 courtlistener.com/help/api/rest/ 会跳转过去）。官方确认程度：**高**。

### 3.5 SAM.gov：合同机会、实体注册、排除名单
- **认证**：用 SAM.gov 账号里生成的 Public API Key（Account Details 页面）。通用的 api.data.gov key 不能用（实测）。
- **怎么调用**：REST JSON GET。
  - 合同机会：`/opportunities/v2/search`
  - 注册实体：`/entity-information/v3/entities`（也有 v4）
  - 排除名单：`/entity-information/v4/exclusions`
- **拿到的信息**（实测，实际返回）：
  - **合同机会**（41 个字段）：
    - 基本信息：标题、通知 ID、招标编号、类型（招标、授标、预告等）、是否有效。
    - 机构：发布机构的完整层级、办公地址。
    - 分类：NAICS 行业代码、产品分类代码、小企业预留类型。
    - 时间：发布日、回复截止日、归档日。
    - 授标：授标日、合同号、金额、中标方名称和所在地。
    - 联系人：姓名、邮箱、电话、传真。
    - 链接：SAM 网页链接、附件链接。`description` 只是一个链接，要另外带上 api_key 请求才能拿到正文。
  - **注册实体**（132 个字段）：
    - 身份：UEI、CAGE 代码、法定名称、商号名称。
    - 注册：状态、注册日期、到期日期、最后更新日期、是否在排除名单上。
    - 地址：实际地址、邮寄地址、国会选区。
    - 主体性质：组织类型、营利结构、注册州或国家、成立日期、财年结束日。
    - 资质：企业类型和 SBA 认证、主营 NAICS 和全部 NAICS / PSC 代码、能否接受信用卡付款。
    - 联系人：政府业务联系人和电子业务联系人。
  - **排除名单**（46 个字段）：
    - 排除详情：分类、排除类型、执行机构、所属排除项目。
    - 被排除对象：姓名或公司名、UEI、CAGE、NPI（医疗服务提供者编号）、地址。
    - 处理记录：创建、更新、生效、终止日期，以及终止类型。
    - 其他：附加说明、调查状态、其他所在地；如果是船只，还有呼号、吨位、船旗、船东。
- **时间戳**：
  - 合同机会：`postedDate`、`responseDeadLine`、`archiveDate`、`award.date`，只有日期。
  - 注册实体：`registrationDate`、`lastUpdateDate`、`registrationExpirationDate`。
  - 排除名单：`createDate` / `updateDate` 等，格式是 **`MM-DD-YYYY`**，跟其他接口不一样（实测）。
- **关键词**：
  - 合同机会：`title=`（只搜标题）。实测："cybersecurity" 从 15,236 条缩到 4 条。
  - 注册实体：`legalBusinessName` / `q` / `ueiSAM` / `cageCode`。
- **时间**（支持）：`postedFrom` 和 `postedTo` **必填**，格式 `MM/dd/yyyy`，跨度不超过 1 年。实测：抽查 10/10 条在区间内。注册实体的 `registrationDate=[起,止]` 支持区间。
- **限制**：
  - 无角色的个人 key **10 次/天**；有角色 1,000 次/天；联邦系统账号 10,000 次/天。
  - 响应里没有剩余额度信息（实测），只能自己记数。
  - `limit` 最多 1000。
  - 使用条款要求每 90 天更换 key。
- **数据分级** ：Public / FOUO（联系人等，要 Read FOUO 角色）/ Sensitive（税号、银行信息，要联邦系统账号）。
- **注意**：key 无效时**所有路径都返回空 body 的 404**，不是 401，很容易误以为地址写错了（实测）。带有效 key 从新加坡访问完全正常（实测）。
- **来源**：open.gsa.gov/api/get-opportunities-public-api、/entity-api、/exclusions-api、sam.gov/about/terms-of-use。官方确认程度：**高**。

### 3.6 DOJ（司法部）新闻
- **怎么调用**：`GET https://www.justice.gov/api/v1/press_releases.json`，另有 `blog_entries.json`。`speeches` 和 `videos` 接口不存在，实测返回 404。备用：RSS `/news/rss?type=press_release`（实测）。
- **拿到的信息**（实测，实际返回，每条 19 个字段）：
  - 标题 `title`、新闻稿编号 `number`（如 26-1168）、正文 `body`（HTML 全文）、摘要 `teaser`（HTML）、原文链接 `url`、唯一 ID `uuid`。
  - 发布部门 `component`（如 Criminal Division、Antitrust Division）、主题 `topic`（如 Homeland Security Task Force）、配图和附件。
  - 时间：`date` / `created` / `changed`。
  - 总共 27 万多条，从 2009 年开始。另有 `blog_entries`（博客，3,342 条）。
- **时间戳**：
  - `date`：Unix 秒，实测是发布日的 12:00 UTC，只有日期精度（实测）。
  - `created` / `changed`：用 HTML 标签 `<time datetime="...">` 包着的 Unix 秒，精确到秒。
- **关键词**（部分支持）：只有 `parameters[title]` 做标题匹配（实测："antitrust" 从 27 万条缩到 270 条）。**`parameters[keyword]` 会被静默忽略**，总数完全不变（实测）。
- **时间**（部分支持）：`parameters[date]` 只能精确匹配某一天。官方示例用 Unix 时间戳，实测：`YYYY-MM-DD` 也能用。不支持区间。
- **排序**：`sort=date&direction=DESC`。不传的话默认从 2009 年最旧的开始（实测）。
- **限制**：每页最多 50 条；**每秒超过 4 次会被降速甚至封掉**。
- **注意**：
  - 传入不认识的参数不会报错，而是直接返回全部数据，一定要检查 `resultset.count`（实测）。
  - 官方开发者页说支持按部门过滤，但 `parameters[component]` 实测无效。
- **更新**：只在工作日发布，一天约 50 条，正好一页，所以要翻页（实测）。
- **来源**：justice.gov/developer/api-documentation/api_v1（2025-12-18 更新）、justice.gov/developer、justice.gov/legalpolicies。官方确认程度：**高**。

### 3.7 FTC（联邦贸易委员会）
- **拿到的信息**：
  - **新闻稿 RSS**（RSS 2.0 标准字段，从另一台主机看到的）：标题、链接、摘要、发布时间 `pubDate`（带时区，如 `Thu, 08 Oct 2026 08:00:00 -0400`）。正文要再抓网页。
  - **HSR 提前终止公告**（api.ftc.gov，实测返回 8 个字段）：
    - 交易：交易编号 `transaction-number`、标题 `title`。
    - 当事方：收购方 `acquiring-party`、被收购方 `acquired-party`、被收购的具体实体 `acquired-entities`。
    - 时间：提前终止日期 `date`、记录创建和更新时间 `created` / `updated`。
- **新闻稿**：没有 API，只有 RSS 和网页。
  - RSS 地址：`/feeds/press-release.xml`、`-competition.xml`、`-consumer-protection.xml`。从另一台主机访问确认在线。
  - 网页列表 `?search_api_fulltext=` 可以按关键词搜（实测）。
  - RSS 只有最近 10～30 条，`pubDate` 带时区（实测）。
- **本机 IP 被拦截**：www.ftc.gov 对所有路径（包括首页）都返回"疑似自动化请求"的拦截页（假 404）（实测）。要么换美国的机器或服务器，要么按拦截页提示发邮件给 PWH-Alert@ftc.gov 申请放行。
- **api.ftc.gov**（可以用）：只有 HSR 提前终止公告和 DNC 投诉两个数据集，**不是新闻稿**。
  - 格式：JSON:API。
  - 过滤：`filter[title][value]` + `[operator]=CONTAINS`（实测有效）。
  - 分页：`page[limit]` / `page[offset]`，每页最多 50 条。
  - 排序：`sort[x][path]=created&sort[x][direction]=DESC`。
  - 时间戳：`created` / `updated`（到秒）、`date`。
  - 额度：实测 20,000 次/小时。HSR 公告每周成批发布（实测）。
- **来源**：ftc.gov/developer、ftc.gov/developer/api/v0/endpoints/hsr-early-termination-notices、ftc.gov/news-events/stay-connected/ftc-rss-feeds。官方确认程度：**高**。

### 3.8 USPTO（美国专利商标局）（已放弃）
- **能拿到的信息**（据官方文档，未实测）：
  - 专利申请：申请号、发明名称、申请日、授权日、专利号、公开日、申请状态、发明人、申请人、CPC 分类、入库时间。
  - 其他：审查文件（每个申请的 `/documents`），以及转让、延续关系等子资源。
  - 商标（TSDR）：按案号查商标的状态和审查文件。
- 专利接口（Open Data Portal）要 `X-API-KEY`。申请 key 需要 USPTO.gov 账号 + 两步验证 + **ID.me 实名验证（要美国证件）**，申请页面是 data.uspto.gov/apikey。商标接口（TSDR）要另一个 key。批量数据接口也要 key（实测）。
- 接口本身能力（已核对官方）：
  - 搜索：`q`，OpenSearch 语法。
  - 时间：`rangeFilters` 按 filingDate / grantDate 等过滤。
  - 增量：`lastIngestionDateTime`（入库时间）。
  - 限制：每周 500 万次（元数据）、4～15 次/秒、同一 key 不能并发。
  - 商标：只能按案号查，60 次/分钟。
- PatentsView：2026-03-20 起迁移，批量数据表已经在新平台，但 API 还没上线。
- 替代方案考虑过 Google Patents（BigQuery），你决定不用，所以没有接入。

### 3.9 付费数据源（代码已按文档写好，没用真实凭证跑过）

| | D&B Direct+ | Moody's Orbis | Quartr | LexisNexis |
|---|---|---|---|---|
| **认证** | OAuth2：Basic(key:secret) → `POST /v3/token`（表单格式）→ Bearer，24 小时有效 | 请求头 `ApiToken`（半官方） | 请求头 `x-api-key` | OAuth2：`auth-api.lexisnexis.com/oauth/v2/token` → Bearer，24 小时 |
| **能拿到的信息**（据官方文档/规格，未实测） | DUNS 编号、公司名和曾用名、地址、电话、网址、注册号、行业代码、员工数、财务数据、法人类型、控股状态、企业族谱（母公司/子公司）；更多内容取决于买了哪些 Data Block | BvD ID、公司名、国家、NACE 行业、营业收入（`OPRE`，按年度）、员工数（`EMPL`）；合作方代码里列了 496 个以上可选字段，包括股权结构（半官方） | 公司（名称、股票代码、ISIN、CIK、国家）、财报会等事件（标题、日期、财年、季度、类型）、文字稿 / 音频 / PPT / 报告的文件链接、直播文字稿、AI 摘要 | 新闻：ResultId、标题、日期、来源、地区/管辖、相似文档；加 `$expand=Document` 可在同一次请求里拿到全文（原始 XML）|
| **主要接口** | `cleanseMatch`（名称 → DUNS 编号）、`search/criteria`、`data/duns/{duns}?blockIDs=` | `Companies/match`、`Companies/data`（WHERE + SELECT）（半官方） | `/public/v3/companies`、`/events`、`/documents/transcripts` 等 | `services-api.lexisnexis.com/v1/News`（OData）|
| **关键词** | 支持 `searchTerm` | 名称匹配（半官方） | 不支持，只能按 ticker/ISIN/CIK | 支持 `$search`（布尔检索） |
| **时间** | 不支持，只能订阅 Monitoring 变更推送 | 未知 | 支持 `startDate/endDate`，增量用 `updatedAfter` | 支持 `$filter=Date ge ... and Date le ...` |
| **限制** | 按合同；超出返回 429；配额每天 UTC 0 点重置 | 半官方：一般 1～10 个并发 | 默认 50 次/秒；每页最多 500 条 | 按合同，超出返回 429；每页最多 50 条 |
| **无凭证测试** | 401（错误码 00004）（实测） | 401 `error.token.rejected`（实测） | 401；v1/v2 已下线（410）（实测） | token 接口 401，数据接口 498（实测） |
| **文档可靠性** | 中：现在要登录才能看，用的是 2024-11 的存档 | **低：没有公开文档**，全部来自合作方开源代码 | 高：文档和 OpenAPI 公开 | 中高：dev.lexisnexis.com 的规格文件公开 |
| **拿到凭证后要做的** | 确认 v3 token 能用 | **对照合同附带文档调整请求体和字段代码** | 直接跑 | 确认数据集名称（如 `News`、`CompanyAndFinancial`） |

---

### 3.10 OSHA（职业安全与健康管理局）：检查、违规、事故
- **认证**：免费 DOL API key，参数 `X-API-KEY`，在 dataportal.dol.gov 注册后生成；已配置在 `.env`。数据集目录 `/v4/datasets` 不需要 key（实测）。
- **怎么调用**：`GET https://apiprod.dol.gov/v4/get/OSHA/{表名}/json?X-API-KEY=...`；字段说明在 `/json/metadata`（每个字段的名称、描述、类型、关联表）（实测）；也支持 csv 和 xml 格式。
- **拿到的信息**（实测，实际返回）：
  - **检查** `inspection`（36 个字段）：检查编号 `activity_nr`；被检查单位名称、现场地址、邮寄地址、员工人数；所有制类型；NAICS 和 SIC 行业代码；检查类型和范围（如事故调查、投诉、计划检查）；安全或卫生检查；工会状态；开案日 `open_date`、案件修改日、结案日。
  - **违规** `violation`（29 个字段）：检查编号、传票编号、违反的条款 `standard`（如 1910.212）、违规类型（严重、故意、重复等）、严重程度、涉及人数和次数、**初始罚款和当前罚款**、签发日、整改期限、最终裁定日、是否被申诉、危险物质代码。
  - **事故** `accident`（16 个字段）：事故编号、事故日期、**事故描述**（如 "Three employees struck by vehicle"）、关键词（如 Guardrail, Struck By）、是否死亡、工程类型和造价、建筑层数。另有受伤人员表 `accident_injury` 和事故摘要表 `accident_abstract`。
  - 其他表：`violation_event`（违规处理过程）、`related_activity`、`emphasis_codes`（重点检查项目）、`optional_code_info` 等。
  - 各表用 `activity_nr` 关联（实测）：从违规记录可以回查到被检查的单位。
- **时间戳**：业务日期（开案、签发、事故日）只有日期；每张表都有入库时间 `load_dt`，**精确到秒**（实测），适合做增量同步。
- **关键词**（支持，已实测）：`filter_object={"field":"estab_name","operator":"like","value":"%WALMART%"}`，返回 20/20 条都含 WALMART。
- **时间**（支持，已实测）：`filter_object` 里用 `gt` / `lt` 比较日期字段，可以用 and/or 组合。实测 `open_date` 2025 年 1 月 20/20 在区间内；`load_dt > 2026-10-01` 增量 20/20。
- **限制**：
  - 单次最多返回 10,000 条或 5 MB，先到为准；`limit` 默认 10，用 `offset` 翻页。
  - 官方没写频率限制，但**实测约 10 分钟内 20 多个请求后开始返回 429**，响应头里没有限流信息，也没有 `Retry-After`，过一阵自动恢复（实测）。模块已设请求间隔 3 秒。
  - 带过滤加排序的查询偶尔很慢，超过 40 秒，所以模块把超时设成 90 秒（实测）。
  - **禁止把 key 公开到代码仓库或论坛**。
- **更新**：每天入库，实测最新 `load_dt` 是 2026-10-12（实测）。
- **来源**：dataportal.dol.gov/api-guide 与用户指南 PDF（2024-08-05 版）、apiprod.dol.gov/v4/datasets、`/json/metadata`。官方确认程度：**高**。

### 3.11 UCC Filings（统一商法典担保登记）
- **背景**：美国**没有联邦统一的 UCC 数据**，各州州务卿分别登记。免费、有 API、能实时查的只有**科罗拉多（CO）**和**康涅狄格（CT）**两州的政府开放数据平台（Socrata SODA API）（实测）。俄勒冈有每月一份上个月的新增数据。
- **认证**：不需要 key（实测）。可选申请 Socrata app token（请求头 `X-App-Token`），有了 token 就有独立额度。
- **怎么调用**：`GET https://data.colorado.gov/resource/{数据集ID}.json`、`https://data.ct.gov/resource/xfev-8smz.json`，用 SoQL 参数 `$where` / `$q` / `$order` / `$select` / `$limit`。
- **拿到的信息**（实测，实际返回）：
  - **科罗拉多**：260 万条申报，最早到 1966 年，分 4 张表，用 `fileid` 关联：
    - 申报 `wffy-3uut`：交易 ID、主文件 ID、交易类型（新申报、修改、续期、终止）、申报日、失效日、文件类型、是否终止。
    - 债务人 `8upq-58vz`：公司名或个人姓名、组织类型、注册地、地址。
    - 担保权人 `ap62-sav4`（209 万条）：公司名或姓名、地址、是否为转让方。
    - 担保物 `4am6-w6u4`：担保物描述、是否农产品、所在县。
  - **康涅狄格**：85 万条，一张平表：留置/UCC 编号、状态、申报类型、债务人姓名或公司名及地址、担保权人姓名或公司名及地址、受理日 `dt_accept`、失效日 `dt_lapse`、页数。**没有担保物字段**。
- **时间戳**：申报日、受理日、失效日，格式是无时区的时间戳，实际只有日期精度（实测）。
- **关键词**（支持，已实测）：`$where=upper(organizationname) like '%BANK%'`。科罗拉多担保权人 209 万 → 60.8 万；也可以用 `$q=` 全文搜索。
- **时间**（支持，已实测）：`$where=filingdate between '2026-09-01T00:00:00' and '2026-09-30T23:59:59'`，科罗拉多 260 万 → 10,609，抽查 20/20 在区间内。康涅狄格的关键词加日期组合查询：85 万 → 2,023 条。
- **限制**：
  - 没有 app token 时按 IP 共享额度，请求过多返回 429，没公布具体数字。
  - 有 app token 时"目前不限流"，除非被判定为滥用。
- **更新**：科罗拉多"每天午夜后"自动更新（实测最新申报 10/11）；康涅狄格每天更新（实测最新 10/12）（实测）。
- **其他州和全国数据**（调研结果，未实测）：
  - 多数州只卖批量文件，例如德州每天 $65（全量 $1,150）、肯塔基每月 $1,500、华盛顿/明尼苏达/伊利诺伊每周更新。
  - 加州、纽约只能网页查询，加州有反爬保护。
  - 商业 API：**Middesk**（覆盖 50 州，含担保物和失效日，按公司查）；**D&B UCC Filings**（按 DUNS 返回最近 10 笔，或按名称加日期区间查。需要单独开通，而且要确认 Direct+ 是否支持）。
  - LexisNexis 的 Web Services API 没有找到 UCC 内容，UCC 在它另外的 Public Records 产品里。
- **来源**：data.colorado.gov 数据集元数据、catalog.data.gov（康涅狄格）、dev.socrata.com/docs/app-tokens.html；各州批量产品见各州州务卿官网。官方确认程度：**高**（CO/CT）。

### 3.12 EarningsCall（财报电话会文字稿）
- **认证**：参数 `apikey`。`demo` key 不用注册，但只能查 AAPL 和 MSFT（实测查 JPM 返回 403）；免费试用 key 要用邮箱或 Google 登录；正式使用要付费。
- **怎么调用**：
  - 某公司的全部电话会：`GET https://api.earningscall.dev/events?exchange=NASDAQ&symbol=AAPL`
  - 文字稿：`GET /transcript?exchange=&symbol=&year=&quarter=&level=1..4`
  - 另有 `/symbols`（搜公司）、`/calendar`（某天有哪些电话会）、`/audio`（音频）、`/slides`（PPT）
- **拿到的信息**（实测，AAPL）：
  - **电话会列表**：33 场，从 2018 年 7 月到 2026 年 7 月，每场有年份、季度、电话会时间、是否已发布。
  - **level 1 整篇纯文本**：一场约 4.5 万字符。
  - **level 2 按发言人分段**：58 段，11 位发言人，每段带姓名和职位（如 Tim Cook，CEO；Kevan Parekh，CFO；各家分析师）。
  - **level 3 逐词时间**：7,692 个词各有开始时间（秒），整场约 60 分钟，可以和音频对齐。
  - **level 4 管理层发言 / 问答拆分**：官方说会拆成 `prepared_remarks` 和 `questions_and_answers`，但演示 key 实测**没有拆分**，`prepared_remarks` 就是整篇全文。多个季度都一样，不确定是演示 key 的限制还是功能问题。
  - **财报日历**：某一天有哪些公司开电话会（演示 key 只能查 2025-01-10，当天 16 场）。
- **时间戳**：单场电话会的 `conference_date` 精确到分钟，带时区（如 `2024-10-31T17:00:00-04:00`）；日历里只有日期。
- **关键词**（不支持）：只能按公司名或代码搜公司（`/symbols?search=`），不能在文字稿里搜关键词。
- **时间**（支持）：按年份 + 季度取某一场；日历按日期查。
- **价格**：Starter $60/月（只有纯文本，10 次/分钟）、Premium $69/月（发言人、逐词时间、问答拆分）、Ultimate $129/月（加音频）、Ultimate+ $155/月（加 webhooks）。
- **覆盖**：9,000+ 家公司，主要美国，加拿大、欧洲、澳洲较少；多数公司从 2020 年起。官方说约一半电话会在结束后 15 分钟内可取。
- **来源**：earningscall.biz/docs、/docs/plans、/api-pricing。官方确认程度：**高**。

### 3.13 Alpha Vantage（财报电话会文字稿，免费）
- **认证**：参数 `apikey`。免费 key 填邮箱就能拿，不用信用卡；已配置在 `.env`。`demo` key 只能查 IBM 2024Q1 这一场（实测）。
- **怎么调用**：
  - 文字稿：`GET https://www.alphavantage.co/query?function=EARNINGS_CALL_TRANSCRIPT&symbol=AAPL&quarter=2026Q3`
  - 历史财报：`function=EARNINGS`
  - 财报日历：`function=EARNINGS_CALENDAR&horizon=3month`，返回 CSV
- **拿到的信息**（实测，2026-10-14）：
  - **文字稿**：按发言人分段，每段有发言人 `speaker`、职位 `title`、内容 `content`、情绪分 `sentiment`。例如 AAPL 2026Q3 有 61 段、48,339 字符、12 位发言人；JPM 2026Q2 有 110 段。情绪分官方没说明范围和算法（IBM 2024Q1 在 0.0～0.8 之间）。
  - **历史财报**：每季度的财报发布日 `reportedDate`、盘前或盘后 `reportTime`、EPS 实际值、预期值、超预期幅度。AAPL 共 122 个季度，从 1996 年起。
  - **财报日历**：未来 3 个月约 4,600 条，每条有股票代码、公司名、报告日、财年截止日、EPS 预期、币种、盘前或盘后。
- **历史和时效**（实测）：
  - AAPL 2010Q1、2015Q1、2020Q1 都有，历史确实能追溯到 2010 年。
  - 最新一季能拿到：AAPL 2026Q3（7 月 30 日的电话会）。
  - 还没开的电话会会返回错误（如 JPM 2026Q3）。电话会开完多久能拿到，这次没测出来。
- **覆盖**（实测）：只覆盖**美国上市的股票**。
  - 有：大盘股、小盘股（PLTR），以及在美国上市的外国公司（台积电 TSM、SAP、丰田 TM）。
  - 没有：伦敦（BP.LON）、多伦多（SHOP.TRT）等非美国交易所的代码，返回空，也不报错。
- **时间戳**：文字稿**没有电话会时间**，只有代码和季度。可以用历史财报接口的发布日加盘前/盘后标记补上，但发布日不一定是电话会当天。
- **关键词**（不支持）：只能按"股票代码 + 季度"取。
- **时间**（支持）：`quarter=YYYYQn`，按公司财年口径。
- **限制**：
  - 免费 key **每天 25 次**。
  - **每秒最多 1 次**，连续请求会被拒（实测，限制写在返回的提示里）。
  - 超额度或出错时**仍返回 HTTP 200**，返回体里是 `Information` 或 `Error Message`，必须检查返回体。
  - 响应头里没有剩余额度信息（实测），只能自己记数。
- **怎么用这 25 次**：每天先用 1 次拉财报日历，选出前一天开过电话会的重点公司，再每家用 1 次拉文字稿。一天最多约 20 家公司。
- **来源**：alphavantage.co/documentation、/support、/premium。官方确认程度：**高**。

### 3.14 其他财报电话会文字稿 API（调研，未实测）

| 提供方 | 免费能不能拿到文字稿 | 最便宜的含文字稿套餐 | 覆盖 | 结构 |
|---|---|---|---|---|
| **EarningsCall**（见 3.12） | 演示 key 只有 AAPL、MSFT | $60/月（纯文本）；$69/月（发言人 + 问答拆分） | 9,000+ 家，主要美国，2020 年起 | 发言人、逐词时间、音频、PPT |
| **Alpha Vantage**（见 3.13） | 能：免费 key 每天 25 次，已实测 | Premium 提高次数 | 美国上市股票，2010 年起 | 按发言人分段、情绪分；没有电话会时间 |
| **roic.ai** | 能：免费注册（只要邮箱，不用信用卡），每家公司只有最近 2 场，5 次/分钟 | $89/月（全部历史 + 发言人 + 音频） | 70+ 个交易所、6.8 万家公司，国际覆盖最好 | 免费版只有纯文本；付费版有发言人 |
| **Financial Modeling Prep** | 不能：免费套餐不含文字稿 | $139/月（年付 $99/月） | 美股为主，8,200 家公司，10 年以上 | 一整段文本，没有问答拆分 |
| **API Ninjas** | 不能：文字稿只在付费套餐 | $59/月（近 5 年）；$149/月（发言人、问答、2005 年起） | 8,000+ 家，美股为主 | 付费高级套餐有发言人和问答标记 |
| **Finnhub** | 不能 | 只有 All-in-One 套餐（约 $3,500/月） | 美、英、欧、澳、加，15 年以上 | 发言人、问答分段、音频 |
| **Benzinga** | 不能 | 需询价 | 罗素 3000，2023 年起 | 文字稿、摘要、音频 |
| **FactSet、S&P Capital IQ、LSEG、Bloomberg、AlphaSense** | 不能 | 企业级，通常每年五位数美元以上 | 全球、历史最长 | 完整结构 |

没有 API 的：Seeking Alpha（文字稿只在网页付费版）、Motley Fool、Koyfin。

**建议**：
- 完全免费、只看美股：Alpha Vantage（每天 25 次，约 20 家公司）。
- 只看美股、要发言人和问答拆分：EarningsCall Premium（$69/月）最便宜。
- 需要国际公司：先用 roic.ai 免费版验证覆盖，再考虑 $89/月的套餐。
- 已在名单里的 Quartr 覆盖 65+ 个市场，也是国际选项，价格需询价。

## 4. 通用注意事项

1. **两种时间要分清**：
   - "业务时间"：发布、签约、判决日期，大多只精确到日。
   - "入库/更新时间"：`lastModified`、`date_modified`、`updatedAfter`、`Last Modified Date`，精确到秒甚至微秒。**做增量同步要用后者**。
2. **日期格式五花八门**：ISO、`MM/DD/YYYY`、`MM-DD-YYYY`、Unix 秒、HTML `<time>` 标签、`Aug 01, 2024 12:00:00 AM EDT`。`common.py` 里的 `parse_any_date()` 都能处理。
3. **无效参数被静默忽略**：DOJ 就是这样。验证过滤是否生效，一定要对比过滤前后的总数（测试框架就是这么做的）。
4. **出错状态码不规范**：SAM 无效 key 返回 404，LexisNexis token 失效返回 498，FTC 被拦截时返回假 404。
5. **api.data.gov key**：GovInfo 和 api.ftc.gov 共用。DEMO_KEY 只能临时试用。
6. **IP 限制**：只有 FTC 网站拦截了本机 IP。其他数据源从新加坡访问都正常，包括 SAM。

---

## 5. 建议的定时安排（新加坡/北京时间）

| 频率 | 数据源 | 时间 | 每次请求数 |
|---|---|---|---|
| 每 1～2 小时 | CourtListener（`date_modified__gte` 增量） | 整点 | ≤ 2 |
| 每 2～4 小时 | DOJ（倒序拉，遇到已抓过的 uuid 就停） | 0/4/8/12/16/20 点 | 1～3 |
| 每天 | SAM.gov 合同机会（`limit=1000`，postedFrom/To=昨天） | 20:00 | 1～2 |
| 每天 | USAspending（先查 `last_updated`）、Grants.gov | 20:00 | 少量 |
| 每天 | GovInfo（`/collections/FR/{上次时间}`） | 00:00 | 少量 |
| 每天 | UCC（CO/CT，`$where` 申报日 = 昨天） | 16:00（美国前一天的数据已在午夜后更新） | 2～6 |
| 每天 | OSHA 检查（`open_date` > 上次时间） | 20:00 | 1～3 |
| 每周 | api.ftc.gov HSR 公告 | 周四 | 1 |

**测试脚本本身也耗额度**：SAM 跑一次用 4 次（一天最多测 2 次），CourtListener 跑一次用 5 次。

---

## 6. 项目文件与用法

```bash
pip install -r requirements.txt
cp .env.example .env              # 填入凭证（已有的 5 个已经填好）
python run_all.py                 # 全部测试
python run_all.py sam doj         # 只测指定的几个
python run_all.py --render-only   # 不发请求，只重新生成报告
```

| 文件 | 内容 |
|---|---|
| `apis/*.py` | 每个数据源一个模块：调用示例 + `META`（限制、来源） |
| `common.py` | 测试框架：自动识别时间戳、验证过滤是否生效、记录限流头、遇到 429 自动重试 |
| `run_all.py` | 运行入口，生成报告 |
| `output/report.md` | 详细测试报告：每次请求的状态、字段和来源 |
| `output/samples/` | 真实返回样例 |
| `README.md` / `LIMITS.md` | 简要结论 / 限制与频率 |
| `.env` | 凭证（**不要提交到 git**） |

## 7. 待办

- [ ] UCC：要覆盖更多州的话，决定是买州批量文件，还是用 Middesk / D&B UCC
- [ ] FTC 新闻稿：在美国 IP 的机器上跑一次 `python run_all.py ftc`
- [ ] 付费数据源：拿到凭证后逐个测试（Orbis 要先对照合同文档调整）
- [ ] 如果 SAM 的 10 次/天不够用：在 SAM 申请角色（可提到 1,000 次/天）
- [ ] 如果 CourtListener 额度不够：考虑会员，或改用批量数据
