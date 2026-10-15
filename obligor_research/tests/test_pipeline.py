"""用假 llm 包把整个流程跑一遍: 校验标记、断点续跑、报告。

    python obligor_research/tests/test_pipeline.py
"""
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FAKE = HERE / "fake_llm"


def run(out, *extra):
    env = {**os.environ, "FAKE_LLM_STATE": str(out / "state.json")}
    cmd = [sys.executable, str(ROOT / "run.py"), "--obligors", str(ROOT / "obligors.example.csv"), "--out", str(out),
           "--llm-root", str(FAKE), "--end", "2026-10-15", "--sources", "usaspending,courtlistener,doj", "--workers", "2", *extra]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    return p.stdout


def main():
    out = Path(tempfile.mkdtemp())
    try:
        s1 = run(out, "--preflight")
        assert "预检 (联网搜索): 通过" in s1
        assert "还有 2 个请求没成功" in s1, s1  # Acme CourtListener 坏 JSON + Beta DOJ 出错
        s2 = run(out)
        assert "各数据源 (2 个请求)" in s2, s2      # 续跑只重试这 2 个
        assert "还有" not in s2, s2

        rows = list(csv.DictReader(open(out / "items.csv", encoding="utf-8-sig")))
        acme = {r["title"]: r for r in rows if r["source"] == "usaspending"}
        assert acme["valid award"]["valid"] == "True"
        assert acme["news site"]["flags"] == "off_source"
        assert acme["too old"]["flags"] == "out_of_window"
        assert acme["no url"]["flags"] == "no_url"
        assert "duplicate" not in acme                       # 同一链接去重
        assert any(r["source"] == "courtlistener" and r["valid"] == "True" for r in rows)

        sites = list(csv.DictReader(open(out / "websites.csv", encoding="utf-8-sig")))
        assert {s["website"] for s in sites} == {"https://www.acme.com", "https://www.beta.com"}

        summary = (out / "summary.md").read_text(encoding="utf-8")
        assert "| USAspending.gov | 1/2 | 1 | 1 | 1 | 1 |" in summary, summary
        assert "找到官网: 2/2" in summary
        assert "联网搜索: 按每次请求至少 1 次估算" in summary

        # 不带联网搜索工具时, 假 llm 拒绝 -> 预检不通过, 程序退出
        bad = Path(tempfile.mkdtemp())
        env = {**os.environ, "FAKE_LLM_STATE": str(bad / "state.json")}
        p = subprocess.run([sys.executable, str(ROOT / "run.py"), "--obligors", str(ROOT / "obligors.example.csv"),
                            "--out", str(bad), "--llm-root", str(FAKE), "--no-web-search-tool", "--preflight"],
                           capture_output=True, text=True, env=env)
        assert p.returncode != 0 and "没开联网搜索" in p.stderr + p.stdout, p.stdout + p.stderr

        dry = Path(tempfile.mkdtemp())
        s3 = subprocess.run([sys.executable, str(ROOT / "run.py"), "--obligors", str(ROOT / "obligors.example.csv"),
                             "--out", str(dry), "--dry-run"], capture_output=True, text=True).stdout
        n = len((dry / "prompts.jsonl").read_text().splitlines())
        assert n == 2 * (11 + 1), n                          # 2 家 × (11 个数据源 + 官网)
        print("全部通过")
    finally:
        shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    main()
