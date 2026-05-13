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
                          performance.annual / performance.quarterly /
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
import sys
from datetime import date, datetime

# ─── 路径配置 ──────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../.."))
DATA_DIR = os.path.join(REPO_ROOT, "web-platform/public/data")


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


# ─── 各模块映射函数 ─────────────────────────────────────────────────────────

def map_basic(fe: dict) -> dict:
    """fund_enhanced.json → basic + fees + scale"""
    def pct(v):
        return round(v * 100, 4) if v is not None else None

    risk_code_map = {"R1": 1, "R2": 2, "R3": 3, "R4": 4, "R5": 5}
    risk_level = fe.get("risk_level", "")
    risk_code = next((v for k, v in risk_code_map.items() if k in risk_level), None)

    basic = {
        "code": fe.get("fund_code"),
        "fullName": fe.get("full_name"),
        "shortName": fe.get("short_name"),
        "type": fe.get("fund_type"),
        "riskLevel": risk_level,
        "riskCode": risk_code,
        "foundDate": fe.get("found_date"),
        "manager": fe.get("company_name"),
        "companyShort": (fe.get("company_name") or "").replace("基金管理有限公司", "基金"),
        "custodian": fe.get("custodian"),
        "benchmark": fe.get("benchmark"),
        "navFallback": fe.get("current_nav"),
        "inceptionReturn": fe.get("return_since_inception"),
    }

    fees = {
        "management": fe.get("management_fee"),
        "custodian": fe.get("custodian_fee"),
        "salesService": fe.get("sales_service_fee"),
        "subscriptionMax": fe.get("purchase_fee_original"),
        "breakdown": fe.get("redemption_rules", []),
    }

    return basic, fees


def map_scale(fe: dict) -> dict:
    """基金规模 → scale"""
    return {
        "nav": fe.get("fund_scale"),
        "date": None,  # fund_enhanced 不含日期，需手动或从 holdings 取
    }


def map_risk(rk: dict, rm: dict, nav_data: list) -> dict:
    """risk_metrics + relative_metrics → risk（仅 A类字段）"""
    risk = {
        "volatility": rk.get("volatility"),
        "annualReturn": rk.get("annual_return"),
        "sharpe": rk.get("sharpe_ratio"),
        "calmar": rk.get("calmar_ratio"),
        "maxDrawdown": rk.get("max_drawdown"),
        "maxDrawdownPeriod": f"{rk.get('max_drawdown_peak_date')} → {rk.get('max_drawdown_trough_date')}",
        "periodMetrics": [
            {"label": "近1年", "volatility": rk.get("volatility_1y"), "sharpe": rk.get("sharpe_1y")},
            {"label": "近2年", "volatility": rk.get("volatility_2y"), "sharpe": rk.get("sharpe_2y")},
            {"label": "近3年", "volatility": rk.get("volatility_3y"), "sharpe": rk.get("sharpe_3y")},
        ],
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
    for h in ho.get("top_10_holdings", []):
        top10.append({
            "name": h.get("stock_name"),
            "code": h.get("stock_code"),
            "ratio": h.get("ratio_pct"),
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
                ratio = s.get("占净值比例") or s.get("ratio_pct")
                if name and ratio is not None:
                    sectors.append({"name": name, "ratio": ratio})
    elif isinstance(ind, list):
        for s in ind:
            if isinstance(s, dict):
                sectors.append({
                    "name": s.get("industry") or s.get("行业类别"),
                    "ratio": s.get("ratio_pct") or s.get("占净值比例"),
                })

    return {
        "date": ho.get("report_date"),
        "top10": top10,
        "top10TotalRatio": ho.get("top_10_concentration_pct"),
        "sectors": sectors,
    }


def map_performance(ar: dict, qr: dict) -> dict:
    """annual_returns + quarterly → performance.annual + performance.quarterly"""
    annual = []
    for row in ar.get("annual_returns", []):
        annual.append({
            "year": row.get("year"),
            "return": row.get("annual_return_pct"),
        })
    quarterly = []
    for row in qr.get("quarterly_performance", []):
        quarterly.append({
            "year": row.get("year"),
            "quarter": row.get("quarter"),
            "return": row.get("return_pct"),
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
    """nav_daily.json → navHistory"""
    return [{"date": n["date"], "nav": n["nav"]} for n in nd.get("nav_data", [])]


# ─── 合并逻辑：A类覆盖，B类保留 ─────────────────────────────────────────────

B_CLASS_KEYS_TOP = {
    "policy", "exclusionCheck", "scoring", "tracking", "company"
}

B_CLASS_KEYS_MANAGER = {
    "philosophy", "consistencyAudit", "abilityProfile",
    "title", "style", "strengths", "weaknesses",
    "manageDate", "manageYears", "tenureReturn", "peerAvgReturn",
    "rankInPeer", "rankTotal", "historicalFunds",
}

B_CLASS_KEYS_HOLDINGS = {
    "themeGroups", "evolutionHighlights", "policyLinks",
    "themeTitle", "themeSubtitle", "concentrationLabel",
    "bondStructure", "policyLinks", "stockRatio", "bondRatio", "cashRatio",
}

B_CLASS_KEYS_PERFORMANCE = {
    "milestones", "stages",
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

    if not os.path.isdir(tmp):
        print(f"❌  缓存目录不存在：{tmp}")
        print(f"    请先运行数据采集脚本（parallel_data_collection_v2.py）")
        sys.exit(1)

    print(f"\n═══════════════════════════════════════")
    print(f"  build_json_from_cache  基金 {code}")
    print(f"═══════════════════════════════════════\n")

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
    existing["meta"]["dataDate"] = date.today().isoformat()

    # ── basic + fees ──
    if fe:
        basic_new, fees_new = map_basic(fe)
        existing.setdefault("basic", {})
        for k, v in basic_new.items():
            if v is not None:
                existing["basic"][k] = v
        existing.setdefault("fees", {})
        for k, v in fees_new.items():
            if v is not None:
                existing["fees"][k] = v
        # scale（nav/规模）
        existing.setdefault("scale", {})
        if fe.get("fund_scale") is not None:
            existing["scale"]["nav"] = fe["fund_scale"]
        print(f"  ✅ basic / fees / scale（from fund_enhanced）")
    else:
        print(f"  ⚠️  fund_enhanced.json 缺失，跳过 basic/fees/scale")

    # ── risk ──
    if rk:
        nav_data = nd.get("nav_data", []) if nd else []
        risk_new = map_risk(rk, rm, nav_data)
        existing.setdefault("risk", {})
        for k, v in risk_new.items():
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
                existing["holdings"][k] = v
        print(f"  ✅ holdings.top10 / sectors（from holdings）")
    else:
        print(f"  ⚠️  holdings.json 缺失，跳过 holdings")

    # ── performance（A类部分）──
    perf_new = {}
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
        existing["stageAnalysis"]["inflectionPoints"] = pts
        existing["stageAnalysis"]["totalInflectionPoints"] = len(pts)
        print(f"  ✅ stageAnalysis.inflectionPoints（{len(pts)}个，from inflection_points）")
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
