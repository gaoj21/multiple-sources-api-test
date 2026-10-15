"""提示词 + 结果校验。

每个 (obligor, 数据源) 一个请求; 另有每家公司一个"找官网"请求。
模型必须联网搜索, 每条结果都要带链接; 程序事后检查链接域名和日期, 不合格的标出来。
"""
import json
import re
from datetime import date
from urllib.parse import urlparse

from sources import SOURCES, WEBSITE_TASK

SYSTEM = (
    "You are a research assistant with web search. Use web search for every request. "
    "Only report facts you found on web pages during this session, each with the exact URL where you found it. "
    "Never rely on memory and never invent URLs, case numbers, award IDs or amounts. "
    "If you find nothing that matches, return an empty list - that is a valid and useful answer. "
    "Reply with a single JSON object and nothing else."
)


def describe(ob: dict) -> str:
    """把 obligor 的已知信息写进提示, 帮模型区分同名公司。"""
    parts = [f'Company: "{ob["name"]}"']
    for key, label in (("aliases", "Also known as"), ("country", "Country"), ("state", "US state"),
                       ("ticker", "Ticker"), ("website", "Website"), ("identifiers", "Known identifiers")):
        if ob.get(key):
            parts.append(f"{label}: {ob[key]}")
    return "\n".join(parts)


def source_messages(ob: dict, source_key: str, start: date, end: date) -> list:
    src = SOURCES[source_key]
    domains = list(src["domains"])
    if src.get("include_company_domain") and ob.get("website"):
        domains.append(domain_of(ob["website"]))
    schema = {
        "found": "true/false",
        "items": [{
            "event_date": "YYYY-MM-DD (date the event happened, e.g. filing/award/decision date)",
            "published_date": "YYYY-MM-DD or null (date the page/record was published or posted, if shown)",
            "event_type": "|".join(src["event_types"]),
            "title": "short title",
            "summary": "1-3 sentences: what happened, to whom, outcome",
            "amount_usd": "number or null",
            "counterparties": ["other parties named, e.g. agency, plaintiff, secured party"],
            "identifiers": {"e.g. award_id / case_number / docket / filing_number / UEI": "value"},
            "url": "exact URL on one of the allowed domains",
        }],
        "match_notes": "how you confirmed this is the same company (and not a similarly named one)",
        "searched_queries": ["the search queries you ran"],
    }
    user = (
        f"{describe(ob)}\n\n"
        f"Task: search {src['name']} for {src['looks_for']}.\n"
        f"Time window: events between {start.isoformat()} and {end.isoformat()} only.\n"
        f"Allowed sources: only pages on these domains count: {', '.join(domains)}. "
        f"Use site: filters in your searches. News articles or other sites do not count, even if they cite the source.\n"
        f"Make sure each item is about this exact company (or its subsidiaries - say so in the summary), "
        f"not a different company with a similar name.\n\n"
        f"Return JSON exactly in this shape:\n{json.dumps(schema, indent=2)}"
    )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def website_messages(ob: dict) -> list:
    schema = {
        "website": "https://... official homepage, or null",
        "investor_relations_url": "https://... or null",
        "newsroom_url": "https://... press releases / news page, or null",
        "evidence": "how you confirmed it is the official site (e.g. matching legal name, address, ticker)",
        "other_candidates": ["other sites you considered and rejected"],
    }
    user = (
        f"{describe(ob)}\n\n"
        "Task: find this company's official website, plus its investor relations page and its press release / "
        "newsroom page if they exist. Verify it is the official site of this exact company, not a distributor, "
        "a directory listing or a similarly named company.\n\n"
        f"Return JSON exactly in this shape:\n{json.dumps(schema, indent=2)}"
    )
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


# ---------------------------------------------------------------- 校验

def domain_of(url: str) -> str:
    host = urlparse(url if "://" in url else "https://" + url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def on_domains(url: str, domains: list) -> bool:
    host = domain_of(url or "")
    return bool(host) and any(host == d or host.endswith("." + d) for d in domains)


def parse_json(text: str):
    """模型偶尔会包一层 ```json ... ``` 或在前后加话, 尽量把 JSON 抠出来。"""
    if not text:
        return None
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except ValueError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except ValueError:
            return None
    return None


def _to_date(value):
    if not value or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def check_source_items(data, ob: dict, source_key: str, start: date, end: date) -> list:
    """给每条结果打校验标记: 链接是否在官方域名、日期是否在窗口内。"""
    src = SOURCES[source_key]
    domains = list(src["domains"])
    if src.get("include_company_domain") and ob.get("website"):
        domains.append(domain_of(ob["website"]))
    items = (data or {}).get("items") or []
    out, seen = [], set()
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        url = (it.get("url") or "").strip()
        key = url or (it.get("title"), it.get("event_date"))
        if key in seen:
            continue
        seen.add(key)
        d = _to_date(it.get("event_date")) or _to_date(it.get("published_date"))
        flags = []
        if not url:
            flags.append("no_url")
        elif not on_domains(url, domains):
            flags.append("off_source")
        if d is None:
            flags.append("no_date")
        elif not (start <= d <= end):
            flags.append("out_of_window")
        out.append({**it, "valid": not flags, "flags": flags})
    return out


def check_website(data) -> dict:
    data = data if isinstance(data, dict) else {}
    site = data.get("website")
    return {**data, "valid": bool(site and domain_of(site)), "flags": [] if site else ["no_website"]}


TASKS = list(SOURCES) + [WEBSITE_TASK]
