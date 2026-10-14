"""Grants.gov — 联邦拨款机会。文档: https://www.grants.gov/api/api-guide"""
from datetime import datetime
from common import Probe

NAME = "Grants.gov"
META = {
    "auth": "search2 / fetchOpportunity 无需 key; 其他部分接口需要找 Help Desk 申请 API key (system-to-system 另有流程)",
    "license": "免费公开 (官方称 Unrestricted Access; 未见 license 声明)",
    "docs": "https://www.grants.gov/api/api-guide",
    "limits": "无公开限流数字; 官方未写 rows 上限 (实测 rows=5000 正常返回, rows=20000 失败); 每日还有完整 XML Extract (grants.gov/xml-extract, ~78MB zip) 可下载",
    "how": "POST JSON → https://api.grants.gov/v1/api/search2 , 详情 POST /v1/api/fetchOpportunity",
    "keyword": "支持: keyword (标题/描述全文); 另有 agencies / fundingCategories / eligibilities / aln (原 CFDA 编号) / oppNum 过滤",
    "date": "search2 没有日期区间参数; 只能 sortBy=openDate|desc 后在客户端按 openDate/closeDate 过滤, 或用 XML Extract",
    "sources": [
        "官方: https://www.grants.gov/api/api-guide (search2/fetchOpportunity 无需认证)",
        "官方: https://www.grants.gov/api/common/search2 (POST 地址、keyword / agencies / fundingCategories / eligibilities / aln / oppStatuses 参数、返回结构 oppHits/hitCount)",
        "官方: https://www.grants.gov/api/common/fetchopportunity (opportunityId、详情字段及时间格式)",
        "官方: https://www.grants.gov/xml-extract (每日 XML 全量导出)",
        "实测: sortBy=openDate|desc 的取值与效果、oppStatuses 默认值、rows 上限、无日期区间参数的影响",
    ],
    "notes": [
        "搜索结果日期是 MM/DD/YYYY 字符串 (无时区); 详情里 postingDate / lastUpdatedDate 有完整时间和时区 (如 EDT)",
        "oppStatuses 默认 forecasted|posted; 要查历史需显式加 closed|archived",
        "返回体里带一个 token 字段, 匿名搜索用不到, 可忽略",
    ],
}
BASE = "https://api.grants.gov/v1/api"


def _s(p, label, **body):
    body = {"rows": 25, "oppStatuses": "forecasted|posted", **body}
    r, j = p.post(label, f"{BASE}/search2", json=body)
    d = (j or {}).get("data", {})
    return d.get("oppHits", []), d.get("hitCount")


def run(p: Probe):
    recs, total0 = _s(p, "baseline")
    p.check("连接", bool(recs), f"当前开放/预告机会总数 {total0}")
    p.record_fields("opportunity (search)", recs[0] if recs else None)

    kw = "cybersecurity"
    k, total1 = _s(p, "keyword", keyword=kw)
    p.verify_keyword(f"关键词搜索 '{kw}'", k, kw, total0, total1)

    # 时间: 没有服务端参数 → 验证排序 + 客户端过滤
    srt, _ = _s(p, "sort by openDate desc", sortBy="openDate|desc", rows=50)
    dates = [x.get("openDate") for x in srt]
    from common import parse_any_date
    ds = [parse_any_date(d) for d in dates if d]
    p.check("时间排序 openDate|desc", ds == sorted(ds, reverse=True) and bool(ds), f"前3条 openDate: {dates[:3]}")
    start, end = datetime(2026, 9, 1), datetime.now()
    inside = [d for d in ds if start <= d <= end]
    p.check("时间过滤 (服务端)", None, f"无服务端参数; 客户端过滤 {start.date()}~今天 得到 {len(inside)}/{len(ds)} 条")

    # 历史数据
    _, total_all = _s(p, "include closed/archived", keyword=kw, oppStatuses="forecasted|posted|closed|archived")
    p.check("可查历史 (closed/archived)", bool(total_all and total1 is not None and total_all > total1), f"{kw}: {total1} → {total_all}")

    if recs:
        r, d = p.post("fetchOpportunity", f"{BASE}/fetchOpportunity", json={"opportunityId": int(recs[0]["id"])})
        data = (d or {}).get("data", {})
        p.record_fields("opportunity (detail)", data)
        p.check("详情接口", bool(data), f"id={recs[0]['id']}")
