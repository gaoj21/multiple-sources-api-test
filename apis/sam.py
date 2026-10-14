"""SAM.gov — 合同机会 (Opportunities)、实体注册 (Entity)、排除名单 (Exclusions)。文档: https://open.gsa.gov/api/"""
from datetime import datetime
from common import Probe, env

NAME = "SAM.gov"
META = {
    "auth": "需要 SAM.gov 账号里生成的 API key (Account Details → Public API Key); 通用 api.data.gov key / DEMO_KEY 无效",
    "license": "免费 (官方未写价格, 未见收费说明); 实体数据分级: Public / FOUO (联系人邮箱电话、层级, 需 Read FOUO 角色) / Sensitive (TIN/EIN/银行信息, 需联邦 System Account + Read Sensitive)",
    "docs": "https://open.gsa.gov/api/get-opportunities-public-api/  ·  https://open.gsa.gov/api/entity-api/",
    "limits": "非联邦个人 key: 无角色 10 次/天, 在 SAM 有任意角色 1,000 次/天; 联邦 system account 10,000 次/天 (Entity/Exclusions 文档); 使用条款要求每 90 天更新 key; Opportunities limit≤1000/页, Exclusions size 1~10",
    "how": "REST JSON GET: /opportunities/v2/search, /entity-information/v3/entities, /entity-information/v4/exclusions; 批量用 Extracts (每日/每月文件)",
    "keyword": "Opportunities: title= (标题), solnum/noticeid/ncode(NAICS)/organizationName; Entity: legalBusinessName / q= 自由文本 / ueiSAM / cageCode",
    "date": "Opportunities: postedFrom & postedTo 必填 (MM/dd/yyyy, 跨度≤1年), 另有 rdlfrom/rdlto (截止日); Entity: registrationDate / updateDate 等支持 [from,to] 区间",
    "sources": [
        "官方: https://open.gsa.gov/api/get-opportunities-public-api/ (端点、title/solnum/ncode 等参数、postedFrom/To 必填且≤1年、limit≤1000、description 需追加 api_key)",
        "官方: https://open.gsa.gov/api/entity-api/ (v3/v4 端点、legalBusinessName / q / registrationDate=[from,to]、限流表 10/1000/10000 每天、数据分级)",
        "官方: https://open.gsa.gov/api/exclusions-api/ (v4 端点、q、size 1~10)",
        "官方: https://sam.gov/about/terms-of-use (每 90 天更新 API key)",
        "实测: DEMO_KEY 返回 404, SAM 账号生成的 key 返回 200 → 必须用 SAM 自己的 key (官方没有明说)",
        "实测 (2026-10-13): 有效 key 下 Opportunities 日期过滤 10/10 在区间内、title 关键词 15236 → 4、Entity 和 Exclusions 都正常; 响应头里没有限流信息, 额度只能自己记"
    ],
    "notes": [
        "无 key / 无效 key 时 api.sam.gov 所有路径都返回空 body 的 404 (不是 401/403, 容易误判为地址错误); 带有效 key 从新加坡 IP 访问完全正常, 不限制非美 IP",
        "时间字段: Opportunities 有 postedDate/responseDeadLine/archiveDate/award.date (只有日期); Entity 有 registrationDate/lastUpdateDate/registrationExpirationDate; Exclusions 是 MM-DD-YYYY 格式的 createDate/updateDate/activateDate/terminationDate; description 字段只是一个需要再带 api_key 请求的链接",
        "10 次/天 的额度非常少, 生产使用一定要申请 entity 角色或用 Extracts 批量文件",
    ],
}
BASE = "https://api.sam.gov"


def run(p: Probe):
    key = env("SAM_API_KEY")
    if not key:
        p.get("no-key probe", f"{BASE}/opportunities/v2/search", params={"limit": 1, "postedFrom": "10/01/2026", "postedTo": "10/10/2026"})
        p.check("连接", None, "未配置 SAM_API_KEY, 仅做无 key 探测 (见上方状态码)")
        return "needs_key"
    p.note("注意: 每次运行消耗 4 次调用 (无角色 key 每天只有 10 次)")

    fmt = lambda d: d.strftime("%m/%d/%Y")
    s, e = datetime(2026, 9, 1), datetime(2026, 9, 30)
    base_p = {"api_key": key, "limit": 10, "postedFrom": fmt(s), "postedTo": fmt(e)}
    r, j = p.get("opportunities (date range)", f"{BASE}/opportunities/v2/search", params=base_p)
    recs, total0 = (j or {}).get("opportunitiesData", []), (j or {}).get("totalRecords")
    p.check("连接", bool(r is not None and r.ok), f"2026-09 发布的机会总数 {total0}")
    p.record_fields("opportunity", recs[0] if recs else None)
    p.verify_dates("时间 postedFrom/postedTo", [x.get("postedDate") for x in recs], s, e.replace(hour=23, minute=59))

    kw = "cybersecurity"
    r, j = p.get("opportunities keyword", f"{BASE}/opportunities/v2/search", params={**base_p, "title": kw})
    p.verify_keyword(f"标题关键词 title='{kw}'", (j or {}).get("opportunitiesData", []), kw, total0, (j or {}).get("totalRecords"))

    r, j = p.get("entity search", f"{BASE}/entity-information/v3/entities", params={"api_key": key, "legalBusinessName": "Lockheed Martin"})
    ent = (j or {}).get("entityData", [])
    p.record_fields("entity", ent[0] if ent else None)
    p.check("Entity 按名称搜索", bool(ent), f"totalRecords={(j or {}).get('totalRecords')}")

    r, j = p.get("exclusions", f"{BASE}/entity-information/v4/exclusions", params={"api_key": key, "q": "fraud", "size": 5})
    ex = (j or {}).get("excludedEntity", [])
    p.record_fields("exclusion", ex[0] if ex else None)
    p.check("Exclusions (排除/禁止名单)", bool(r is not None and r.ok), f"totalRecords={(j or {}).get('totalRecords')}")
