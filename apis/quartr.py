"""Quartr — 上市公司财报电话会: 事件、文字稿、音频、PPT、报告 (API v3)。文档: https://quartr.com/docs/"""
from datetime import datetime
from common import Probe, env

NAME = "Quartr"
META = {
    "auth": "Header x-api-key (Quartr 商务开通, 在 Quartr Portal portal.quartr.dev 生成)",
    "license": "💰 商业付费 license: 数据集可单买或打包 (transcripts、audio、live、summaries、解析文档等), companies 和 events 始终包含",
    "docs": "https://quartr.com/docs/ (docs.quartr.com 会跳转到这里)  ·  OpenAPI: https://api.quartr.com/public/v3/openapi.json",
    "limits": "按套餐, 默认 50 次/秒, 超出返回 429; 游标分页 (limit 默认 10、最大 500, 跟 nextCursor 直到为 null); v1/v2 已下线 (实测 410 Gone), 只能用 v3",
    "how": "REST JSON: /public/v3/companies, /events, /documents/{transcripts|reports|slides}, /audio, /live; 另有 Webhooks 和 Snowflake 数据共享",
    "keyword": "❗没有全文关键词搜索; 只能按 tickers / isins / ciks / companyIds / countries / exchanges / typeIds 过滤",
    "date": "支持: startDate / endDate (事件日期) 以及 updatedAfter / updatedBefore (数据更新时间, 适合增量)",
    "sources": [
        "✅ 官方: https://api.quartr.com/public/v3/openapi.json (全部端点和参数、x-api-key、无关键词参数)",
        "✅ 官方: https://quartr.com/docs/rest-api/auth.md (认证、Portal、默认 50 次/秒)",
        "✅ 官方: https://quartr.com/docs/rest-api/fetching-data.md (游标分页、startDate/endDate 按事件日期、updatedAfter 用于增量、计费方式)",
        "✅ 官方: https://quartr.com/docs/datasets/summaries.md 与 live-earnings-call-transcripts.md (摘要、直播文字稿 transcriptVersion 1.6/1.7)",
        "🧪 实测: v1/v2 返回 410、v3 无 key 返回 401",
    ],
    "notes": [
        "实时电话会: /live 和 /live/transcripts 提供直播中的文字稿 (transcriptVersion)",
        "documents/*/summary 提供 AI 摘要 (length / plain 参数); transcripts/{id}/chapters 有分段",
        "OpenAPI 公开, 但所有数据接口无 key 返回 401",
    ],
}
BASE = "https://api.quartr.com/public/v3"


def run(p: Probe):
    r, j = p.get("openapi spec (public)", f"{BASE}/openapi.json", save=False)
    p.check("OpenAPI 公开可读", bool(j), f"{len((j or {}).get('paths', {}))} 个 path")
    key = env("QUARTR_API_KEY")
    if not key:
        p.get("no-key probe", f"{BASE}/companies", params={"tickers": "AAPL"})
        p.check("连接", None, "未配置 QUARTR_API_KEY; 返回 401")
        return "needs_key"
    p.session.headers["x-api-key"] = key

    r, j = p.get("companies by ticker", f"{BASE}/companies", params={"tickers": "AAPL", "limit": 5})
    comps = (j or {}).get("data", [])
    p.record_fields("company", comps[0] if comps else None)
    p.check("连接 / 按 ticker 查公司", bool(comps), f"{len(comps)} 条")

    s, e = "2025-01-01", "2025-12-31"
    r, j = p.get("events by date", f"{BASE}/events", params={"tickers": "AAPL", "startDate": s, "endDate": e, "limit": 20})
    ev = (j or {}).get("data", [])
    p.record_fields("event", ev[0] if ev else None)
    p.verify_dates("events startDate/endDate (2025)", [x.get("date") for x in ev], datetime(2025, 1, 1), datetime(2025, 12, 31, 23, 59))

    r, j = p.get("transcripts", f"{BASE}/documents/transcripts", params={"tickers": "AAPL", "limit": 5})
    docs = (j or {}).get("data", [])
    p.record_fields("transcript document", docs[0] if docs else None)
    p.check("文字稿列表", bool(docs), f"{len(docs)} 条")

    r, j = p.get("updatedAfter (incremental)", f"{BASE}/events", params={"updatedAfter": "2026-10-01T00:00:00Z", "limit": 10})
    p.check("增量 updatedAfter", bool(r is not None and r.ok), f"{len((j or {}).get('data', []))} 条")
    p.check("关键词搜索", None, "API 不支持")
