"""EarningsCall — 财报电话会文字稿 / 音频 / PPT。文档: https://earningscall.biz/docs"""
from datetime import datetime
from common import Probe, env

NAME = "EarningsCall"
META = {
    "auth": "参数 apikey; 'demo' key 无需注册, 只能查 AAPL 和 MSFT; 免费试用 key 需邮箱或 Google 登录; 正式使用要付费",
    "license": "付费: Starter $60/月 (只有纯文本)、Premium $69/月 (发言人、逐词时间、问答拆分)、Ultimate $129/月 (加音频)、Ultimate+ $155/月 (加 webhooks)",
    "docs": "https://earningscall.biz/docs  ·  套餐: https://earningscall.biz/docs/plans  ·  价格: https://earningscall.biz/api-pricing",
    "limits": "Starter 套餐 10 次/分钟; 实测响应头 x-ratelimit-remaining (demo 为 89 左右); 试用 key 的剩余次数在 x-trial-calls-remaining",
    "how": "REST JSON: GET https://api.earningscall.dev/events (某公司全部电话会) → /transcript?year=&quarter=&level=1..4; 另有 /symbols、/calendar、/audio、/slides",
    "keyword": "只能按公司名或代码搜公司 (/symbols?search=); 不能在文字稿里做关键词搜索",
    "date": "按 year + quarter 取某一场; /calendar?year=&month=&day= 查某一天有哪些电话会",
    "sources": [
        "官方: https://earningscall.biz/docs 、/docs/plans 、/api-pricing — 接口、四个 level、套餐价格、覆盖 9,000+ 家公司 (主要美国, 加拿大/欧洲/澳洲较少)、多数公司 2020 年起",
        "实测: demo key 的 level 4 没有拆分: prepared_remarks 就是整篇全文, 没有 questions_and_answers 字段 (多个季度都一样; 不确定是 demo 限制还是功能问题)",
        "实测: demo key 可取 AAPL/MSFT 全部四个 level; 查 JPM 返回 403 'Demo accounts can only access Apple (AAPL) and Microsoft'; 日历只能查 2025-01-10",
    ],
    "notes": [
        "四个 level (官方): 1 = 整篇纯文本; 2 = 按发言人分段 + 发言人姓名职位; 3 = 每个词的开始时间 (秒); 4 = 拆成管理层发言 prepared_remarks 和问答 questions_and_answers (demo key 实测没拆)",
        "实测 AAPL: 33 场电话会 (2018-07 起); 一场约 4.5 万字符、58 段发言、11 位发言人; level 3 有 7,692 个词的时间, 整场约 60 分钟",
        "财报日历里的 conference_date 只有日期 (时间是 00:00), 单场电话会的 conference_date 精确到分钟",
        "每场电话会都有 conference_date (带时区, 如 2024-10-31T17:00:00-04:00), 精确到分钟",
        "官方说约一半电话会在结束后 15 分钟内可取",
    ],
}
B = "https://api.earningscall.dev"


def run(p: Probe):
    key = env("EARNINGSCALL_API_KEY") or "demo"
    if key == "demo":
        p.note("未配置 EARNINGSCALL_API_KEY, 用 demo key (只能查 AAPL / MSFT)")
    P = {"apikey": key}

    r, ev = p.get("events AAPL", f"{B}/events", params={**P, "exchange": "NASDAQ", "symbol": "AAPL"})
    events = (ev or {}).get("events", [])
    p.check("连接 / 电话会列表", bool(events), f"AAPL 共 {len(events)} 场, 最早 {events[-1].get('conference_date') if events else None}, 最新 {events[0].get('conference_date') if events else None}")
    p.record_fields("event", events[0] if events else None)
    pub = [e for e in events if e.get("is_published")]
    y, q = (pub[0]["year"], pub[0]["quarter"]) if pub else (2024, 4)

    T = {**P, "exchange": "NASDAQ", "symbol": "AAPL", "year": y, "quarter": q}
    r, t1 = p.get("transcript level 1", f"{B}/transcript", params={**T, "level": 1})
    text = (t1 or {}).get("text", "")
    p.check(f"level 1 纯文本 ({y}Q{q})", bool(text), f"{len(text)} 字符; 开头: {text[:80]}")
    p.record_fields("transcript level 1", {k: v for k, v in (t1 or {}).items() if k != "text"})

    r, t2 = p.get("transcript level 2", f"{B}/transcript", params={**T, "level": 2})
    sp = (t2 or {}).get("speakers", [])
    names = {}
    for s in sp:
        info = s.get("speaker") or {}
        if isinstance(info, dict) and info.get("name"):
            names[info["name"]] = info.get("title")
    p.check("level 2 按发言人分段", bool(sp), f"{len(sp)} 段, {len(names)} 位发言人, 如 {list(names.items())[:4]}")
    p.record_fields("speaker segment", sp[0] if sp else None)

    r, t3 = p.get("transcript level 3", f"{B}/transcript", params={**T, "level": 3})
    sp3 = (t3 or {}).get("speakers", [])
    w = sum(len(s.get("words", [])) for s in sp3)
    last = sp3[-1]["start_times"][-1] if sp3 and sp3[-1].get("start_times") else None
    p.check("level 3 逐词时间", bool(sp3), f"{w} 个词带开始时间; 最后一个词在第 {last} 秒 (约 {round(last / 60) if last else '?'} 分钟)")

    r, t4 = p.get("transcript level 4", f"{B}/transcript", params={**T, "level": 4})
    pr, qa = (t4 or {}).get("prepared_remarks", ""), (t4 or {}).get("questions_and_answers", "")
    same = bool(pr) and pr == text
    p.check("level 4 管理层发言 / 问答拆分", bool(pr) and bool(qa),
            f"管理层发言 {len(pr)} 字符, 问答 {len(qa)} 字符" + ("; prepared_remarks 与 level 1 全文完全相同, 没有拆分" if same else ""))

    kw = "microsoft"
    r, sy = p.get("symbols search", f"{B}/symbols", params={**P, "search": kw})
    syms = (sy or {}).get("symbols", [])
    p.verify_keyword(f"按公司名搜索 '{kw}'", syms, kw)

    r, cal = p.get("calendar 2025-01-10", f"{B}/calendar", params={**P, "year": 2025, "month": 1, "day": 10})
    rows = cal if isinstance(cal, list) else (cal or {}).get("events", (cal or {}).get("calendar", []))
    p.record_fields("calendar row", rows[0] if rows else None)
    p.verify_dates("财报日历 2025-01-10", [x.get("conference_date") for x in rows if isinstance(x, dict)],
                   datetime(2025, 1, 10), datetime(2025, 1, 11, 6))

    r, _ = p.get("demo restriction (JPM)", f"{B}/transcript", params={**P, "exchange": "NYSE", "symbol": "JPM", "year": 2024, "quarter": 4}, save=False)
    p.check("demo key 限制", r is not None and r.status_code == 403 if key == "demo" else None,
            "查 AAPL/MSFT 以外的公司返回 403" if key == "demo" else "非 demo key, 跳过")
