# 15 个数据源 API 能力测试

## 运行

```bash
pip install -r requirements.txt
cp .env.example .env      # 填入你有的 key, 没填的 API 只做无 key 探测
python run_all.py                     # 全部
python run_all.py doj courtlistener   # 只跑某几个 (结果会合并进已有报告)
python run_all.py --render-only       # 不发请求, 只重新生成报告
```

输出：
- `output/report.md` — 完整报告：每个 API 的结论、字段、时间戳样例、HTTP 调用和限流头、注意事项
- `output/results.json` — 原始结果
- `output/samples/` — 每次调用的真实返回样例
- `apis/<name>.py` — 每个 API 一个模块，也可以当成调用示例直接参考

每个模块测四件事：① 能否连接，以及认证、限流响应头 ② 自动识别返回记录里的时间戳字段 ③ 用"过滤前后总数是否变化 + 抽查记录内容"来验证关键词和时间过滤是否真的生效 ④ 注意事项。

**调用限制与建议运行频率见 [LIMITS.md](LIMITS.md)。**

## 实测结论 (2026-10-13, 出口 IP 在新加坡)

| API | 无 key 能连? | 认证 / 费用 | 关键词 | 时间过滤 | 时间戳 |
|---|---|---|---|---|---|
| USAspending.gov | ✅ 完全可用 | 无需 key, 免费 | ✅ `keywords` | ✅ `time_period` (可选 action/signed/last_modified) | `Last Modified Date` 到秒 |
| Grants.gov | ✅ 完全可用 | 无需 key, 免费 | ✅ `keyword` | ❌ 无区间参数, 只能按 openDate 排序后客户端过滤 | 列表只有日期; 详情有 `lastUpdatedDate` 到秒 |
| CourtListener | ✅ search 匿名可用 | 其他端点需免费 token；默认只有 5 次/分钟、50 次/小时、125 次/天 | ✅ `q` (布尔语法) | ✅ `filed_after/before`, `date_modified__gte` | `dateFiled` + `meta.timestamp` 到微秒 |
| DOJ News | ✅ | 无需 key, 免费 | ⚠️ **只能匹配标题**, `parameters[keyword]` 被静默忽略 | ⚠️ 只能查**单日** `parameters[date]` | `date` (Unix 秒, 日期精度), `created`/`changed` 到秒 |
| GovInfo | ✅ 个人 key 全部通过 | 免费 api.data.gov key，36,000 次/小时 | ✅ 字段操作符语法 | ✅ `publishdate:range()` / lastModified 增量 | `dateIssued`, `lastModified` 到秒 |
| FTC 新闻稿 | ⛔ **www.ftc.gov 被 WAF 拦截** | 新闻稿无 API, 只有 RSS/网页 | 网页可以 | RSS 只有最近的条目 | `pubDate`; api.ftc.gov 有 `created/updated` |
| SAM.gov | ✅ 有效 key 全部通过 | 免费 key, 但**无角色每天只有 10 次** | `title` | ✅ `postedFrom/To` 必填, 跨度 ≤1 年 | `postedDate`, `responseDeadLine` |
| USPTO | ⛔ 拿不到 key（ID.me 需要美国证件） | 免费 key, 需 MFA + ID.me 实名; 商标用另一个 key | ✅ `q` | ✅ `rangeFilters` | `filingDate`, `lastIngestionDateTime` |
| D&B Direct+ | 🔑 401 | 💰 付费, 按调用计费 | ✅ `searchTerm` | ❌ 只能用 Monitoring 推送 | `transactionTimestamp` |
| Moody's Orbis | 🔑 401 | 💰 付费 | 名称匹配 / 条件筛选 | ❓ 需和 Moody's 确认 | 需在 SELECT 里请求 |
| Quartr | 🔑 401 | 💰 付费 (v3, v1/v2 已 410) | ❌ 只能按 ticker/ISIN/CIK | ✅ `startDate/endDate`, `updatedAfter` | 事件 `date` (未用 key 验证) |
| LexisNexis Data+ | 🔑 401/498 | 💰 付费 | ✅ `$search` 布尔 | ✅ `$filter=Date ge ...` | `Date` |
| OSHA | ✅ 用 DOL key 全部通过 | 免费 DOL key；连续请求会 429 | ✅ `like` | ✅ `gt`/`lt` | 入库时间 `load_dt` 到秒 |
| UCC Filings（CO / CT） | ✅ 完全可用 | 不需要 key，免费 | ✅ `$where like` / `$q` | ✅ `$where between` | 申报日、失效日（只有日期） |
| Earnings Calls | ✅ Alpha Vantage demo 可用 | 免费 key（25 次/天） | ❌ 按代码 + 季度 | 🟡 按季度 / 日历范围 | 发布日只有日期；文字稿无时间 |

## 重点注意

