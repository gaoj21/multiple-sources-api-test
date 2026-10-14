"""OSHA (美国职业安全与健康管理局) 执法数据 — 通过劳工部 DOL 开放数据 API v4。文档: https://dataportal.dol.gov/api-guide"""
import json
from datetime import datetime
from common import Probe, env

NAME = "OSHA"
META = {
    "auth": "免费 DOL API key (在 dataportal.dol.gov/registration 注册并填问卷后生成, 最多 5 个); 参数 X-API-KEY; 数据集目录 /v4/datasets 无需 key",
    "license": "免费公开 (美国政府数据)",
    "docs": "https://dataportal.dol.gov/api-guide  ·  用户指南 PDF: https://dataportal.dol.gov/pdf/dol-api-user-guide.pdf",
    "limits": "单次最多 10,000 条或 5 MB (先到为准), limit 默认 10, 用 offset 翻页; 官方未写频率限制, 但实测约 10 分钟内 20 多个请求后开始返回 429 (无限流响应头、无 Retry-After), 过一阵自动恢复 → 请求间隔 ≥ 3 秒; 禁止把 key 公开到代码仓库或论坛",
    "how": "REST GET https://apiprod.dol.gov/v4/get/OSHA/{表名}/json?X-API-KEY=...; 元数据 /json/metadata; 另支持 csv / xml 格式",
    "keyword": "支持: filter_object 用 like 运算符做模糊匹配, 如 {\"field\":\"estab_name\",\"operator\":\"like\",\"value\":\"%WALMART%\"}",
    "date": "支持: filter_object 用 gt / lt 比较日期字段 (如 open_date), 可用 and/or 组合; sort + sort_by 排序",
    "sources": [
        "官方: https://dataportal.dol.gov/pdf/dol-api-user-guide.pdf (2024-08-05 版): 注册拿 key、请求模板、limit/offset/fields/sort/sort_by/filter_object、运算符 eq/neq/gt/lt/in/not_in/like、10,000 条或 5MB 上限、禁止公开 key",
        "官方: https://apiprod.dol.gov/v4/datasets (无需 key, 实测可访问): OSHA 有 11 张表",
        "实测: 无 key 请求数据返回 401 'The API key is either incorrect or missing'",
        "实测 (有 key): 公司名 like 过滤、open_date 区间、load_dt 增量、违规表 → 检查表关联都有效; 连续请求会触发 429",
        "官方: /json/metadata 字段说明 (实测可读): 每个字段的名称、描述、类型、关联表",
    ],
    "notes": [
        "OSHA 的 11 张表: inspection (检查)、violation (违规)、violation_event、violation_gen_duty_std、accident (事故)、accident_abstract、accident_injury、accident_lookup2、related_activity、emphasis_codes、optional_code_info",
        "表之间用 activity_nr (检查编号) 关联: 先按公司名查 inspection, 再用 activity_nr 查 violation 拿罚款",
        "OSHA 原来的 enforcedata.dol.gov 已跳转到 data.dol.gov",
    ],
}
BASE = "https://apiprod.dol.gov/v4"


def _get(p, label, table, key, **params):
    if "filter_object" in params and not isinstance(params["filter_object"], str):
        params["filter_object"] = json.dumps(params["filter_object"])
    r, j = p.get(label, f"{BASE}/get/OSHA/{table}/json", params={"X-API-KEY": key, **params}, timeout=90)
    recs = j.get("data", j) if isinstance(j, dict) else (j or [])
    return r, (recs if isinstance(recs, list) else [])


def run(p: Probe):
    r, j = p.get("dataset catalog (no key)", f"{BASE}/datasets", params={"limit": 500})
    osha = [d["tablename"] for d in (j or {}).get("datasets", []) if (d.get("agency") or {}).get("abbr") == "OSHA"]
    p.check("数据集目录 (无需 key)", bool(osha), f"OSHA 表 {len(osha)} 张: {osha}")

    key = env("DOL_API_KEY")
    p.min_interval = 3  # 实测: 短时间连续请求会被 429 (无限流响应头), 隔一会自动恢复
    if not key:
        p.get("no-key probe", f"{BASE}/get/OSHA/inspection/json", params={"limit": 1})
        p.check("数据接口", None, "未配置 DOL_API_KEY; 返回 401")
        return "needs_key"

    r, meta = p.get("inspection metadata", f"{BASE}/get/OSHA/inspection/json/metadata", params={"X-API-KEY": key})
    cols = {m.get("short_name") for m in (meta or []) if isinstance(m, dict)}
    p.check("元数据 (字段说明)", bool(cols), f"inspection 表 {len(cols)} 个字段; 每个字段有名称、描述、类型、关联表")
    name_f = "estab_name" if "estab_name" in cols else None
    date_f = "open_date" if "open_date" in cols else None

    r, recs = _get(p, "inspection latest", "inspection", key, limit=10, sort="desc", sort_by=date_f or "activity_nr")
    p.check("连接 / 最新检查记录", bool(recs), f"返回 {len(recs)} 条, 最新 open_date {recs[0].get('open_date') if recs else None}")
    p.record_fields("inspection", recs[0] if recs else None)

    if name_f:
        kw = "WALMART"
        r, k = _get(p, "keyword (estab_name like)", "inspection", key, limit=20,
                    filter_object={"field": name_f, "operator": "like", "value": f"%{kw}%"})
        p.verify_keyword(f"公司名模糊匹配 '{kw}'", k, kw)
    if date_f:
        r, d = _get(p, "date range (open_date)", "inspection", key, limit=20, sort="desc", sort_by=date_f,
                    filter_object={"and": [{"field": date_f, "operator": "gt", "value": "2025-01-01"},
                                           {"field": date_f, "operator": "lt", "value": "2025-01-31"}]})
        p.verify_dates("open_date 2025-01", [x.get(date_f) for x in d], datetime(2025, 1, 1), datetime(2025, 1, 31, 23, 59))
    if "load_dt" in cols:
        r, inc = _get(p, "incremental (load_dt)", "inspection", key, limit=20, sort="desc", sort_by="load_dt",
                      filter_object={"field": "load_dt", "operator": "gt", "value": "2026-10-01"})
        p.verify_dates("增量 load_dt > 2026-10-01 (入库时间)", [x.get("load_dt") for x in inc], datetime(2026, 10, 1), datetime(2100, 1, 1))

    # 违规表: 取最新的违规, 再用 activity_nr 回查是哪次检查
    r, v = _get(p, "violation latest", "violation", key, limit=10, sort="desc", sort_by="activity_nr")
    p.record_fields("violation", v[0] if v else None)
    p.check("违规表 (violation)", bool(v), f"返回 {len(v)} 条")
    if v:
        r, back = _get(p, "inspection of a violation", "inspection", key, limit=1,
                       filter_object={"field": "activity_nr", "operator": "eq", "value": str(v[0]["activity_nr"])})
        p.check("按 activity_nr 关联 违规 → 检查", bool(back),
                f"activity_nr={v[0]['activity_nr']} → {back[0].get('estab_name') if back else None}")
    r, acc = _get(p, "accident latest", "accident", key, limit=5, sort="desc", sort_by="event_date")
    p.record_fields("accident", acc[0] if acc else None)
    p.check("事故表 (accident)", r is not None and r.ok, f"返回 {len(acc)} 条")
