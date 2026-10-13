"""
运行所有 API 测试并生成报告。

用法:
    python run_all.py                 # 全部
    python run_all.py usaspending doj # 只跑指定模块
输出:
    output/report.md      人类可读报告
    output/results.json   全部原始结果
    output/samples/       每个调用的样例返回
"""
import importlib
import json
import sys
import traceback

from common import OUT_DIR, Probe

MODULES = ["usaspending", "sam", "grants", "dnb", "orbis", "doj", "ftc", "uspto",
           "quartr", "govinfo", "courtlistener", "lexisnexis"]
ICON = {True: "✅", False: "❌", None: "⏭️"}
STATUS_TXT = {"ok": "✅ 可用", "partial": "🟡 部分可用", "needs_key": "🔑 需要 key/license",
              "blocked": "⛔ 被拦截", "rate_limited": "⏳ 被限流", "error": "❌ 出错", "unknown": "?"}


def main(selected):
    results = []
    for mod_name in selected:
        mod = importlib.import_module(f"apis.{mod_name}")
        p = Probe(mod.NAME, mod.META)
        print(f"\n{'=' * 70}\n▶ {mod.NAME}\n{'=' * 70}")
        try:
            status = mod.run(p)
        except Exception as e:  # 单个 API 出错不影响其他
            traceback.print_exc()
            p.note(f"测试脚本异常: {type(e).__name__}: {e}")
            status = "error"
        res = p.finish(status)
        print(f"  ⇒ 结论: {STATUS_TXT[res['status']]}")
        results.append(res)

    # 只跑部分模块时, 合并进已有结果, 不覆盖其他 API 的结论
    OUT_DIR.mkdir(exist_ok=True)
    old_path = OUT_DIR / "results.json"
    if old_path.exists() and set(selected) != set(MODULES):
        merged = {r["name"]: r for r in json.loads(old_path.read_text())}
        merged.update({r["name"]: r for r in results})
        order = [importlib.import_module(f"apis.{m}").NAME for m in MODULES]
        results = sorted(merged.values(), key=lambda r: order.index(r["name"]) if r["name"] in order else 99)
    (OUT_DIR / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    (OUT_DIR / "report.md").write_text(render(results))
    print(f"\n报告已写入 {OUT_DIR / 'report.md'}")


def render(results):
    L = ["# API 能力测试报告\n", "| API | 结论 | 认证 | License/费用 | 关键词 | 时间过滤 |", "|---|---|---|---|---|---|"]
    for r in results:
        m = r["meta"]
        L.append(f"| {r['name']} | {STATUS_TXT[r['status']]} | {m['auth']} | {m['license']} | {m['keyword']} | {m['date']} |")
    for r in results:
        m = r["meta"]
        L += [f"\n## {r['name']}  —  {STATUS_TXT[r['status']]}", f"_测试时间 {r['tested_at']}_\n",
              f"- **文档**: {m['docs']}", f"- **认证**: {m['auth']}", f"- **License**: {m['license']}",
              f"- **限制**: {m['limits']}", f"- **获取方式**: {m['how']}",
              f"- **关键词**: {m['keyword']}", f"- **时间**: {m['date']}"]
        if m.get("sources"):
            L.append("\n### 信息来源 (调用方式从哪来)")
            L += [f"- {src}" for src in m["sources"]]
        L.append("\n### 测试结果")
        for c in r["checks"]:
            L.append(f"- {ICON[c['passed']]} **{c['item']}** — {c['detail']}")
        if r["fields"]:
            L.append("\n### 拿到的字段 / 时间戳")
            for label, f in r["fields"].items():
                L.append(f"- **{label}** ({len(f['all_fields'])} 个字段): `{', '.join(f['all_fields'][:25])}`")
                for k, v in f["timestamp_fields"].items():
                    L.append(f"  - ⏱ `{k}` = `{v}`")
        L.append("\n### HTTP 调用")
        for c in r["calls"]:
            rate = f" · 限流头 `{c['rate_headers']}`" if c.get("rate_headers") else ""
            err = f" · `{(c.get('error') or c.get('error_body') or '')[:160]}`" if not (c.get("status") or 0) < 300 or not c.get("status") else ""
            L.append(f"- `{c['method']} {c['label']}` → **{c.get('status')}** ({c.get('elapsed_s')}s){rate}{err}")
        if r["notes"]:
            L.append("\n### 注意事项")
            L += [f"- {n}" for n in r["notes"]]
    return "\n".join(L) + "\n"


def render_only():
    """不发请求: 用 results.json 里的测试结果 + 模块里最新的 META (说明/来源) 重新生成报告。"""
    results = json.loads((OUT_DIR / "results.json").read_text())
    metas = {importlib.import_module(f"apis.{m}").NAME: importlib.import_module(f"apis.{m}").META for m in MODULES}
    for r in results:
        r["meta"] = metas.get(r["name"], r["meta"])
    (OUT_DIR / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    (OUT_DIR / "report.md").write_text(render(results))
    print(f"报告已重新生成 (未发请求): {OUT_DIR / 'report.md'}")


if __name__ == "__main__":
    if "--render-only" in sys.argv:
        render_only()
    else:
        main(sys.argv[1:] or MODULES)
