"""
公共测试框架：所有 API 测试模块都用 Probe 来发请求、记录结果、生成报告。

Probe 会自动记录：
  - HTTP 状态码、耗时、返回类型
  - 限流相关的响应头 (X-RateLimit-*, Retry-After ...)
  - 返回记录里的字段 + 自动识别"时间戳类"字段及样例值
  - 关键词 / 时间过滤是否真的生效 (对比过滤前后的结果数 + 抽查记录内容)
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:  # python-dotenv 可选
    pass

OUT_DIR = Path(__file__).parent / "output"
SAMPLE_DIR = OUT_DIR / "samples"
UA = "Mozilla/5.0 (api-capability-test; python-requests)"
# 时间戳字段识别: date_signed / closeDate / Start Date / created / updated_at ... (排除 consolidated 这种误伤)
TS_KEY_RE = re.compile(r"(?:^|[^a-zA-Z])(?i:date|time|timestamp)|[a-z](?:Date|Time|At)\b|_at$|^dt_|_dt$|"
                       r"^[a-z]+(?:date|time)$|"  # 全小写连写: filingdate / lapsedate
                       r"(?i:created|changed|modified|updated|posted|filed|published|issued)")
RATE_HDR_RE = re.compile(r"(ratelimit|rate-limit|retry-after|x-quota|quota)", re.I)

# 某些网站的 WAF 会返回"看似正常"的 404/403 拦截页，这里识别一下
BLOCK_PATTERNS = ["abusive automated request", "Access Denied", "Request blocked", "captcha", "cf-chl"]


def env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name, default)
    return v if v else None


class Probe:
    def __init__(self, name: str, meta: dict):
        self.name = name
        self.slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        self.meta = meta
        self.calls: list[dict] = []
        self.checks: list[dict] = []
        self.fields: dict[str, dict] = {}
        self.notes: list[str] = list(meta.get("notes", []))
        self.status = "unknown"  # ok / partial / needs_key / blocked / error
        self.session = requests.Session()
        self.session.headers["User-Agent"] = UA
        self.min_interval = 0.0  # 两次请求之间的最小间隔 (秒), 给限流很严的 API 用
        self._last_req = 0.0

    # ------------------------------------------------------------------ HTTP
    def request(self, label: str, method: str, url: str, *, save: bool = True, timeout: int = 40, **kw):
        wait = self.min_interval - (time.time() - self._last_req)
        if wait > 0:
            time.sleep(wait)
        self._last_req = time.time()
        t0 = time.time()
        rec = {"label": label, "method": method, "url": _redact(url, kw.get("params"))}
        try:
            r = self.session.request(method, url, timeout=timeout, **kw)
            ra = r.headers.get("Retry-After", "")
            if r.status_code == 429 and ra.isdigit() and int(ra) <= 60:  # 短暂限流: 等一下重试一次
                print(f"  ⏳ {label}: 429, 等待 {int(ra) + 1}s 后重试")
                time.sleep(int(ra) + 1)
                rec["retried_after_429"] = True
                r = self.session.request(method, url, timeout=timeout, **kw)
        except requests.RequestException as e:
            rec.update(status=None, error=f"{type(e).__name__}: {e}"[:300], elapsed_s=round(time.time() - t0, 2))
            self.calls.append(rec)
            _print_call(rec)
            return None, None
        rec.update(
            status=r.status_code,
            elapsed_s=round(time.time() - t0, 2),
            content_type=r.headers.get("content-type", ""),
            bytes=len(r.content),
            rate_headers={k: v for k, v in r.headers.items() if RATE_HDR_RE.search(k)},
        )
        body = None
        if "json" in rec["content_type"]:
            try:
                body = r.json()
            except ValueError:
                pass
        text = r.text[:2000] if body is None else None
        if text and any(p.lower() in text.lower() for p in BLOCK_PATTERNS):
            rec["blocked_by_waf"] = True
        if not r.ok:
            rec["error_body"] = (json.dumps(body)[:400] if body is not None else _strip_html(r.text)[:400])
        self.calls.append(rec)
        _print_call(rec)
        if save and r.ok:
            SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
            ext = "json" if body is not None else "txt"
            path = SAMPLE_DIR / f"{self.slug}__{re.sub(r'[^a-z0-9]+', '_', label.lower())}.{ext}"
            path.write_text(json.dumps(body, indent=2, ensure_ascii=False)[:500_000] if body is not None else r.text[:500_000])
        r._parsed = body  # type: ignore[attr-defined]
        return r, body

    def get(self, label, url, **kw):
        return self.request(label, "GET", url, **kw)

    def post(self, label, url, **kw):
        return self.request(label, "POST", url, **kw)

    # --------------------------------------------------------------- checks
    def check(self, item: str, passed: bool | None, detail: str = ""):
        """passed: True=通过, False=失败, None=未测/跳过"""
        last = self.calls[-1] if self.calls else {}
        if passed is False and last.get("status") == 429:
            passed = None
            detail = f"⚠️ 被限流 (429, Retry-After={last.get('rate_headers', {}).get('Retry-After')}s), 未能验证; " + detail
        self.checks.append({"item": item, "passed": passed, "detail": detail})
        mark = {True: "✅", False: "❌", None: "⏭️ "}[passed]
        print(f"    {mark} {item}: {detail}")

    def note(self, text: str):
        self.notes.append(text)
        print(f"    📝 {text}")

    def record_fields(self, label: str, record: dict | None):
        """记录一条样例数据的字段，并自动挑出时间戳类字段。"""
        if not isinstance(record, dict):
            return
        flat = _flatten(record)
        ts = {k: _short(v) for k, v in flat.items() if TS_KEY_RE.search(k.split(".")[-1]) and v not in (None, "", [])}
        self.fields[label] = {"all_fields": list(flat.keys())[:80], "timestamp_fields": ts}
        print(f"    🔎 [{label}] 字段数={len(flat)}  时间戳字段: {json.dumps(ts, ensure_ascii=False)[:500]}")

    def verify_keyword(self, item: str, records: list[dict], keyword: str, total_before=None, total_after=None):
        hits = sum(1 for r in records if keyword.lower() in json.dumps(r, ensure_ascii=False).lower())
        narrowed = (total_before is None or total_after is None) or (int(total_after) < int(total_before))
        ok = bool(records) and hits > 0 and narrowed
        self.check(item, ok, f"返回{len(records)}条, 其中{hits}条包含'{keyword}'"
                   + (f"; 总数 {total_before} → {total_after}" if total_before is not None else ""))
        return ok

    def verify_dates(self, item: str, values: list, start: datetime, end: datetime, total_before=None, total_after=None):
        parsed = [parse_any_date(v) for v in values]
        parsed = [d for d in parsed if d]
        inside = [d for d in parsed if start <= d <= end]
        ok = bool(parsed) and len(inside) == len(parsed)
        if total_before is not None and total_after is not None:
            ok = ok and int(total_after) <= int(total_before)
        self.check(item, ok, f"{len(inside)}/{len(parsed)} 条在 {start.date()}~{end.date()} 内"
                   + (f"; 总数 {total_before} → {total_after}" if total_before is not None else "")
                   + (f"; 样例 {[d.date().isoformat() for d in parsed[:3]]}" if parsed else ""))
        return ok

    # --------------------------------------------------------------- report
    def finish(self, status: str | None = None):
        if status:
            self.status = status
        elif self.status == "unknown":
            tested = [c for c in self.checks if c["passed"] is not None]
            if not tested and any(c.get("status") == 429 for c in self.calls):
                self.status = "rate_limited"
            elif not tested:
                self.status = "needs_key" if any(c.get("status") in (401, 403) for c in self.calls) else "error"
            elif all(c["passed"] for c in tested):
                self.status = "ok"
            elif any(c["passed"] for c in tested):
                self.status = "partial"
            else:
                self.status = "error"
        if any(c.get("blocked_by_waf") for c in self.calls) and self.status != "ok":
            self.status = "blocked"
        return {
            "name": self.name, "status": self.status, "meta": self.meta, "checks": self.checks,
            "fields": self.fields, "notes": self.notes, "calls": self.calls,
            "tested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }


# ---------------------------------------------------------------- helpers
def parse_any_date(v) -> datetime | None:
    """尽量把各种格式的日期统一解析为 naive datetime (UTC)。"""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)) or (isinstance(v, str) and re.fullmatch(r"\d{9,13}", v.strip())):
        n = float(v)
        if n > 1e11:  # 毫秒
            n /= 1000
        return datetime.fromtimestamp(n, tz=timezone.utc).replace(tzinfo=None)
    s = str(v).strip()
    m = re.search(r'datetime="([^"]+)"', s)  # DOJ 的 <time datetime="..."> 格式
    if m:
        s = m.group(1)
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%Y %I:%M:%S %p",
                "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z", "%b %d, %Y %I:%M:%S %p %Z", "%Y%m%d"):
        try:
            d = datetime.strptime(s, fmt)
            if d.tzinfo:
                d = d.astimezone(timezone.utc).replace(tzinfo=None)
            return d
        except ValueError:
            continue
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    return datetime.strptime(m.group(1), "%Y-%m-%d") if m else None


def _flatten(d, prefix="", out=None, depth=0):
    out = {} if out is None else out
    if isinstance(d, dict) and depth < 4:
        for k, v in d.items():
            _flatten(v, f"{prefix}{k}.", out, depth + 1)
    elif isinstance(d, list) and d and isinstance(d[0], dict) and depth < 4:
        _flatten(d[0], f"{prefix}[0].", out, depth + 1)
    else:
        out[prefix.rstrip(".")] = d
    return out


def _short(v, n=80):
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + "…"


def _strip_html(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).strip()


def _redact(url: str, params) -> str:
    """URL 里不要把 api_key 打印/保存出来。"""
    q = ""
    if params:
        q = "?" + "&".join(f"{k}={'***' if 'key' in k.lower() or 'token' in k.lower() else v}" for k, v in params.items())
    return re.sub(r"(api_key|apikey|token)=[^&]+", r"\1=***", url) + q


def _print_call(rec):
    s = rec.get("status")
    icon = "🟢" if s and s < 300 else ("🟡" if s and s < 500 else "🔴")
    extra = f" rate={rec['rate_headers']}" if rec.get("rate_headers") else ""
    waf = " ⚠️WAF拦截" if rec.get("blocked_by_waf") else ""
    err = f"\n       ↳ {rec.get('error') or rec.get('error_body', '')}"[:300] if not (s and s < 300) else ""
    print(f"  {icon} {rec['method']} {rec['label']}: {s} ({rec.get('elapsed_s')}s, {rec.get('bytes', 0)}B){extra}{waf}{err}")
