"""UCC Filings (统一商法典担保登记) — 美国没有联邦统一来源, 各州州务卿分别登记。
免费且有 API 的: 科罗拉多州 (CO)、康涅狄格州 (CT) 的政府开放数据平台 (Socrata SODA API)。"""
from datetime import datetime
from common import Probe, env

NAME = "UCC Filings"
META = {
    "auth": "不需要 key; 可选 Socrata app token (请求头 X-App-Token, 免费注册) 以获得独立额度",
    "license": "免费公开 (州政府开放数据)",
    "docs": "https://data.colorado.gov/d/wffy-3uut  ·  https://data.ct.gov/d/xfev-8smz  ·  SODA API: https://dev.socrata.com/docs/queries/",
    "limits": "无 app token: 按 IP 共享额度, 请求过多会被限流 (返回 429, 无公布数字); 有 app token: 目前不限流 (除非被判滥用); 单次 $limit 可自定, 用 $offset 翻页",
    "how": "REST GET https://data.colorado.gov/resource/{数据集ID}.json 或 data.ct.gov/resource/xfev-8smz.json, 用 SoQL 参数 $where / $q / $order / $select / $limit",
    "keyword": "支持: $q= 全文搜索, 或 $where=upper(organizationname) like '%XXX%' (按债务人/担保权人名称)",
    "date": "支持: $where=filingdate between '2026-09-01' and '2026-09-30' (CO) / dt_accept (CT); 也能按失效日 lapsedate / dt_lapse 查",
    "sources": [
        "✅ 官方 (州政府): 科罗拉多数据集元数据 https://data.colorado.gov/api/views/wffy-3uut.json — 每天午夜后自动更新, 最早记录 1966-04-01, 来源 Colorado Department of State",
        "✅ 官方 (州政府): 康涅狄格 https://catalog.data.gov/dataset/uniform-commercial-code-ucc-lien-filings 与 data.ct.gov/d/xfev-8smz",
        "✅ 官方: https://dev.socrata.com/docs/app-tokens.html — 无 token 按 IP 限流、有 token 目前不限流、超限 429",
        "🧪 实测: 字段名 (响应头 X-SODA2-Fields)、CO 4 张表用 fileid 关联、CO 最新申报 2026-10-11 / CT 最新 2026-10-12、关键词和日期过滤结果",
        "🔶 调研 (见汇总): 其他州多为付费批量文件 (TX $65/天, KY $1,500/月 等) 或只有网页; 商业 API 有 Middesk、D&B UCC Filings",
    ],
    "notes": [
        "只覆盖 CO 和 CT 两个州 (加上 OR 每月一份上月新增); 要全国数据只能买各州批量文件或用商业 API",
        "CO 分 4 张表, 用 fileid 关联: 申报 wffy-3uut (类型、申报日、失效日)、债务人 8upq-58vz、担保权人 ap62-sav4、担保物 4am6-w6u4",
        "CT 是一张平表 (债务人 + 担保权人 + 日期), 没有担保物字段",
        "日期是 floating_timestamp (无时区), 实际只有日期精度",
    ],
}
CO = "https://data.colorado.gov/resource"
CT = "https://data.ct.gov/resource/xfev-8smz.json"


def _count(p, label, url, where=None, q=None):
    params = {"$select": "count(*) AS n"}
    if where:
        params["$where"] = where
    if q:
        params["$q"] = q
    r, j = p.get(label, url, params=params, save=False)
    return int(j[0]["n"]) if isinstance(j, list) and j else None


def run(p: Probe):
    tok = env("SOCRATA_APP_TOKEN")
    if tok:
        p.session.headers["X-App-Token"] = tok

    # ---------- Colorado
    f_url = f"{CO}/wffy-3uut.json"
    r, recs = p.get("CO filings latest", f_url, params={"$limit": 10, "$order": "filingdate DESC"})
    total = _count(p, "CO filings count", f_url)
    p.check("CO 连接 / 最新申报", bool(recs), f"总数 {total}, 最新 filingdate {recs[0]['filingdate'][:10] if recs else None}")
    p.record_fields("CO filing", recs[0] if recs else None)

    s, e = "2026-09-01", "2026-09-30"
    where = f"filingdate between '{s}T00:00:00' and '{e}T23:59:59'"
    r, d = p.get("CO filings date range", f_url, params={"$where": where, "$limit": 20, "$order": "filingdate DESC"})
    n = _count(p, "CO date count", f_url, where=where)
    p.verify_dates(f"CO 按申报日 {s}~{e}", [x.get("filingdate") for x in (d or [])],
                   datetime(2026, 9, 1), datetime(2026, 9, 30, 23, 59), total, n)

    kw = "BANK"
    sp_url = f"{CO}/ap62-sav4.json"
    w = f"upper(organizationname) like '%{kw}%'"
    r, sp = p.get("CO secured party keyword", sp_url, params={"$where": w, "$limit": 10})
    p.verify_keyword(f"CO 担保权人名称含 '{kw}'", sp or [], kw, _count(p, "CO sp total", sp_url), _count(p, "CO sp kw count", sp_url, where=w))
    p.record_fields("CO secured party", (sp or [None])[0])

    # 用 fileid 关联: 从一个担保权人出发, 拿到同一笔申报的 申报信息 + 债务人 + 担保物
    if sp:
        fid = sp[0]["fileid"]
        r, fl = p.get("CO filing by fileid", f_url, params={"fileid": fid})
        r, debt = p.get("CO debtor by fileid", f"{CO}/8upq-58vz.json", params={"fileid": fid})
        r, col = p.get("CO collateral by fileid", f"{CO}/4am6-w6u4.json", params={"fileid": fid})
        p.record_fields("CO debtor", (debt or [None])[0])
        p.record_fields("CO collateral", (col or [None])[0])
        p.check("CO 按 fileid 关联 4 张表", bool(fl) and bool(debt),
                f"fileid={fid}: 申报 {len(fl or [])} 条 ({(fl or [{}])[0].get('documenttype')}), 债务人 {len(debt or [])} 个, 担保物 {len(col or [])} 条")

    # ---------- Connecticut
    r, ct = p.get("CT latest", CT, params={"$limit": 10, "$order": "dt_accept DESC"})
    ct_total = _count(p, "CT count", CT)
    p.check("CT 连接 / 最新申报", bool(ct), f"总数 {ct_total}, 最新 dt_accept {ct[0]['dt_accept'][:10] if ct else None}")
    p.record_fields("CT filing", ct[0] if ct else None)
    w = f"dt_accept between '{s}T00:00:00' and '{e}T23:59:59' AND upper(sec_party_nm_bus) like '%{kw}%'"
    r, c2 = p.get("CT keyword+date", CT, params={"$where": w, "$limit": 20})
    n2 = _count(p, "CT keyword+date count", CT, where=w)
    p.verify_keyword(f"CT 担保权人含 '{kw}' + 2026-09", c2 or [], kw, ct_total, n2)
    p.verify_dates("CT dt_accept 2026-09", [x.get("dt_accept") for x in (c2 or [])], datetime(2026, 9, 1), datetime(2026, 9, 30, 23, 59))
