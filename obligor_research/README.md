# Obligor 多数据源调研（GPT 联网搜索）

给定 obligor 名单，**只用 GPT 的联网搜索**（不调用本仓库 `apis/` 里的直连 API），分别在 11 个数据源里找**过去一年**的信息，外加每家公司的**官网**（及投资者关系页、新闻页）。

程序只用 `llm` 包的公开接口（contract `llm-v12`）：不写任何服务商名字，也不读服务商的原始响应。所以同一份代码在 DeepSeek 机器和 SafeChain 机器上都能跑，只要那台机器配置的 provider 开着联网搜索。

## 在另一台机器上运行

只需要 `obligor_research/` 这一个目录。那台机器上的结构：

```
code/
├── .env                  ← API key 和单价 (EVO_TOKEN_* 等)
└── obligor_research/
    ├── llm/              ← 那台机器自己的 llm 包 (不进仓库)
    ├── run.py
    ├── sources.py
    ├── tasks.py
    └── tests/
```

- **`llm/`**：程序直接从 `obligor_research/llm/` 导入，不需要额外参数。按 contract，每台机器自己提供它，已在 `.gitignore` 里。放在别处时用 `--llm-root` 指定。
- **`.env`**：`llm` 包自己只在 `llm/` 的上一级（`obligor_research/`）和 `llm/` 里找 `.env`，找不到 `code/.env`。所以程序在导入 `llm` 之前先自己加载：依次找 `obligor_research/.env` 和 `code/.env`，已有的环境变量不覆盖。运行时会打印读到了哪个文件。放在别处时用 `--env-file` 指定。
- 下面的命令都在 `code/` 目录下运行。

```bash
# 1. 准备 obligor 名单 (CSV), 格式见 obligors.example.csv
#    必需: 公司名列 (name / obligor / company 等都认)
#    可选: aliases, country, state, ticker, website, identifiers —— 越多越能区分同名公司

# 2. 先预检 + 只跑 2 家试试
python obligor_research/run.py --obligors obligors.csv --preflight --limit 2

# 3. 没问题再全量跑; 中断了直接重跑同一条命令, 已完成的不会重查
python obligor_research/run.py --obligors obligors.csv
```

常用参数：

| 参数 | 说明 |
|---|---|
| `--llm-root` | `llm/` 不在 `obligor_research/` 下时，指定包含它的目录 |
| `--env-file` | 指定 `.env`；默认依次找 `obligor_research/.env` 和 `code/.env` |
| `--provider` | 用哪个 provider；不填就用配置里的 default，或环境变量 `LLM_PROVIDER` |
| `--llm-options` | 每次调用额外传给 `chat_result` 的参数（JSON）。默认不传，因为适配器自动开启搜索；需要手动开启的机器才用 |
| `--preflight` | 先问一个只有联网搜索才答得出的问题（justice.gov 最近两周的新闻稿），确认搜索真的开着 |
| `--days` / `--end` | 时间窗，默认今天往前 365 天 |
| `--sources` | 只跑部分数据源，逗号分隔 |
| `--limit` | 只跑前 N 家 |
| `--workers` | 并发数，默认 4 |
| `--dry-run` | 不调用模型，只把提示词写到 `out/prompts.jsonl`，可以先检查 |
| `--report-only` | 不调用模型，按已有结果重新出报告 |

## 联网搜索怎么开启

那台机器的 SafeChain 适配器**默认开着 GPT 联网搜索**（`tool_choice="auto"`，由模型自己决定要不要搜），所以程序默认不传任何额外参数：

```python
chat_result(provider, messages, temperature=0, timeout=300)
```

换到需要手动开启搜索的机器，用 `--llm-options` 传。`llm` 包会把这些参数原样转给服务商（和 `providers.json` 里的 `params` 合并），例如：

```bash
--llm-options '{"tools": [{"type": "web_search"}]}'
```

跑之前先用 `--preflight` 确认搜索真的生效，没生效会直接停下。

## 统计每次请求的搜索次数

程序会记录每次请求实际搜了几次，写在 `results.jsonl` 的 `web_search_calls` 字段里。运行时会实时打印"搜索 N 次"，`summary.md` 里也有一节"联网搜索次数"，按任务列出：总次数、平均每次、中位数、最多，以及没搜索就作答的请求数。搜索费用按真实次数计算。

实际次数要由 `llm` 包的适配器从原始响应里数出来，放到 `LLMResult.web_search_calls` 上，因为 contract 规定外面的代码不能读原始响应。适配器要加的代码和验证方法见 [ADAPTER_WEB_SEARCH_COUNT.md](ADAPTER_WEB_SEARCH_COUNT.md)。适配器没报这个字段时，报告会注明，并改用模型自己列出的搜索词数作参考，这个数不一定准。

## 查哪些数据源

USAspending、SAM.gov、Grants.gov、GovInfo / 联邦公报、CourtListener、DOJ、FTC、OSHA、UCC（各州州务卿）、USPTO、财报电话会文字稿。每个数据源只认它的官方域名（见 `sources.py`）。财报电话会还会额外认公司自己的网站。

D&B、Orbis、Quartr、LexisNexis 是付费数据，在登录墙后面，联网搜索看不到，所以不查。

## 怎么防止编造

