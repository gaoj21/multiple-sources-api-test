"""给定 obligor 名单, 用联网搜索的 GPT 分别在各数据源找过去一年的信息, 外加每家公司的官网。

只用 llm 包的公开接口 (contract llm-v12): 不写服务商名字, provider 默认用配置里的 default,
也可以用 --provider 或环境变量 LLM_PROVIDER 指定一个开了联网搜索的 provider。

    python obligor_research/run.py --obligors obligors.csv              # llm/ 放在 obligor_research/ 下
    python obligor_research/run.py --obligors obligors.csv --dry-run          # 只生成提示词, 不调用模型
    python obligor_research/run.py --report-only --out obligor_research/out   # 只根据已有结果重新出报告
"""
import argparse
import concurrent.futures
import csv
import json
import sys
import threading
import time
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sources import SOURCES, WEBSITE_TASK  # noqa: E402
from tasks import (check_source_items, check_website, domain_of, on_domains, parse_json,  # noqa: E402
                   source_messages, website_messages)

NAME_COLUMNS = ("name", "obligor", "obligor_name", "company", "company_name", "legal_name")
OPTIONAL = ("aliases", "country", "state", "ticker", "website", "identifiers")


# ---------------------------------------------------------------- 环境变量

def env_candidates(extra: Path | None = None) -> list:
    """.env 的查找顺序: --env-file, obligor_research/.env, 上一级 (code/.env)。

    llm 包自己只在 llm/ 的上一级和 llm/ 里找 .env; llm 放在 obligor_research/ 下时,
    它找不到 code/.env, 所以这里在导入 llm 之前先加载。
    """
    paths = [extra] if extra else []
    return paths + [HERE / ".env", HERE.parent / ".env"]


def load_env_files(extra: Path | None = None) -> list:
    """把 .env 读进 os.environ; 已有的环境变量不覆盖。不依赖 python-dotenv。返回读到的文件。"""
    import os
    loaded = []
    for path in env_candidates(extra):
        if not path or not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            if value[:1] in "\"'" and value[-1:] == value[:1] and len(value) >= 2:
                value = value[1:-1]
            elif " #" in value:
                value = value.split(" #", 1)[0].rstrip()
            if key and key not in os.environ:
                os.environ[key] = value
        loaded.append(str(path))
    return loaded


# ---------------------------------------------------------------- 输入

def load_obligors(path: Path) -> list:
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        sys.exit(f"{path} 是空的")
    cols = {c.lower().strip(): c for c in rows[0].keys()}
    name_col = next((cols[c] for c in NAME_COLUMNS if c in cols), None)
    if not name_col:
        sys.exit(f"找不到公司名列, 需要以下之一: {', '.join(NAME_COLUMNS)}; 现有列: {list(rows[0].keys())}")
    out = []
    for i, r in enumerate(rows, 1):
        name = (r.get(name_col) or "").strip()
        if not name:
            continue
        ob = {"id": (r.get(cols.get("id", ""), "") or str(i)).strip() or str(i), "name": name}
        for key in OPTIONAL:
            if key in cols and (r.get(cols[key]) or "").strip():
                ob[key] = r[cols[key]].strip()
        out.append(ob)
    return out


# ---------------------------------------------------------------- 结果文件 (断点续跑)

class Store:
    def __init__(self, out: Path):
        self.path = out / "results.jsonl"
        self.lock = threading.Lock()
        self.done = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("status") == "ok":
                    self.done[(rec["obligor_id"], rec["task"])] = rec

    def write(self, rec: dict):
        with self.lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if rec.get("status") == "ok":
                self.done[(rec["obligor_id"], rec["task"])] = rec


# ---------------------------------------------------------------- 调用模型

DEFAULT_LLM_OPTIONS = {"tools": [{"type": "web_search"}]}  # 开启联网搜索工具; 写法按那台机器的要求用 --llm-options 改


