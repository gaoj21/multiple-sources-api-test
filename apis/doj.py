"""DOJ News — 司法部新闻稿。文档: https://www.justice.gov/developer"""
from datetime import datetime, timezone
from common import Probe, parse_any_date

NAME = "DOJ News"
META = {
    "auth": "无需 key",
    "license": "免费公开 (美国政府作品)",
    "docs": "https://www.justice.gov/developer",
    "limits": "pagesize 最大 50; 官方限流: 超过 4 次/秒会降速甚至被封; 总量 27 万+ 条 (2009 至今, 官方页面写的 14,000 已过时)",
    "how": "GET https://www.justice.gov/api/v1/press_releases.json (另有 blog_entries.json; speeches/videos 不存在, 实测 404); 也有 RSS /news/rss?type=press_release",
    "keyword": "❗无全文搜索参数 (parameters[keyword] 会被静默忽略); 只能 parameters[title]=xxx 做标题匹配",
    "date": "支持: parameters[date] 精确匹配某一天 (官方示例用 Unix 时间戳, 实测 YYYY-MM-DD 也可以); 无区间 → 需逐天查或按 sort=date 翻页 (不传 sort 默认从 2009 年最旧的开始)",
    "sources": [
        "✅ 官方: https://www.justice.gov/developer/api-documentation/api_v1 (2025-12-18 更新: press_releases / blog_entries 端点、pagesize≤50、4 次/秒限流、parameters[title] / parameters[date]、sort/direction/page、字段格式)",
        "✅ 官方: https://www.justice.gov/developer (概览; 写着可按部门/主题过滤, 与实测不符)",
        "✅ 官方: https://www.justice.gov/legalpolicies (内容默认 public domain, 部分图片除外)",
        "🧪 实测: parameters[keyword] 和 parameters[component] 被忽略、YYYY-MM-DD 日期格式可用、date 为当天 12:00 UTC、RSS /news/rss?type=press_release (不在 API 文档里)",
    ],
    "notes": [
        "时间字段: date = Unix 秒 (实测是发布日 12:00 UTC, 只有日期精度); created/changed 是 HTML <time datetime=...> 包着 Unix 秒, 精确到秒",
        "body/teaser 是 HTML, 需要自己清洗; component(发布部门)/topic 是 list",
        "未知参数不报错, 直接返回全量 → 一定要校验 resultset.count 是否变化",
        "按部门过滤 parameters[component]: 官方开发者页说支持按部门/主题过滤, 但实测被忽略 (总数不变), 需要客户端过滤",
    ],
}
URL = "https://www.justice.gov/api/v1/press_releases.json"


def _q(p, label, **params):
    r, j = p.get(label, URL, params={"pagesize": 20, "sort": "date", "direction": "DESC", **params})
    j = j or {}
    return j.get("results", []), (j.get("metadata", {}).get("resultset", {}) or {}).get("count")


def run(p: Probe):
    recs, total0 = _q(p, "latest")
    p.check("连接", bool(recs), f"总数 {total0}")
    p.record_fields("press_release", recs[0] if recs else None)
    if recs:
        r0 = recs[0]
        p.note(f"时间戳示例: date={r0.get('date')} → {parse_any_date(r0.get('date'))} UTC; created={parse_any_date(r0.get('created'))}; changed={parse_any_date(r0.get('changed'))}")

    kw = "antitrust"
    k, t = _q(p, "keyword param (expected ignored)", **{"parameters[keyword]": kw})
    p.check("全文关键词 parameters[keyword]", t is not None and int(t) < int(total0), f"总数 {total0} → {t} (不变 = 参数无效)")
    k, t = _q(p, "title match", **{"parameters[title]": kw})
    p.verify_keyword(f"标题匹配 parameters[title]='{kw}'", k, kw, total0, t)

    day = "2026-10-01"
    d, t = _q(p, "single date", **{"parameters[date]": day})
    s = datetime.strptime(day, "%Y-%m-%d")
    # date 是美东 00:00 → UTC 04:00/05:00, 给 1 天宽度
    p.verify_dates(f"按日期 parameters[date]={day}", [x.get("date") for x in d], s, s.replace(hour=23, minute=59), total0, t)

    r, _ = p.get("RSS feed", "https://www.justice.gov/news/rss", params={"type": "press_release"})
    p.check("RSS 备用通道", bool(r is not None and r.ok), "RSS 只含最近若干条, 适合增量监控")
