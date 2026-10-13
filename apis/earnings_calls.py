"""Earnings Calls — 财报电话会: Alpha Vantage (文字稿、历史财报、财报日历)。
付费的 Quartr 另见 quartr.py。"""
import csv
import io
from datetime import datetime, timedelta
from common import Probe, env

NAME = "Earnings Calls"
META = {
    "auth": "Alpha Vantage: 免费 API key (alphavantage.co/support/#api-key, 填邮箱即得), 参数 apikey; 'demo' key 只能查官方示例 (IBM)",
    "license": "免费层 (25 次/天) + 付费 Premium",
    "docs": "https://www.alphavantage.co/documentation/ (Earnings Call Transcript / Earnings / Earnings Calendar)",
    "limits": "Alpha Vantage 免费 key: 25 次/天 (官方), 超出返回 200 + 'Information' 提示而不是 429",
    "how": "Alpha Vantage: GET https://www.alphavantage.co/query?function=EARNINGS_CALL_TRANSCRIPT&symbol=IBM&quarter=2024Q1; 另有 function=EARNINGS (历史财报) 和 EARNINGS_CALENDAR (CSV)",
    "keyword": "❌ Alpha Vantage 文字稿只能按 股票代码+季度 取, 不能关键词搜",
    "date": "Alpha Vantage: quarter=YYYYQn (2010Q1 起); 财报日历 horizon=3month/6month/12month",
    "sources": [
        "✅ 官方: https://www.alphavantage.co/documentation/ — EARNINGS_CALL_TRANSCRIPT 参数 symbol + quarter (YYYYQM, 2010Q1 起), 含逐段情绪信号; EARNINGS_CALENDAR (CSV, horizon); EARNINGS",
        "✅ 官方: https://www.alphavantage.co/support/ 与 /premium/ — 免费 25 次/天",
        "❓ 未核对: 免费 key 能否取所有公司的文字稿 (demo key 只覆盖 IBM)",
    ],
    "notes": [
        "实测拿到的内容: 文字稿每段 = 发言人 speaker、职位 title、内容 content、情绪分 sentiment (IBM 2024Q1 共 37 段、5 万多字符), 但没有通话时间; 历史财报有 reportedDate、reportTime (盘前/盘后)、EPS 实际值/预期值/超预期幅度 (IBM 共 122 个季度); 财报日历是 CSV: 股票代码、公司名、报告日、财年截止日、EPS 预期、币种",
        "Alpha Vantage 超额度或参数错误时仍返回 HTTP 200, 内容是 {'Information': ...} 或 {'Error Message': ...}, 必须检查返回体",
    ],
}
AV = "https://www.alphavantage.co/query"


def _av(p, label, key, **params):
    r, j = p.get(label, AV, params={**params, "apikey": key})
    if isinstance(j, dict) and ("Information" in j or "Error Message" in j or "Note" in j):
        msg = j.get("Information") or j.get("Error Message") or j.get("Note")
        p.calls[-1]["error_body"] = msg[:300]
        return r, None, msg
    return r, j, None


def run(p: Probe):
    key = env("ALPHAVANTAGE_API_KEY") or "demo"
    if key == "demo":
        p.note("未配置 ALPHAVANTAGE_API_KEY, 用 demo key (只能查 IBM)")

    # 1) 文字稿
    r, t, err = _av(p, "transcript IBM 2024Q1", key, function="EARNINGS_CALL_TRANSCRIPT", symbol="IBM", quarter="2024Q1")
    segs = (t or {}).get("transcript", [])
    p.check("Alpha Vantage 文字稿", bool(segs), err or f"{len(segs)} 段发言, {sum(len(s.get('content', '')) for s in segs)} 字符")
    p.record_fields("transcript segment", segs[0] if segs else None)
    if segs:
        p.note(f"文字稿每段字段: {list(segs[0].keys())}; 顶层只有 symbol / quarter, 没有通话日期时间戳")

    # 2) 历史财报 (含发布日期)
    r, e, err = _av(p, "earnings history IBM", key, function="EARNINGS", symbol="IBM")
    q = (e or {}).get("quarterlyEarnings", [])
    p.record_fields("quarterly earnings", q[0] if q else None)
    p.check("历史财报 (EPS / 发布日)", bool(q), err or f"{len(q)} 个季度")

    # 3) 财报日历
    r, _ = p.get("earnings calendar", AV, params={"function": "EARNINGS_CALENDAR", "horizon": "3month", "apikey": key})
    rows = list(csv.DictReader(io.StringIO(r.text))) if r is not None and r.ok and "symbol" in r.text[:200] else []
    p.record_fields("calendar row", rows[0] if rows else None)
    if rows:
        p.verify_dates("财报日历 (未来 3 个月)", [x.get("reportDate") for x in rows[:200]],
                       datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1), datetime(2100, 1, 1))
    else:
        p.check("财报日历 (未来 3 个月)", False, (r.text[:200] if r is not None else "无响应"))

    p.check("关键词搜索", None, "Alpha Vantage 不支持")
