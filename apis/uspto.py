"""USPTO — 专利申请/授权 (Open Data Portal) + 商标 (TSDR) + PatentsView。"""
from datetime import datetime
from common import Probe, env

NAME = "USPTO"
META = {
    "auth": "Open Data Portal: Header X-API-KEY (免费, 需 USPTO.gov 账号 + MFA + 已关联的 ID.me 实名验证, 在 https://data.uspto.gov/apikey 生成); TSDR 商标: 另一个 key (account.uspto.gov/api-manager), Header USPTO-API-KEY",
    "license": "免费 (官方: at no cost; 未见数据 license 声明)",
    "docs": "https://data.uspto.gov/apis/getting-started  ·  https://data.uspto.gov/apis/api-rate-limits  ·  https://data.uspto.gov/swagger/swagger.yaml",
    "limits": "ODP 按 key: 元数据 500 万次/周、文档 120 万次/周、4~15 次/秒; 同一 key 不能并发 (burst=1); bulk 同一文件每年 20 次; TSDR 60 次/分钟 (PDF/ZIP 4 次/分钟); 查询 limit 默认 25",
    "how": "ODP REST JSON: GET/POST /api/v1/patent/applications/search (q 走 OpenSearch 语法), /{appNumber}/documents 等; 批量用 bulk datasets",
    "keyword": "支持: q=applicationMetaData.inventionTitle:battery 或全文 q=battery; 支持 AND/OR/字段过滤",
    "date": "支持: rangeFilters (POST) 或 GET 的 rangeFilters=applicationMetaData.filingDate 2024-01-01:2024-12-31; 可按 filingDate/grantDate 等",
    "sources": [
        "✅ 官方: https://data.uspto.gov/apis/getting-started (X-API-KEY、免费、USPTO.gov 账号 + ID.me、key 在 /apikey 页)",
        "✅ 官方: https://data.uspto.gov/apis/api-rate-limits (每周额度、每秒限速、禁止并发、bulk 限制)",
        "✅ 官方: https://data.uspto.gov/apis/api-syntax-examples 与 /apis/patent-file-wrapper/search (q 语法、POST 体 pagination/sort/rangeFilters、字段名、patentFileWrapperDataBag、lastIngestionDateTime)",
        "✅ 官方: https://data.uspto.gov/swagger/swagger.yaml、odp-common-base.yaml、tsdr-swagger.yaml (limit 默认 25; TSDR 只能按案号查)",
        "✅ 官方: https://tsdr.uspto.gov/faqview (TSDR 单独 key、60 次/分钟)",
        "✅ 官方: https://data.uspto.gov/support/transition-guide/patentsview (PatentsView 迁移状态)",
        "✅ 官方 (ODP 网站横幅): 2026-06-18 起登录需 MFA; 2026-08-18 起需补填 4 项资料, 未补的 key 已于 2026-10-08 停用; 90 天未用的 key 会被删除",
        "🧪 实测: 无 key 返回 401; TSDR 请求头名 USPTO-API-KEY (官方用户指南已失效, 由网关响应推断); 路径带 .json 也能被接受",
    ],
    "notes": [
        "⛔ 2026-10-13: 用户无美国证件, 通不过 ID.me, 拿不到 ODP key; 实测 ODP 的 bulk 数据接口 (/api/v1/datasets/...) 也要 key, TSDR 也要 key",
        "时间字段: filingDate, grantDate, effectiveFilingDate, earliestPublicationDate, lastIngestionDateTime (入库时间, 适合增量)",
        "商标没有公开的关键词搜索 API (TSDR 只能按序列号/注册号查); 商标全文搜索只能用网页或 bulk 数据",
        "PatentsView: 2026-03-20 起迁移, bulk 数据表已在 ODP, 但 API 尚未上线 (官方无时间表); 旧 api.patentsview.org 已 301 跳转到迁移说明, 旧 key 不能用于 ODP",
    ],
}
ODP = "https://api.uspto.gov/api/v1/patent/applications/search"


def run(p: Probe):
    key = env("USPTO_API_KEY")
    if not key:
        p.get("no-key probe", ODP, params={"q": "battery"})
        p.check("连接", None, "未配置 USPTO_API_KEY; 返回 401 Unauthorized")
        tkey = env("USPTO_TSDR_API_KEY")
        if not tkey:
            p.get("TSDR no-key probe", "https://tsdrapi.uspto.gov/ts/cd/casestatus/sn97000000/info.json")
        return "needs_key"
    p.session.headers["X-API-KEY"] = key

    r, j = p.post("baseline", ODP, json={"q": "*", "pagination": {"offset": 0, "limit": 1}})
    total0 = (j or {}).get("count")
    p.check("连接", bool(r is not None and r.ok), f"专利申请总数 {total0}")

    kw = "battery"
    body = {"q": f"applicationMetaData.inventionTitle:{kw}", "pagination": {"offset": 0, "limit": 10},
            "sort": [{"field": "applicationMetaData.filingDate", "order": "desc"}]}
    r, j = p.post("keyword", ODP, json=body)
    recs = (j or {}).get("patentFileWrapperDataBag", [])
    p.record_fields("patent application", recs[0] if recs else None)
    p.verify_keyword(f"标题关键词 '{kw}'", [x.get("applicationMetaData", {}) for x in recs], kw, total0, (j or {}).get("count"))
    total_kw = (j or {}).get("count")

    body["rangeFilters"] = [{"field": "applicationMetaData.filingDate", "valueFrom": "2024-01-01", "valueTo": "2024-03-31"}]
    r, j = p.post("keyword+date", ODP, json=body)
    recs = (j or {}).get("patentFileWrapperDataBag", [])
    p.verify_dates("rangeFilters filingDate 2024Q1", [x.get("applicationMetaData", {}).get("filingDate") for x in recs],
                   datetime(2024, 1, 1), datetime(2024, 3, 31, 23, 59), total_kw, (j or {}).get("count"))

    tkey = env("USPTO_TSDR_API_KEY")
    if tkey:
        r, j = p.get("TSDR trademark status", "https://tsdrapi.uspto.gov/ts/cd/casestatus/sn97000000/info.json",
                     headers={"USPTO-API-KEY": tkey})
        p.record_fields("trademark", (j or {}).get("trademarks", [{}])[0] if j else None)
        p.check("TSDR 商标 (按序列号)", bool(r is not None and r.ok), "无关键词搜索")
