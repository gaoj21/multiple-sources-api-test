"""D&B Direct+ — 邓白氏企业数据 (DUNS, 公司信息, 股权/族谱, 财务, 风险评分)。文档: https://directplus.documentation.dnb.com"""
import base64
from common import Probe, env

NAME = "D&B Direct+"
META = {
    "auth": "OAuth2 client_credentials: Basic base64(key:secret) → POST /v3/token (form 表单 grant_type=client_credentials) 拿 access_token (24 小时有效), 之后 Bearer; 旧版 /v2/token 用 JSON body",
    "license": "💰 商业付费 license: key/secret 只能找 D&B 客户代表开通, 按产品/Data Block 授权 (companyinfo L1 是所有 block 的起点); 每次调用计入合同配额",
    "docs": "https://directplus.documentation.dnb.com (除首页外现在都要 D&B 账号登录)",
    "limits": "TPS 和 周/月/年配额都按合同 (官方无默认数字), 超出返回 429 (errorCode 0045/0046), 配额每天 UTC 0 点重置; 未开通的产品返回 401 errorCode 00004",
    "how": "REST JSON: /v1/match/cleanseMatch (名称+地址→DUNS), /v1/search/criteria (条件搜索), /v1/data/duns/{duns}?blockIDs=... (数据块)",
    "keyword": "支持: search/criteria 的 searchTerm (公司名/关键词) 及 industry/地域等条件; typeahead 可前缀匹配",
    "date": "❗不支持按时间查询; 变化追踪要用 Monitoring (订阅 DUNS 后推送变更通知) ",
    "sources": [
        "✅ 官方 (Wayback 存档, 因现在需登录): directplus.documentation.dnb.com/html/pages/Authentication.html — 2024-11 版 /v3/token、form body、24 小时、错误码 00004/00040; 2022 版 /v2/token",
        "✅ 官方 (Wayback 存档 2024-01): .../html/pages/UsingDplusAPIs.html — 配额按合同、429 错误码 0045/0046",
        "✅ 官方 (Wayback 存档 2025-01): .../html/resources/JSONSample_IDR.html 与 JSONSample_Search.html — cleanseMatch、search/criteria、typeahead 的请求和返回字段",
        "✅ 官方 (Wayback 存档): companyinfo_L2_v1.json swagger (data/duns + blockIDs)、StandardDataBlocks、Monitoring 页面",
        "🧪 实测: 无凭证请求 token 返回 401 'not currently authorised' (= 官方错误码 00004)",
        "⚠️ 未用真实凭证跑过; 官方文档最新只看到 2024-11 的存档",
    ],
    "notes": [
        "每个响应都带 transactionDetail.transactionTimestamp (调用时间); 数据块里各元素带 lastUpdatedDate",
        "Data Block 命名规则: companyinfo_L2_v1, hierarchyconnections_L1_v1, financialstrengthinsight_L2_v1 … (Level 越高内容越多; 价格官方未公开)",
        "本机无凭证探测: POST /v2/token 返回 401 'You are not currently authorised to access this product' — 端点可达",
    ],
}
BASE = "https://plus.dnb.com"


def run(p: Probe):
    k, s = env("DNB_API_KEY"), env("DNB_API_SECRET")
    if not (k and s):
        p.post("no-key token probe", f"{BASE}/v2/token", json={"grant_type": "client_credentials"})
        p.check("连接", None, "未配置 DNB_API_KEY / DNB_API_SECRET; 端点可达, 返回 401")
        return "needs_key"
    basic = base64.b64encode(f"{k}:{s}".encode()).decode()
    r, j = p.post("token v3", f"{BASE}/v3/token", data={"grant_type": "client_credentials"},
                  headers={"Authorization": f"Basic {basic}"}, save=False)
    if r is not None and r.status_code == 404:  # 老账号可能还在 v2
        r, j = p.post("token v2 (legacy)", f"{BASE}/v2/token", json={"grant_type": "client_credentials"},
                      headers={"Authorization": f"Basic {basic}"}, save=False)
    tok = (j or {}).get("access_token") or (j or {}).get("accessToken")
    p.check("OAuth token", bool(tok), f"expires_in={(j or {}).get('expires_in') or (j or {}).get('expiresIn')}")
    if not tok:
        return "needs_key"
    p.session.headers["Authorization"] = f"Bearer {tok}"

    r, j = p.get("cleanseMatch", f"{BASE}/v1/match/cleanseMatch", params={"name": "Lockheed Martin", "countryISOAlpha2Code": "US"})
    cands = (j or {}).get("matchCandidates", [])
    p.record_fields("match candidate", cands[0] if cands else None)
    p.check("名称匹配 → DUNS", bool(cands), f"{len(cands)} 个候选, top confidence={cands[0].get('matchQualityInformation', {}).get('confidenceCode') if cands else None}")

    kw = "cybersecurity"
    r, j = p.post("search criteria", f"{BASE}/v1/search/criteria", json={"searchTerm": kw, "countryISOAlpha2Code": "US", "pageSize": 10})
    hits = (j or {}).get("searchCandidates", [])
    p.check(f"关键词搜索 searchTerm='{kw}'", bool(hits), f"candidatesMatchedQuantity={(j or {}).get('candidatesMatchedQuantity')}")

    if cands:
        duns = cands[0].get("organization", {}).get("duns")
        r, j = p.get("data block companyinfo_L2", f"{BASE}/v1/data/duns/{duns}", params={"blockIDs": "companyinfo_L2_v1"})
        p.record_fields("companyinfo_L2_v1", j)
        p.check("Data Block 获取", bool(r is not None and r.ok), f"DUNS={duns}; 未开通的 block 会返回错误码")
    p.check("按时间查询", None, "API 不支持, 需用 Monitoring 推送")
