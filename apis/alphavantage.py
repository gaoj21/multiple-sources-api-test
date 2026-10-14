"""Alpha Vantage — 财报电话会文字稿 (+ 历史财报、财报日历)。文档: https://www.alphavantage.co/documentation/"""
import csv
import io
from datetime import datetime, timedelta
from common import Probe, env

NAME = "Alpha Vantage (Earnings Calls)"
META = {
    "auth": "参数 apikey; 免费 key 填邮箱即得 (alphavantage.co/support/#api-key), 不用信用卡; 'demo' key 只能查 IBM 2024Q1 这一场",
    "license": "免费 25 次/天; 更多次数要买 Premium",
    "docs": "https://www.alphavantage.co/documentation/ (Earnings Call Transcript / Earnings / Earnings Calendar)",
    "limits": "免费 key 25 次/天 (官方), 且每秒最多 1 次 (实测: 连续请求时返回的提示里写的); 响应头里没有额度信息 (实测); 超额或出错仍返回 HTTP 200, 返回体里是 Information 或 Error Message (实测)",
    "how": "GET https://www.alphavantage.co/query?function=EARNINGS_CALL_TRANSCRIPT&symbol=IBM&quarter=2024Q1; 另有 function=EARNINGS (历史财报) 和 EARNINGS_CALENDAR (CSV)",
    "keyword": "不支持: 只能按 股票代码 + 季度 取, 不能关键词搜",
    "date": "quarter=YYYYQn (2010Q1 起, 公司财年口径); 财报日历 horizon=3month/6month/12month",
    "sources": [
        "官方: https://www.alphavantage.co/documentation/ — EARNINGS_CALL_TRANSCRIPT 参数 symbol + quarter (YYYYQM, 2010Q1 起), 带逐段情绪信号; EARNINGS; EARNINGS_CALENDAR",
        "官方: https://www.alphavantage.co/support/ 与 /premium/ — 免费 25 次/天",
        "实测 (2026-10-14, 免费 key): AAPL 2010Q1/2015Q1/2020Q1/2026Q3 都有; JPM 2026Q2 有 (110 段); 小盘 PLTR 有; 在美上市的外国公司 TSM、SAP、TM 有; 伦敦 BP.LON、多伦多 SHOP.TRT 返回空 → 只覆盖美国上市股票",
        "实测: demo key 只能查 IBM 2024Q1, 其他季度或公司都返回 Information 提示",
    ],
    "notes": [
        "文字稿每段: 发言人 speaker、职位 title、内容 content、情绪分 sentiment (IBM 2024Q1 的取值在 0.0~0.8; 官方没说明范围和算法)",
        "文字稿没有电话会时间, 顶层只有 symbol 和 quarter; 可用 EARNINGS 接口的 reportedDate (财报发布日) + reportTime (盘前/盘后) 补, 但发布日不一定等于电话会当天",
        "财报日历是 CSV, 每行: 股票代码、公司名、报告日、财年截止日、EPS 预期、币种、盘前/盘后 timeOfTheDay; 未来 3 个月共约 4,600 条",
        "还没开的电话会返回 Error Message 'Invalid API call' (如 JPM 2026Q3); 查不到的非美国代码返回空 transcript 而不是错误",
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
    key = env("ALPHAVANTAGE_API_KEY")
    p.min_interval = 1.5  # 免费 key 每秒最多 1 次 (超过会返回 Information 提示)
    sym, qq = ("AAPL", "2026Q3") if key else ("IBM", "2024Q1")
    if not key:
        key = "demo"
        p.note("未配置 ALPHAVANTAGE_API_KEY, 用 demo key (只能查 IBM 2024Q1)")

    r, t, err = _av(p, f"transcript {sym} {qq}", key, function="EARNINGS_CALL_TRANSCRIPT", symbol=sym, quarter=qq)
    segs = (t or {}).get("transcript", [])
    speakers = {(s.get("speaker"), s.get("title")) for s in segs}
    p.check(f"文字稿 {sym} {qq}", bool(segs), err or f"{len(segs)} 段, {sum(len(s.get('content', '')) for s in segs)} 字符, {len(speakers)} 位发言人")
    p.record_fields("transcript segment", segs[0] if segs else None)
    p.record_fields("transcript (top level)", {k: v for k, v in (t or {}).items() if k != "transcript"})

    r, e, err = _av(p, f"earnings history {sym}", key, function="EARNINGS", symbol=sym)
    q = (e or {}).get("quarterlyEarnings", [])
    p.record_fields("quarterly earnings", q[0] if q else None)
    p.check("历史财报 (发布日、盘前/盘后、EPS)", bool(q), err or f"{len(q)} 个季度, 最早 {q[-1].get('fiscalDateEnding') if q else None}")

    r, _ = p.get("earnings calendar", AV, params={"function": "EARNINGS_CALENDAR", "horizon": "3month", "apikey": key})
    rows = list(csv.DictReader(io.StringIO(r.text))) if r is not None and r.ok and "symbol" in r.text[:200] else []
    p.record_fields("calendar row", rows[0] if rows else None)
    if rows:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        p.verify_dates(f"财报日历 (未来 3 个月, {len(rows)} 条)", [x.get("reportDate") for x in rows[:300]], today - timedelta(days=1), datetime(2100, 1, 1))
    else:
        p.check("财报日历 (未来 3 个月)", False, r.text[:200] if r is not None else "无响应")
    p.check("关键词搜索", None, "不支持")