def call_model(llm, provider, messages, timeout, llm_options):
    """一个请求失败只影响它自己 (batch_result 里一个失败会让整批报错, 所以不用它)。

    llm_options 原样作为关键字参数传给 chat_result, llm 包会把它转给服务商 (用来开启联网搜索工具)。
    """
    t0 = time.time()
    try:
        res = llm.chat_result(provider, messages, temperature=0, timeout=timeout, **llm_options)
        return {"status": "ok", "content": res.content, "usage": res.usage.as_dict() if res.usage else None,
                "model": res.model, "seconds": round(time.time() - t0, 1)}, res
    except llm.ProviderError as e:
        return {"status": "error", "error": f"ProviderError: {e}", "seconds": round(time.time() - t0, 1)}, None
    except Exception as e:  # 网络等其他错误, 记下来, 下次续跑会重试
        return {"status": "error", "error": f"{type(e).__name__}: {e}", "seconds": round(time.time() - t0, 1)}, None


def run_jobs(jobs, llm, provider, store, tracker, workers, timeout, llm_options):
    total, done_n = len(jobs), 0
    lock = threading.Lock()

    def one(job):
        nonlocal done_n
        ob, task, messages, post = job
        rec, res = call_model(llm, provider, messages, timeout, llm_options)
        if res is not None:
            if not tracker.add(res):
                rec["usage_missing"] = True  # 服务商没报用量, 不当作免费
            if llm_options.get("tools") or llm_options.get("web_search_options") is not None:
                tracker.add_web_search(1)    # 实际搜索次数拿不到, 按每次请求至少 1 次估算
        rec.update({"obligor_id": ob["id"], "obligor": ob["name"], "task": task})
        if rec["status"] == "ok":
            data = parse_json(rec["content"])
            if data is None:
                rec.update(status="bad_json")  # 不算完成, 续跑时会重试
            else:
                rec["data"] = data
                rec["checked"] = post(data)
        store.write(rec)
        with lock:
            done_n += 1
            mark = {"ok": "ok", "bad_json": "JSON 解析失败", "error": "出错"}[rec["status"]]
            print(f"  [{done_n}/{total}] {ob['name'][:40]:40} {task:16} {mark} ({rec.get('seconds')}s)", flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(one, jobs))


def missing_module_hint(text: str) -> str:
    """服务商适配器缺少依赖时, 给出换 Python 环境的提示 (不点名服务商, 遵守 contract)。"""
    import re
    m = re.search(r"requires ([A-Za-z_][\w.]+)|No module named '([\w.]+)'", text or "")
    if not m:
        return ""
    mod = m.group(1) or m.group(2)
    return (f"提示: 当前 Python ({sys.executable}) 里缺少模块 {mod}。这是 llm 包里服务商适配器需要的 SDK, "
            f"不是本程序的问题。请改用装了它的 Python 环境运行 (例如项目的 .venv/bin/python), "
            f"可以先用  <那个python> -c \"import {mod}\"  确认能导入。")


def preflight(llm, provider, timeout, llm_options, show_raw=False):
    """问一个只有联网搜索才答得出的问题, 确认 provider 开着联网搜索。"""
    since = date.today() - timedelta(days=14)
    msgs = [{"role": "system", "content": "Use web search. Reply with JSON only."},
            {"role": "user", "content": "Search justice.gov for the most recent US Department of Justice press release "
             f"published on or after {since.isoformat()}. Return JSON: {{\"title\": ..., \"date\": \"YYYY-MM-DD\", \"url\": ...}}"}]
    rec, _ = call_model(llm, provider, msgs, timeout, llm_options)
    if show_raw:
        print(f"    --- 预检原始回答 (参数 {json.dumps(llm_options)}) ---\n    {(rec.get('content') or rec.get('error') or '')[:1500]}")
    if rec["status"] != "ok":
        return False, rec.get("error")
    data = parse_json(rec["content"]) or {}
    url, d = data.get("url") or "", (data.get("date") or "")[:10]
    ok = on_domains(url, ["justice.gov"]) and d >= since.isoformat()
    return ok, f"date={d} url={url}"


