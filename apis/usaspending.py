"""USAspending.gov — 联邦合同/拨款支出数据。文档: https://api.usaspending.gov/docs/endpoints"""
from datetime import datetime
from common import Probe

NAME = "USAspending.gov"
META = {
    "auth": "无需 API key",
    "license": "免费公开 (官方未见数据 license 声明; 代码仓库是 CC0)",
    "docs": "https://api.usaspending.gov/docs/endpoints",
    "limits": "无公开的硬性限流; limit 默认 10、最大 100 (实测报错提示); page × limit 最多 50,000 条, 再往后要用 last_record_sort_value; 搜索数据从 FY2008 (2007-10-01) 开始, 下载接口可到 FY2001",
    "how": "REST JSON, 搜索类接口全是 POST + JSON filters",
    "keyword": "支持: filters.keywords (字符串数组; 官方没写具体搜哪些字段; 旧的单数 keyword 已废弃)",
    "date": "支持: filters.time_period[{start_date,end_date,date_type}], date_type 可选 action_date / date_signed / last_modified_date / new_awards_only",
    "sources": [
        "官方: https://api.usaspending.gov/docs/endpoints (无需认证、端点列表)",
        "官方: GitHub api_contracts — https://github.com/fedspendingtransparency/usaspending-api/tree/master/usaspending_api/api_contracts (spending_by_award.md / spending_by_award_count.md / awards/last_updated.md / bulk_download/awards.md: 参数、字段名、award 类型代码)",
        "官方: .../api_contracts/search_filters.md (keywords、time_period + date_type 四种取值、最早 2007-10-01)",
        "官方: https://www.usaspending.gov/data/data-sources-download.pdf 与 about-the-data-download.pdf (每日更新、DoD/USACE 90 天延迟)",
        "实测: limit 最大 100、award_type_codes 不能跨组混用 (官方示例反而混用了)、各项过滤的总数变化",
    ],
    "notes": [
        "award_type_codes 必须同一大类: 合同 A/B/C/D, 拨款 02-05, 贷款 07/08 等, 混用会 400",
        "数据每日更新 (/api/v2/awards/last_updated/ 可查最近更新日期); 合同数据有 ~90 天 DoD 延迟发布",
        "大批量建议用 /api/v2/bulk_download/awards/ (异步生成 zip) 而不是翻页",
    ],
}
BASE = "https://api.usaspending.gov/api/v2"
FIELDS = ["Award ID", "Recipient Name", "Description", "Award Amount", "Awarding Agency",
          "Start Date", "End Date", "Last Modified Date", "Base Obligation Date", "generated_internal_id"]


def _search(p, label, kw=None, start=None, end=None, date_type="action_date"):
    filters = {"award_type_codes": ["A", "B", "C", "D"]}
    if kw:
        filters["keywords"] = [kw]
    if start:
        filters["time_period"] = [{"start_date": start, "end_date": end, "date_type": date_type}]
    else:
        filters["time_period"] = [{"start_date": "2007-10-01", "end_date": datetime.now().strftime("%Y-%m-%d")}]
    body = {"filters": filters, "fields": FIELDS, "limit": 10, "page": 1, "sort": "Award Amount", "order": "desc"}
    r, j = p.post(label, f"{BASE}/search/spending_by_award/", json=body)
    # 总数单独接口
    r2, c = p.post(label + " count", f"{BASE}/search/spending_by_award_count/", json={"filters": filters}, save=False)
    total = (c or {}).get("results", {}).get("contracts") if c else None
    return (j or {}).get("results", []), total


def run(p: Probe):
    r, j = p.get("last_updated", f"{BASE}/awards/last_updated/")
    p.check("连接", bool(r is not None and r.ok), f"数据最近更新: {j}")

    base, total0 = _search(p, "baseline")
    p.record_fields("award (search)", base[0] if base else None)

    kw = "cybersecurity"
    recs, total1 = _search(p, "keyword", kw=kw)
    p.verify_keyword(f"关键词搜索 '{kw}'", recs, kw, total0, total1)

    s, e = "2025-01-01", "2025-01-31"
    recs, total2 = _search(p, "date range", start=s, end=e, date_type="date_signed")
    p.check("时间过滤 (date_signed 2025-01)", bool(recs) and total2 is not None and total2 < total0,
            f"总数 {total0} → {total2}; 注意返回字段里的 Start Date 不等于签约日期，可以用详情接口核对")

    # 详情接口：拿到完整记录和更多时间戳
    if base:
        gid = base[0].get("generated_internal_id")
        r, d = p.get("award detail", f"{BASE}/awards/{gid}/")
        p.record_fields("award (detail)", d)
        p.check("详情接口", bool(d), f"generated_internal_id={gid}")
