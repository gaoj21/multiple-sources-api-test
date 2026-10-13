"""FTC Press Releases — 联邦贸易委员会新闻稿 (+ api.ftc.gov 的 HSR 提前终止公告)。"""
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from common import Probe, env

NAME = "FTC Press Releases"
META = {
    "auth": "新闻稿: 无官方 API, 只有 RSS + 网页 (无需 key); api.ftc.gov (HSR 提前终止/DNC 投诉) 需要 api.data.gov key",
    "license": "免费公开",
    "docs": "https://www.ftc.gov/developer  ·  https://www.ftc.gov/developer/api/v0/endpoints/hsr-early-termination-notices  ·  RSS: https://www.ftc.gov/news-events/stay-connected/ftc-rss-feeds",
    "limits": "www.ftc.gov 有 WAF, 识别为自动化请求会返回 404 拦截页 (按 IP, 换一台机器即可访问); api.ftc.gov 限流由 api.data.gov 控制 (实测个人 key X-RateLimit-Limit=20000, DEMO_KEY 实测 10), 每页最多 50 条",
    "how": "RSS (feeds/press-release*.xml) 或抓取 /news-events/news/press-releases 列表页",
    "keyword": "RSS 不支持; 网页列表 ?search_api_fulltext=xxx 支持 (需抓 HTML)",
    "date": "RSS 只有最近若干条 (10~30 条不等, pubDate 带时区如 -0400); 网页列表有起止日期筛选; api.ftc.gov 支持 filter[date][condition][path/value/operator]",
    "sources": [
        "✅ 官方: https://www.ftc.gov/developer (只有 dnc-complaints 和 hsr-early-termination-notices 两个 API, 无新闻稿 API; 需 api.data.gov key)",
        "✅ 官方: https://www.ftc.gov/developer/api/v0/endpoints/hsr-early-termination-notices (filter[title][value]+operator=CONTAINS、page[limit]/page[offset]、sort[x][path]/sort[x][direction])",
        "✅ 官方: https://www.ftc.gov/news-events/stay-connected/ftc-rss-feeds (feeds/press-release.xml、-competition.xml、-consumer-protection.xml 三个 RSS 地址) — 从另一台主机访问确认 feed 在线",
        "🧪 实测/页面观察: 网页列表 ?search_api_fulltext= 参数 (来自页面搜索表单, 无文档)、WAF 拦截行为、RSS 条数",
    ],
    "notes": [
        "⚠️ 本机测试时 www.ftc.gov 对所有路径返回 'The request resembles an abusive automated request' (WAF 拦截, 带 Error Reference ID), 需要换 IP / 联系 PWH-Alert@ftc.gov 加白名单",
        "api.ftc.gov 的数据不是新闻稿, 而是 HSR 早期终止公告等结构化数据 (JSON:API 格式)",
        "抓网页请降低频率、带正常 UA, 否则很容易被 WAF 拉黑",
    ],
}
FEEDS = {
    "all press releases": "https://www.ftc.gov/feeds/press-release.xml",
    "competition": "https://www.ftc.gov/feeds/press-release-competition.xml",
    "consumer protection": "https://www.ftc.gov/feeds/press-release-consumer-protection.xml",
}


def run(p: Probe):
    # 先看主页: 被 WAF 拉黑时主页会返回 "abusive automated request"
    r, _ = p.get("homepage (WAF check)", "https://www.ftc.gov/", save=False)
    # 被拦截时可能是 "abusive automated request" 页, 也可能是一个 1.3KB 的假 404 页 (主页不可能真的 404)
    blocked = bool(p.calls[-1].get("blocked_by_waf")) or (r is not None and r.status_code in (403, 404))
    p.check("www.ftc.gov 可访问", not blocked and bool(r is not None and r.ok),
            "被 WAF 拦截 (IP 被判定为自动化请求)" if blocked else f"HTTP {getattr(r, 'status_code', None)}")
    for label, url in FEEDS.items():
        r, _ = p.get(f"RSS {label}", url)
        if r is not None and r.ok and "<rss" in r.text[:500]:
            items = ET.fromstring(r.content).findall(".//item")
            recs = [{c.tag: (c.text or "") for c in it} for it in items]
            p.record_fields(f"rss item ({label})", recs[0] if recs else None)
            p.check(f"RSS {label}", True, f"{len(recs)} 条, 最新 pubDate={recs[0].get('pubDate') if recs else None}")
        else:
            p.check(f"RSS {label}", False, f"HTTP {getattr(r, 'status_code', None)}" + (" (主页已被 WAF 拦截, 无法判断 URL 是否正确)" if blocked else ""))

    kw = "merger"
    r, _ = p.get("web search list", "https://www.ftc.gov/news-events/news/press-releases",
                 params={"search_api_fulltext": kw}, save=False)
    if r is not None and r.ok and not p.calls[-1].get("blocked_by_waf"):
        titles = re.findall(r'<h3[^>]*>\s*<a[^>]*>([^<]+)</a>', r.text)
        p.check(f"网页关键词搜索 '{kw}'", bool(titles), f"抓到 {len(titles)} 个标题: {titles[:3]}")
    else:
        p.check(f"网页关键词搜索 '{kw}'", False, "WAF 拦截 / 不可达")

    # api.ftc.gov — 结构化数据 (不是新闻稿)
    key = env("FTC_API_KEY") or env("DATA_GOV_API_KEY") or "DEMO_KEY"
    r, j = p.get("api.ftc.gov HSR early termination", "https://api.ftc.gov/v0/hsr-early-termination-notices",
                 params={"api_key": key, "page[limit]": 5, "sort[c][path]": "created", "sort[c][direction]": "DESC"})
    data = (j or {}).get("data", [])
    p.record_fields("HSR early termination notice", data[0].get("attributes") if data else None)
    p.check("api.ftc.gov 连接 (HSR 公告)", bool(data), f"{len(data)} 条")

    r, j = p.get("api.ftc.gov keyword filter", "https://api.ftc.gov/v0/hsr-early-termination-notices",
                 params={"api_key": key, "page[limit]": 5, "filter[title][value]": "Holdings", "filter[title][operator]": "CONTAINS"})
    d2 = (j or {}).get("data", [])
    p.verify_keyword("api.ftc.gov filter[title] CONTAINS 'Holdings'", [{"title": x.get("attributes", {}).get("title")} for x in d2], "holdings")
    return "blocked" if blocked else None
