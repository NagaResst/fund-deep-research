#!/usr/bin/env python3
"""
Step 2：数据完整性与时效性检查
用法：python3 skills/fund-deep-research/scripts/check_data_integrity.py <基金代码>

检查 /tmp/fund_research_{code}/raw/ 下所有 JSON 的完整性和时效性，
输出需要处理的问题列表，并返回对应的 NEXT_ACTION。
"""

import json
import os
import sys
from datetime import date, datetime


def load(tmp: str, fname: str):
    path = f"{tmp}/{fname}"
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            print(f"⚠️  {fname} 存在但内容为空（0 字节），视为缺失", file=sys.stderr)
            return None
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"⚠️  {fname} JSON 解析失败：{e}，视为缺失", file=sys.stderr)
        return None


def main():
    if len(sys.argv) < 2:
        print("用法：python3 check_data_integrity.py <基金代码>")
        sys.exit(1)

    code = sys.argv[1].strip()
    tmp = f"/tmp/fund_research_{code}/raw"

    print(f"═══════════════════════════════════════")
    print(f"  Step 2 完整性检查：基金代码 {code}")
    print(f"═══════════════════════════════════════")

    fe = load(tmp, "fund_enhanced.json")
    rk = load(tmp, "risk_metrics.json")
    rel = load(tmp, "relative_metrics.json")
    ho = load(tmp, "holdings.json")
    na = load(tmp, "nav_daily.json")
    mi = load(tmp, "manager_info.json")

    issues = []
    today = date.today()

    # ── A. 基础信息完整性 ─────────────────────────────────────────────
    if not fe:
        issues.append("❌ fund_enhanced.json 缺失")
    else:
        # fund_enhanced 字段名映射（脚本实际输出的字段名）
        field_map = {
            "full_name":    "基金全称",
            "fund_type":    "基金类型",
            "found_date":   "成立日期",
            "fund_scale":   "基金规模",
            "manager_name": "基金经理",
            "company_name": "基金公司",
        }
        for field, label in field_map.items():
            val = fe.get(field)
            if not val or val in ["N/A", "", None]:
                issues.append(f"⚠️  fund_enhanced.{field}（{label}）= N/A")

    # ── B. 风险指标完整性 ─────────────────────────────────────────────
    if not rk:
        issues.append("❌ risk_metrics.json 缺失")
    else:
        # calc_risk_metrics.py 实际输出 annual_return，不含 return_1y（后者在 fund_enhanced.json）
        for field in ["annual_return", "sharpe_ratio", "max_drawdown"]:
            val = rk.get(field)
            if val is None or val in ["N/A", ""]:
                issues.append(f"⚠️  risk_metrics.{field} = N/A")

    # ── C. 相对基准指标完整性与新鲜度 ─────────────────────────────────
    if not rel:
        issues.append("❌ relative_metrics.json 缺失")
    else:
        for field in ["beta", "alpha_annualized", "information_ratio", "tracking_error_annualized", "end_date"]:
            val = rel.get(field)
            if val is None or val in ["N/A", ""]:
                issues.append(f"⚠️  relative_metrics.{field} = N/A")

        data_sources = rel.get("data_sources") or []
        if "industry_estimate" in data_sources:
            issues.append("⚠️  relative_metrics 使用了 industry_estimate 估算值，需重拉基准后重算")

    # ── D. 净值时效（T-3 告警，>3 个自然日则需重拉）──────────────────
    if not na:
        issues.append("❌ nav_daily.json 缺失")
    else:
        # nav_daily.json 是 dict，净值列表在 nav_data 字段，按升序排列，最后一条最新
        nav_list = na.get("nav_data", []) if isinstance(na, dict) else na
        latest_date = nav_list[-1].get("date") if nav_list else None
        if latest_date:
            latest = datetime.strptime(latest_date, "%Y-%m-%d").date()
            days_lag = (today - latest).days
            if days_lag > 3:
                issues.append(
                    f"⚠️  nav_daily 最新日期 {latest_date}，已落后 {days_lag} 天（>T-1），需重拉"
                )
            else:
                print(f"✅ nav_daily 时效正常：{latest_date}（T-{days_lag}），共 {len(nav_list)} 条")

            if rel and rel.get("end_date"):
                try:
                    relative_end = datetime.strptime(rel["end_date"], "%Y-%m-%d").date()
                    gap = (latest - relative_end).days
                    if gap > 10:
                        issues.append(
                            f"⚠️  relative_metrics 截止 {rel['end_date']}，较 nav_daily 最新 {latest_date} 落后 {gap} 天，需重算"
                        )
                    else:
                        print(f"✅ relative_metrics 时效正常：{rel['end_date']}（距最新净值 {gap} 天）")
                except ValueError:
                    issues.append(f"⚠️  relative_metrics.end_date 格式异常：{rel.get('end_date')}")

    # ── E. 持仓时效（最近季报，>4 个月告警）──────────────────────────
    if not ho:
        issues.append("❌ holdings.json 缺失")
    else:
        report_date = ho.get("report_date", "")
        if report_date:
            try:
                rd = datetime.strptime(report_date, "%Y-%m-%d").date()
                months_old = (today.year - rd.year) * 12 + today.month - rd.month
                if months_old > 4:
                    issues.append(
                        f"⚠️  holdings 持仓来自 {report_date}（{months_old} 个月前），可能不是最新季报"
                    )
                else:
                    print(f"✅ holdings 时效正常：{report_date}（{months_old} 个月前）")
            except ValueError:
                print(f"ℹ️  holdings report_date 格式无法解析：{report_date!r}")

    # ── F. 经理信息完整性与口径冲突 ───────────────────────────────────
    if not mi:
        issues.append("❌ manager_info.json 缺失")
    else:
        authoritative_names = mi.get("authoritative_current_manager_names") or []
        if not authoritative_names:
            issues.append("⚠️  manager_info.authoritative_current_manager_names 缺失")

        if mi.get("manager_identity_conflict"):
            issues.append("⚠️  manager_info 顶层经理字段与 tenure_history 冲突，写报告时必须以 tenure_history 为准")

    # ── 汇总输出 ──────────────────────────────────────────────────────
    print()
    if issues:
        print("=== 需要处理的问题 ===")
        for i in issues:
            print(f"  {i}")
        print()

        has_missing   = any(i.startswith("❌") for i in issues)
        has_na        = any("N/A" in i for i in issues)
        has_stale_nav = any("nav_daily" in i and "需重拉" in i for i in issues)
        has_stale_rel = any("relative_metrics" in i and ("需重算" in i or "估算值" in i) for i in issues)
        has_stale_ho  = any("holdings" in i and "季报" in i for i in issues)
        has_manager_refresh = any(
            "manager_info.authoritative_current_manager_names 缺失" in i for i in issues
        )

        if has_missing:
            print("NEXT_ACTION: REFETCH_MISSING")
            print("→ 重跑 Step 1 补齐缺失文件后，重新执行本脚本")
        elif has_stale_nav:
            print("NEXT_ACTION: REFRESH_NAV")
            print("→ 重拉 nav_daily.json：")
            print(f"  python3 skills/fund-deep-research/scripts/ak_nav_history.py {code}")
        elif has_stale_rel:
            print("NEXT_ACTION: REFRESH_RELATIVE")
            print("→ 重算 relative_metrics.json：")
            print(f"  python3 skills/fund-deep-research/scripts/calc_relative_metrics.py {code} > /tmp/fund_research_{code}/raw/relative_metrics.json")
        elif has_manager_refresh:
            print("NEXT_ACTION: REFRESH_MANAGER")
            print("→ 重拉 manager_info.json：")
            print(f"  python3 skills/fund-deep-research/scripts/fetch_manager_info.py {code} > /tmp/fund_research_{code}/raw/manager_info.json")
        elif has_stale_ho:
            print("NEXT_ACTION: REFRESH_HOLDINGS")
            print("→ 重跑 parallel_data_collection.py 更新持仓季报数据")
        elif has_na:
            print("NEXT_ACTION: WEB_SEARCH")
            print("→ 进入 Step 3 联网搜索补充上述 N/A 字段")
        else:
            print("NEXT_ACTION: PROCEED_TO_STEP4")
            print("→ 数据完整，跳到 Step 4 执行数据验证")
    else:
        print("✅ 所有数据完整且在时效内")
        print()
        print("NEXT_ACTION: PROCEED_TO_STEP4")
        print("→ 直接跳到 Step 4 执行数据验证与交叉核对")


if __name__ == "__main__":
    main()
