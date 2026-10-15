"""结果抽查: 从 out/items.csv 里按数据源随机抽有效条目, 检查链接能不能打开, 生成人工核对表。

用来估算 GPT 联网搜索结果的编造比例。不调用模型, 也不调用任何数据源的 API, 只是打开结果里的链接。

    python obligor_research/tests/sample_for_review.py --out obligor_research/out --per-source 10 --check-urls

输出 out/review_sample.csv: 每行一条抽中的结果, 后面几列留给人工填:
  公司对吗 / 日期对吗 / 内容对吗 (填 y / n), 备注
填完后再运行一次 (加 --score) 统计准确率。
"""
import argparse
import csv
import random
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

REVIEW_COLS = ["公司对吗", "日期对吗", "内容对吗", "备注"]


def url_status(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (obligor-research review)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return str(r.status)
    except urllib.error.HTTPError as e:
        return str(e.code)
    except Exception as e:
        return type(e).__name__


def sample(out: Path, per_source: int, check_urls: bool, seed: int):
    rows = list(csv.DictReader(open(out / "items.csv", encoding="utf-8-sig")))
    valid = [r for r in rows if r.get("valid") == "True"]
    by_src = defaultdict(list)
    for r in valid:
        by_src[r["source"]].append(r)
    rng = random.Random(seed)
    picked = []
    for src, items in sorted(by_src.items()):
        picked += rng.sample(items, min(per_source, len(items)))
    for i, r in enumerate(picked, 1):
        r["链接状态"] = url_status(r["url"]) if check_urls else ""
        for c in REVIEW_COLS:
            r[c] = ""
        if check_urls:
            print(f"  [{i}/{len(picked)}] {r['链接状态']:>5} {r['source']:14} {r['url'][:90]}", flush=True)
    cols = ["obligor", "source", "event_date", "event_type", "title", "summary", "amount_usd", "identifiers", "url",
            "链接状态"] + REVIEW_COLS
    path = out / "review_sample.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(picked)
    print(f"\n有效条目 {len(valid)} 条, 抽中 {len(picked)} 条 (每个数据源最多 {per_source} 条) -> {path}")
    if check_urls and picked:
        ok = sum(1 for r in picked if r["链接状态"][:1] in "23")
        print(f"链接能打开: {ok}/{len(picked)}。打不开的可能是编造的链接, 也可能是网站拦截脚本, 需要人工确认。")
    print("请人工打开每个链接, 在最后几列填 y / n, 然后运行: --score")


def score(out: Path):
    rows = list(csv.DictReader(open(out / "review_sample.csv", encoding="utf-8-sig")))
    done = [r for r in rows if all((r.get(c) or "").strip().lower() in ("y", "n") for c in REVIEW_COLS[:3])]
    if not done:
        sys.exit("review_sample.csv 里还没有填好的行 (公司对吗 / 日期对吗 / 内容对吗 都要填 y 或 n)")
    print(f"已核对 {len(done)}/{len(rows)} 条\n")
    print(f"{'数据源':16} {'条数':>4} {'全部正确':>8} {'公司对':>6} {'日期对':>6} {'内容对':>6}")
    groups = defaultdict(list)
    for r in done:
        groups[r["source"]].append(r)
    groups["(合计)"] = done
    for src, rs in groups.items():
        c = Counter()
        for r in rs:
            ys = [(r[col].strip().lower() == "y") for col in REVIEW_COLS[:3]]
            c["all"] += all(ys)
            c["co"], c["dt"], c["ct"] = c["co"] + ys[0], c["dt"] + ys[1], c["ct"] + ys[2]
        n = len(rs)
        pct = lambda k: f"{c[k] / n:.0%}"
        print(f"{src:16} {n:>4} {pct('all'):>8} {pct('co'):>6} {pct('dt'):>6} {pct('ct'):>6}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "out")
    ap.add_argument("--per-source", type=int, default=10, help="每个数据源最多抽几条 (默认 10)")
    ap.add_argument("--check-urls", action="store_true", help="逐个打开抽中的链接, 记录 HTTP 状态")
    ap.add_argument("--seed", type=int, default=42, help="随机种子 (固定后每次抽到同一批)")
    ap.add_argument("--score", action="store_true", help="统计已人工核对的结果")
    a = ap.parse_args()
    if a.score:
        score(a.out)
    else:
        sample(a.out, a.per_source, a.check_urls, a.seed)


if __name__ == "__main__":
    main()
