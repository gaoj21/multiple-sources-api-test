# API 能力测试报告

| API | 结论 | 认证 | License/费用 | 关键词 | 时间过滤 |
|---|---|---|---|---|---|
| USAspending.gov | 可用 | 无需 API key | 免费公开 (官方未见数据 license 声明; 代码仓库是 CC0) | 支持: filters.keywords (字符串数组; 官方没写具体搜哪些字段; 旧的单数 keyword 已废弃) | 支持: filters.time_period[{start_date,end_date,date_type}], date_type 可选 action_date / date_signed / last_modified_date / new_awards_only |
| SAM.gov | 可用 | 需要 SAM.gov 账号里生成的 API key (Account Details → Public API Key); 通用 api.data.gov key / DEMO_KEY 无效 | 免费 (官方未写价格, 未见收费说明); 实体数据分级: Public / FOUO (联系人邮箱电话、层级, 需 Read FOUO 角色) / Sensitive (TIN/EIN/银行信息, 需联邦 System Account + Read Sensitive) | Opportunities: title= (标题), solnum/noticeid/ncode(NAICS)/organizationName; Entity: legalBusinessName / q= 自由文本 / ueiSAM / cageCode | Opportunities: postedFrom & postedTo 必填 (MM/dd/yyyy, 跨度≤1年), 另有 rdlfrom/rdlto (截止日); Entity: registrationDate / updateDate 等支持 [from,to] 区间 |
| Grants.gov | 可用 | search2 / fetchOpportunity 无需 key; 其他部分接口需要找 Help Desk 申请 API key (system-to-system 另有流程) | 免费公开 (官方称 Unrestricted Access; 未见 license 声明) | 支持: keyword (标题/描述全文); 另有 agencies / fundingCategories / eligibilities / aln (原 CFDA 编号) / oppNum 过滤 | search2 没有日期区间参数; 只能 sortBy=openDate|desc 后在客户端按 openDate/closeDate 过滤, 或用 XML Extract |
| D&B Direct+ | 需要 key / license | OAuth2 client_credentials: Basic base64(key:secret) → POST /v3/token (form 表单 grant_type=client_credentials) 拿 access_token (24 小时有效), 之后 Bearer; 旧版 /v2/token 用 JSON body | 商业付费 license: key/secret 只能找 D&B 客户代表开通, 按产品/Data Block 授权 (companyinfo L1 是所有 block 的起点); 每次调用计入合同配额 | 支持: search/criteria 的 searchTerm (公司名/关键词) 及 industry/地域等条件; typeahead 可前缀匹配 | 不支持按时间查询; 变化追踪要用 Monitoring (订阅 DUNS 后推送变更通知)  |
| Moody's Orbis | 需要 key / license | Header ApiToken: <token> (由 BvD/Moody's 客户经理开通, 和 Orbis 网页账号绑定) | 商业付费 license (Orbis 订阅 + API 模块单独签约), 下载量/字段范围按合同 | 支持: match 接口按名称/国家/城市/网址等匹配; data 接口 WHERE 支持搜索策略 (行业、地区、规模等) | 财务数据按年份 (如 OPRE 的各年度); 按'更新时间'增量一般需要单独的 Updates/Delivery 产品, 需和 Moody's 确认 |
| DOJ News | 部分可用 | 无需 key | 免费公开 (美国政府作品) | 无全文搜索参数 (parameters[keyword] 会被静默忽略); 只能 parameters[title]=xxx 做标题匹配 | 支持: parameters[date] 精确匹配某一天 (官方示例用 Unix 时间戳, 实测 YYYY-MM-DD 也可以); 无区间 → 需逐天查或按 sort=date 翻页 (不传 sort 默认从 2009 年最旧的开始) |
| FTC Press Releases | 被拦截 | 新闻稿: 无官方 API, 只有 RSS + 网页 (无需 key); api.ftc.gov (HSR 提前终止/DNC 投诉) 需要 api.data.gov key | 免费公开 | RSS 不支持; 网页列表 ?search_api_fulltext=xxx 支持 (需抓 HTML) | RSS 只有最近若干条 (10~30 条不等, pubDate 带时区如 -0400); 网页列表有起止日期筛选; api.ftc.gov 支持 filter[date][condition][path/value/operator] |
| USPTO | 需要 key / license | Open Data Portal: Header X-API-KEY (免费, 需 USPTO.gov 账号 + MFA + 已关联的 ID.me 实名验证, 在 https://data.uspto.gov/apikey 生成); TSDR 商标: 另一个 key (account.uspto.gov/api-manager), Header USPTO-API-KEY | 免费 (官方: at no cost; 未见数据 license 声明) | 支持: q=applicationMetaData.inventionTitle:battery 或全文 q=battery; 支持 AND/OR/字段过滤 | 支持: rangeFilters (POST) 或 GET 的 rangeFilters=applicationMetaData.filingDate 2024-01-01:2024-12-31; 可按 filingDate/grantDate 等 |
| Quartr | 需要 key / license | Header x-api-key (Quartr 商务开通, 在 Quartr Portal portal.quartr.dev 生成) | 商业付费 license: 数据集可单买或打包 (transcripts、audio、live、summaries、解析文档等), companies 和 events 始终包含 | 没有全文关键词搜索; 只能按 tickers / isins / ciks / companyIds / countries / exchanges / typeIds 过滤 | 支持: startDate / endDate (事件日期) 以及 updatedAfter / updatedBefore (数据更新时间, 适合增量) |
| GovInfo | 可用 | 需要 api.data.gov key (免费, 邮箱注册: https://api.data.gov/signup); DEMO_KEY 可试用 | 免费公开 | 支持: POST /search {query:'antitrust collection:(FR)'} (字段操作符语法, 可加 publishdate:range(...)) | 支持: 路径里的 lastModified 时间 (ISO8601, 精确到秒) / published 日期区间 / search 的 publishdate:range() |
| CourtListener | 可用 | 搜索接口 /search/ 可匿名; 其他 (dockets/opinions/clusters/people...) 需要免费 token (注册账号后获取), Header: Authorization: Token xxx | 免费 (非营利); bulk 数据标注 Public Domain Mark; 提额、Webhooks 等高级功能需会员或商业协议 (收费) | 支持: q= (Solr/ES 语法, 支持 AND/OR/"短语"/字段 caseName:xxx) | 支持: filed_after / filed_before (YYYY-MM-DD, 实测可用但文档没列名字; 官方写法是 q=dateFiled:[2025-01-01 TO 2025-06-30]); REST 端点 date_modified__gte=ISO时间 (官方只给了 __gte 语法模式; 实测 dockets 可用, 精确到微秒, 适合增量) |
| LexisNexis Data+ | 需要 key / license | OAuth2 client_credentials: POST auth-api.lexisnexis.com/oauth/v2/token (Basic client_id:secret, form 表单, scope=http://oauth.lexisnexis.com/all) → Bearer, 24 小时有效; 凭证需要 Service-to-Service ID | 商业付费 license: 调用方承担所有 LexisNexis 费用, 能看哪些内容源取决于授权; 具体计费和再分发条款看合同 | 支持: $search= (必填; 有 Boolean 布尔检索模式, 如 antitrust AND merger; w/5 近邻语法在 API 文档里未确认) | 支持: $filter=Date ge 2025-01-01 and Date le 2025-03-31; $orderby=Date desc |
| OSHA | 可用 | 免费 DOL API key (在 dataportal.dol.gov/registration 注册并填问卷后生成, 最多 5 个); 参数 X-API-KEY; 数据集目录 /v4/datasets 无需 key | 免费公开 (美国政府数据) | 支持: filter_object 用 like 运算符做模糊匹配, 如 {"field":"estab_name","operator":"like","value":"%WALMART%"} | 支持: filter_object 用 gt / lt 比较日期字段 (如 open_date), 可用 and/or 组合; sort + sort_by 排序 |
| UCC Filings | 可用 | 不需要 key; 可选 Socrata app token (请求头 X-App-Token, 免费注册) 以获得独立额度 | 免费公开 (州政府开放数据) | 支持: $q= 全文搜索, 或 $where=upper(organizationname) like '%XXX%' (按债务人/担保权人名称) | 支持: $where=filingdate between '2026-09-01' and '2026-09-30' (CO) / dt_accept (CT); 也能按失效日 lapsedate / dt_lapse 查 |

## USAspending.gov  —  可用
_测试时间 2026-10-13T06:43:01+00:00_

- **文档**: https://api.usaspending.gov/docs/endpoints
- **认证**: 无需 API key
- **License**: 免费公开 (官方未见数据 license 声明; 代码仓库是 CC0)
- **限制**: 无公开的硬性限流; limit 默认 10、最大 100 (实测报错提示); page × limit 最多 50,000 条, 再往后要用 last_record_sort_value; 搜索数据从 FY2008 (2007-10-01) 开始, 下载接口可到 FY2001
- **获取方式**: REST JSON, 搜索类接口全是 POST + JSON filters
- **关键词**: 支持: filters.keywords (字符串数组; 官方没写具体搜哪些字段; 旧的单数 keyword 已废弃)
- **时间**: 支持: filters.time_period[{start_date,end_date,date_type}], date_type 可选 action_date / date_signed / last_modified_date / new_awards_only

### 信息来源 (调用方式从哪来)
- 官方: https://api.usaspending.gov/docs/endpoints (无需认证、端点列表)
- 官方: GitHub api_contracts — https://github.com/fedspendingtransparency/usaspending-api/tree/master/usaspending_api/api_contracts (spending_by_award.md / spending_by_award_count.md / awards/last_updated.md / bulk_download/awards.md: 参数、字段名、award 类型代码)
- 官方: .../api_contracts/search_filters.md (keywords、time_period + date_type 四种取值、最早 2007-10-01)
- 官方: https://www.usaspending.gov/data/data-sources-download.pdf 与 about-the-data-download.pdf (每日更新、DoD/USACE 90 天延迟)
- 实测: limit 最大 100、award_type_codes 不能跨组混用 (官方示例反而混用了)、各项过滤的总数变化

### 测试结果
- [通过] **连接** — 数据最近更新: {'last_updated': '10/12/2026'}
- [通过] **关键词搜索 'cybersecurity'** — 返回10条, 其中10条包含'cybersecurity'; 总数 72022085 → 3645
- [通过] **时间过滤 (date_signed 2025-01)** — 总数 72022085 → 433784; 注意返回字段里的 Start Date 不等于签约日期，可以用详情接口核对
- [通过] **详情接口** — generated_internal_id=CONT_AWD_HT940216C0001_9700_-NONE-_-NONE-

### 拿到的字段 / 时间戳
- **award (search)** (13 个字段): `internal_id, Award ID, Recipient Name, Description, Award Amount, Awarding Agency, Start Date, End Date, Last Modified Date, Base Obligation Date, generated_internal_id, awarding_agency_id, agency_slug`
  - 时间戳 `Start Date` = `2016-08-01`
  - 时间戳 `End Date` = `2025-12-31`
  - 时间戳 `Last Modified Date` = `2026-02-10 17:52:09`
  - 时间戳 `Base Obligation Date` = `2016-07-29`
- **award (detail)** (80 个字段): `id, generated_unique_award_id, piid, category, type, type_description, description, total_obligation, subaward_count, total_subaward_amount, date_signed, base_exercised_options, base_and_all_options, total_account_outlay, total_account_obligation, account_outlays_by_defc.[0].code, account_outlays_by_defc.[0].amount, account_obligations_by_defc.[0].code, account_obligations_by_defc.[0].amount, parent_award, latest_transaction_contract_data.idv_type_description, latest_transaction_contract_data.type_of_idc_description, latest_transaction_contract_data.referenced_idv_agency_iden, latest_transaction_contract_data.referenced_idv_agency_desc, latest_transaction_contract_data.solicitation_identifier`
  - 时间戳 `date_signed` = `2016-07-29`
  - 时间戳 `period_of_performance.start_date` = `2016-08-01`
  - 时间戳 `period_of_performance.end_date` = `2025-12-31`
  - 时间戳 `period_of_performance.last_modified_date` = `2026-02-10`
  - 时间戳 `period_of_performance.potential_end_date` = `2025-12-31 00:00:00`

### HTTP 调用
- `GET last_updated` → **200** (1.73s)
- `POST baseline` → **200** (0.39s)
- `POST baseline count` → **200** (0.3s)
- `POST keyword` → **200** (0.36s)
- `POST keyword count` → **200** (0.33s)
- `POST date range` → **200** (0.36s)
- `POST date range count` → **200** (0.32s)
- `GET award detail` → **200** (0.35s)

### 注意事项
- award_type_codes 必须同一大类: 合同 A/B/C/D, 拨款 02-05, 贷款 07/08 等, 混用会 400
- 数据每日更新 (/api/v2/awards/last_updated/ 可查最近更新日期); 合同数据有 ~90 天 DoD 延迟发布
- 大批量建议用 /api/v2/bulk_download/awards/ (异步生成 zip) 而不是翻页

## SAM.gov  —  可用
_测试时间 2026-10-13T06:45:58+00:00_

- **文档**: https://open.gsa.gov/api/get-opportunities-public-api/  ·  https://open.gsa.gov/api/entity-api/
- **认证**: 需要 SAM.gov 账号里生成的 API key (Account Details → Public API Key); 通用 api.data.gov key / DEMO_KEY 无效
- **License**: 免费 (官方未写价格, 未见收费说明); 实体数据分级: Public / FOUO (联系人邮箱电话、层级, 需 Read FOUO 角色) / Sensitive (TIN/EIN/银行信息, 需联邦 System Account + Read Sensitive)
- **限制**: 非联邦个人 key: 无角色 10 次/天, 在 SAM 有任意角色 1,000 次/天; 联邦 system account 10,000 次/天 (Entity/Exclusions 文档); 使用条款要求每 90 天更新 key; Opportunities limit≤1000/页, Exclusions size 1~10
- **获取方式**: REST JSON GET: /opportunities/v2/search, /entity-information/v3/entities, /entity-information/v4/exclusions; 批量用 Extracts (每日/每月文件)
- **关键词**: Opportunities: title= (标题), solnum/noticeid/ncode(NAICS)/organizationName; Entity: legalBusinessName / q= 自由文本 / ueiSAM / cageCode
- **时间**: Opportunities: postedFrom & postedTo 必填 (MM/dd/yyyy, 跨度≤1年), 另有 rdlfrom/rdlto (截止日); Entity: registrationDate / updateDate 等支持 [from,to] 区间

### 信息来源 (调用方式从哪来)
- 官方: https://open.gsa.gov/api/get-opportunities-public-api/ (端点、title/solnum/ncode 等参数、postedFrom/To 必填且≤1年、limit≤1000、description 需追加 api_key)
- 官方: https://open.gsa.gov/api/entity-api/ (v3/v4 端点、legalBusinessName / q / registrationDate=[from,to]、限流表 10/1000/10000 每天、数据分级)
- 官方: https://open.gsa.gov/api/exclusions-api/ (v4 端点、q、size 1~10)
- 官方: https://sam.gov/about/terms-of-use (每 90 天更新 API key)
- 实测: DEMO_KEY 返回 404, SAM 账号生成的 key 返回 200 → 必须用 SAM 自己的 key (官方没有明说)
- 实测 (2026-10-13): 有效 key 下 Opportunities 日期过滤 10/10 在区间内、title 关键词 15236 → 4、Entity 和 Exclusions 都正常; 响应头里没有限流信息, 额度只能自己记

### 测试结果
- [通过] **连接** — 2026-09 发布的机会总数 15236
- [通过] **时间 postedFrom/postedTo** — 10/10 条在 2026-09-01~2026-09-30 内; 样例 ['2026-09-30', '2026-09-30', '2026-09-30']
- [通过] **标题关键词 title='cybersecurity'** — 返回4条, 其中4条包含'cybersecurity'; 总数 15236 → 4
- [通过] **Entity 按名称搜索** — totalRecords=163
- [通过] **Exclusions (排除/禁止名单)** — totalRecords=57

### 拿到的字段 / 时间戳
- **opportunity** (41 个字段): `active, additionalInfoLink, archiveDate, archiveType, award.date, award.number, award.amount, award.awardee.name, award.awardee.location.city, award.awardee.location.state, award.awardee.location.zip, award.awardee.location.country, baseType, classificationCode, description, fullParentPathCode, fullParentPathName, links.[0].rel, links.[0].href, naicsCode, naicsCodes, noticeId, officeAddress.zipcode, officeAddress.city, officeAddress.countryCode`
  - 时间戳 `archiveDate` = `2026-10-15`
  - 时间戳 `award.date` = `2026-09-30`
  - 时间戳 `postedDate` = `2026-09-30`
- **entity** (80 个字段): `entityRegistration.samRegistered, entityRegistration.ueiSAM, entityRegistration.entityEFTIndicator, entityRegistration.cageCode, entityRegistration.dodaac, entityRegistration.legalBusinessName, entityRegistration.dbaName, entityRegistration.purposeOfRegistrationCode, entityRegistration.purposeOfRegistrationDesc, entityRegistration.registrationStatus, entityRegistration.evsSource, entityRegistration.registrationDate, entityRegistration.lastUpdateDate, entityRegistration.registrationExpirationDate, entityRegistration.activationDate, entityRegistration.ueiStatus, entityRegistration.ueiExpirationDate, entityRegistration.ueiCreationDate, entityRegistration.publicDisplayFlag, entityRegistration.exclusionStatusFlag, entityRegistration.exclusionURL, entityRegistration.dnbOpenData, coreData.entityInformation.entityURL, coreData.entityInformation.entityDivisionName, coreData.entityInformation.entityDivisionNumber`
  - 时间戳 `entityRegistration.registrationDate` = `2003-04-04`
  - 时间戳 `entityRegistration.lastUpdateDate` = `2022-03-28`
  - 时间戳 `entityRegistration.registrationExpirationDate` = `2018-06-06`
  - 时间戳 `entityRegistration.activationDate` = `2017-06-06`
  - 时间戳 `entityRegistration.ueiCreationDate` = `2020-06-21`
  - 时间戳 `coreData.entityInformation.entityStartDate` = `1994-08-29`
  - 时间戳 `coreData.entityInformation.fiscalYearEndCloseDate` = `12/31`
  - 时间戳 `coreData.entityInformation.submissionDate` = `2017-06-06`
- **exclusion** (46 个字段): `exclusionDetails.classificationType, exclusionDetails.exclusionType, exclusionDetails.exclusionProgram, exclusionDetails.excludingAgencyCode, exclusionDetails.excludingAgencyName, exclusionIdentification.ueiSAM, exclusionIdentification.cageCode, exclusionIdentification.npi, exclusionIdentification.prefix, exclusionIdentification.firstName, exclusionIdentification.middleName, exclusionIdentification.lastName, exclusionIdentification.suffix, exclusionIdentification.entityName, exclusionIdentification.dnbOpenData, exclusionActions.listOfActions.[0].createDate, exclusionActions.listOfActions.[0].updateDate, exclusionActions.listOfActions.[0].activateDate, exclusionActions.listOfActions.[0].terminationDate, exclusionActions.listOfActions.[0].terminationType, exclusionActions.listOfActions.[0].recordStatus, exclusionPrimaryAddress.addressLine1, exclusionPrimaryAddress.addressLine2, exclusionPrimaryAddress.city, exclusionPrimaryAddress.stateOrProvinceCode`
  - 时间戳 `exclusionActions.listOfActions.[0].createDate` = `05-16-2025`
  - 时间戳 `exclusionActions.listOfActions.[0].updateDate` = `05-16-2025`
  - 时间戳 `exclusionActions.listOfActions.[0].activateDate` = `05-15-2025`
  - 时间戳 `exclusionActions.listOfActions.[0].terminationDate` = `05-14-2035`

### HTTP 调用
- `GET opportunities (date range)` → **200** (1.05s)
- `GET opportunities keyword` → **200** (0.41s)
- `GET entity search` → **200** (0.36s)
- `GET exclusions` → **200** (0.36s)

### 注意事项
- 无 key / 无效 key 时 api.sam.gov 所有路径都返回空 body 的 404 (不是 401/403, 容易误判为地址错误); 带有效 key 从新加坡 IP 访问完全正常, 不限制非美 IP
- 时间字段: Opportunities 有 postedDate/responseDeadLine/archiveDate/award.date (只有日期); Entity 有 registrationDate/lastUpdateDate/registrationExpirationDate; Exclusions 是 MM-DD-YYYY 格式的 createDate/updateDate/activateDate/terminationDate; description 字段只是一个需要再带 api_key 请求的链接
- 10 次/天 的额度非常少, 生产使用一定要申请 entity 角色或用 Extracts 批量文件
- 注意: 每次运行消耗 4 次调用 (无角色 key 每天只有 10 次)

## Grants.gov  —  可用
_测试时间 2026-10-14T01:45:53+00:00_

- **文档**: https://www.grants.gov/api/api-guide
- **认证**: search2 / fetchOpportunity 无需 key; 其他部分接口需要找 Help Desk 申请 API key (system-to-system 另有流程)
- **License**: 免费公开 (官方称 Unrestricted Access; 未见 license 声明)
- **限制**: 无公开限流数字; 官方未写 rows 上限 (实测 rows=5000 正常返回, rows=20000 失败); 每日还有完整 XML Extract (grants.gov/xml-extract, ~78MB zip) 可下载
- **获取方式**: POST JSON → https://api.grants.gov/v1/api/search2 , 详情 POST /v1/api/fetchOpportunity
- **关键词**: 支持: keyword (标题/描述全文); 另有 agencies / fundingCategories / eligibilities / aln (原 CFDA 编号) / oppNum 过滤
- **时间**: search2 没有日期区间参数; 只能 sortBy=openDate|desc 后在客户端按 openDate/closeDate 过滤, 或用 XML Extract

### 信息来源 (调用方式从哪来)
- 官方: https://www.grants.gov/api/api-guide (search2/fetchOpportunity 无需认证)
- 官方: https://www.grants.gov/api/common/search2 (POST 地址、keyword / agencies / fundingCategories / eligibilities / aln / oppStatuses 参数、返回结构 oppHits/hitCount)
- 官方: https://www.grants.gov/api/common/fetchopportunity (opportunityId、详情字段及时间格式)
- 官方: https://www.grants.gov/xml-extract (每日 XML 全量导出)
- 实测: sortBy=openDate|desc 的取值与效果、oppStatuses 默认值、rows 上限、无日期区间参数的影响

### 测试结果
- [通过] **连接** — 当前开放/预告机会总数 1469
- [通过] **关键词搜索 'cybersecurity'** — 返回25条, 其中3条包含'cybersecurity'; 总数 1469 → 193
- [通过] **时间排序 openDate|desc** — 前3条 openDate: ['10/13/2026', '10/13/2026', '10/13/2026']
- [跳过] **时间过滤 (服务端)** — 无服务端参数; 客户端过滤 2026-09-01~今天 得到 50/50 条
- [通过] **可查历史 (closed/archived)** — cybersecurity: 193 → 2127
- [通过] **详情接口** — id=355824

### 拿到的字段 / 时间戳
- **opportunity (search)** (10 个字段): `id, number, title, agencyCode, agency, openDate, closeDate, oppStatus, docType, cfdaList`
  - 时间戳 `openDate` = `08/01/2024`
- **opportunity (detail)** (80 个字段): `id, revision, opportunityNumber, opportunityTitle, owningAgencyCode, listed, publisherUid, modifiedComments, flag2006, opportunityCategory.category, opportunityCategory.description, agencyDetails.code, agencyDetails.seed, agencyDetails.agencyName, agencyDetails.agencyCode, agencyDetails.topAgencyCode, topAgencyDetails.code, topAgencyDetails.seed, topAgencyDetails.agencyName, topAgencyDetails.agencyCode, topAgencyDetails.topAgencyCode, forecast.opportunityId, forecast.version, forecast.postingDate, forecast.forecastDesc`
  - 时间戳 `modifiedComments` = `Title revision`
  - 时间戳 `forecast.postingDate` = `Aug 01, 2024 12:00:00 AM EDT`
  - 时间戳 `forecast.estSynopsisPostingDate` = `Apr 14, 2025 12:00:00 AM EDT`
  - 时间戳 `forecast.estApplicationResponseDate` = `Jun 23, 2025 12:00:00 AM EDT`
  - 时间戳 `forecast.estAwardDate` = `Sep 15, 2025 12:00:00 AM EDT`
  - 时间戳 `forecast.estProjectStartDate` = `Sep 30, 2025 12:00:00 AM EDT`
  - 时间戳 `forecast.createdDate` = `Aug 01, 2024 03:26:32 PM EDT`
  - 时间戳 `forecast.lastUpdatedDate` = `Mar 20, 2025 10:28:30 AM EDT`
  - 时间戳 `opportunityHistoryDetails.[0].forecast.postingDate` = `Aug 01, 2024 12:00:00 AM EDT`
  - 时间戳 `opportunityHistoryDetails.[0].forecast.estSynopsisPostingDate` = `Nov 21, 2024 12:00:00 AM EST`
  - 时间戳 `opportunityHistoryDetails.[0].forecast.estApplicationResponseDate` = `Feb 13, 2025 12:00:00 AM EST`
  - 时间戳 `opportunityHistoryDetails.[0].forecast.estAwardDate` = `Jun 17, 2025 12:00:00 AM EDT`
  - 时间戳 `opportunityHistoryDetails.[0].forecast.estProjectStartDate` = `Jul 01, 2025 12:00:00 AM EDT`
  - 时间戳 `opportunityHistoryDetails.[0].forecast.actionDate` = `Aug 02, 2024 02:18:11 PM EDT`
  - 时间戳 `opportunityHistoryDetails.[0].forecast.createdDate` = `Aug 01, 2024 03:26:32 PM EDT`
  - 时间戳 `opportunityHistoryDetails.[0].forecast.lastUpdatedDate` = `Aug 01, 2024 03:26:32 PM EDT`
  - 时间戳 `forecastModifiedFields` = `["revision", "version", "opportunityTitle"]`

### HTTP 调用
- `POST baseline` → **200** (1.59s)
- `POST keyword` → **200** (0.35s)
- `POST sort by openDate desc` → **200** (0.41s)
- `POST include closed/archived` → **200** (0.39s)
- `POST fetchOpportunity` → **200** (0.52s)

### 注意事项
- 搜索结果日期是 MM/DD/YYYY 字符串 (无时区); 详情里 postingDate / lastUpdatedDate 有完整时间和时区 (如 EDT)
- oppStatuses 默认 forecasted|posted; 要查历史需显式加 closed|archived
- 返回体里带一个 token 字段, 匿名搜索用不到, 可忽略

## D&B Direct+  —  需要 key / license
_测试时间 2026-10-13T06:43:06+00:00_

- **文档**: https://directplus.documentation.dnb.com (除首页外现在都要 D&B 账号登录)
- **认证**: OAuth2 client_credentials: Basic base64(key:secret) → POST /v3/token (form 表单 grant_type=client_credentials) 拿 access_token (24 小时有效), 之后 Bearer; 旧版 /v2/token 用 JSON body
- **License**: 商业付费 license: key/secret 只能找 D&B 客户代表开通, 按产品/Data Block 授权 (companyinfo L1 是所有 block 的起点); 每次调用计入合同配额
- **限制**: TPS 和 周/月/年配额都按合同 (官方无默认数字), 超出返回 429 (errorCode 0045/0046), 配额每天 UTC 0 点重置; 未开通的产品返回 401 errorCode 00004
- **获取方式**: REST JSON: /v1/match/cleanseMatch (名称+地址→DUNS), /v1/search/criteria (条件搜索), /v1/data/duns/{duns}?blockIDs=... (数据块)
- **关键词**: 支持: search/criteria 的 searchTerm (公司名/关键词) 及 industry/地域等条件; typeahead 可前缀匹配
- **时间**: 不支持按时间查询; 变化追踪要用 Monitoring (订阅 DUNS 后推送变更通知) 

### 信息来源 (调用方式从哪来)
- 官方 (Wayback 存档, 因现在需登录): directplus.documentation.dnb.com/html/pages/Authentication.html — 2024-11 版 /v3/token、form body、24 小时、错误码 00004/00040; 2022 版 /v2/token
- 官方 (Wayback 存档 2024-01): .../html/pages/UsingDplusAPIs.html — 配额按合同、429 错误码 0045/0046
- 官方 (Wayback 存档 2025-01): .../html/resources/JSONSample_IDR.html 与 JSONSample_Search.html — cleanseMatch、search/criteria、typeahead 的请求和返回字段
- 官方 (Wayback 存档): companyinfo_L2_v1.json swagger (data/duns + blockIDs)、StandardDataBlocks、Monitoring 页面
- 实测: 无凭证请求 token 返回 401 'not currently authorised' (= 官方错误码 00004)
- 注意: 未用真实凭证跑过; 官方文档最新只看到 2024-11 的存档

### 测试结果
- [跳过] **连接** — 未配置 DNB_API_KEY / DNB_API_SECRET; 端点可达, 返回 401

### HTTP 调用
- `POST no-key token probe` → **401** (0.33s) · `{"transactionDetail": {"transactionID": "072e4376-3a64-4a3d-9ca3-76cb823c34ce14865", "transactionTimestamp": "2026-10-13T06:43:06.198Z", "inLanguage": "en-US", `

### 注意事项
- 每个响应都带 transactionDetail.transactionTimestamp (调用时间); 数据块里各元素带 lastUpdatedDate
- Data Block 命名规则: companyinfo_L2_v1, hierarchyconnections_L1_v1, financialstrengthinsight_L2_v1 … (Level 越高内容越多; 价格官方未公开)
- 本机无凭证探测: POST /v2/token 返回 401 'You are not currently authorised to access this product' — 端点可达

## Moody's Orbis  —  需要 key / license
_测试时间 2026-10-13T06:43:06+00:00_

- **文档**: 无公开官方文档 (客户专属, HTML/PDF 格式随合同提供); 公开可参考的是合作方开源集成, 见 sources
- **认证**: Header ApiToken: <token> (由 BvD/Moody's 客户经理开通, 和 Orbis 网页账号绑定)
- **License**: 商业付费 license (Orbis 订阅 + API 模块单独签约), 下载量/字段范围按合同
- **限制**: 按合同; 合作方 Maltego 称多数 license 约 1~10 个并发请求; match 最多 ~50 条结果; 字段名必须用 Orbis 数据字典里的代码 (可用 Companies/metadata/select 查)
- **获取方式**: REST JSON (api.bvdinfo.com/v1/orbis/...): Companies/match (名称匹配→BvD ID), Companies/data (WHERE + SELECT 取字段)
- **关键词**: 支持: match 接口按名称/国家/城市/网址等匹配; data 接口 WHERE 支持搜索策略 (行业、地区、规模等)
- **时间**: 财务数据按年份 (如 OPRE 的各年度); 按'更新时间'增量一般需要单独的 Updates/Delivery 产品, 需和 Moody's 确认

### 信息来源 (调用方式从哪来)
- 半官方: CluedIn 开源 BvD 集成 https://github.com/CluedIn-io/CluedIn.Enricher.BvD (ApiToken 请求头、Companies/match 与 Companies/data 的请求体和返回结构、字段代码列表)
- 半官方: https://documentation.cluedin.net/preparation/enricher/bvd 、 https://docs.strise.ai/technology/orbis-delegated-access/ (ApiToken 需找 BvD 客户代表)
- 半官方: https://docs.maltego.com/support/solutions/articles/15000036595-bvd-orbis (API 权限单独开通、并发数)
- 半官方: 英国政府 G-Cloud 采购目录中 Moody's Analytics UK 的 Orbis 条目 (价格示例、API 文档为 HTML/PDF)
- 实测: api.bvdinfo.com/v1/orbis/* 无 token 返回 401 error.token.rejected
- 没有任何一条能标为官方 : Moody's/BvD 未公开 API 文档

### 测试结果
- [跳过] **连接** — 未配置 ORBIS_API_TOKEN; 端点可达, 返回 401

### HTTP 调用
- `POST no-token probe` → **401** (0.6s) · `{"Message": "Unauthorized Access. Please contact support.", "ErrorCode": "error.token.rejected"}`

### 注意事项
- 注意: 本模块的请求体结构基于 BvD API 的常见形式, 不同账号版本的字段代码可能不同, 拿到 token 后先对照账号内文档调整 ORBIS_* 变量
- 本机无 token 探测: 返回 401 {'ErrorCode': 'error.token.rejected'} — 端点可达
- 财务字段按年份取, 例如 {"OPRE": {"INDEXORYEAR": "0", "CURRENCY": "USD"}}; 代码里的 CLOSDATE / UPDATED_DATE 字段名未经验证

## DOJ News  —  部分可用
_测试时间 2026-10-13T06:43:07+00:00_

- **文档**: https://www.justice.gov/developer
- **认证**: 无需 key
- **License**: 免费公开 (美国政府作品)
- **限制**: pagesize 最大 50; 官方限流: 超过 4 次/秒会降速甚至被封; 总量 27 万+ 条 (2009 至今, 官方页面写的 14,000 已过时)
- **获取方式**: GET https://www.justice.gov/api/v1/press_releases.json (另有 blog_entries.json; speeches/videos 不存在, 实测 404); 也有 RSS /news/rss?type=press_release
- **关键词**: 无全文搜索参数 (parameters[keyword] 会被静默忽略); 只能 parameters[title]=xxx 做标题匹配
- **时间**: 支持: parameters[date] 精确匹配某一天 (官方示例用 Unix 时间戳, 实测 YYYY-MM-DD 也可以); 无区间 → 需逐天查或按 sort=date 翻页 (不传 sort 默认从 2009 年最旧的开始)

### 信息来源 (调用方式从哪来)
- 官方: https://www.justice.gov/developer/api-documentation/api_v1 (2025-12-18 更新: press_releases / blog_entries 端点、pagesize≤50、4 次/秒限流、parameters[title] / parameters[date]、sort/direction/page、字段格式)
- 官方: https://www.justice.gov/developer (概览; 写着可按部门/主题过滤, 与实测不符)
- 官方: https://www.justice.gov/legalpolicies (内容默认 public domain, 部分图片除外)
- 实测: parameters[keyword] 和 parameters[component] 被忽略、YYYY-MM-DD 日期格式可用、date 为当天 12:00 UTC、RSS /news/rss?type=press_release (不在 API 文档里)

### 测试结果
- [通过] **连接** — 总数 273982
- [失败] **全文关键词 parameters[keyword]** — 总数 273982 → 273982 (不变 = 参数无效)
- [通过] **标题匹配 parameters[title]='antitrust'** — 返回20条, 其中20条包含'antitrust'; 总数 273982 → 270
- [通过] **按日期 parameters[date]=2026-10-01** — 20/20 条在 2026-10-01~2026-10-01 内; 总数 273982 → 105; 样例 ['2026-10-01', '2026-10-01', '2026-10-01']
- [通过] **RSS 备用通道** — RSS 只含最近若干条, 适合增量监控

### 拿到的字段 / 时间戳
- **press_release** (19 个字段): `attachment, body, changed, component.[0].uuid, component.[0].name, created, date, image.[0].file.id, image.[0].file.resource, image.[0].file.uuid, image.[0].alt, image.[0].title, number, teaser, title, topic.[0].uuid, topic.[0].name, url, uuid`
  - 时间戳 `changed` = `<time datetime="2026-10-12T09:02:46-04:00">1791810166</time>
`
  - 时间戳 `created` = `<time datetime="2026-10-11T21:47:15-04:00">1791769635</time>
`
  - 时间戳 `date` = `1791806400`

### HTTP 调用
- `GET latest` → **200** (0.35s)
- `GET keyword param (expected ignored)` → **200** (0.16s)
- `GET title match` → **200** (0.18s)
- `GET single date` → **200** (0.15s)
- `GET RSS feed` → **200** (0.09s)

### 注意事项
- 时间字段: date = Unix 秒 (实测是发布日 12:00 UTC, 只有日期精度); created/changed 是 HTML <time datetime=...> 包着 Unix 秒, 精确到秒
- body/teaser 是 HTML, 需要自己清洗; component(发布部门)/topic 是 list
- 未知参数不报错, 直接返回全量 → 一定要校验 resultset.count 是否变化
- 按部门过滤 parameters[component]: 官方开发者页说支持按部门/主题过滤, 但实测被忽略 (总数不变), 需要客户端过滤
- 时间戳示例: date=1791806400 → 2026-10-12 12:00:00 UTC; created=2026-10-12 01:47:15; changed=2026-10-12 13:02:46

## FTC Press Releases  —  被拦截
_测试时间 2026-10-13T06:43:11+00:00_

- **文档**: https://www.ftc.gov/developer  ·  https://www.ftc.gov/developer/api/v0/endpoints/hsr-early-termination-notices  ·  RSS: https://www.ftc.gov/news-events/stay-connected/ftc-rss-feeds
- **认证**: 新闻稿: 无官方 API, 只有 RSS + 网页 (无需 key); api.ftc.gov (HSR 提前终止/DNC 投诉) 需要 api.data.gov key
- **License**: 免费公开
- **限制**: www.ftc.gov 有 WAF, 识别为自动化请求会返回 404 拦截页 (按 IP, 换一台机器即可访问); api.ftc.gov 限流由 api.data.gov 控制 (实测个人 key X-RateLimit-Limit=20000, DEMO_KEY 实测 10), 每页最多 50 条
- **获取方式**: RSS (feeds/press-release*.xml) 或抓取 /news-events/news/press-releases 列表页
- **关键词**: RSS 不支持; 网页列表 ?search_api_fulltext=xxx 支持 (需抓 HTML)
- **时间**: RSS 只有最近若干条 (10~30 条不等, pubDate 带时区如 -0400); 网页列表有起止日期筛选; api.ftc.gov 支持 filter[date][condition][path/value/operator]

### 信息来源 (调用方式从哪来)
- 官方: https://www.ftc.gov/developer (只有 dnc-complaints 和 hsr-early-termination-notices 两个 API, 无新闻稿 API; 需 api.data.gov key)
- 官方: https://www.ftc.gov/developer/api/v0/endpoints/hsr-early-termination-notices (filter[title][value]+operator=CONTAINS、page[limit]/page[offset]、sort[x][path]/sort[x][direction])
- 官方: https://www.ftc.gov/news-events/stay-connected/ftc-rss-feeds (feeds/press-release.xml、-competition.xml、-consumer-protection.xml 三个 RSS 地址) — 从另一台主机访问确认 feed 在线
- 实测/页面观察: 网页列表 ?search_api_fulltext= 参数 (来自页面搜索表单, 无文档)、WAF 拦截行为、RSS 条数

### 测试结果
- [失败] **www.ftc.gov 可访问** — 被 WAF 拦截 (IP 被判定为自动化请求)
- [失败] **RSS all press releases** — HTTP 404 (主页已被 WAF 拦截, 无法判断 URL 是否正确)
- [失败] **RSS competition** — HTTP 404 (主页已被 WAF 拦截, 无法判断 URL 是否正确)
- [失败] **RSS consumer protection** — HTTP 404 (主页已被 WAF 拦截, 无法判断 URL 是否正确)
- [失败] **网页关键词搜索 'merger'** — WAF 拦截 / 不可达
- [通过] **api.ftc.gov 连接 (HSR 公告)** — 5 条
- [通过] **api.ftc.gov filter[title] CONTAINS 'Holdings'** — 返回5条, 其中5条包含'holdings'

### 拿到的字段 / 时间戳
- **HSR early termination notice** (8 个字段): `title, created, updated, acquired-party, acquiring-party, date, acquired-entities, transaction-number`
  - 时间戳 `created` = `2026-10-07T13:22:14+00:00`
  - 时间戳 `updated` = `2026-10-07T13:22:14+00:00`
  - 时间戳 `date` = `2026-10-05`

### HTTP 调用
- `GET homepage (WAF check)` → **404** (0.24s) · `Page Not Found No additional information is available with regards to this resource . $('#resource').text(window.location);`
- `GET RSS all press releases` → **404** (0.07s) · `Page Not Found No additional information is available with regards to this resource . $('#resource').text(window.location);`
- `GET RSS competition` → **404** (0.07s) · `Page Not Found No additional information is available with regards to this resource . $('#resource').text(window.location);`
- `GET RSS consumer protection` → **404** (0.07s) · `Page Not Found No additional information is available with regards to this resource . $('#resource').text(window.location);`
- `GET web search list` → **404** (0.07s) · `Page Not Found No additional information is available with regards to this resource . $('#resource').text(window.location);`
- `GET api.ftc.gov HSR early termination` → **200** (2.31s) · 限流头 `{'X-Ratelimit-Limit': '20000', 'X-Ratelimit-Remaining': '19995'}`
- `GET api.ftc.gov keyword filter` → **200** (1.4s) · 限流头 `{'X-Ratelimit-Limit': '20000', 'X-Ratelimit-Remaining': '19994'}`

### 注意事项
- 注意: 本机测试时 www.ftc.gov 对所有路径返回 'The request resembles an abusive automated request' (WAF 拦截, 带 Error Reference ID), 需要换 IP / 联系 PWH-Alert@ftc.gov 加白名单
- api.ftc.gov 的数据不是新闻稿, 而是 HSR 早期终止公告等结构化数据 (JSON:API 格式)
- 抓网页请降低频率、带正常 UA, 否则很容易被 WAF 拉黑

## USPTO  —  需要 key / license
_测试时间 2026-10-13T06:43:13+00:00_

- **文档**: https://data.uspto.gov/apis/getting-started  ·  https://data.uspto.gov/apis/api-rate-limits  ·  https://data.uspto.gov/swagger/swagger.yaml
- **认证**: Open Data Portal: Header X-API-KEY (免费, 需 USPTO.gov 账号 + MFA + 已关联的 ID.me 实名验证, 在 https://data.uspto.gov/apikey 生成); TSDR 商标: 另一个 key (account.uspto.gov/api-manager), Header USPTO-API-KEY
- **License**: 免费 (官方: at no cost; 未见数据 license 声明)
- **限制**: ODP 按 key: 元数据 500 万次/周、文档 120 万次/周、4~15 次/秒; 同一 key 不能并发 (burst=1); bulk 同一文件每年 20 次; TSDR 60 次/分钟 (PDF/ZIP 4 次/分钟); 查询 limit 默认 25
- **获取方式**: ODP REST JSON: GET/POST /api/v1/patent/applications/search (q 走 OpenSearch 语法), /{appNumber}/documents 等; 批量用 bulk datasets
- **关键词**: 支持: q=applicationMetaData.inventionTitle:battery 或全文 q=battery; 支持 AND/OR/字段过滤
- **时间**: 支持: rangeFilters (POST) 或 GET 的 rangeFilters=applicationMetaData.filingDate 2024-01-01:2024-12-31; 可按 filingDate/grantDate 等

### 信息来源 (调用方式从哪来)
- 官方: https://data.uspto.gov/apis/getting-started (X-API-KEY、免费、USPTO.gov 账号 + ID.me、key 在 /apikey 页)
- 官方: https://data.uspto.gov/apis/api-rate-limits (每周额度、每秒限速、禁止并发、bulk 限制)
- 官方: https://data.uspto.gov/apis/api-syntax-examples 与 /apis/patent-file-wrapper/search (q 语法、POST 体 pagination/sort/rangeFilters、字段名、patentFileWrapperDataBag、lastIngestionDateTime)
- 官方: https://data.uspto.gov/swagger/swagger.yaml、odp-common-base.yaml、tsdr-swagger.yaml (limit 默认 25; TSDR 只能按案号查)
- 官方: https://tsdr.uspto.gov/faqview (TSDR 单独 key、60 次/分钟)
- 官方: https://data.uspto.gov/support/transition-guide/patentsview (PatentsView 迁移状态)
- 官方 (ODP 网站横幅): 2026-06-18 起登录需 MFA; 2026-08-18 起需补填 4 项资料, 未补的 key 已于 2026-10-08 停用; 90 天未用的 key 会被删除
- 实测: 无 key 返回 401; TSDR 请求头名 USPTO-API-KEY (官方用户指南已失效, 由网关响应推断); 路径带 .json 也能被接受

### 测试结果
- [跳过] **连接** — 未配置 USPTO_API_KEY; 返回 401 Unauthorized

### HTTP 调用
- `GET no-key probe` → **401** (0.91s) · `{"message": "Unauthorized"}`
- `GET TSDR no-key probe` → **401** (0.83s) · `Beginning October 2, you’ll need to register for an API key to download bulk data from our TSDR APIs. Register for an API key at https://account.uspto.gov/api-m`

### 注意事项
- 时间字段: filingDate, grantDate, effectiveFilingDate, earliestPublicationDate, lastIngestionDateTime (入库时间, 适合增量)
- 商标没有公开的关键词搜索 API (TSDR 只能按序列号/注册号查); 商标全文搜索只能用网页或 bulk 数据
- PatentsView: 2026-03-20 起迁移, bulk 数据表已在 ODP, 但 API 尚未上线 (官方无时间表); 旧 api.patentsview.org 已 301 跳转到迁移说明, 旧 key 不能用于 ODP

## Quartr  —  需要 key / license
_测试时间 2026-10-13T06:43:14+00:00_

- **文档**: https://quartr.com/docs/ (docs.quartr.com 会跳转到这里)  ·  OpenAPI: https://api.quartr.com/public/v3/openapi.json
- **认证**: Header x-api-key (Quartr 商务开通, 在 Quartr Portal portal.quartr.dev 生成)
- **License**: 商业付费 license: 数据集可单买或打包 (transcripts、audio、live、summaries、解析文档等), companies 和 events 始终包含
- **限制**: 按套餐, 默认 50 次/秒, 超出返回 429; 游标分页 (limit 默认 10、最大 500, 跟 nextCursor 直到为 null); v1/v2 已下线 (实测 410 Gone), 只能用 v3
- **获取方式**: REST JSON: /public/v3/companies, /events, /documents/{transcripts|reports|slides}, /audio, /live; 另有 Webhooks 和 Snowflake 数据共享
- **关键词**: 没有全文关键词搜索; 只能按 tickers / isins / ciks / companyIds / countries / exchanges / typeIds 过滤
- **时间**: 支持: startDate / endDate (事件日期) 以及 updatedAfter / updatedBefore (数据更新时间, 适合增量)

### 信息来源 (调用方式从哪来)
- 官方: https://api.quartr.com/public/v3/openapi.json (全部端点和参数、x-api-key、无关键词参数)
- 官方: https://quartr.com/docs/rest-api/auth.md (认证、Portal、默认 50 次/秒)
- 官方: https://quartr.com/docs/rest-api/fetching-data.md (游标分页、startDate/endDate 按事件日期、updatedAfter 用于增量、计费方式)
- 官方: https://quartr.com/docs/datasets/summaries.md 与 live-earnings-call-transcripts.md (摘要、直播文字稿 transcriptVersion 1.6/1.7)
- 实测: v1/v2 返回 410、v3 无 key 返回 401

### 测试结果
- [通过] **OpenAPI 公开可读** — 35 个 path
- [跳过] **连接** — 未配置 QUARTR_API_KEY; 返回 401

### HTTP 调用
- `GET openapi spec (public)` → **200** (1.0s)
- `GET no-key probe` → **401** (0.28s) · `{"message": "Unauthorized", "statusCode": 401}`

### 注意事项
- 实时电话会: /live 和 /live/transcripts 提供直播中的文字稿 (transcriptVersion)
- documents/*/summary 提供 AI 摘要 (length / plain 参数); transcripts/{id}/chapters 有分段
- OpenAPI 公开, 但所有数据接口无 key 返回 401

## GovInfo  —  可用
_测试时间 2026-10-13T06:43:20+00:00_

- **文档**: https://api.govinfo.gov/docs  /  https://github.com/usgpo/api
- **认证**: 需要 api.data.gov key (免费, 邮箱注册: https://api.data.gov/signup); DEMO_KEY 可试用
- **License**: 免费公开
- **限制**: 个人 key: 36,000 次/小时、1,200 次/分钟、40 次/秒 (官方 README; 实测响应头 X-RateLimit-Limit=36000 一致); DEMO_KEY 官方写 30 次/小时+50 次/天, 实测只给 10; pageSize 最大 1000
- **获取方式**: REST JSON: /collections/{code}/{lastModifiedStart} 增量; /published/{date} 按发布日期; POST /search 全文; /packages/{id}/summary 详情
- **关键词**: 支持: POST /search {query:'antitrust collection:(FR)'} (字段操作符语法, 可加 publishdate:range(...))
- **时间**: 支持: 路径里的 lastModified 时间 (ISO8601, 精确到秒) / published 日期区间 / search 的 publishdate:range()

### 信息来源 (调用方式从哪来)
- 官方: https://github.com/usgpo/api (README: 认证、限流 36,000/小时、/collections、/published、/search、offsetMark、sorts、/packages/{id}/summary 下载链接)
- 官方: https://api.govinfo.gov/api-docs (OpenAPI 3.0.1 规格; /docs 页面是 JS 渲染, 实际从这里读) — lastModified 格式 yyyy-MM-dd'T'HH:mm:ss'Z'、pageSize≤1000
- 官方: https://www.govinfo.gov/help/finding-info (publishdate:range(...) 语法)
- 官方: https://api.data.gov/docs/developer-manual/ (DEMO_KEY 默认 30/小时、50/天; X-RateLimit 头)
- 实测: DEMO_KEY 实际 Limit=10、用完后 Retry-After≈64000s; 个人 key Limit=36000; 各项过滤的总数变化

### 测试结果
- [通过] **连接** — 42 个 collection, 如 ['ANNUALREP', 'BILLS', 'BILLSTATUS', 'BILLSUM', 'BUDGET', 'CCAL', 'CDIR', 'CDOC']
- [通过] **全文搜索 'antitrust' (FR)** — FR 总数 1027506 → 14650; 首条标题: Fees for Services Performed in Connection With Licensing and Related Services-20
- [通过] **search + publishdate:range(2025Q1)** — 10/10 条在 2025-01-01~2025-03-31 内; 总数 14650 → 101; 样例 ['2025-03-31', '2025-03-18', '2025-03-17']
- [通过] **增量: FR lastModified >= 2026-10-01T00:00:00Z** — 10/10 条在 2026-10-01~2100-01-01 内; 样例 ['2026-10-10', '2026-10-09', '2026-10-09']
- [通过] **详情 /packages/{id}/summary** — download 链接: ['premisLink', 'xmlLink', 'zipLink', 'modsLink', 'pdfLink']

### 拿到的字段 / 时间戳
- **search result** (15 个字段): `title, packageId, granuleId, lastModified, governmentAuthor, dateIssued, collectionCode, dateIngested, download.premisLink, download.txtLink, download.zipLink, download.modsLink, download.pdfLink, relatedLink, resultLink`
  - 时间戳 `lastModified` = `2026-10-10T07:43:47Z`
  - 时间戳 `dateIssued` = `2026-10-13`
  - 时间戳 `dateIngested` = `2026-10-10`
- **package (collections)** (7 个字段): `congress, dateIssued, docClass, lastModified, packageId, packageLink, title`
  - 时间戳 `dateIssued` = `2026-10-13`
  - 时间戳 `lastModified` = `2026-10-10T07:43:47Z`
- **package summary** (28 个字段): `dateIssued, issue, documentType, packageId, collectionCode, detailsLink, title, branch, collectionName, volume, download.premisLink, download.xmlLink, download.zipLink, download.modsLink, download.pdfLink, pages, governmentAuthor2, governmentAuthor1, publisher, suDocClassNumber, docClass, lastModified, category, otherIdentifier.issn, otherIdentifier.migrated-doc-id`
  - 时间戳 `dateIssued` = `2026-10-13`
  - 时间戳 `lastModified` = `2026-10-10T07:43:47Z`

### HTTP 调用
- `GET collections` → **200** (3.35s) · 限流头 `{'X-Ratelimit-Limit': '36000', 'X-Ratelimit-Remaining': '35987'}`
- `POST search baseline FR` → **200** (0.4s) · 限流头 `{'X-Ratelimit-Limit': '36000', 'X-Ratelimit-Remaining': '35986'}`
- `POST search keyword` → **200** (0.38s) · 限流头 `{'X-Ratelimit-Limit': '36000', 'X-Ratelimit-Remaining': '35986'}`
- `POST search keyword+date` → **200** (0.39s) · 限流头 `{'X-Ratelimit-Limit': '36000', 'X-Ratelimit-Remaining': '35984'}`
- `GET collection since lastModified` → **200** (0.36s) · 限流头 `{'X-Ratelimit-Limit': '36000', 'X-Ratelimit-Remaining': '35984'}`
- `GET package summary` → **200** (0.41s) · 限流头 `{'X-Ratelimit-Limit': '36000', 'X-Ratelimit-Remaining': '35982'}`

### 注意事项
- 翻页使用 offsetMark=* 游标 (旧的 offset 参数已废弃)
- 两种时间要区分: dateIssued (文件发布日) vs lastModified (GovInfo 入库/更新时间, 用于增量同步)
- DEMO_KEY 用完后返回 429 + Retry-After≈64000s (约 18 小时), 实际上是按天的额度
- 实测 (2026-10-13, DEMO_KEY 用完前): 连接 42 个 collection; 关键词 antitrust 使 FR 总数 1,027,506 → 14,650; publishdate:range(2025Q1) 14,650 → 101 且 10/10 条在区间内; /collections/FR/{lastModified} 增量; /packages/{id}/summary 提供 pdf/xml/zip/mods 下载链接
- collection 代码: FR=联邦公报, CFR, USCOURTS=法院意见, BILLS, CREC=国会记录, PLAW 等

## CourtListener  —  可用
_测试时间 2026-10-13T06:44:08+00:00_

- **文档**: https://wiki.free.law/c/courtlistener/help/api/rest/v4/rest-api-v47 (旧地址 courtlistener.com/help/api/rest/ 会跳转到这里)
- **认证**: 搜索接口 /search/ 可匿名; 其他 (dockets/opinions/clusters/people...) 需要免费 token (注册账号后获取), Header: Authorization: Token xxx
- **License**: 免费 (非营利); bulk 数据标注 Public Domain Mark; 提额、Webhooks 等高级功能需会员或商业协议 (收费)
- **限制**: 注意: 认证用户默认只有 5 次/分钟、50 次/小时、125 次/天 (会员或商业协议可提额); 匿名有限流但没公布数字; search 用游标翻页, 其他端点 page 最多 100 页; 大批量请用 bulk data (S3 上的全量 CSV 快照)
- **获取方式**: REST JSON v4: /api/rest/v4/search/?type=o|r|d|oa|p , /dockets/, /opinions/, /clusters/; 另有 Webhooks / Search Alerts 做推送
- **关键词**: 支持: q= (Solr/ES 语法, 支持 AND/OR/"短语"/字段 caseName:xxx)
- **时间**: 支持: filed_after / filed_before (YYYY-MM-DD, 实测可用但文档没列名字; 官方写法是 q=dateFiled:[2025-01-01 TO 2025-06-30]); REST 端点 date_modified__gte=ISO时间 (官方只给了 __gte 语法模式; 实测 dockets 可用, 精确到微秒, 适合增量)

### 信息来源 (调用方式从哪来)
- 官方: https://wiki.free.law/c/courtlistener/help/api/rest/v4/rest-api-v47 (Token 认证、限流 5/分钟·50/小时·125/天、Webhooks/Alerts)
- 官方: https://wiki.free.law/c/courtlistener/help/api/rest/v4/search (type 代码 o/r/rd/d/p/oa、q 语法、返回样例与时间字段)
- 官方: https://wiki.free.law/c/courtlistener/help/api/rest/v4/query-refinement (__gte 过滤语法、游标/页码翻页)
- 官方: https://wiki.free.law/c/courtlistener/help/api/bulk-data/bulk-legal-data 及 data-coverage/federal-cases-and-filings
- 实测: /search/ 匿名可用、/dockets/ 无 token 401 / 有 token 200、filed_after/filed_before 有效、dockets 的 date_modified__gte 有效

### 测试结果
- [通过] **连接 (search, 带 token)** — 判决意见总数 8332113
- [通过] **关键词 q='antitrust'** — 返回20条, 其中20条包含'antitrust'; 总数 8332113 → 44907
- [通过] **时间 filed_after/filed_before (2025H1)** — 20/20 条在 2025-01-01~2025-06-30 内; 总数 44907 → 152; 样例 ['2025-06-30', '2025-06-27', '2025-06-27']
- [通过] **RECAP (PACER) 案卷搜索** — 总数 152805
- [通过] **增量 dockets?date_modified__gte=2026-10-01** — 20/20 条在 2026-10-01~2100-01-01 内; 样例 ['2026-10-13', '2026-10-13', '2026-10-13']

### 拿到的字段 / 时间戳
- **opinion (search)** (47 个字段): `absolute_url, attorney, caseName, caseNameFull, citation, citeCount, cluster_id, court, court_citation_string, court_id, court_jurisdiction, dateArgued, dateFiled, dateReargued, dateReargumentDenied, docketNumber, docket_id, judge, lexisCite, meta.timestamp, meta.date_created, meta.score.bm25, neutralCite, non_participating_judge_ids, opinions.[0].author_id`
  - 时间戳 `dateFiled` = `2026-10-12`
  - 时间戳 `meta.timestamp` = `2026-10-13T05:06:18.978150Z`
  - 时间戳 `meta.date_created` = `2026-10-13T05:06:18.884487Z`
  - 时间戳 `opinions.[0].meta.timestamp` = `2026-10-13T05:08:52.497687Z`
  - 时间戳 `opinions.[0].meta.date_created` = `2026-10-13T05:06:18.889204Z`
- **docket (RECAP search)** (50 个字段): `assignedTo, assigned_to_id, attorney, attorney_id, caseName, case_name_full, cause, chapter, court, court_citation_string, court_id, dateArgued, dateFiled, dateTerminated, docketNumber, docket_absolute_url, docket_id, firm, firm_id, jurisdictionType, juryDemand, meta.timestamp, meta.date_created, meta.score.bm25, meta.more_docs`
  - 时间戳 `dateFiled` = `2016-06-13`
  - 时间戳 `meta.timestamp` = `2025-03-03T18:10:51.921387Z`
  - 时间戳 `meta.date_created` = `2017-04-25T03:40:02.963196Z`
  - 时间戳 `recap_documents.[0].entry_date_filed` = `2017-05-17`
  - 时间戳 `recap_documents.[0].meta.timestamp` = `2024-04-01T18:20:21.836005Z`
  - 时间戳 `recap_documents.[0].meta.date_created` = `2017-05-22T21:00:58.081781Z`
- **docket (REST)** (60 个字段): `resource_uri, id, court, court_id, original_court_info, idb_data, clusters, audio_files, assigned_to, referred_to, bankruptcy_information, absolute_url, date_created, date_modified, source, appeal_from_str, assigned_to_str, referred_to_str, panel_str, date_last_index, date_cert_granted, date_cert_denied, date_argued, date_reargued, date_reargument_denied`
  - 时间戳 `date_created` = `2026-10-12T23:43:06.632772-07:00`
  - 时间戳 `date_modified` = `2026-10-12T23:43:06.632787-07:00`
  - 时间戳 `date_filed` = `2026-10-12`
  - 时间戳 `date_last_filing` = `2026-10-12`
  - 时间戳 `ia_date_first_change` = `2026-10-12T23:43:06.622804-07:00`
  - 时间戳 `date_blocked` = `2026-10-12`

### HTTP 调用
- `GET search baseline` → **200** (0.98s)
- `GET search keyword` → **200** (0.76s)
- `GET search keyword+date` → **200** (0.66s)
- `GET search RECAP` → **200** (1.16s)
- `GET dockets endpoint` → **200** (0.5s)

### 注意事项
- type: o=判决意见, r=RECAP(PACER 案卷+文件), rd=RECAP 文件, d=只要案卷, oa=口头辩论音频, p=法官
- 时间字段: dateFiled (判决日, 只有日期), meta.timestamp / date_created / date_modified (入库时间, 精确到微秒)
- RECAP 覆盖不完整: 主要来自 RECAP 插件用户购买的文件, 外加 @recap.email、PACER RSS、爬虫等来源

## LexisNexis Data+  —  需要 key / license
_测试时间 2026-10-13T06:44:11+00:00_

- **文档**: https://dev.lexisnexis.com (公开可读的 API 规格; 凭证需要合同)
- **认证**: OAuth2 client_credentials: POST auth-api.lexisnexis.com/oauth/v2/token (Basic client_id:secret, form 表单, scope=http://oauth.lexisnexis.com/all) → Bearer, 24 小时有效; 凭证需要 Service-to-Service ID
- **License**: 商业付费 license: 调用方承担所有 LexisNexis 费用, 能看哪些内容源取决于授权; 具体计费和再分发条款看合同
- **限制**: QPS 按合同, 超出返回 429 (官方无数字); 每页默认 10 条, $top 最大 50
- **获取方式**: OData REST: GET services-api.lexisnexis.com/v1/News?$search=...&$filter=...&$top=...; 另有 bulk 交付 (S3/SFTP)
- **关键词**: 支持: $search= (必填; 有 Boolean 布尔检索模式, 如 antitrust AND merger; w/5 近邻语法在 API 文档里未确认)
- **时间**: 支持: $filter=Date ge 2025-01-01 and Date le 2025-03-31; $orderby=Date desc

### 信息来源 (调用方式从哪来)
- 官方: https://dev.lexisnexis.com — Web Services API 规格文件 (公开): Introduction&Endpoint URI.yml (服务地址、token 地址)、Authorization and Authentication.yml (client_credentials 请求示例、24 小时)
- 官方: 同门户 Filter Descriptions and Examples.yml ($filter=Date gt/le 示例、$top≤50)、News/NewsAPI.yml 与 NewsExamples.yml ($search 必填、Boolean、$orderby、$expand、value/@odata.count/ResultId、429)
- 官方: https://www.lexisnexis.com/en-us/products/nexis-data-plus/data-delivery.page (Nexis Data+ 产品与交付方式)
- 半官方: https://github.com/rwcuffney/lexisnexisapi (LexisNexis 集成顾问写的 Python 包)
- 实测: token 端点无凭证 401、数据端点 498

### 测试结果
- [跳过] **连接** — 未配置 LEXIS_CLIENT_ID / LEXIS_CLIENT_SECRET; 端点可达 (401/498)

### HTTP 调用
- `POST no-key token probe` → **401** (1.35s) · `{"timestamp": "2026-10-13T06:44:10.046872201Z", "status": 401, "error": "Unauthorized", "path": "/api/oauth/token"}`
- `GET no-key data probe` → **498** (1.37s) · `{"error": {"code": "", "message": "Access Denied. The token provided is either invalid or has expired. Please re-authenticate to continue."}}`

### 注意事项
- 端点/实体集名称 (News, LegalNews, Cases, CompanyAndFinancial ...) 取决于开通的数据集, 用 LEXIS_ENTITY 变量调整
- 本机无凭证探测: token 端点返回 401, 数据端点返回 498 'token invalid or expired' (498 是实测, 官方文档只列了 429)
- 返回带 Date (出版日期) 和 ResultId; 加 $expand=Document 可在同一次请求里拿到全文 (计费方式看合同)

## OSHA  —  可用
_测试时间 2026-10-13T12:24:20+00:00_

- **文档**: https://dataportal.dol.gov/api-guide  ·  用户指南 PDF: https://dataportal.dol.gov/pdf/dol-api-user-guide.pdf
- **认证**: 免费 DOL API key (在 dataportal.dol.gov/registration 注册并填问卷后生成, 最多 5 个); 参数 X-API-KEY; 数据集目录 /v4/datasets 无需 key
- **License**: 免费公开 (美国政府数据)
- **限制**: 单次最多 10,000 条或 5 MB (先到为准), limit 默认 10, 用 offset 翻页; 官方未写频率限制, 但实测约 10 分钟内 20 多个请求后开始返回 429 (无限流响应头、无 Retry-After), 过一阵自动恢复 → 请求间隔 ≥ 3 秒; 禁止把 key 公开到代码仓库或论坛
- **获取方式**: REST GET https://apiprod.dol.gov/v4/get/OSHA/{表名}/json?X-API-KEY=...; 元数据 /json/metadata; 另支持 csv / xml 格式
- **关键词**: 支持: filter_object 用 like 运算符做模糊匹配, 如 {"field":"estab_name","operator":"like","value":"%WALMART%"}
- **时间**: 支持: filter_object 用 gt / lt 比较日期字段 (如 open_date), 可用 and/or 组合; sort + sort_by 排序

### 信息来源 (调用方式从哪来)
- 官方: https://dataportal.dol.gov/pdf/dol-api-user-guide.pdf (2024-08-05 版): 注册拿 key、请求模板、limit/offset/fields/sort/sort_by/filter_object、运算符 eq/neq/gt/lt/in/not_in/like、10,000 条或 5MB 上限、禁止公开 key
- 官方: https://apiprod.dol.gov/v4/datasets (无需 key, 实测可访问): OSHA 有 11 张表
- 实测: 无 key 请求数据返回 401 'The API key is either incorrect or missing'
- 实测 (有 key): 公司名 like 过滤、open_date 区间、load_dt 增量、违规表 → 检查表关联都有效; 连续请求会触发 429
- 官方: /json/metadata 字段说明 (实测可读): 每个字段的名称、描述、类型、关联表

### 测试结果
- [通过] **数据集目录 (无需 key)** — OSHA 表 11 张: ['OSHA_accident_lookup2', 'OSHA_accident', 'OSHA_accident_abstract', 'OSHA_accident_injury', 'OSHA_inspection', 'OSHA_related_activity', 'OSHA_emphasis_codes', 'OSHA_violation', 'OSHA_violation_gen_duty_std', 'OSHA_optional_code_info', 'OSHA_violation_event']
- [通过] **元数据 (字段说明)** — inspection 表 36 个字段; 每个字段有名称、描述、类型、关联表
- [通过] **连接 / 最新检查记录** — 返回 10 条, 最新 open_date 2026-09-23T00:00:00
- [通过] **公司名模糊匹配 'WALMART'** — 返回20条, 其中20条包含'WALMART'
- [通过] **open_date 2025-01** — 20/20 条在 2025-01-01~2025-01-31 内; 样例 ['2025-01-30', '2025-01-30', '2025-01-30']
- [通过] **增量 load_dt > 2026-10-01 (入库时间)** — 20/20 条在 2026-10-01~2100-01-01 内; 样例 ['2026-10-12', '2026-10-12', '2026-10-12']
- [通过] **违规表 (violation)** — 返回 10 条
- [通过] **按 activity_nr 关联 违规 → 检查** — activity_nr=349149898 → JOHNSON COUNTY BOARD OF EDUCATION - MIDDLE SCHOOL
- [通过] **事故表 (accident)** — 返回 5 条

### 拿到的字段 / 时间戳
- **inspection** (36 个字段): `activity_nr, reporting_id, state_flag, estab_name, site_address, site_city, site_state, site_zip, owner_type, owner_code, adv_notice, safety_hlth, sic_code, naics_code, insp_type, insp_scope, why_no_insp, union_status, safety_manuf, safety_const, safety_marit, health_manuf, health_const, health_marit, migrant`
  - 时间戳 `open_date` = `2026-09-23T00:00:00`
  - 时间戳 `case_mod_date` = `2026-10-11T00:00:00`
  - 时间戳 `load_dt` = `2026-10-12T00:20:22`
- **violation** (29 个字段): `activity_nr, citation_id, delete_flag, standard, viol_type, issuance_date, abate_date, abate_complete, current_penalty, initial_penalty, contest_date, final_order_date, nr_instances, nr_exposed, rec, gravity, emphasis, hazcat, fta_insp_nr, fta_issuance_date, fta_penalty, fta_contest_date, fta_final_order_date, hazsub1, hazsub2`
  - 时间戳 `issuance_date` = `2026-09-10T00:00:00`
  - 时间戳 `final_order_date` = `2026-09-10T00:00:00`
  - 时间戳 `load_dt` = `2026-10-12T00:24:18`
- **accident** (16 个字段): `summary_nr, report_id, event_date, event_time, event_desc, event_keyword, const_end_use, build_stories, nonbuild_ht, project_cost, project_type, sic_list, fatality, state_flag, abstract_text, load_dt`
  - 时间戳 `event_date` = `2025-03-28T00:00:00`
  - 时间戳 `load_dt` = `2026-10-12T00:17:52`

### HTTP 调用
- `GET dataset catalog (no key)` → **200** (2.6s)
- `GET inspection metadata` → **200** (2.92s)
- `GET inspection latest` → **200** (3.72s)
- `GET keyword (estab_name like)` → **200** (4.48s)
- `GET date range (open_date)` → **200** (3.38s)
- `GET incremental (load_dt)` → **200** (2.79s)
- `GET violation latest` → **200** (2.8s)
- `GET inspection of a violation` → **200** (3.46s)
- `GET accident latest` → **200** (3.27s)

### 注意事项
- OSHA 的 11 张表: inspection (检查)、violation (违规)、violation_event、violation_gen_duty_std、accident (事故)、accident_abstract、accident_injury、accident_lookup2、related_activity、emphasis_codes、optional_code_info
- 表之间用 activity_nr (检查编号) 关联: 先按公司名查 inspection, 再用 activity_nr 查 violation 拿罚款
- OSHA 原来的 enforcedata.dol.gov 已跳转到 data.dol.gov

## UCC Filings  —  可用
_测试时间 2026-10-13T09:58:36+00:00_

- **文档**: https://data.colorado.gov/d/wffy-3uut  ·  https://data.ct.gov/d/xfev-8smz  ·  SODA API: https://dev.socrata.com/docs/queries/
- **认证**: 不需要 key; 可选 Socrata app token (请求头 X-App-Token, 免费注册) 以获得独立额度
- **License**: 免费公开 (州政府开放数据)
- **限制**: 无 app token: 按 IP 共享额度, 请求过多会被限流 (返回 429, 无公布数字); 有 app token: 目前不限流 (除非被判滥用); 单次 $limit 可自定, 用 $offset 翻页
- **获取方式**: REST GET https://data.colorado.gov/resource/{数据集ID}.json 或 data.ct.gov/resource/xfev-8smz.json, 用 SoQL 参数 $where / $q / $order / $select / $limit
- **关键词**: 支持: $q= 全文搜索, 或 $where=upper(organizationname) like '%XXX%' (按债务人/担保权人名称)
- **时间**: 支持: $where=filingdate between '2026-09-01' and '2026-09-30' (CO) / dt_accept (CT); 也能按失效日 lapsedate / dt_lapse 查

### 信息来源 (调用方式从哪来)
- 官方 (州政府): 科罗拉多数据集元数据 https://data.colorado.gov/api/views/wffy-3uut.json — 每天午夜后自动更新, 最早记录 1966-04-01, 来源 Colorado Department of State
- 官方 (州政府): 康涅狄格 https://catalog.data.gov/dataset/uniform-commercial-code-ucc-lien-filings 与 data.ct.gov/d/xfev-8smz
- 官方: https://dev.socrata.com/docs/app-tokens.html — 无 token 按 IP 限流、有 token 目前不限流、超限 429
- 实测: 字段名 (响应头 X-SODA2-Fields)、CO 4 张表用 fileid 关联、CO 最新申报 2026-10-11 / CT 最新 2026-10-12、关键词和日期过滤结果
- 调研 (见汇总): 其他州多为付费批量文件 (TX $65/天, KY $1,500/月 等) 或只有网页; 商业 API 有 Middesk、D&B UCC Filings

### 测试结果
- [通过] **CO 连接 / 最新申报** — 总数 2602391, 最新 filingdate 2026-10-11
- [通过] **CO 按申报日 2026-09-01~2026-09-30** — 20/20 条在 2026-09-01~2026-09-30 内; 总数 2602391 → 10609; 样例 ['2026-09-30', '2026-09-30', '2026-09-30']
- [通过] **CO 担保权人名称含 'BANK'** — 返回10条, 其中10条包含'BANK'; 总数 2092969 → 608235
- [通过] **CO 按 fileid 关联 4 张表** — fileid=422053: 申报 1 条 (UCC financing statement), 债务人 1 个, 担保物 1 条
- [通过] **CT 连接 / 最新申报** — 总数 848486, 最新 dt_accept 2026-10-12
- [通过] **CT 担保权人含 'BANK' + 2026-09** — 返回20条, 其中20条包含'BANK'; 总数 848486 → 2023
- [通过] **CT dt_accept 2026-09** — 20/20 条在 2026-09-01~2026-09-30 内; 样例 ['2026-09-01', '2026-09-01', '2026-09-01']

### 拿到的字段 / 时间戳
- **CO filing** (10 个字段): `transactionid, masterdocumentid, transactiontype, filingdate, filingtype, documenttype, continuation, terminationflag, manufacturedhometransactions, fileid`
  - 时间戳 `filingdate` = `2026-10-11T00:00:00.000`
- **CO secured party** (13 个字段): `spid, fileid, actiontypecode, actiontype, recordstatuscd, recordstatus, organizationname, address1, city, state, country, zipcode, assignor`
- **CO debtor** (16 个字段): `debtorid, fileid, actiontypecode, actiontype, recordstatuscode, recordstatus, organizationname, organizationjurisdiction, organizationtype, organizationid, address1, city, state, country, zipcode, efsuniqueid`
- **CO collateral** (9 个字段): `collateralid, fileid, actiontypecode, actiontype, recordstatuscode, recordstatus, farmproductflag, collateraldescription, additionalcollateraldescription`
- **CT filing** (20 个字段): `id_lien_flng_nbr, id_ucc_flng_nbr, lien_status, cd_flng_type, tx_lien_descript, debtor_nm_last, debtor_nm_first, debtor_nm_mid, debtor_ad_str1, debtor_ad_city, debtor_ad_state, debtor_ad_zip, sec_party_nm_bus, sec_party_ad_str1, sec_party_ad_city, sec_party_ad_state, sec_party_ad_zip, dt_lapse, dt_accept, qt_pages`
  - 时间戳 `dt_lapse` = `2031-11-10T00:00:00.000`
  - 时间戳 `dt_accept` = `2026-10-12T00:00:00.000`

### HTTP 调用
- `GET CO filings latest` → **200** (1.38s)
- `GET CO filings count` → **200** (0.45s)
- `GET CO filings date range` → **200** (0.35s)
- `GET CO date count` → **200** (0.37s)
- `GET CO secured party keyword` → **200** (0.35s)
- `GET CO sp total` → **200** (0.63s)
- `GET CO sp kw count` → **200** (2.14s)
- `GET CO filing by fileid` → **200** (0.35s)
- `GET CO debtor by fileid` → **200** (0.36s)
- `GET CO collateral by fileid` → **200** (0.37s)
- `GET CT latest` → **200** (1.37s)
- `GET CT count` → **200** (0.4s)
- `GET CT keyword+date` → **200** (0.36s)
- `GET CT keyword+date count` → **200** (0.4s)

### 注意事项
- 只覆盖 CO 和 CT 两个州 (加上 OR 每月一份上月新增); 要全国数据只能买各州批量文件或用商业 API
- CO 分 4 张表, 用 fileid 关联: 申报 wffy-3uut (类型、申报日、失效日)、债务人 8upq-58vz、担保权人 ap62-sav4、担保物 4am6-w6u4
- CT 是一张平表 (债务人 + 担保权人 + 日期), 没有担保物字段
- 日期是 floating_timestamp (无时区), 实际只有日期精度
