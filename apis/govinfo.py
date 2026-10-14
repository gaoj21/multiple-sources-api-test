"""GovInfo (GPO) — 联邦公报、法规、国会文件、法院意见等。文档: https://api.govinfo.gov/docs"""
from datetime import datetime
from common import Probe, env

NAME = "GovInfo"
META = {
    "auth": "需要 api.data.gov key (免费, 邮箱注册: https://api.data.gov/signup); DEMO_KEY 可试用",
    "license": "免费公开",
    "docs": "https://api.govinfo.gov/docs  /  https://github.com/usgpo/api",
    "limits": "个人 key: 36,000 次/小时、1,200 次/分钟、40 次/秒 (官方 README; 实测响应头 X-RateLimit-Limit=36000 一致); DEMO_KEY 官方写 30 次/小时+50 次/天, 实测只给 10; pageSize 最大 1000",
    "how": "REST JSON: /collections/{code}/{lastModifiedStart} 增量; /published/{date} 按发布日期; POST /search 全文; /packages/{id}/summary 详情",
    "keyword": "支持: POST /search {query:'antitrust collection:(FR)'} (字段操作符语法, 可加 publishdate:range(...))",
    "date": "支持: 路径里的 lastModified 时间 (ISO8601, 精确到秒) / published 日期区间 / search 的 publishdate:range()",
    "sources": [
        "官方: https://github.com/usgpo/api (README: 认证、限流 36,000/小时、/collections、/published、/search、offsetMark、sorts、/packages/{id}/summary 下载链接)",
        "官方: https://api.govinfo.gov/api-docs (OpenAPI 3.0.1 规格; /docs 页面是 JS 渲染, 实际从这里读) — lastModified 格式 yyyy-MM-dd'T'HH:mm:ss'Z'、pageSize≤1000",
        "官方: https://www.govinfo.gov/help/finding-info (publishdate:range(...) 语法)",
        "官方: https://api.data.gov/docs/developer-manual/ (DEMO_KEY 默认 30/小时、50/天; X-RateLimit 头)",
        "实测: DEMO_KEY 实际 Limit=10、用完后 Retry-After≈64000s; 个人 key Limit=36000; 各项过滤的总数变化",
    ],
    "notes": [
        "翻页使用 offsetMark=* 游标 (旧的 offset 参数已废弃)",
        "两种时间要区分: dateIssued (文件发布日) vs lastModified (GovInfo 入库/更新时间, 用于增量同步)",
        "DEMO_KEY 用完后返回 429 + Retry-After≈64000s (约 18 小时), 实际上是按天的额度",
        "实测 (2026-10-13, DEMO_KEY 用完前): 连接  42 个 collection; 关键词 antitrust 使 FR 总数 1,027,506 → 14,650 ; "
        "publishdate:range(2025Q1) 14,650 → 101 且 10/10 条在区间内 ; /collections/FR/{lastModified} 增量 ; /packages/{id}/summary 提供 pdf/xml/zip/mods 下载链接 ",
        "collection 代码: FR=联邦公报, CFR, USCOURTS=法院意见, BILLS, CREC=国会记录, PLAW 等",
    ],
}
BASE = "https://api.govinfo.gov"


def run(p: Probe):
    key = env("GOVINFO_API_KEY") or env("DATA_GOV_API_KEY") or "DEMO_KEY"
    if key == "DEMO_KEY":
        p.note("未配置 GOVINFO_API_KEY, 使用 DEMO_KEY (限流非常严格)")
    P = {"api_key": key}

    r, j = p.get("collections", f"{BASE}/collections", params=P)
    cols = (j or {}).get("collections", [])
    p.check("连接", bool(cols), f"{len(cols)} 个 collection, 如 {[c['collectionCode'] for c in cols[:8]]}")

    # 关键词 + 时间 一起用 search
    kw = "antitrust"
    r, s0 = p.post("search baseline FR", f"{BASE}/search", params=P,
                   json={"query": "collection:(FR)", "pageSize": 1, "offsetMark": "*"}, save=False)
    body = {"query": f"{kw} collection:(FR)", "pageSize": 10, "offsetMark": "*",
            "sorts": [{"field": "publishdate", "sortOrder": "DESC"}]}
    r, s = p.post("search keyword", f"{BASE}/search", params=P, json=body)
    res = (s or {}).get("results", [])
    p.record_fields("search result", res[0] if res else None)
    total_kw, total_fr = (s or {}).get("count"), (s0 or {}).get("count")
    # search 结果不带正文, 只能靠总数变化判断关键词是否生效
    p.check(f"全文搜索 '{kw}' (FR)", bool(res) and total_kw < total_fr,
            f"FR 总数 {total_fr} → {total_kw}; 首条标题: {res[0].get('title', '')[:80] if res else None}")

    body["query"] = f"{kw} collection:(FR) publishdate:range(2025-01-01,2025-03-31)"
    r, s2 = p.post("search keyword+date", f"{BASE}/search", params=P, json=body)
    res2 = (s2 or {}).get("results", [])
    p.verify_dates("search + publishdate:range(2025Q1)", [x.get("dateIssued") for x in res2],
                   datetime(2025, 1, 1), datetime(2025, 3, 31, 23, 59), total_kw, (s2 or {}).get("count"))

    # 增量接口: 按 lastModified
    since = "2026-10-01T00:00:00Z"
    r, c = p.get("collection since lastModified", f"{BASE}/collections/FR/{since}", params={**P, "pageSize": 10, "offsetMark": "*"})
    pk = (c or {}).get("packages", [])
    p.record_fields("package (collections)", pk[0] if pk else None)
    p.verify_dates(f"增量: FR lastModified >= {since}", [x.get("lastModified") for x in pk], datetime(2026, 10, 1), datetime(2100, 1, 1))

    if pk:
        r, d = p.get("package summary", f"{BASE}/packages/{pk[0]['packageId']}/summary", params=P)
        p.record_fields("package summary", d)
        p.check("详情 /packages/{id}/summary", bool(d), f"download 链接: {list((d or {}).get('download', {}).keys())}")
