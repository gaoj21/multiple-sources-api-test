"""LexisNexis Data+ — 官方文档里的名字是 LexisNexis Web Services API (OData 4.0), 托管在 Nexis Data+ 开发者门户。"""
from datetime import datetime
from common import Probe, env

NAME = "LexisNexis Data+"
META = {
    "auth": "OAuth2 client_credentials: POST auth-api.lexisnexis.com/oauth/v2/token (Basic client_id:secret, form 表单, scope=http://oauth.lexisnexis.com/all) → Bearer, 24 小时有效; 凭证需要 Service-to-Service ID",
    "license": "💰 商业付费 license: 调用方承担所有 LexisNexis 费用, 能看哪些内容源取决于授权; 具体计费和再分发条款看合同",
    "docs": "https://dev.lexisnexis.com (公开可读的 API 规格; 凭证需要合同)",
    "limits": "QPS 按合同, 超出返回 429 (官方无数字); 每页默认 10 条, $top 最大 50",
    "how": "OData REST: GET services-api.lexisnexis.com/v1/News?$search=...&$filter=...&$top=...; 另有 bulk 交付 (S3/SFTP)",
    "keyword": "支持: $search= (必填; 有 Boolean 布尔检索模式, 如 antitrust AND merger; w/5 近邻语法在 API 文档里未确认)",
    "date": "支持: $filter=Date ge 2025-01-01 and Date le 2025-03-31; $orderby=Date desc",
    "sources": [
        "✅ 官方: https://dev.lexisnexis.com — Web Services API 规格文件 (公开): Introduction&Endpoint URI.yml (服务地址、token 地址)、Authorization and Authentication.yml (client_credentials 请求示例、24 小时)",
        "✅ 官方: 同门户 Filter Descriptions and Examples.yml ($filter=Date gt/le 示例、$top≤50)、News/NewsAPI.yml 与 NewsExamples.yml ($search 必填、Boolean、$orderby、$expand、value/@odata.count/ResultId、429)",
        "✅ 官方: https://www.lexisnexis.com/en-us/products/nexis-data-plus/data-delivery.page (Nexis Data+ 产品与交付方式)",
        "🔶 半官方: https://github.com/rwcuffney/lexisnexisapi (LexisNexis 集成顾问写的 Python 包)",
        "🧪 实测: token 端点无凭证 401、数据端点 498",
    ],
    "notes": [
        "端点/实体集名称 (News, LegalNews, Cases, CompanyAndFinancial ...) 取决于开通的数据集, 用 LEXIS_ENTITY 变量调整",
        "本机无凭证探测: token 端点返回 401, 数据端点返回 498 'token invalid or expired' (498 是实测, 官方文档只列了 429)",
        "返回带 Date (出版日期) 和 ResultId; 加 $expand=Document 可在同一次请求里拿到全文 (计费方式看合同)",
    ],
}
TOKEN_URL = "https://auth-api.lexisnexis.com/oauth/v2/token"


def run(p: Probe):
    base = env("LEXIS_BASE_URL", "https://services-api.lexisnexis.com/v1")
    entity = env("LEXIS_ENTITY", "News")
    cid, sec = env("LEXIS_CLIENT_ID"), env("LEXIS_CLIENT_SECRET")
    if not (cid and sec):
        p.post("no-key token probe", TOKEN_URL, data={"grant_type": "client_credentials"})
        p.get("no-key data probe", f"{base}/{entity}", params={"$search": "antitrust", "$top": 1})
        p.check("连接", None, "未配置 LEXIS_CLIENT_ID / LEXIS_CLIENT_SECRET; 端点可达 (401/498)")
        return "needs_key"
    r, j = p.post("token", TOKEN_URL, auth=(cid, sec), save=False,
                  data={"grant_type": "client_credentials", "scope": "http://oauth.lexisnexis.com/all"})
    tok = (j or {}).get("access_token")
    p.check("OAuth token", bool(tok), f"expires_in={(j or {}).get('expires_in')}")
    if not tok:
        return "needs_key"
    p.session.headers["Authorization"] = f"Bearer {tok}"

    kw = "antitrust"
    r, j = p.get("search keyword", f"{base}/{entity}", params={"$search": kw, "$top": 10, "$orderby": "Date desc"})
    recs = (j or {}).get("value", [])
    total_kw = (j or {}).get("@odata.count")
    p.record_fields(entity, recs[0] if recs else None)
    p.verify_keyword(f"$search='{kw}'", recs, kw)

    r, j = p.get("search keyword+date", f"{base}/{entity}",
                 params={"$search": kw, "$top": 10, "$filter": "Date ge 2025-01-01 and Date le 2025-03-31", "$expand": "Source"})
    recs = (j or {}).get("value", [])
    p.verify_dates("$filter Date 2025Q1", [x.get("Date") for x in recs], datetime(2025, 1, 1), datetime(2025, 3, 31, 23, 59))
