"""Moody's Orbis (原 Bureau van Dijk) — 全球 4 亿+ 公司的工商/财务/股权数据。"""
from common import Probe, env

NAME = "Moody's Orbis"
META = {
    "auth": "Header ApiToken: <token> (由 BvD/Moody's 客户经理开通, 和 Orbis 网页账号绑定)",
    "license": "💰 商业付费 license (Orbis 订阅 + API 模块单独签约), 下载量/字段范围按合同",
    "docs": "无公开官方文档 (客户专属, HTML/PDF 格式随合同提供); 公开可参考的是合作方开源集成, 见 sources",
    "limits": "按合同; 合作方 Maltego 称多数 license 约 1~10 个并发请求; match 最多 ~50 条结果; 字段名必须用 Orbis 数据字典里的代码 (可用 Companies/metadata/select 查)",
    "how": "REST JSON (api.bvdinfo.com/v1/orbis/...): Companies/match (名称匹配→BvD ID), Companies/data (WHERE + SELECT 取字段)",
    "keyword": "支持: match 接口按名称/国家/城市/网址等匹配; data 接口 WHERE 支持搜索策略 (行业、地区、规模等)",
    "date": "财务数据按年份 (如 OPRE 的各年度); 按'更新时间'增量一般需要单独的 Updates/Delivery 产品, 需和 Moody's 确认",
    "sources": [
        "🔶 半官方: CluedIn 开源 BvD 集成 https://github.com/CluedIn-io/CluedIn.Enricher.BvD (ApiToken 请求头、Companies/match 与 Companies/data 的请求体和返回结构、字段代码列表)",
        "🔶 半官方: https://documentation.cluedin.net/preparation/enricher/bvd 、 https://docs.strise.ai/technology/orbis-delegated-access/ (ApiToken 需找 BvD 客户代表)",
        "🔶 半官方: https://docs.maltego.com/support/solutions/articles/15000036595-bvd-orbis (API 权限单独开通、并发数)",
        "🔶 半官方: 英国政府 G-Cloud 采购目录中 Moody's Analytics UK 的 Orbis 条目 (价格示例、API 文档为 HTML/PDF)",
        "🧪 实测: api.bvdinfo.com/v1/orbis/* 无 token 返回 401 error.token.rejected",
        "❌ 没有任何一条能标为官方 ✅: Moody's/BvD 未公开 API 文档",
    ],
    "notes": [
        "⚠️ 本模块的请求体结构基于 BvD API 的常见形式, 不同账号版本的字段代码可能不同, 拿到 token 后先对照账号内文档调整 ORBIS_* 变量",
        "本机无 token 探测: 返回 401 {'ErrorCode': 'error.token.rejected'} — 端点可达",
        "财务字段按年份取, 例如 {\"OPRE\": {\"INDEXORYEAR\": \"0\", \"CURRENCY\": \"USD\"}}; 代码里的 CLOSDATE / UPDATED_DATE 字段名未经验证",
    ],
}


def run(p: Probe):
    base = env("ORBIS_BASE_URL", "https://api.bvdinfo.com/v1/orbis")
    tok = env("ORBIS_API_TOKEN")
    if not tok:
        p.post("no-token probe", f"{base}/Companies/data", json={})
        p.check("连接", None, "未配置 ORBIS_API_TOKEN; 端点可达, 返回 401")
        return "needs_key"
    p.session.headers["ApiToken"] = tok

    r, j = p.post("match by name", f"{base}/Companies/match",
                  json={"MATCH": {"Criteria": {"Name": "Lockheed Martin", "Country": "US"}, "Options": {"ScoreLimit": 0.8}},
                        "SELECT": ["Match.BvDId", "Match.Name", "Match.MatchedName", "Match.City", "Match.Country",
                                   "Match.Score", "Match.Hint"]})
    # match 接口直接返回 JSON 数组; data 接口返回 {"SearchSummary":..., "Data":[...]}
    data = j if isinstance(j, list) else (j or {}).get("Data", [])
    p.record_fields("match", data[0] if data else None)
    p.check("名称匹配 → BvD ID", bool(data), f"{len(data)} 个候选")

    if data:
        bvd = data[0].get("BvDId") or data[0].get("Match.BvDId") or data[0].get("BVDID")
        r, j = p.post("company data", f"{base}/Companies/data",
                      json={"WHERE": [{"BvDID": [bvd]}],
                            "SELECT": ["BVDID", "NAME", "COUNTRY_ISO_CODE", "NACE2_MAIN_SECTION", "OPRE", "EMPL", "CLOSDATE", "UPDATED_DATE"]})
        d = j if isinstance(j, list) else (j or {}).get("Data", [])
        p.record_fields("company data", d[0] if d else None)
        p.check("按 BvD ID 取字段", bool(d), f"BvDID={bvd}; 字段代码不对时会返回 400 并提示")
    p.check("按时间查询", None, "需按合同确认 (Updates 产品)")
