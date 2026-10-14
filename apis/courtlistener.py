"""CourtListener (Free Law Project) — 判决意见、PACER/RECAP 案卷、口头辩论、法官。文档: https://wiki.free.law/c/courtlistener/help/api/rest/v4/rest-api-v47"""
from datetime import datetime
from common import Probe, env

NAME = "CourtListener"
META = {
    "auth": "搜索接口 /search/ 可匿名; 其他 (dockets/opinions/clusters/people...) 需要免费 token (注册账号后获取), Header: Authorization: Token xxx",
    "license": "免费 (非营利); bulk 数据标注 Public Domain Mark; 提额、Webhooks 等高级功能需会员或商业协议 (收费)",
    "docs": "https://wiki.free.law/c/courtlistener/help/api/rest/v4/rest-api-v47 (旧地址 courtlistener.com/help/api/rest/ 会跳转到这里)",
    "limits": "注意: 认证用户默认只有 5 次/分钟、50 次/小时、125 次/天 (会员或商业协议可提额); 匿名有限流但没公布数字; search 用游标翻页, 其他端点 page 最多 100 页; 大批量请用 bulk data (S3 上的全量 CSV 快照)",
    "how": "REST JSON v4: /api/rest/v4/search/?type=o|r|d|oa|p , /dockets/, /opinions/, /clusters/; 另有 Webhooks / Search Alerts 做推送",
    "keyword": "支持: q= (Solr/ES 语法, 支持 AND/OR/\"短语\"/字段 caseName:xxx)",
    "date": "支持: filed_after / filed_before (YYYY-MM-DD, 实测可用但文档没列名字; 官方写法是 q=dateFiled:[2025-01-01 TO 2025-06-30]); REST 端点 date_modified__gte=ISO时间 (官方只给了 __gte 语法模式; 实测 dockets 可用, 精确到微秒, 适合增量)",
    "sources": [
        "官方: https://wiki.free.law/c/courtlistener/help/api/rest/v4/rest-api-v47 (Token 认证、限流 5/分钟·50/小时·125/天、Webhooks/Alerts)",
        "官方: https://wiki.free.law/c/courtlistener/help/api/rest/v4/search (type 代码 o/r/rd/d/p/oa、q 语法、返回样例与时间字段)",
        "官方: https://wiki.free.law/c/courtlistener/help/api/rest/v4/query-refinement (__gte 过滤语法、游标/页码翻页)",
        "官方: https://wiki.free.law/c/courtlistener/help/api/bulk-data/bulk-legal-data 及 data-coverage/federal-cases-and-filings",
        "实测: /search/ 匿名可用、/dockets/ 无 token 401 / 有 token 200、filed_after/filed_before 有效、dockets 的 date_modified__gte 有效",
    ],
    "notes": [
        "type: o=判决意见, r=RECAP(PACER 案卷+文件), rd=RECAP 文件, d=只要案卷, oa=口头辩论音频, p=法官",
        "时间字段: dateFiled (判决日, 只有日期), meta.timestamp / date_created / date_modified (入库时间, 精确到微秒)",
        "RECAP 覆盖不完整: 主要来自 RECAP 插件用户购买的文件, 外加 @recap.email、PACER RSS、爬虫等来源",
    ],
}
BASE = "https://www.courtlistener.com/api/rest/v4"


def run(p: Probe):
    tok = env("COURTLISTENER_TOKEN")
    if tok:
        p.session.headers["Authorization"] = f"Token {tok}"
        p.min_interval = 12  # 默认额度 5 次/分钟
    else:
        p.note("未配置 COURTLISTENER_TOKEN: 只测试匿名可用的 /search/")

    r, j = p.get("search baseline", f"{BASE}/search/", params={"type": "o", "order_by": "dateFiled desc"})
    total0 = (j or {}).get("count")
    res = (j or {}).get("results", [])
    p.check("连接 (search, " + ("带 token)" if tok else "匿名)"), bool(res), f"判决意见总数 {total0}")
    p.record_fields("opinion (search)", res[0] if res else None)

    kw = "antitrust"
    r, j = p.get("search keyword", f"{BASE}/search/", params={"type": "o", "q": kw})
    p.verify_keyword(f"关键词 q='{kw}'", (j or {}).get("results", []), kw, total0, (j or {}).get("count"))
    total_kw = (j or {}).get("count")

    r, j = p.get("search keyword+date", f"{BASE}/search/",
                 params={"type": "o", "q": kw, "filed_after": "2025-01-01", "filed_before": "2025-06-30", "order_by": "dateFiled desc"})
    res = (j or {}).get("results", [])
    p.verify_dates("时间 filed_after/filed_before (2025H1)", [x.get("dateFiled") for x in res],
                   datetime(2025, 1, 1), datetime(2025, 6, 30, 23, 59), total_kw, (j or {}).get("count"))

    r, j = p.get("search RECAP", f"{BASE}/search/", params={"type": "r", "q": kw})
    res = (j or {}).get("results", [])
    p.record_fields("docket (RECAP search)", res[0] if res else None)
    p.check("RECAP (PACER) 案卷搜索", bool(res), f"总数 {(j or {}).get('count')}")

    r, j = p.get("dockets endpoint", f"{BASE}/dockets/", params={"date_modified__gte": "2026-10-01T00:00:00Z"})
    if r is not None and r.status_code == 401:
        p.check("非 search 端点 (dockets)", None, "401: 需要 token")
    else:
        res = (j or {}).get("results", [])
        p.record_fields("docket (REST)", res[0] if res else None)
        p.verify_dates("增量 dockets?date_modified__gte=2026-10-01", [x.get("date_modified") for x in res],
                       datetime(2026, 10, 1), datetime(2100, 1, 1))
