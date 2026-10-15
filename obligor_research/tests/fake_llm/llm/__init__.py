"""测试用的假 llm 包: 公开接口和 contract llm-v12 一样, 按提示内容返回事先设计好的结果, 不联网。"""
import json
import os
from dataclasses import dataclass, field


class ProviderError(Exception):
    pass


@dataclass
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cache_read_tokens: int = 0
    reasoning_tokens: int = 0

    def as_dict(self):
        return dict(vars(self))


@dataclass
class LLMResult:
    content: str
    usage: LLMUsage | None = None
    provider: str | None = None
    model: str | None = None


class UsageTracker:
    def __init__(self):
        self.calls, self.inp, self.out = 0, 0, 0

    def add(self, r):
        if not r.usage:
            return False
        self.calls += 1; self.inp += r.usage.input_tokens; self.out += r.usage.output_tokens
        return True

    def add_web_search(self, actions=1):
        self.searches = getattr(self, "searches", 0) + actions

    def snapshot(self):
        return {"token_calls": self.calls, "input_tokens_total": self.inp, "output_tokens_total": self.out,
                "total_token_cost": 0.0, "web_search_actions": getattr(self, "searches", 0), "total_cost": 0.0}


STATE = os.environ.get("FAKE_LLM_STATE", "/tmp/fake_llm_state.json")


def _count(key):
    """每个场景单独一个计数文件, 并发线程之间不会互相覆盖。"""
    path = f"{STATE}.{key}"
    with open(path, "a") as f:
        f.write("x")
    return os.path.getsize(path)


def chat_result(provider, messages, **options):
    if os.environ.get("FAKE_LLM_NEEDS_KEY") == "1" and not os.environ.get("FAKE_LLM_KEY"):
        raise ProviderError("LLM provider 'fake' needs FAKE_LLM_KEY in the environment")  # 模拟: .env 没读到
    if not options.get("tools") and os.environ.get("FAKE_LLM_REQUIRE_TOOLS", "1") == "1":
        raise ProviderError("web search tool not enabled")  # 模拟: 不带工具就搜不了
    user = messages[-1]["content"]
    company = user.split('"')[1]
    u = LLMUsage(1000, 200, 1200)
    if "official website" in user:
        return LLMResult(json.dumps({"website": f"https://www.{company.split()[0].lower()}.com", "evidence": "fake"}), u, "fake", "fake")
    if "justice.gov for the most recent" in user:  # 预检
        return LLMResult(json.dumps({"title": "x", "date": "2099-01-01", "url": "https://www.justice.gov/opa/pr/x"}), u)
    src = user.split("Task: search ")[1].split(" for ")[0]
    if company == "Acme Corp" and src == "USAspending.gov":
        return LLMResult("```json\n" + json.dumps({"found": True, "items": [
            {"event_date": "2026-03-01", "title": "valid award", "url": "https://www.usaspending.gov/award/X1", "amount_usd": 1000000},
            {"event_date": "2026-03-02", "title": "news site", "url": "https://www.reuters.com/x"},
            {"event_date": "2020-01-01", "title": "too old", "url": "https://www.usaspending.gov/award/OLD"},
            {"event_date": "2026-04-01", "title": "no url"},
            {"event_date": "2026-03-01", "title": "duplicate", "url": "https://www.usaspending.gov/award/X1"},
        ]}) + "\n```", u)
    if company == "Acme Corp" and src.startswith("CourtListener"):
        # 第一次返回坏 JSON, 第二次正常 -> 测试续跑只重试失败的
        if _count("acme-court") == 1:
            return LLMResult("Sorry, I could not format that.", u)
        return LLMResult(json.dumps({"found": True, "items": [
            {"event_date": "2026-05-05", "title": "Acme v. Foo", "url": "https://www.courtlistener.com/docket/1/", "identifiers": {"docket": "1:26-cv-1"}}]}), u)
    if company == "Beta Ltd" and src.startswith("US Department of Justice"):
        if _count("beta-doj") == 1:
            raise ProviderError("simulated failure")
        return LLMResult(json.dumps({"found": False, "items": []}), None)  # 不报用量
    return LLMResult(json.dumps({"found": False, "items": []}), u)
