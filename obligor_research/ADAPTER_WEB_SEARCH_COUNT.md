# 让 SafeChain 适配器报告每次请求的搜索次数

`obligor_research` 会统计每次请求实际搜了几次，但实际次数只在 GPT 的原始响应里（每次搜索一条 `web_search_call`）。按 contract，`llm/` 外面的代码不能读服务商的原始响应，所以要由适配器数出来，作为字段 `web_search_calls` 放到返回的 `LLMResult` 上。

我们的程序依次读取下面几个位置，哪个有值就用哪个：

- `result.web_search_calls`
- `result.usage.web_search_calls`
- 以及同名的 `web_search_requests`、`web_searches`

没报的时候，报告会注明，并改用模型自己列出的搜索词数作参考。

改动只在 `llm/adapters/safechain.py` 里，不影响其他使用这个 `llm` 包的地方。

## 1. 加一个数搜索次数的函数

放在 `llm/adapters/safechain.py` 里，比如 `_response_tool_calls` 旁边：

```python
def _count_web_search_calls(response) -> int:
    """数出一次响应里 GPT 服务端执行了几次 web search。

    LangChain / langchain-openai 不同版本放的位置不一样, 都看一遍, 按 id 去重:
      - response.content 是块列表时, 里面 type == "web_search_call" 的块 (Responses API 原始格式),
        或 type == "server_tool_call" 且 name 是 web_search 的块 (新的标准格式)
      - response.additional_kwargs["tool_outputs"] 里 type == "web_search_call" 的项 (较早版本)
      - response.response_metadata["output"] 里 type == "web_search_call" 的项
    """
    seen, count = set(), 0

    def scan(items):
        nonlocal count
        if not isinstance(items, list):
            return
        for item in items:
            get = item.get if isinstance(item, dict) else (lambda k, d=None, it=item: getattr(it, k, d))
            kind, name = get("type"), get("name")
            is_search = kind == "web_search_call" or (
                kind == "server_tool_call" and name in ("web_search", "web_search_preview"))
            if not is_search:
                continue
            key = get("id") or id(item)
            if key in seen:
                continue
            seen.add(key)
            count += 1

    scan(getattr(response, "content", None))
    scan((getattr(response, "additional_kwargs", None) or {}).get("tool_outputs"))
    scan((getattr(response, "response_metadata", None) or {}).get("output"))
    return count
```

## 2. 在返回结果前加上这个字段

找到 `chat()`（以及 `achat()`、`batch`、`abatch`，如果它们各自构造结果）里构造 `LLMResult` 的地方。在开启了联网搜索的请求上加上次数：

```python
result = LLMResult(content=..., usage=..., provider=..., model=...)   # 原来的代码
result.web_search_calls = _count_web_search_calls(response)            # response: 模型返回的消息对象
return result
```

几点说明：
- 传了 `tools=[{"type": "web_search"}]` 的请求，模型可能搜也可能不搜（`tool_choice="auto"`）。数出来是 0，说明这次没搜索就作答了，报告会单独统计这类请求。
- 没开启搜索的请求不要加这个字段，免得它们被算成"没搜索就作答"。
- 如果 `LLMResult` 是用 `slots=True` 定义的、不能动态加属性，可以给 `LLMResult`（或 `LLMUsage`）加一个可选字段 `web_search_calls: int | None = None`。我们的程序两处都会读。

## 3. 验证

先看响应里搜索记录放在哪里，确认上面的函数能数到。这是排查用的一次性命令，可以读原始响应：

```bash
python -c "
import sys; sys.path.insert(0, 'obligor_research')
from llm import chat_result
r = chat_result(None, [{'role': 'user', 'content': 'Search the web: latest US DOJ press release title and URL'}], tools=[{'type': 'web_search'}])
print('web_search_calls =', getattr(r, 'web_search_calls', None))
raw = getattr(r, 'raw', None)
print(type(raw)); print(repr(raw)[:3000])
"
```

如果 `web_search_calls` 是 `None` 或 `0`，但原始响应里明明有搜索记录，就把 `repr(raw)` 里搜索记录那一段发过来，我再调整函数。

然后跑冒烟测试，第 6b 项会显示每次调用的搜索次数：

```bash
python obligor_research/tests/test_live_websearch.py
```

## 报告里会看到什么

跑完 `run.py` 后，`out/summary.md` 里有一节"联网搜索次数"：

| 任务 | 请求数 | 总搜索次数 | 平均每次 | 中位数 | 最多 | 没搜索就作答 |
|---|---|---|---|---|---|---|
| 公司官网 | … | … | … | … | … | … |
| USAspending.gov | … | … | … | … | … | … |
| … | | | | | | |
| (合计) | … | … | … | … | … | … |

另外：
- 每个请求的次数记在 `out/results.jsonl` 的 `web_search_calls` 字段，运行时也会实时打印"搜索 N 次"。
- 搜索费用按真实次数乘以 `EVO_WEB_SEARCH_PRICE_PER_1K` 计算。
- "没搜索就作答"的请求，结果更可能来自模型记忆，建议重点抽查。
