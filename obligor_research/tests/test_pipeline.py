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
        # 抽查脚本: 抽样 -> 模拟人工填表 -> 打分
        sp = subprocess.run([sys.executable, str(HERE / "sample_for_review.py"), "--out", str(out), "--per-source", "5"],
                            capture_output=True, text=True)
        assert sp.returncode == 0 and "抽中 2 条" in sp.stdout, sp.stdout + sp.stderr
        review = list(csv.DictReader(open(out / "review_sample.csv", encoding="utf-8-sig")))
        for r, ans in zip(review, (("y", "y", "y"), ("y", "n", "y"))):
            r["公司对吗"], r["日期对吗"], r["内容对吗"] = ans
        with open(out / "review_sample.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(review[0].keys()))
            w.writeheader(); w.writerows(review)
        sc = subprocess.run([sys.executable, str(HERE / "sample_for_review.py"), "--out", str(out), "--score"],
                            capture_output=True, text=True).stdout
        assert "已核对 2/2 条" in sc and "(合计)" in sc and "50%" in sc, sc
        # 真实布局: code/obligor_research/llm/ + code/.env, 不带 --llm-root
        code = Path(tempfile.mkdtemp()) / "code"
        shutil.copytree(ROOT, code / "obligor_research", ignore=shutil.ignore_patterns("out", "__pycache__", "tests"))
        shutil.copytree(FAKE / "llm", code / "obligor_research" / "llm")
        (code / ".env").write_text('FAKE_LLM_KEY="from-code-env"\nexport EXTRA_VAR=1  # 注释\nPRESET=from-file\n')
        env2 = {**os.environ, "FAKE_LLM_NEEDS_KEY": "1", "PRESET": "from-process", "FAKE_LLM_STATE": str(code / "st")}
        env2.pop("FAKE_LLM_KEY", None)
        lay = subprocess.run([sys.executable, str(code / "obligor_research" / "run.py"), "--obligors",
                              str(ROOT / "obligors.example.csv"), "--out", str(code / "out"), "--sources", "usaspending",
                              "--preflight", "--end", "2026-10-15"], capture_output=True, text=True, env=env2)
        assert lay.returncode == 0 and "预检 (联网搜索): 通过" in lay.stdout, lay.stdout + lay.stderr
        assert str(code / ".env") in lay.stdout                  # 读的是 code/.env
        # 没有 .env 时读不到 key -> 预检失败退出
        (code / ".env").unlink()
        lay2 = subprocess.run([sys.executable, str(code / "obligor_research" / "run.py"), "--obligors",
                               str(ROOT / "obligors.example.csv"), "--out", str(code / "out2"), "--preflight"],
                              capture_output=True, text=True, env=env2)
        assert lay2.returncode != 0 and "没找到" in lay2.stdout, lay2.stdout + lay2.stderr
        # .env 解析: 引号、export、行尾注释; 已有环境变量不覆盖
        sys.path.insert(0, str(ROOT))
        import run as runner
        envf = code / "t.env"
        envf.write_text('A1="q v"\nexport A2=x  # c\nA3=keep\n# A4=no\n')
        os.environ["A3"] = "process"
        runner.load_env_files(envf)
        assert (os.environ["A1"], os.environ["A2"], os.environ["A3"]) == ("q v", "x", "process")
        assert "A4" not in os.environ
        shutil.rmtree(code.parent, ignore_errors=True)

        # 冒烟测试: default_provider() 为空时从 list_providers 找到默认 provider; 缺 SDK 时给出换 Python 的提示
        env3 = {**os.environ, "FAKE_LLM_STATE": str(out / "st3"), "FAKE_LLM_MISSING_SDK": "1"}
        sm = subprocess.run([sys.executable, str(HERE / "test_live_websearch.py"), "--llm-root", str(FAKE), "--skip-control"],
                            capture_output=True, text=True, env=env3)
        assert "[通过] 1. provider 可用: fakechain" in sm.stdout, sm.stdout
        assert "缺少模块 fakechain.core.model.model" in sm.stdout and sm.returncode == 1, sm.stdout
        print("全部通过")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_pipeline():  # pytest 入口
    main()


if __name__ == "__main__":
    main()
