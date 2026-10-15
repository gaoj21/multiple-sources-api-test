"""联网冒烟测试: 在有真实 llm 包的机器上, 用 GPT 联网搜索做几次调用, 确认整条链路能用。

会产生真实费用 (约 8~10 次调用)。测试公司用 Lockheed Martin: 政府合同和诉讼都很多, 结果好判断。

    python obligor_research/tests/test_live_websearch.py                # llm/ 放在 obligor_research/ 下
    python obligor_research/tests/test_live_websearch.py --provider xxx \\
        --llm-options '{"tools": [{"type": "web_search"}]}'

检查项 (前 4 项不通过会以非 0 退出):
  1. provider 配置可用 (需要的环境变量都在)
  2. 联网搜索生效: 能答出 justice.gov 最近两周的新闻稿
  3. 官网: 找到 lockheedmartin.com
  4. 数据源: 在 USAspending / CourtListener 上至少找到 1 条有效记录 (官方域名 + 时间窗内)
  5. 返回的有效链接能打开 (只提示, 不算失败: 有些网站会拦截脚本)
  6. 服务商报了 token 用量 (只提示)
  7. 对照: 不带联网搜索工具时能不能答出最新新闻稿 (只提示; 能答出说明模型自带搜索)
"""
import argparse
import json
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import run as runner  # noqa: E402
from tasks import check_source_items, check_website, domain_of, parse_json, source_messages, website_messages  # noqa: E402

COMPANY = {"id": "smoke", "name": "Lockheed Martin Corporation", "aliases": "Lockheed Martin", "country": "US",
           "state": "MD", "ticker": "LMT"}
EXPECTED_SITE = "lockheedmartin.com"


def url_opens(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (obligor-research smoke test)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return str(r.status)
    except urllib.error.HTTPError as e:
        return str(e.code)
    except Exception as e:
        return type(e).__name__


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--llm-root", type=Path, help="llm/ 不在 obligor_research/ 下时, 指定包含 llm/ 的目录")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--llm-options", default=json.dumps(runner.DEFAULT_LLM_OPTIONS))
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--skip-control", action="store_true", help="跳过第 7 项对照调用 (省 1 次调用)")
    a = ap.parse_args(argv)
    if a.llm_root:
        sys.path.insert(0, str(a.llm_root.resolve()))
    try:
        import llm
    except ImportError:
        sys.exit("找不到 llm 包: 把 llm/ 放在 obligor_research/ 下, 或用 --llm-root 指定包含 llm/ 的目录")
    opts = json.loads(a.llm_options)
    results = []  # (编号, 名称, 状态, 说明); 状态: 通过 / 失败 / 提示

    def record(no, name, status, detail):
        results.append((no, name, status, detail))
        print(f"[{status}] {no}. {name}: {detail}", flush=True)

    # 1. provider
    try:
        listed = llm.list_providers() if hasattr(llm, "list_providers") else {}
        # contract 里 list_providers() 返回 {名字: {available, missing_env, ...}}; 也兼容列表形式
        provs = listed if isinstance(listed, dict) else {p.get("name"): p for p in listed}
        name = a.provider or (llm.default_provider() if hasattr(llm, "default_provider") else None)
        info = provs.get(name, {})
        ok = (not provs) or info.get("available", False)
        record(1, "provider 可用", "通过" if ok else "失败",
               f"{name}; 缺少环境变量: {info.get('missing_env') or '无'}" if provs else "list_providers 不可用, 跳过检查")
    except Exception as e:
        record(1, "provider 可用", "失败", f"{type(e).__name__}: {e}")

    tracker = llm.UsageTracker()
    usage_missing = 0

    def call(messages, options):
        nonlocal usage_missing
        rec, res = runner.call_model(llm, a.provider, messages, a.timeout, options)
        if res is not None and not tracker.add(res):
            usage_missing += 1
        return rec

    # 2. 联网搜索生效
    ok_search, detail = runner.preflight(llm, a.provider, a.timeout, opts)
    record(2, f"联网搜索生效 (参数 {json.dumps(opts)})", "通过" if ok_search else "失败", detail)

    # 3. 官网
    rec = call(website_messages(COMPANY), opts)
    site = check_website(parse_json(rec.get("content", "")) or {}) if rec["status"] == "ok" else {}
    got = domain_of(site.get("website") or "")
    record(3, "找到官网", "通过" if got.endswith(EXPECTED_SITE) else "失败",
           f"{site.get('website')} (期望 {EXPECTED_SITE})" if rec["status"] == "ok" else rec.get("error"))

    # 4. 数据源
    end = date.today()
    start = end - timedelta(days=365)
    valid_items = []
    for src in ("usaspending", "courtlistener"):
        rec = call(source_messages(COMPANY, src, start, end), opts)
        if rec["status"] != "ok":
            print(f"    {src}: 调用失败 {rec.get('error')}")
            continue
        data = parse_json(rec["content"])
        items = check_source_items(data, COMPANY, src, start, end) if data else []
        good = [i for i in items if i["valid"]]
        valid_items += [(src, i) for i in good]
        flags = {}
        for i in items:
            for f in i["flags"]:
                flags[f] = flags.get(f, 0) + 1
        print(f"    {src}: 返回 {len(items)} 条, 有效 {len(good)} 条, 被标记 {flags or '无'}"
              + ("" if data else " (JSON 解析失败)"))
    record(4, "数据源上找到有效记录", "通过" if valid_items else "失败",
           f"共 {len(valid_items)} 条有效; 例: {[(s, i.get('title'), i.get('url')) for s, i in valid_items[:2]]}")

    # 5. 链接能打开
    sample = valid_items[:6]
    if sample:
        codes = [(i.get("url"), url_opens(i.get("url"))) for _, i in sample]
        opened = sum(1 for _, c in codes if c.startswith("2") or c.startswith("3"))
        record(5, "有效链接能打开", "提示", f"{opened}/{len(codes)} 能打开; " + "; ".join(f"{c} {u}" for u, c in codes))
    else:
        record(5, "有效链接能打开", "提示", "没有有效链接可检查")

    # 6. 用量
    snap = tracker.snapshot()
    record(6, "服务商报了用量", "提示",
           f"{snap.get('token_calls')} 次调用有用量, {usage_missing} 次没报; 输入 {snap.get('input_tokens_total')} / 输出 {snap.get('output_tokens_total')} token")

    # 7. 对照: 不带工具
    if not a.skip_control:
        ok_ctrl, d_ctrl = runner.preflight(llm, a.provider, a.timeout, {})
        if ok_ctrl:
            verdict = "也能答出最新新闻稿 (模型可能自带搜索, 工具参数可以不传)"
        elif ok_search:
            verdict = "答不出最新新闻稿, 而带工具时能答出 -> 工具参数确实起作用"
        else:
            verdict = "带不带工具都答不出 -> 这个 provider 现在搜不了, 检查工具写法或换 provider"
        record(7, "对照: 不带联网搜索工具", "提示", f"{verdict} - {d_ctrl}")

    failed = [r for r in results if r[2] == "失败"]
    print("\n" + ("全部关键检查通过" if not failed else f"{len(failed)} 项关键检查没通过: {[r[1] for r in failed]}"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