- 提示里要求：每条都要有找到它的链接；找不到就返回空列表；不能凭记忆回答。
- 程序拿到结果后逐条检查，并在 `flags` 列标出问题：
  - `off_source`：链接不在该数据源的官方域名上（比如新闻网站转述）
  - `out_of_window`：日期不在时间窗内
  - `no_url` / `no_date`：没有链接或日期
- 报告里只统计没有任何标记的**有效条目**。被标记的条目都留在 `items.csv` 里，方便人工复核。
- 模型给出的链接本身没有逐个打开验证，建议人工抽查一部分。

## 输出（`out/` 目录）

| 文件 | 内容 |
|---|---|
| `summary.md` | 各数据源：有结果的 obligor 数、有效条目数、各类被标记数、失败数；每家 obligor × 数据源的条目数矩阵；用量和费用 |
| `items.csv` | 每条结果一行：obligor、数据源、事件日期、发布日期、类型、标题、摘要、金额、相关方、编号、链接、是否有效、标记 |
| `websites.csv` | 每家公司的官网、投资者关系页、新闻页，以及判断依据 |
| `results.jsonl` | 每个请求的原始返回（含模型输出原文），用于断点续跑和排查 |
| `usage.json` | `UsageTracker.snapshot()` 的 token 用量和费用 |

## 规模和费用估算

请求数 = obligor 数 × (数据源数 + 1)。55 家 × 12 = **660 个请求**。

- 费用按那台机器的 `EVO_TOKEN_*` 单价计算。
- 搜索费用按适配器报告的真实次数，乘以 `EVO_WEB_SEARCH_PRICE_PER_1K` 计算；适配器没报次数的请求按 1 次估算。

## 注意

- 联网搜索的结果每次可能不同，同一个请求重跑可能拿到不同条目。
- 对 UCC 这种只能在州政府网站的查询表单里查的数据，搜索引擎往往收录不到，预计结果很少。
- 输出目录 `out/` 已在 `.gitignore` 里，不会提交。

## 如何测试

分三步，前一步通过再做下一步。

### 第 1 步：离线测试（不联网、不花钱，任何机器都能跑）

```bash
python obligor_research/tests/test_pipeline.py
# 或
python -m pytest obligor_research/tests/test_pipeline.py
```

用假的 `llm` 包（`tests/fake_llm/`，公开接口和 contract 一致）跑完整流程，覆盖：
- 各类校验标记：链接不在官方域名、日期不在窗口、没有链接，以及同一链接去重。
- 坏 JSON 和调用出错后的断点续跑：第二次只重试失败的请求。
- 官网结果、报告统计、演练模式。
- 不带联网搜索工具时，预检会拦下并退出。
- 真实目录布局：`code/obligor_research/llm/` 加 `code/.env`，确认能读到 `code/.env` 里的 key；没有 `.env` 时会报错退出。还会检查 `.env` 的几种写法（引号、`export`、行尾注释）。
- 抽查脚本：抽样、人工填表、打分。

### 第 2 步：联网冒烟测试（在 GPT 那台机器上，约 8～10 次调用，有少量费用）

```bash
python obligor_research/tests/test_live_websearch.py
# 指定 provider 或换联网搜索工具的写法:
python obligor_research/tests/test_live_websearch.py --provider xxx \
    --llm-options '{"tools": [{"type": "web_search"}]}'
```

用 Lockheed Martin 做测试公司（政府合同和诉讼很多，结果好判断）：

| 检查 | 不通过时 |
|---|---|
| 1. provider 可用（需要的环境变量都在） | 退出码 1 |
| 2. 联网搜索生效：能答出 justice.gov 最近两周的新闻稿 | 退出码 1 |
| 3. 找到官网 lockheedmartin.com | 退出码 1 |
| 4. 在 USAspending / CourtListener 上至少找到 1 条有效记录 | 退出码 1 |
| 5. 有效链接能打开 | 只提示（有些网站会拦截脚本） |
| 6. 服务商报了 token 用量 | 只提示 |
| 6b. 每次调用的搜索次数 | 只提示，需要适配器报告 `web_search_calls` |
| 7. 对照：不带额外参数时能不能答出最新新闻稿 | 只提示，只在传了 `--llm-options` 时做 |

第 2 项不通过，先确认适配器开着搜索；需要手动开启的机器，用 `--llm-options` 传开启参数再试。

参考：在只有 DeepSeek 的机器上跑，LiteLLM 会提示 "DeepSeek chat completions only supports function tools; dropping unsupported tool type(s) ['web_search']"，第 2 项不通过。这说明 `tools` 参数确实传到了服务商那一层，只是 DeepSeek 不支持。

### 第 3 步：小规模试跑 + 结果抽查

```bash
# 先跑 2～5 家
python obligor_research/run.py --obligors obligors.csv --preflight --limit 5

# 每个数据源随机抽 10 条有效结果, 自动检查链接能不能打开, 生成人工核对表
python obligor_research/tests/sample_for_review.py --out obligor_research/out --per-source 10 --check-urls
```

然后人工打开 `out/review_sample.csv` 里的每个链接，在最后几列填 `y` / `n`（公司对吗、日期对吗、内容对吗），再统计准确率：

```bash
python obligor_research/tests/sample_for_review.py --out obligor_research/out --score
```

会按数据源列出"全部正确"和各项的比例。准确率可以接受，再去掉 `--limit` 全量跑。

抽查脚本不调用模型，也不调用任何数据源的 API，只是打开结果里的链接。