1. **FTC**：本机 IP 访问 www.ftc.gov 的所有路径都返回 *"request resembles an abusive automated request"* 拦截页（假 404），不过从另一台主机访问时，官方 RSS 地址（`feeds/press-release.xml` 等）是在线的，所以问题出在这台机器的 IP，脚本里的地址没写错。需要换美国 IP 或服务器，或者按拦截页的提示发邮件给 PWH-Alert@ftc.gov。api.ftc.gov 可以正常用，但它提供的是 HSR 提前终止公告，不是新闻稿。
2. **SAM.gov**：key 无效时所有路径都返回空 body 的 404（不是 401），很容易误以为地址写错了。用 SAM 账号生成的 key 从新加坡访问完全正常，不限制非美国 IP。测试脚本跑一次用 4 次调用，而无角色 key 每天只有 10 次，别反复跑。
3. **DOJ**：传入未知参数不会报错，而是直接返回全量数据，所以一定要校验 `resultset.count`。
4. **api.data.gov key**：GovInfo 和 api.ftc.gov 共用同一个 key（已填在 `.env`）。实测个人 key 的额度是 GovInfo 36,000 次/小时、api.ftc.gov 20,000 次/小时。DEMO_KEY 实测只有 10 次，用完后要等约 18 小时。
5. **两种时间要分清**："业务时间"是发布/签约/判决日期，通常只精确到日；"入库/更新时间"（`lastModified`、`date_modified`、`updatedAfter`）通常精确到秒，适合做增量同步。
6. 付费的 4 家（D&B、Orbis、Quartr、Lexis）脚本已经按官方接口写好。其中 **Orbis 和 Lexis 的请求体或端点不能公开验证**，拿到凭证后需要对照合同附带的文档调整 `.env` 里的 `ORBIS_*` / `LEXIS_*`。

## 调用方式的信息来源

每个 `apis/*.py` 的 `META["sources"]` 里都逐条列了来源，`output/report.md` 每个 API 下面也有"信息来源"一节。标记含义：

- ✅ **官方**：在官方文档里亲眼看到（附网址）
- 🔶 **半官方**：厂商合作方的开源代码或文档、采购目录等（只用于 Orbis 和 Lexis）
- 🧪 **实测**：文档里没写，是实际调用观察到的
- ❓ **未确认**：官方没找到，也没实测

做法：最初的代码基于对这些 API 的已有知识写成，再逐一实际调用验证；之后分 4 组对照官方文档逐条核对，把和官方不一致的地方都改掉了。

| API | 主要官方文档 | 官方确认程度 | 核对时改正的内容 |
|---|---|---|---|
| USAspending | api.usaspending.gov/docs + GitHub `api_contracts` | 高 | 补充：最多翻到 5 万条、默认每页 10 条 |
| Grants.gov | grants.gov/api/common/search2、fetchopportunity | 高 | 参数名是 `aln`（不是 `cfda`）；官方没有单页上限 |
| DOJ | justice.gov/developer/api-documentation/api_v1 | 高 | **官方限流每秒 4 次**；没有 speeches/videos 接口；按部门过滤官方说支持但实测无效 |
| SAM.gov | open.gsa.gov（Opportunities / Entity / Exclusions） | 高 | 数据分级：税号、银行信息属于 Sensitive，不是 FOUO |
| GovInfo | github.com/usgpo/api + api.govinfo.gov/api-docs | 高 | 个人 key **每小时 36,000 次**（不是 1,000） |
| FTC | ftc.gov/developer + RSS 列表页 | 高（从另一台主机核实） | RSS 地址正确；排序参数换成文档写法 |
| CourtListener | wiki.free.law/c/courtlistener/help/api/rest/v4 | 高 | **默认每分钟 5 次、每小时 50 次、每天 125 次**（不是每小时 5,000 次），实测也撞到了 |
| USPTO | data.uspto.gov/apis/* + swagger | 高 | 申请 key 的页面是 `/apikey`；需要 MFA；PatentsView 的 API 还没迁到新平台 |
| Quartr | quartr.com/docs + openapi.json | 高 | 默认每秒 50 次；每页最多 500 条 |
| D&B Direct+ | directplus 文档（现在需要登录，用的是 Wayback 存档，最新到 2024-11） | 中 | token 接口换成 **v3 + 表单格式** |
| LexisNexis | dev.lexisnexis.com 公开的规格文件 | 中高 | 官方名称是 Web Services API；公司数据集叫 `CompanyAndFinancial`；加 `$expand=Document` 可以直接拿全文 |
| OSHA | dataportal.dol.gov/api-guide + 用户指南 PDF + `/json/metadata` | 高 | 新增；官方没写限流，实测会 429 |
| UCC Filings | data.colorado.gov、data.ct.gov 元数据 + dev.socrata.com | 高 | 新增；其他州多为付费批量文件 |
| Earnings Calls | alphavantage.co/documentation | 高 | 新增（Alpha Vantage） |
| Moody's Orbis | **没有公开官方文档** | 低（全部是半官方或实测） | 匹配接口返回数组（修了一个会报错的 bug）；查询字段要加 `Match.` 前缀 |
