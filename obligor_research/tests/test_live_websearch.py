"""联网冒烟测试: 在有真实 llm 包的机器上, 用 GPT 联网搜索做几次调用, 确认整条链路能用。

会产生真实费用 (约 6~8 次调用)。每次调用最多等 --timeout 秒 (默认 180), 等待时每 30 秒打印进度;
费用超过 --max-cost (默认 $1) 就跳过剩下的调用; 每次调用后打印本次和累计的用量与费用。测试公司用 Lockheed Martin: 政府合同和诉讼都很多, 结果好判断。

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
  6b. 每次调用的搜索次数 (只提示; 需要适配器报告 web_search_calls)
  7. 对照: 不带额外参数时能不能答出最新新闻稿 (只提示; 只在传了 --llm-options 时做)
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
    ap.add_argument("--env-file", type=Path, help="指定 .env 文件; 默认依次找 obligor_research/.env 和上一级 (code/.env)")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--llm-options", default=json.dumps(runner.DEFAULT_LLM_OPTIONS))
    ap.add_argument("--timeout", type=int, default=180, help="单次调用最多等多少秒, 超过就放弃等待 (默认 180)")
    ap.add_argument("--max-cost", type=float, default=1.0, help="费用上限 (美元, 默认 1.0); 超过后跳过剩下的调用")
    ap.add_argument("--skip-control", action="store_true", help="跳过第 7 项对照调用 (省 1 次调用)")
    ap.add_argument("--show-raw", action="store_true", help="打印每次调用模型的原始回答 (排查搜索是否真的发生)")
    a = ap.parse_args(argv)
    print(f"Python: {sys.executable}")
    loaded = runner.load_env_files(a.env_file)
    print(f".env: {', '.join(loaded) if loaded else '没找到 (只用当前环境变量)'}")
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
        # contract 里 list_providers() 返回 {名字: {available, missing_env, default, ...}}; 也兼容列表形式
        provs = listed if isinstance(listed, dict) else {p.get("name"): p for p in listed}
        name = a.provider or (llm.default_provider() if hasattr(llm, "default_provider") else None)
        if not name:  # default_provider() 可能返回空: 用 list_providers 里标为 default 的, 或唯一的那个
            name = next((n for n, i in provs.items() if i.get("default")), None)
            if not name and len(provs) == 1:
                name = next(iter(provs))
        overview = ", ".join(f"{n}({'可用' if i.get('available') else '不可用'})" for n, i in provs.items()) or "无"
        if not provs:
            record(1, "provider 可用", "提示", "list_providers 不可用或为空, 跳过检查")
        elif name not in provs:
            record(1, "provider 可用", "失败", f"没有默认 provider; 已配置: {overview}。用 --provider 指定一个")
        else:
            info = provs[name]
            record(1, "provider 可用", "通过" if info.get("available") else "失败",
                   f"{name}; 缺少环境变量: {info.get('missing_env') or '无'}; 已配置: {overview}")
            a.provider = a.provider or name
    except Exception as e:
        record(1, "provider 可用", "失败", f"{type(e).__name__}: {e}")

    tracker = llm.UsageTracker()
    usage_missing = 0
    search_counts = []  # 每次调用的实际搜索次数 (适配器报告的)

    def over_budget():
        cost = tracker.snapshot().get("total_cost") or 0
        return cost >= a.max_cost

    def call(messages, options, label=""):
        nonlocal usage_missing
        if over_budget():
            print(f"    跳过 {label}: 费用已达上限 ${a.max_cost}")
            return {"status": "error", "error": "skipped: over budget"}
        rec, res = runner.call_model(llm, a.provider, messages, a.timeout, options, label=label)
        if res is not None and not tracker.add(res):
            usage_missing += 1
        n = runner.web_search_count(res) if res is not None else None
        search_counts.append(n)
        if res is not None:
            tracker.add_web_search(n if n is not None else 1)
        u = rec.get("usage") or {}
        print(f"    ({label}: {rec.get('seconds')}s, 输入 {u.get('input_tokens', '?')} / 输出 {u.get('output_tokens', '?')} token, "
              f"搜索 {n if n is not None else '?'} 次 | {runner.cost_line(tracker)})", flush=True)
        if a.show_raw:
            u = res.usage.as_dict() if res is not None and res.usage else None
            print(f"    --- 原始回答 (用量 {u}) ---\n    {(rec.get('content') or rec.get('error') or '')[:1500]}")
        return rec

    # 2. 联网搜索生效
    ok_search, detail = runner.preflight(llm, a.provider, a.timeout, opts, a.show_raw)
    record(2, f"联网搜索生效 (参数 {json.dumps(opts) if opts else '无, 适配器自动开启'})", "通过" if ok_search else "失败", detail)

    # 3. 官网
    rec = call(website_messages(COMPANY), opts, label="官网")
    site = check_website(parse_json(rec.get("content", "")) or {}) if rec["status"] == "ok" else {}
    got = domain_of(site.get("website") or "")
    record(3, "找到官网", "通过" if got.endswith(EXPECTED_SITE) else "失败",
           f"{site.get('website')} (期望 {EXPECTED_SITE})" if rec["status"] == "ok" else rec.get("error"))

    # 4. 数据源
    end = date.today()
    start = end - timedelta(days=365)
    valid_items = []
    for src in ("usaspending", "courtlistener"):
        rec = call(source_messages(COMPANY, src, start, end), opts, label=src)
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
    known = [n for n in search_counts if n is not None]
    record("6b", "每次调用的搜索次数", "提示",
           (f"适配器报告了 {len(known)}/{len(search_counts)} 次: {search_counts}, 合计 {sum(known)} 次" if known
            else "适配器没有报告搜索次数 (LLMResult 上没有 web_search_calls), 见 obligor_research/ADAPTER_WEB_SEARCH_COUNT.md"))

    # 7. 对照: 不带工具 (只有传了 --llm-options 才有意义; 适配器自动开启搜索时两次结果一样)
    if not opts:
        record(7, "对照: 不带联网搜索工具", "提示", "跳过: 没传额外参数, 搜索由适配器自动开启")
    elif not a.skip_control:
        ok_ctrl, d_ctrl = runner.preflight(llm, a.provider, a.timeout, {}, a.show_raw)
        if ok_ctrl:
            verdict = "也能答出最新新闻稿 (模型可能自带搜索, 工具参数可以不传)"
        elif ok_search:
            verdict = "答不出最新新闻稿, 而带工具时能答出 -> 工具参数确实起作用"
        else:
            verdict = "带不带工具都答不出 -> 这个 provider 现在搜不了, 检查工具写法或换 provider"
        record(7, "对照: 不带联网搜索工具", "提示", f"{verdict} - {d_ctrl}")

    hint = runner.missing_module_hint(" ".join(str(r[3]) for r in results))
    if hint:
        print("\n" + hint)
    failed = [r for r in results if r[2] == "失败"]
    print("\n" + ("全部关键检查通过" if not failed else f"{len(failed)} 项关键检查没通过: {[r[1] for r in failed]}"))
    print(runner.cost_line(tracker) + " (不含预检和对照调用)")
    if runner.ABANDONED:
        print(f"有 {len(runner.ABANDONED)} 次调用超时被放弃: {runner.ABANDONED} (服务端可能仍在处理并计费), 强制退出。", flush=True)
        import os
        os._exit(1)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
