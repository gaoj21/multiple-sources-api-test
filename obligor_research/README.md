# Obligor 多数据源调研（GPT 联网搜索）

给定 obligor 名单，让带联网搜索的 GPT 分别在 11 个数据源里找**过去一年**的信息，外加每家公司的**官网**（及投资者关系页、新闻页）。

程序只用 `llm` 包的公开接口（contract `llm-v12`）：不写任何服务商名字，也不读服务商的原始响应。所以同一份代码在 DeepSeek 机器和 SafeChain 机器上都能跑，只要那台机器配置的 provider 开着联网搜索。

## 在另一台机器上运行

```bash
# 1. 准备 obligor 名单 (CSV), 格式见 obligors.example.csv
#    必需: 公司名列 (name / obligor / company 等都认)
#    可选: aliases, country, state, ticker, website, identifiers —— 越多越能区分同名公司

# 2. 先预检 + 只跑 2 家试试 (在包含 llm/ 的仓库根目录运行, 或用 --llm-root 指过去)
python obligor_research/run.py --obligors obligors.csv --llm-root /path/to/repo --preflight --limit 2

# 3. 没问题再全量跑; 中断了直接重跑同一条命令, 已完成的不会重查
python obligor_research/run.py --obligors obligors.csv --llm-root /path/to/repo
```

常用参数：

| 参数 | 说明 |
|---|---|
| `--provider` | 用哪个 provider（要开着联网搜索）；不填就用配置里的 default，或环境变量 `LLM_PROVIDER` |
| `--preflight` | 先问一个只有联网搜索才答得出的问题（justice.gov 最近两周的新闻稿），确认搜索真的开着 |
| `--days` / `--end` | 时间窗，默认今天往前 365 天 |
| `--sources` | 只跑部分数据源，逗号分隔 |
| `--limit` | 只跑前 N 家 |
| `--workers` | 并发数，默认 4 |
| `--dry-run` | 不调用模型，只把提示词写到 `out/prompts.jsonl`，可以先检查 |
| `--report-only` | 不调用模型，按已有结果重新出报告 |

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
- 模型给出的链接本身没有逐个打开验证。建议抽查一部分：可以拿已实测过的直连 API 结果（本仓库 `apis/`）对比同一批公司，估算编造比例。

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
- 联网搜索本身的次数从公开接口拿不到，所以 `usage.json` 里只有 token 费用。

## 注意

- 联网搜索的结果每次可能不同，同一个请求重跑可能拿到不同条目。
- 对 UCC 这种只能在州政府网站的查询表单里查的数据，搜索引擎往往收录不到，预计结果很少。
- 输出目录 `out/` 已在 `.gitignore` 里，不会提交。

## 测试

```bash
python obligor_research/tests/test_pipeline.py
```

用假的 `llm` 包（`tests/fake_llm/`，公开接口和 contract 一致）把整个流程跑一遍，不联网、不花钱。覆盖：各类校验标记、去重、坏 JSON 和调用出错后的断点续跑、官网结果、报告统计、演练模式。
