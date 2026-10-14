"""FTC — 联邦贸易委员会: 新闻稿 (RSS/网页)、api.ftc.gov 的 HSR 提前终止公告、联邦公报里的 FTC 正式文件 (经 GovInfo)。"""
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from common import Probe, env

NAME = "FTC"
META = {
    "auth": "新闻稿: 无官方 API, 只有 RSS + 网页 (无需 key); api.ftc.gov (HSR 提前终止/DNC 投诉) 和联邦公报 (GovInfo) 都用 api.data.gov key",
    "license": "免费公开",
    "docs": "https://www.ftc.gov/developer  ·  https://www.ftc.gov/developer/api/v0/endpoints/hsr-early-termination-notices  ·  RSS: https://www.ftc.gov/news-events/stay-connected/ftc-rss-feeds",
    "limits": "www.ftc.gov 有 WAF, 识别为自动化请求会返回 404 拦截页 (按 IP, 换一台机器即可访问); api.ftc.gov 限流由 api.data.gov 控制 (实测个人 key X-RateLimit-Limit=20000, DEMO_KEY 实测 10), 每页最多 50 条",
    "how": "新闻稿: RSS (feeds/press-release*.xml) 或网页列表; HSR: GET api.ftc.gov/v0/hsr-early-termination-notices; 联邦公报: POST api.govinfo.gov/search, query 里加 collection:(FR) agency:\"Federal Trade Commission\"",
    "keyword": "RSS 不支持; 网页列表 ?search_api_fulltext=xxx 支持 (需抓 HTML); api.ftc.gov 支持 filter[title]; 联邦公报支持全文关键词 (如 \"consent order\")",
    "date": "RSS 只有最近若干条 (10~30 条不等, pubDate 带时区如 -0400); 网页列表有起止日期筛选; api.ftc.gov 支持 filter[date][condition][path/value/operator]; 联邦公报用 publishdate:range(起,止)",
    "sources": [
        "官方: https://www.ftc.gov/developer (只有 dnc-complaints 和 hsr-early-termination-notices 两个 API, 无新闻稿 API; 需 api.data.gov key)",
        "官方: https://www.ftc.gov/developer/api/v0/endpoints/hsr-early-termination-notices (filter[title][value]+operator=CONTAINS、page[limit]/page[offset]、sort[x][path]/sort[x][direction])",
        "官方: https://www.ftc.gov/news-events/stay-connected/ftc-rss-feeds (feeds/press-release.xml、-competition.xml、-consumer-protection.xml 三个 RSS 地址) — 从另一台主机访问确认 feed 在线",
        "官方: https://github.com/usgpo/api 与 https://www.govinfo.gov/help/finding-info (GovInfo 搜索语法、publishdate:range、collection 过滤)",
        "实测 (2026-10-14): 联邦公报里 FTC 文件 2026-07~10 共 27 份; 过去一年拟议和解令 15 份 (如 Beretta and Ruger、Aurobindo and Lannett、Ascension Health、CMG Media)",
        "实测/页面观察: 网页列表 ?search_api_fulltext= 参数 (来自页面搜索表单, 无文档)、WAF 拦截行为、RSS 条数",
    ],
    "notes": [
        "注意: 本机测试时 www.ftc.gov 对所有路径返回 'The request resembles an abusive automated request' (WAF 拦截, 带 Error Reference ID), 需要换 IP / 联系 PWH-Alert@ftc.gov 加白名单",
        "api.ftc.gov 的数据不是新闻稿, 而是 HSR 早期终止公告等结构化数据 (JSON:API 格式)",
        "抓网页请降低频率、带正常 UA, 否则很容易被 WAF 拉黑",
        "联邦公报只收 FTC 的正式法律文件 (规则、拟议和解令及其案件分析、征求意见等), 没有一般新闻稿; 和解令要到和解阶段才刊登, 比新闻稿晚",
        "联邦公报每份文件有 dateIssued (刊登日) 和 lastModified (入库时间, 到秒); 单份文件用 /packages/{packageId}/granules/{granuleId}/summary 取详情和 PDF / HTML / TXT 链接 (packageId 是当天整期公报)",
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

    # 联邦公报里的 FTC 正式文件 (经 GovInfo, 不受 www.ftc.gov 拦截影响)
    gi = env("GOVINFO_API_KEY") or env("DATA_GOV_API_KEY") or "DEMO_KEY"
    base_q = 'collection:(FR) agency:"Federal Trade Commission"'

    def fr(label, query, n=10):
        r, j = p.post(label, "https://api.govinfo.gov/search", params={"api_key": gi},
                      json={"query": query, "pageSize": n, "offsetMark": "*", "sorts": [{"field": "publishdate", "sortOrder": "DESC"}]})
        return (j or {}).get("count"), (j or {}).get("results", [])

    total, recs = fr("Federal Register: FTC documents", base_q)
    p.check("联邦公报: 按机构筛 FTC 文件", bool(recs), f"共 {total} 份, 最新: {[(x.get('dateIssued'), x.get('title', '')[:60]) for x in recs[:3]]}")
    p.record_fields("Federal Register FTC document", recs[0] if recs else None)

    s_, e_ = "2026-07-01", "2026-09-30"
    n_date, d = fr("Federal Register: FTC 2026Q3", f"{base_q} publishdate:range({s_},{e_})")
    p.verify_dates(f"联邦公报: 刊登日 {s_}~{e_}", [x.get("dateIssued") for x in d],
                   datetime(2026, 7, 1), datetime(2026, 9, 30, 23, 59), total, n_date)

    kw = "consent order"
    n_kw, k = fr("Federal Register: FTC consent orders", f'{base_q} "{kw}"')
    p.check(f"联邦公报: 关键词 '{kw}'", bool(k) and n_kw is not None and total is not None and n_kw < total,
            f"FTC 文件 {total} → {n_kw}; 例: {[x.get('title', '')[:70] for x in k[:3]]}")

    if k:
        # 搜索结果里的 packageId 是当天整期公报, granuleId 才是这一份 FTC 文件
        pkg, gid = k[0].get("packageId"), k[0].get("granuleId")
        r, summ = p.get("Federal Register: document (granule) summary",
                        f"https://api.govinfo.gov/packages/{pkg}/granules/{gid}/summary", params={"api_key": gi})
        p.record_fields("Federal Register FTC document detail", summ)
        p.check("联邦公报: 单份文件详情和全文链接", bool(summ),
                f"{gid}: {(summ or {}).get('title', '')[:70]} | 下载格式 {list((summ or {}).get('download', {}).keys())}")
    return None  # 新闻稿被拦截, 但 HSR 和联邦公报可用 → 由检查结果算出"部分可用"