# ---------------------------------------------------------------- 报告

def build_report(out: Path, obligors: list, sources: list, start: date, end: date, usage: dict | None):
    store = Store(out)
    recs = list(store.done.values())
    # 所有尝试过的 (含失败), 用来统计失败数
    attempts = Counter()
    if store.path.exists():
        for line in store.path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
                attempts[(r["obligor_id"], r["task"], r["status"])] += 1
            except (ValueError, KeyError):
                pass

    item_rows, site_rows = [], []
    valid = defaultdict(lambda: defaultdict(int))     # valid[source][obligor_id] = 有效条数
    flagged = defaultdict(Counter)                     # flagged[source][flag] += 1
    names = {o["id"]: o["name"] for o in obligors} or {r["obligor_id"]: r["obligor"] for r in recs}
    for r in recs:
        if r["task"] == WEBSITE_TASK:
            c = r.get("checked") or {}
            site_rows.append({"obligor_id": r["obligor_id"], "obligor": r["obligor"], "website": c.get("website"),
                              "investor_relations_url": c.get("investor_relations_url"),
                              "newsroom_url": c.get("newsroom_url"), "evidence": c.get("evidence"),
                              "valid": c.get("valid")})
            continue
        for it in r.get("checked") or []:
            item_rows.append({"obligor_id": r["obligor_id"], "obligor": r["obligor"], "source": r["task"],
                              "event_date": it.get("event_date"), "published_date": it.get("published_date"),
                              "event_type": it.get("event_type"), "title": it.get("title"),
                              "summary": it.get("summary"), "amount_usd": it.get("amount_usd"),
                              "counterparties": "; ".join(map(str, it.get("counterparties") or [])),
                              "identifiers": json.dumps(it.get("identifiers") or {}, ensure_ascii=False),
                              "url": it.get("url"), "valid": it.get("valid"), "flags": ",".join(it.get("flags") or [])})
            if it.get("valid"):
                valid[r["task"]][r["obligor_id"]] += 1
            for fl in it.get("flags") or []:
                flagged[r["task"]][fl] += 1

    def write_csv(name, rows):
        if not rows:
            return
        with open(out / name, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    write_csv("items.csv", item_rows)
    write_csv("websites.csv", site_rows)

    n_ob = len(names)
    L = [f"# Obligor 多数据源调研结果", "",
         f"- 时间窗: {start} ~ {end}", f"- Obligor 数: {n_ob}", f"- 数据源: {', '.join(sources)}",
         "- 只统计**有效**条目: 链接在该数据源官方域名上、日期在时间窗内。被标记的条目在 items.csv 里 (flags 列)。", "",
         "## 各数据源", "", "| 数据源 | 有结果的 obligor | 有效条目 | 被标记: 链接不在官方域名 | 被标记: 日期不在窗口 | 被标记: 没有链接 | 失败 (出错/JSON) |",
         "|---|---|---|---|---|---|---|"]
    for s in sources:
        fails = sum(v for (o, t, st), v in attempts.items() if t == s and st != "ok" and (o, t) not in store.done)
        L.append(f"| {SOURCES[s]['name']} | {len(valid[s])}/{n_ob} | {sum(valid[s].values())} | "
                 f"{flagged[s]['off_source']} | {flagged[s]['out_of_window']} | {flagged[s]['no_url']} | {fails} |")
    found_sites = sum(1 for r in site_rows if r["valid"])
    L += ["", f"## 公司官网", "", f"找到官网: {found_sites}/{n_ob} (明细见 websites.csv)", "",
          "## 每家 obligor × 数据源 (有效条目数)", "",
          "| Obligor | " + " | ".join(sources) + " |", "|---|" + "---|" * len(sources)]
    for oid, nm in names.items():
        L.append(f"| {nm} | " + " | ".join(str(valid[s].get(oid, 0) or "") for s in sources) + " |")
    if usage:
        L += ["", "## 用量与费用", "", f"- 请求数 (有用量的): {usage.get('token_calls')}",
              f"- 输入 token: {usage.get('input_tokens_total')}, 输出 token: {usage.get('output_tokens_total')}",
              f"- token 费用: {usage.get('total_token_cost')} (单价来自环境变量 EVO_TOKEN_*)",
              f"- 联网搜索: 按每次请求至少 1 次估算 {usage.get('web_search_actions')} 次 (实际次数从公开接口拿不到, 这是下限)",
              f"- 合计 (下限): {usage.get('total_cost')}"]
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\n报告: {out / 'summary.md'} | 明细: items.csv ({len(item_rows)} 条), websites.csv ({len(site_rows)} 家)")


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--obligors", type=Path, help="obligor 名单 CSV (需要公司名列; 可选 aliases/country/state/ticker/website/identifiers)")
    ap.add_argument("--out", type=Path, default=HERE / "out", help="输出目录 (默认 obligor_research/out)")
    ap.add_argument("--provider", default=None, help="llm provider 名; 不填用配置的 default 或环境变量 LLM_PROVIDER")
    ap.add_argument("--llm-root", type=Path, help="llm/ 不在 obligor_research/ 下时, 指定包含 llm/ 的目录")
    ap.add_argument("--env-file", type=Path, help="指定 .env 文件; 默认依次找 obligor_research/.env 和上一级 (code/.env)")
    ap.add_argument("--days", type=int, default=365, help="往前查多少天 (默认 365)")
    ap.add_argument("--end", type=date.fromisoformat, default=date.today(), help="时间窗结束日 YYYY-MM-DD (默认今天)")
    ap.add_argument("--sources", default=",".join(SOURCES), help="逗号分隔, 默认全部: " + ",".join(SOURCES))
    ap.add_argument("--no-website", action="store_true", help="不查公司官网")
    ap.add_argument("--limit", type=int, help="只跑前 N 家 obligor (先小规模试)")
    ap.add_argument("--workers", type=int, default=4, help="并发请求数 (默认 4)")
    ap.add_argument("--timeout", type=int, default=300, help="单个请求超时秒数 (联网搜索较慢, 默认 300)")
    ap.add_argument("--preflight", action="store_true", help="先确认 provider 开着联网搜索")
    ap.add_argument("--llm-options", default=json.dumps(DEFAULT_LLM_OPTIONS),
                    help='传给 chat_result 的额外参数 (JSON), 用来开启联网搜索工具; 默认 \'{"tools": [{"type": "web_search"}]}\'')
    ap.add_argument("--no-web-search-tool", action="store_true", help="不传联网搜索工具 (模型自带搜索时用)")
    ap.add_argument("--dry-run", action="store_true", help="只把提示词写到 out/prompts.jsonl, 不调用模型")
    ap.add_argument("--report-only", action="store_true", help="不调用模型, 只根据 out/results.jsonl 重新出报告")
    a = ap.parse_args()

    sources = [s.strip() for s in a.sources.split(",") if s.strip()]
    try:
        llm_options = {} if a.no_web_search_tool else json.loads(a.llm_options)
    except ValueError:
        sys.exit("--llm-options 不是合法的 JSON")
    bad = [s for s in sources if s not in SOURCES]
    if bad:
        sys.exit(f"未知数据源: {bad}; 可选: {list(SOURCES)}")
    start, end = a.end - timedelta(days=a.days), a.end
    a.out.mkdir(parents=True, exist_ok=True)
    obligors = load_obligors(a.obligors) if a.obligors else []
    if a.limit:
        obligors = obligors[:a.limit]

    if a.report_only:
        build_report(a.out, obligors, sources, start, end, None)
        return
    if not obligors:
        sys.exit("需要 --obligors")

    store = Store(a.out)
    print(f"Obligor {len(obligors)} 家 | 数据源 {len(sources)} 个 | 时间窗 {start} ~ {end} | 已完成 {len(store.done)} 个请求")

    if a.dry_run:
        with open(a.out / "prompts.jsonl", "w", encoding="utf-8") as f:
            for ob in obligors:
                if not a.no_website:
                    f.write(json.dumps({"obligor": ob["name"], "task": WEBSITE_TASK, "messages": website_messages(ob)}, ensure_ascii=False) + "\n")
                for s in sources:
                    f.write(json.dumps({"obligor": ob["name"], "task": s, "messages": source_messages(ob, s, start, end)}, ensure_ascii=False) + "\n")
        n = len(obligors) * (len(sources) + (0 if a.no_website else 1))
        print(f"演练模式: {n} 个请求的提示词已写到 {a.out / 'prompts.jsonl'}")
        return

    print(f"Python: {sys.executable}")
    loaded = load_env_files(a.env_file)
    print(f".env: {', '.join(loaded) if loaded else '没找到 (只用当前环境变量)'}")
    if a.llm_root:
        sys.path.insert(0, str(a.llm_root.resolve()))
    try:
        import llm
    except ImportError:
        sys.exit("找不到 llm 包: 把 llm/ 放在 obligor_research/ 下, 或用 --llm-root 指定包含 llm/ 的目录")
    tracker = llm.UsageTracker()

    if a.preflight:
        print(f"调用参数: {json.dumps(llm_options, ensure_ascii=False) or '(无)'}")
        ok, detail = preflight(llm, a.provider, a.timeout, llm_options)
        print(f"预检 (联网搜索): {'通过' if ok else '没通过'} - {detail}")
        if not ok and missing_module_hint(detail):
            sys.exit(missing_module_hint(detail))
        if not ok:
            sys.exit("这个 provider 看起来没开联网搜索 (或搜索结果不新); 换一个 provider 再试, 或去掉 --preflight 强行运行")

    # 第 1 步: 官网 (结果用来区分同名公司, 也加进财报电话会允许的域名)
    if not a.no_website:
        jobs = [(ob, WEBSITE_TASK, website_messages(ob), check_website)
                for ob in obligors if (ob["id"], WEBSITE_TASK) not in store.done]
        if jobs:
            print(f"\n第 1 步: 查官网 ({len(jobs)} 个请求)")
            run_jobs(jobs, llm, a.provider, store, tracker, a.workers, a.timeout, llm_options)
        for ob in obligors:
            got = (store.done.get((ob["id"], WEBSITE_TASK)) or {}).get("checked") or {}
            if not ob.get("website") and got.get("valid"):
                ob["website"] = got["website"]

    # 第 2 步: 每家公司 × 每个数据源
    jobs = []
    for ob in obligors:
        for s in sources:
            if (ob["id"], s) in store.done:
                continue
            jobs.append((ob, s, source_messages(ob, s, start, end),
                         lambda data, ob=ob, s=s: check_source_items(data, ob, s, start, end)))
    if jobs:
        print(f"\n第 2 步: 各数据源 ({len(jobs)} 个请求)")
        run_jobs(jobs, llm, a.provider, store, tracker, a.workers, a.timeout, llm_options)

    usage = tracker.snapshot()
    (a.out / "usage.json").write_text(json.dumps(usage, indent=2, ensure_ascii=False), encoding="utf-8")
    build_report(a.out, obligors, sources, start, end, usage)
    left = len(obligors) * (len(sources) + (0 if a.no_website else 1)) - len(Store(a.out).done)
    if left:
        print(f"还有 {left} 个请求没成功 (出错或 JSON 解析失败), 再运行一次同样的命令会只重试这些")


if __name__ == "__main__":
    main()
