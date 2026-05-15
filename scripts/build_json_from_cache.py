#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_json_from_cache.py — 从缓存自动组装/更新 web-platform JSON

用法：
    python3 skills/fund-deep-research/scripts/build_json_from_cache.py <基金代码>

功能：
    1. 读取 /tmp/fund_research_{code}/raw/ 下所有缓存文件
    2. 将 A类字段（可确定性提取）映射到 web-platform/public/data/{code}.json
    3. 保留 JSON 中已有的 B类字段（由 AI/人工填写，不覆盖）
    4. 输出变更摘要

字段分类：
    A类（本脚本自动填写）：basic / fees / scale / risk / holdings.top10 /
                          performance.stages / performance.annual / performance.quarterly /
                          stageAnalysis.inflectionPoints / navHistory /
                          managers.current（name/id/scale/count等）
    B类（保留已有，不覆盖）：policy / exclusionCheck / scoring / tracking /
                           stageAnalysis.stages[].description/env/managerAction /
                           managers.current.philosophy / consistencyAudit / abilityProfile /
                           holdings.themeGroups / evolutionHighlights / policyLinks /
                           performance.milestones / company.complianceChecks
"""

import json
import os
import re
import sys
from datetime import date, datetime
from typing import Optional, Union

# ─── 路径配置 ──────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../.."))
DATA_DIR = os.path.join(REPO_ROOT, "web-platform/public/data")
DEFAULT_DISCLAIMER = (
    "本报告仅供个人学习和信息整理使用，所有分析内容均不构成任何投资建议。"
    "投资有风险，入市需谨慎，请依据自身判断做出投资决策。"
)
NAV_HISTORY_FALLBACK_LIMIT = 90

REDEMPTION_RULE_LABELS = {
    "rule_lt_7d": "持有少于7天",
    "rule_ge_7d": "持有7天及以上",
    "rule_7d_to_30d": "持有7天至30天",
    "rule_30d_to_1y": "持有30天至1年",
    "rule_1y_to_2y": "持有1年至2年",
    "rule_ge_2y": "持有2年及以上",
}


def load_cache(tmp: str, fname: str):
    """安全加载缓存文件，失败返回 None"""
    path = os.path.join(tmp, fname)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  加载 {fname} 失败：{e}", file=sys.stderr)
        return None


def load_existing_json(code: str) -> dict:
    """加载已有的 JSON，不存在则返回空骨架"""
    path = os.path.join(DATA_DIR, f"{code}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"id": code}


def save_json(code: str, data: dict):
    path = os.path.join(DATA_DIR, f"{code}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅  已写入 {path}")


def first_non_none(*values):
    for value in values:
        if value is not None:
            return value
    return None


def parse_percentage(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)

    text = str(value).strip()
    if not text or text in {"--", "—", "N/A", "---（每年）"}:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text.replace(',', ''))
    if not match:
        return None
    return round(float(match.group(0)), 2)


def parse_numeric_text(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 4)

    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(',', ''))
    if not match:
        return None
    return round(float(match.group(0)), 4)


def normalize_date_string(value):
    if not value:
        return None

    text = str(value).strip()
    if not text:
        return None

    iso_match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
    if iso_match:
        return f"{iso_match.group(1)}-{iso_match.group(2)}-{iso_match.group(3)}"

    cn_day_match = re.match(r"^(\d{4})年(\d{1,2})月(\d{1,2})日", text)
    if cn_day_match:
        return f"{cn_day_match.group(1)}-{int(cn_day_match.group(2)):02d}-{int(cn_day_match.group(3)):02d}"

    quarter_match = re.match(r"^(\d{4})年([1-4])季度", text)
    if quarter_match:
        quarter_end = {"1": "03-31", "2": "06-30", "3": "09-30", "4": "12-31"}
        return f"{quarter_match.group(1)}-{quarter_end[quarter_match.group(2)]}"

    return None


def split_fund_type(value):
    text = (value or "").strip()
    if not text:
        return None, None
    if "-" not in text:
        return text, None
    main_type, sub_type = text.split("-", 1)
    return main_type.strip(), sub_type.strip() or None


def combine_status(purchase_status, redemption_status):
    purchase = (purchase_status or "").strip()
    redemption = (redemption_status or "").strip()
    if purchase and redemption:
        return f"{purchase} / {redemption}"
    return purchase or redemption or None


def build_fee_breakdown(fe: dict):
    management = parse_percentage(fe.get("management_fee"))
    custodian = parse_percentage(fe.get("custodian_fee"))
    sales_service = parse_percentage(fe.get("sales_service_fee"))
    subscription_max = parse_percentage(fe.get("purchase_fee_original"))
    subscription_discounted = parse_percentage(fe.get("purchase_fee_discounted"))

    breakdown = []
    if management is not None:
        breakdown.append({"name": "管理费", "value": management})
    if custodian is not None:
        breakdown.append({"name": "托管费", "value": custodian})
    if sales_service is not None:
        breakdown.append({"name": "销售服务费", "value": sales_service})
    if subscription_max is not None or subscription_discounted is not None:
        item = {"name": "申购费", "value": first_non_none(subscription_max, 0)}
        if subscription_discounted is not None:
            item["actualRate"] = subscription_discounted
        breakdown.append(item)

    redemption_rules = fe.get("redemption_rules")
    redemption_max = None
    if isinstance(redemption_rules, dict):
        rules = []
        for key, raw_value in redemption_rules.items():
            if key == "note":
                continue
            rate = parse_percentage(raw_value)
            if rate is None:
                continue
            redemption_max = rate if redemption_max is None else max(redemption_max, rate)
            rules.append({
                "label": REDEMPTION_RULE_LABELS.get(key, key),
                "rate": rate,
            })
        if redemption_max is not None:
            item = {
                "name": "赎回费",
                "value": redemption_max,
                "rate": redemption_max,
            }
            if rules:
                item["rules"] = rules
            if redemption_rules.get("note"):
                item["note"] = redemption_rules["note"]
            breakdown.append(item)

    return {
        "management": management,
        "custodian": custodian,
        "salesService": sales_service,
        "subscriptionMax": subscription_max,
        "subscriptionDiscounted": subscription_discounted,
        "redemptionMax": redemption_max,
        "breakdown": breakdown,
    }


def resolve_data_date(fe: Optional[dict], ho: Optional[dict], nd: Optional[dict]) -> Optional[str]:
    candidates = [
        normalize_date_string((fe or {}).get("current_nav_date")),
        normalize_date_string((ho or {}).get("report_date")),
    ]

    nav_data = (nd or {}).get("nav_data") or []
    if nav_data:
        candidates.append(normalize_date_string(nav_data[-1].get("date")))

    candidates = [candidate for candidate in candidates if candidate]
    return max(candidates) if candidates else None


# ─── 各模块映射函数 ─────────────────────────────────────────────────────────

def map_basic(fe: dict) -> dict:
    """fund_enhanced.json → basic + fees + scale"""
    risk_code_map = {"R1": 1, "R2": 2, "R3": 3, "R4": 4, "R5": 5}
    risk_level = fe.get("risk_level", "")
    risk_code = next((v for k, v in risk_code_map.items() if k in risk_level), None)
    fund_type, sub_type = split_fund_type(fe.get("fund_type"))

    basic = {
        "code": fe.get("fund_code"),
        "fullName": fe.get("full_name"),
        "shortName": fe.get("short_name"),
        "type": fund_type or fe.get("fund_type"),
        "subType": sub_type,
        "riskLevel": risk_level,
        "riskCode": risk_code,
        "foundDate": fe.get("found_date"),
        "manager": fe.get("company_name"),
        "companyShort": (fe.get("company_name") or "").replace("基金管理有限公司", "基金"),
        "custodian": fe.get("custodian"),
        "benchmark": fe.get("benchmark"),
        "navFallback": fe.get("current_nav"),
        "navDateFallback": normalize_date_string(fe.get("current_nav_date")) or fe.get("current_nav_date"),
        "inceptionReturn": parse_percentage(fe.get("return_since_inception")),
        "status": combine_status(fe.get("purchase_status"), fe.get("redemption_status")),
    }

    fees = build_fee_breakdown(fe)

    return basic, fees


def map_scale(fe: dict) -> dict:
    """基金规模 → scale"""
    return {
        "nav": parse_numeric_text(fe.get("fund_scale")),
        "date": normalize_date_string(fe.get("current_nav_date")) or fe.get("current_nav_date"),
    }


def map_risk(rk: dict, rm: dict, nav_data: list) -> dict:
    """risk_metrics + relative_metrics → risk（仅 A类字段）"""
    yearly_fund = {
        int(item.get("year")): item.get("fund")
        for item in (rk.get("yearly_drawdowns") or [])
        if item.get("year") is not None and item.get("fund") is not None
    }
    yearly_benchmark = {
        int(item.get("year")): item.get("hs300")
        for item in ((rm or {}).get("benchmark_yearly_drawdowns") or [])
        if item.get("year") is not None and item.get("hs300") is not None
    }
    chart_years = sorted(yearly_fund, reverse=True) if yearly_fund else sorted(yearly_benchmark, reverse=True)
    yearly_max_drawdowns = [
        {
            "year": year,
            "fund": yearly_fund.get(year),
            "hs300": yearly_benchmark.get(year),
        }
        for year in chart_years
        if yearly_fund.get(year) is not None or yearly_benchmark.get(year) is not None
    ]

    risk = {
        "volatility": rk.get("volatility"),
        "annualReturn": rk.get("annual_return"),
        "sharpe": rk.get("sharpe_ratio"),
        "calmar": rk.get("calmar_ratio"),
        "maxDrawdown": rk.get("max_drawdown"),
        "maxDrawdownPeriod": f"{rk.get('max_drawdown_peak_date')} → {rk.get('max_drawdown_trough_date')}",
        "periodMetrics": [
            {"label": "近1年", "volatility": rk.get("volatility_1y"), "sharpe": rk.get("sharpe_1y"), "maxDrawdown": rk.get("max_drawdown_1y")},
            {"label": "近2年", "volatility": rk.get("volatility_2y"), "sharpe": rk.get("sharpe_2y"), "maxDrawdown": rk.get("max_drawdown_2y")},
            {"label": "近3年", "volatility": rk.get("volatility_3y"), "sharpe": rk.get("sharpe_3y"), "maxDrawdown": rk.get("max_drawdown_3y")},
        ],
    }
    if yearly_max_drawdowns:
        risk["riskBreakdown"] = {
            "yearlyMaxDrawdowns": yearly_max_drawdowns,
        }
    if rm:
        risk["relativeMetrics"] = {
            "beta": rm.get("beta"),
            "alpha": rm.get("alpha_annualized"),
            "informationRatio": rm.get("information_ratio"),
            "trackingError": rm.get("tracking_error_annualized"),
            "r2": rm.get("r_squared"),
        }
    # 历史分位
    if nav_data:
        navs = [n["nav"] for n in nav_data if n.get("nav")]
        latest_nav = navs[-1] if navs else None
        if latest_nav and navs:
            below = sum(1 for n in navs if n <= latest_nav)
            risk["navPercentile"] = round(below / len(navs) * 100, 1)
    return risk


def map_holdings(ho: dict) -> dict:
    """holdings.json → holdings（仅 A类字段）"""
    top10 = []
    for index, h in enumerate(ho.get("top_10_holdings", []), 1):
        ratio = h.get("ratio_pct")
        if ratio is None:
            ratio = h.get("占净值比例")

        top10.append({
            "rank": first_non_none(h.get("rank"), h.get("序号"), index),
            "name": h.get("stock_name") or h.get("股票名称"),
            "code": h.get("stock_code") or h.get("股票代码"),
            "ratio": parse_percentage(ratio),
        })

    # industry_distribution 可能是 dict（含 other_sectors 列表）或 list
    sectors = []
    ind = ho.get("industry_distribution", {})
    if isinstance(ind, dict):
        # 格式：{report_date, manufacturing_pct, it_sector_pct, other_sectors:[{行业类别, 占净值比例}]}
        if ind.get("manufacturing_pct") is not None:
            sectors.append({"name": "制造业", "ratio": ind["manufacturing_pct"]})
        if ind.get("it_sector_pct") is not None:
            sectors.append({"name": "信息技术业", "ratio": ind["it_sector_pct"]})
        for s in ind.get("other_sectors", []):
            if isinstance(s, dict):
                name = s.get("行业类别") or s.get("industry")
                ratio = first_non_none(s.get("占净值比例"), s.get("ratio_pct"))
                if name and ratio is not None:
                    sectors.append({"name": name, "ratio": parse_percentage(ratio)})
    elif isinstance(ind, list):
        for s in ind:
            if isinstance(s, dict):
                sectors.append({
                    "name": s.get("industry") or s.get("行业类别"),
                    "ratio": parse_percentage(first_non_none(s.get("ratio_pct"), s.get("占净值比例"))),
                })

    top10_total_ratio = ho.get("top_10_concentration_pct")
    if top10_total_ratio is None and top10:
        top10_total_ratio = round(sum(item["ratio"] or 0 for item in top10), 2)

    return {
        "date": ho.get("report_date"),
        "top10": top10,
        "top10Total": top10_total_ratio,
        "top10TotalRatio": top10_total_ratio,
        "sectors": sectors,
    }


def merge_top10_metadata(existing_top10, new_top10):
    if not isinstance(new_top10, list):
        return new_top10

    existing_by_code = {
        str(item.get("code")): item
        for item in (existing_top10 or [])
        if isinstance(item, dict) and item.get("code")
    }

    merged = []
    for item in new_top10:
        if not isinstance(item, dict):
            merged.append(item)
            continue

        existing_item = existing_by_code.get(str(item.get("code")))
        if existing_item:
            enriched = dict(item)
            for key in ("sector", "color"):
                if enriched.get(key) is None and existing_item.get(key) is not None:
                    enriched[key] = existing_item.get(key)
            merged.append(enriched)
        else:
            merged.append(item)

    return merged


def parse_rank_text(value):
    if not value:
        return None, None
    text = str(value).strip()
    if '/' not in text:
        return None, None

    left, right = text.split('/', 1)
    try:
        rank = int(left) if left not in {'--', '—'} else None
    except ValueError:
        rank = None
    try:
        rank_total = int(right) if right not in {'--', '—'} else None
    except ValueError:
        rank_total = None
    return rank, rank_total


def map_stage_returns(fe: dict) -> list:
    stage_specs = [
        ("近1周", "return_1w", "return_1w_peer_avg", "return_1w_hs300", "return_1w_rank"),
        ("近1月", "return_1m", "return_1m_peer_avg", "return_1m_hs300", "return_1m_rank"),
        ("近3月", "return_3m", "return_3m_peer_avg", "return_3m_hs300", "return_3m_rank"),
        ("近6月", "return_6m", "return_6m_peer_avg", "return_6m_hs300", "return_6m_rank"),
        ("近1年", "return_1y", "return_1y_peer_avg", "return_1y_hs300", "return_1y_rank"),
        ("近2年", "return_2y", "return_2y_peer_avg", "return_2y_hs300", "return_2y_rank"),
        ("近3年", "return_3y", "return_3y_peer_avg", "return_3y_hs300", "return_3y_rank"),
        ("近5年", "return_5y", "return_5y_peer_avg", "return_5y_hs300", "return_5y_rank"),
        ("今年来", "return_ytd", "return_ytd_peer_avg", "return_ytd_hs300", "return_ytd_rank"),
        ("成立来", "return_since_inception", None, None, None),
    ]

    stages = []
    for period, fund_key, peer_key, hs300_key, rank_key in stage_specs:
        fund_value = parse_percentage(fe.get(fund_key))
        if fund_value is None:
            continue

        rank, rank_total = parse_rank_text(fe.get(rank_key)) if rank_key else (None, None)
        stages.append({
            "period": period,
            "fund": fund_value,
            "peer": parse_percentage(fe.get(peer_key)) if peer_key else None,
            "hs300": parse_percentage(fe.get(hs300_key)) if hs300_key else None,
            "rank": rank,
            "rankTotal": rank_total,
            "quartile": None,
        })

    return stages


def map_performance(ar: dict, qr: dict) -> dict:
    """annual_returns + quarterly → performance.annual + performance.quarterly"""
    def quarter_label(row: dict) -> Optional[Union[str, int]]:
        label = row.get("quarter_label")
        if label:
            return label

        year = row.get("year")
        quarter = row.get("quarter")
        if year is None or quarter is None:
            return quarter

        quarter_str = str(quarter)
        if quarter_str.upper().startswith("Q"):
            return f"{year}{quarter_str.upper()}"
        if quarter_str.isdigit():
            return f"{year}Q{quarter_str}"
        return quarter

    annual = []
    for row in ar.get("annual_returns", []):
        annual.append({
            "year": row.get("year"),
            "fund": first_non_none(row.get("fund"), row.get("annual_return_pct"), row.get("return")),
            "peer": row.get("peer"),
            "hs300": row.get("hs300"),
            "rank": row.get("rank"),
            "rankTotal": first_non_none(row.get("rankTotal"), row.get("rank_total")),
            "quartile": row.get("quartile"),
        })
    quarterly = []
    for row in qr.get("quarterly_performance", []):
        quarterly.append({
            "year": row.get("year"),
            "quarter": quarter_label(row),
            "fund": first_non_none(
                row.get("fund"),
                row.get("quarterly_return_pct"),
                row.get("return_pct"),
                row.get("return"),
            ),
            "peer": row.get("peer"),
            "hs300": row.get("hs300"),
            "rank": row.get("rank"),
            "rankTotal": first_non_none(row.get("rankTotal"), row.get("rank_total")),
            "quartile": row.get("quartile"),
        })
    return {"annual": annual, "quarterly": quarterly}


def map_inflection_points(ip: dict) -> list:
    """inflection_points.json → stageAnalysis.inflectionPoints"""
    result = []
    for i, p in enumerate(ip.get("inflection_points", []), 1):
        result.append({
            "id": i,
            "startDate": p.get("start_date"),
            "endDate": p.get("end_date"),
            "startNav": p.get("start_nav"),
            "endNav": p.get("end_nav"),
            "changePct": round(p.get("change_pct", 0), 2),
            "type": p.get("type"),  # "peak" | "trough"
        })
    return result


def parse_stage_period_dates(period: str):
    parts = [part.strip() for part in str(period or "").split("→")]
    if len(parts) != 2:
        return None, None

    def normalize_month(text: str, is_end: bool):
        match = re.match(r"^(\d{4})-(\d{2})$", text)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{'28' if is_end else '01'}"
        return normalize_date_string(text) or text

    return normalize_month(parts[0], False), normalize_month(parts[1], True)


def build_stage_ranges(stage_list: list) -> list:
    ranges = []
    for stage in stage_list or []:
        if not isinstance(stage, dict):
            continue
        start_date, end_date = parse_stage_period_dates(stage.get("period"))
        if not start_date or not end_date:
            continue
        ranges.append({
            **stage,
            "startDate": start_date,
            "endDate": end_date,
        })
    return ranges


def find_stage_for_point(point: dict, stage_ranges: list):
    point_end = normalize_date_string(point.get("endDate")) or point.get("endDate")
    if not point_end:
        return None

    point_dt = datetime.strptime(point_end, "%Y-%m-%d")
    for stage in stage_ranges:
        try:
            start_dt = datetime.strptime(stage["startDate"], "%Y-%m-%d")
            end_dt = datetime.strptime(stage["endDate"], "%Y-%m-%d")
        except Exception:
            continue
        if start_dt <= point_dt <= end_dt:
            return stage
    return None


def enrich_inflection_points(points: list, stage_list: list) -> list:
    if not isinstance(points, list):
        return points

    stage_ranges = build_stage_ranges(stage_list)
    if not stage_ranges:
        return points

    stage_by_id = {str(stage.get("id")): stage for stage in stage_ranges if stage.get("id") is not None}
    enriched_points = []
    for point in points:
        if not isinstance(point, dict):
            enriched_points.append(point)
            continue

        stage = None
        stage_id = point.get("stageId")
        if stage_id is not None:
            stage = stage_by_id.get(str(stage_id))
        if stage is None:
            stage = find_stage_for_point(point, stage_ranges)

        enriched = dict(point)
        if stage:
            if enriched.get("stageId") is None and stage.get("id") is not None:
                enriched["stageId"] = stage.get("id")
            if enriched.get("holdingsSummary") is None and stage.get("description"):
                enriched["holdingsSummary"] = stage.get("description")
            if enriched.get("env") is None and stage.get("env"):
                enriched["env"] = stage.get("env")
            if enriched.get("managerAction") is None and stage.get("managerAction"):
                enriched["managerAction"] = stage.get("managerAction")
            if enriched.get("attribution") is None and stage.get("attribution"):
                enriched["attribution"] = stage.get("attribution")
        enriched_points.append(enriched)
    return enriched_points


def merge_inflection_point_metadata(existing_points, new_points):
    if not isinstance(new_points, list):
        return new_points

    existing_by_id = {
        str(point.get("id")): point
        for point in (existing_points or [])
        if isinstance(point, dict) and point.get("id") is not None
    }
    existing_by_signature = {
        (
            point.get("startDate"),
            point.get("endDate"),
            point.get("type"),
        ): point
        for point in (existing_points or [])
        if isinstance(point, dict)
    }

    merged = []
    for point in new_points:
        if not isinstance(point, dict):
            merged.append(point)
            continue

        existing = existing_by_id.get(str(point.get("id")))
        if existing is None:
            existing = existing_by_signature.get((point.get("startDate"), point.get("endDate"), point.get("type")))

        if existing:
            enriched = dict(point)
            for key, value in existing.items():
                if key not in enriched and value is not None:
                    enriched[key] = value
            merged.append(enriched)
        else:
            merged.append(point)

    return merged


def map_manager(mi: dict) -> dict:
    """manager_info.json → managers.current（A类字段）"""
    # all_manager_ids：当前联席经理列表（单人管理时也有，仅1个元素）
    all_ids = mi.get("all_manager_ids") or []
    if not all_ids and mi.get("manager_id"):
        all_ids = [str(mi["manager_id"])]

    return {
        "managerId": mi.get("manager_id"),       # 主经理（任职表第一行）
        "allManagerIds": all_ids,                 # 全部联席经理 ID 列表
        "name": mi.get("manager_name"),
        "experience": mi.get("years_of_experience"),
        "education": mi.get("education"),
        "joinDate": None,  # 缓存无此字段，需人工填写
        "fundCount": mi.get("current_fund_count"),
        "totalScale": mi.get("current_aum_yi"),
    }


def map_nav_history(nd: dict) -> list:
    """nav_daily.json → navHistory（仅保留前端折线图 fallback 所需的最近数据）"""
    nav_data = nd.get("nav_data", [])
    if NAV_HISTORY_FALLBACK_LIMIT > 0:
        nav_data = nav_data[-NAV_HISTORY_FALLBACK_LIMIT:]
    return [{"date": n["date"], "nav": n["nav"]} for n in nav_data]


# ─── 合并逻辑：A类覆盖，B类保留 ─────────────────────────────────────────────

B_CLASS_KEYS_TOP = {
    "policy", "exclusionCheck", "scoring", "tracking", "company"
}

B_CLASS_KEYS_MANAGER = {
    "philosophy", "consistencyAudit", "abilityProfile",
    "title", "style", "strengths", "weaknesses",
    "education", "joinDate", "experience",
    "bestReturn", "worstReturn",
    "manageDate", "manageYears", "tenureReturn", "peerAvgReturn",
    "rankInPeer", "rankTotal", "historicalFunds", "history",
}

B_CLASS_KEYS_HOLDINGS = {
    "themeGroups", "evolutionHighlights", "policyLinks",
    "themeTitle", "themeSubtitle", "concentrationLabel",
    "bondStructure", "policyLinks", "stockRatio", "bondRatio", "cashRatio",
}

B_CLASS_KEYS_PERFORMANCE = {
    "milestones",
}

B_CLASS_KEYS_RISK = {
    "radarDimensions", "riskBreakdown", "riskWarnings", "recentPerf",
    "maxDrawdownMonths",
}

B_CLASS_KEYS_STAGE = {
    "stages",  # stages[].description/env/managerAction/attribution 等叙述字段
}


def merge(existing: dict, key: str, new_val, b_keys: set = None):
    """
    将 new_val 合并到 existing[key]。
    - 若 key 在 B_CLASS_KEYS_TOP，跳过
    - 若 new_val 是 dict，递归合并（B类子字段保留）
    - 否则直接覆盖
    """
    if key in B_CLASS_KEYS_TOP:
        return  # B类顶层字段，整体保留
    if b_keys and key in b_keys:
        return  # B类子字段，保留

    if isinstance(new_val, dict) and isinstance(existing.get(key), dict):
        for k, v in new_val.items():
            merge(existing[key], k, v)
    else:
        existing[key] = new_val


# ─── 主流程 ─────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法：python3 build_json_from_cache.py <基金代码>")
        sys.exit(1)

    code = sys.argv[1].strip()
    tmp = f"/tmp/fund_research_{code}/raw"
    has_cache_dir = os.path.isdir(tmp)

    print(f"\n═══════════════════════════════════════")
    print(f"  build_json_from_cache  基金 {code}")
    print(f"═══════════════════════════════════════\n")

    if not has_cache_dir:
        print(f"⚠️  缓存目录不存在：{tmp}")
        print(f"    将仅基于现有 JSON 执行可回填的字段修复")

    # 加载缓存
    fe = load_cache(tmp, "fund_enhanced.json")
    rk = load_cache(tmp, "risk_metrics.json")
    rm = load_cache(tmp, "relative_metrics.json")
    ho = load_cache(tmp, "holdings.json")
    ar = load_cache(tmp, "annual_returns.json")
    qr = load_cache(tmp, "quarterly.json")
    ip = load_cache(tmp, "inflection_points.json")
    mi = load_cache(tmp, "manager_info.json")
    nd = load_cache(tmp, "nav_daily.json")

    # 加载已有 JSON（保留 B 类字段）
    existing = load_existing_json(code)

    # ── meta ──
    existing.setdefault("meta", {})
    existing["meta"]["reportDate"] = date.today().isoformat()
    data_date = resolve_data_date(fe, ho, nd)
    existing["meta"]["dataDate"] = data_date or date.today().isoformat()
    existing["meta"].setdefault("disclaimer", DEFAULT_DISCLAIMER)

    # ── basic + fees ──
    if fe:
        basic_new, fees_new = map_basic(fe)
        scale_new = map_scale(fe)
        existing.setdefault("basic", {})
        for k, v in basic_new.items():
            if v is not None:
                existing["basic"][k] = v
        existing.setdefault("fees", {})
        for k, v in fees_new.items():
            if v is not None:
                existing["fees"][k] = v
        existing.setdefault("scale", {})
        for k, v in scale_new.items():
            if v is not None:
                existing["scale"][k] = v
        print(f"  ✅ basic / fees / scale（from fund_enhanced）")
    else:
        print(f"  ⚠️  fund_enhanced.json 缺失，跳过 basic/fees/scale")

    # ── risk ──
    if rk:
        nav_data = nd.get("nav_data", []) if nd else []
        risk_new = map_risk(rk, rm, nav_data)
        existing.setdefault("risk", {})
        for k, v in risk_new.items():
            if k == "riskBreakdown" and isinstance(v, dict):
                existing.setdefault("risk", {}).setdefault("riskBreakdown", {})
                yearly_drawdowns = v.get("yearlyMaxDrawdowns")
                if yearly_drawdowns:
                    existing["risk"]["riskBreakdown"]["yearlyMaxDrawdowns"] = yearly_drawdowns
                continue
            if k not in B_CLASS_KEYS_RISK and v is not None:
                existing["risk"][k] = v
        print(f"  ✅ risk（from risk_metrics + relative_metrics）")
    else:
        print(f"  ⚠️  risk_metrics.json 缺失，跳过 risk")

    # ── holdings（A类部分）──
    if ho:
        hmap = map_holdings(ho)
        existing.setdefault("holdings", {})
        for k, v in hmap.items():
            if k not in B_CLASS_KEYS_HOLDINGS and v is not None:
                if k == "top10":
                    v = merge_top10_metadata(existing["holdings"].get("top10"), v)
                existing["holdings"][k] = v
        print(f"  ✅ holdings.top10 / sectors（from holdings）")
    else:
        print(f"  ⚠️  holdings.json 缺失，跳过 holdings")

    # ── performance（A类部分）──
    perf_new = {}
    if fe:
        perf_new["stages"] = map_stage_returns(fe)
        print(f"  ✅ performance.stages（from fund_enhanced）")
    if ar:
        perf_new["annual"] = map_performance(ar, qr or {}).get("annual", [])
        print(f"  ✅ performance.annual（from annual_returns）")
    if qr:
        perf_new["quarterly"] = map_performance(ar or {}, qr).get("quarterly", [])
        print(f"  ✅ performance.quarterly（from quarterly）")
    if perf_new:
        existing.setdefault("performance", {})
        for k, v in perf_new.items():
            if k not in B_CLASS_KEYS_PERFORMANCE:
                existing["performance"][k] = v

    # ── stageAnalysis.inflectionPoints ──
    if ip:
        existing.setdefault("stageAnalysis", {})
        pts = map_inflection_points(ip)
        pts = merge_inflection_point_metadata(existing["stageAnalysis"].get("inflectionPoints"), pts)
        pts = enrich_inflection_points(pts, existing["stageAnalysis"].get("stages", []))
        existing["stageAnalysis"]["inflectionPoints"] = pts
        existing["stageAnalysis"]["totalInflectionPoints"] = len(pts)
        print(f"  ✅ stageAnalysis.inflectionPoints（{len(pts)}个，from inflection_points）")
    else:
        existing_points = ((existing.get("stageAnalysis") or {}).get("inflectionPoints"))
        if existing_points:
            pts = enrich_inflection_points(existing_points, (existing.get("stageAnalysis") or {}).get("stages", []))
            existing["stageAnalysis"]["inflectionPoints"] = pts
            existing["stageAnalysis"]["totalInflectionPoints"] = len(pts)
            print(f"  ✅ stageAnalysis.inflectionPoints（{len(pts)}个，from existing JSON fallback）")
        else:
            print(f"  ⚠️  inflection_points.json 缺失，跳过 stageAnalysis.inflectionPoints")

    # ── managers.current（A类部分）──
    if mi:
        mgr_new = map_manager(mi)
        existing.setdefault("managers", {}).setdefault("current", {})
        for k, v in mgr_new.items():
            if k not in B_CLASS_KEYS_MANAGER and v is not None:
                existing["managers"]["current"][k] = v
        # managerId / allManagerIds 总是从缓存更新（经理变更时自动刷新）
        if mgr_new.get("managerId"):
            existing["managers"]["current"]["managerId"] = mgr_new["managerId"]
        if mgr_new.get("allManagerIds"):
            existing["managers"]["current"]["allManagerIds"] = mgr_new["allManagerIds"]
        all_ids = mgr_new.get("allManagerIds", [])
        if len(all_ids) > 1:
            print(f"  ✅ managers.current（联席经理{len(all_ids)}人，from manager_info）")
            print(f"     主经理 managerId = {mgr_new['managerId']}")
            print(f"     allManagerIds = {all_ids}")
        else:
            print(f"  ✅ managers.current（name/id/scale，from manager_info）")
            print(f"     managerId = {mgr_new['managerId']}")
    else:
        print(f"  ⚠️  manager_info.json 缺失，跳过 managers.current")

    # ── navHistory ──
    if nd:
        existing["navHistory"] = map_nav_history(nd)
        print(f"  ✅ navHistory（{len(existing['navHistory'])}条，from nav_daily）")
    else:
        print(f"  ⚠️  nav_daily.json 缺失，跳过 navHistory")

    # ── B类字段检查（提示缺失但不覆盖）──
    print(f"\n─── B类字段检查（需AI/人工填写）─────────────────")
    b_checks = [
        ("policy", "第八章 政策匹配度"),
        ("exclusionCheck", "排除法检查（10项）"),
        ("scoring", "第二章 综合评级"),
        ("tracking", "第十章 跟踪计划"),
        ("stageAnalysis.stages", "第三章 各阶段叙述"),
        ("managers.current.philosophy", "第四章 4.3 投资理念"),
        ("managers.current.consistencyAudit", "第四章 4.4 言行审计"),
        ("managers.current.abilityProfile", "第四章 4.6 能力画像"),
        ("holdings.themeGroups", "第六章 持仓主题"),
        ("performance.milestones", "第九章 9.3 里程碑"),
    ]
    for key_path, desc in b_checks:
        parts = key_path.split(".")
        obj = existing
        for p in parts:
            obj = obj.get(p) if isinstance(obj, dict) else None
            if obj is None:
                break
        status = "✅ 已有" if obj else "❌ 缺失"
        print(f"  {status}  {desc}（{key_path}）")

    # ── 写入 ──
    print()
    save_json(code, existing)
    print(f"\n完成。B类缺失字段请参考：")
    print(f"  skills/fund-deep-research/reference/report_to_json_spec.md")


if __name__ == "__main__":
    main()
