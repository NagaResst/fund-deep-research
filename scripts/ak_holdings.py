#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版持仓结构分析 - 包含资产配置比例、行业分布汇总、集中度等
替代原 analyze_holdings.py
"""

import sys
import json
import akshare as ak
import pandas as pd
from datetime import datetime


def fetch_enhanced_holdings(fund_code: str) -> dict:
    """
    获取增强的持仓结构数据（全年度，支持逐季对比）

    Bug8修复：
    - 原版硬编码 year="2024"，只获取单年数据，无法支撑 SKILL Step5D 的逐季持仓对比
    - 新版循环查询成立以来每一年，按季度聚合到 holdings_by_period，AI 可逐季比较

    Returns:
        dict: 含 holdings_by_period（全历史各季度持仓）和最新季度的摘要字段
    """
    current_year = datetime.now().year

    result = {
        "fund_code": fund_code,
        "report_date": "",
        "fetch_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "data_sources": []
    }

    # 1. 逐年获取股票持仓，按季度字段（AKShare 列名为"季度"）聚合
    holdings_by_period = {}   # {"2026年1季度股票投资明细": [...], ...}
    latest_holdings_df = pd.DataFrame()  # 用于后续资产配置估算

    for year in range(2010, current_year + 1):
        try:
            df = ak.fund_portfolio_hold_em(symbol=fund_code, date=str(year))
            if df.empty:
                continue
            if '季度' in df.columns:
                for period, group in df.groupby('季度'):
                    holdings_by_period[str(period)] = group.to_dict('records')
            else:
                holdings_by_period[str(year)] = df.to_dict('records')
            latest_holdings_df = df  # 记录最后有数据年份的 DataFrame，用于资产配置估算
        except Exception:
            continue

    if holdings_by_period:
        latest_period = sorted(holdings_by_period.keys())[-1]
        latest_data = holdings_by_period[latest_period]

        result["report_date"] = latest_period
        result["holdings_count"] = len(latest_data)
        result["top_10_holdings"] = latest_data[:10]
        result["all_holdings"] = latest_data
        result["holdings_by_period"] = holdings_by_period

        top_10_pct = sum(
            h.get('占净值比例', 0) for h in latest_data[:10]
            if isinstance(h.get('占净值比例'), (int, float))
        )
        result["top_10_concentration_pct"] = round(top_10_pct, 2)
        result["data_sources"].append("akshare_holdings_all_years")
    else:
        result["holdings_count"] = 0
        result["top_10_concentration_pct"] = 0
        result["top_10_holdings"] = []
        result["all_holdings"] = []
        result["holdings_by_period"] = {}

    # 2. 获取行业配置（使用当前年份）
    try:
        industry_df = ak.fund_portfolio_industry_allocation_em(symbol=fund_code, date=str(current_year))

        if not industry_df.empty:
            latest_report = industry_df.iloc[0]['截止时间']
            latest_industry = industry_df[industry_df['截止时间'] == latest_report]

            manufacturing_total = latest_industry[latest_industry['行业类别'].str.contains('制造', na=False)]['占净值比例'].sum()
            it_total = latest_industry[latest_industry['行业类别'].str.contains('信息传输|软件|信息技术', na=False)]['占净值比例'].sum()

            result["industry_distribution"] = {
                "report_date": latest_report,
                "manufacturing_pct": round(manufacturing_total, 2),
                "it_sector_pct": round(it_total, 2),
                "other_sectors": latest_industry[~latest_industry['行业类别'].str.contains('制造|信息传输|软件|信息技术', na=False)].to_dict('records')
            }
            result["data_sources"].append("akshare_industry")
        else:
            result["industry_distribution"] = None

    except Exception as e:
        print(f"[WARN] fund_portfolio_industry_allocation_em failed: {e}", file=sys.stderr)
        result["industry_distribution"] = None

    # 3. 估算资产配置比例（基于最新持仓市值和规模）
    try:
        overview_df = ak.fund_overview_em(fund_code)
        if not overview_df.empty:
            scale_info = str(overview_df.iloc[0].get('净资产规模', ''))
            import re
            scale_match = re.search(r'([\d.]+)亿元', scale_info)
            if scale_match and not latest_holdings_df.empty:
                total_aum = float(scale_match.group(1)) * 100000000
                stock_market_value = latest_holdings_df['持仓市值'].sum() * 10000
                stock_ratio = (stock_market_value / total_aum * 100) if total_aum > 0 else 0

                result["asset_allocation"] = {
                    "stock_pct": round(min(stock_ratio, 95), 2),
                    "bond_and_cash_pct": round(max(100 - stock_ratio, 5), 2),
                    "total_aum_billion": round(total_aum / 100000000, 2)
                }
                result["data_sources"].append("akshare_overview_for_allocation")
            else:
                result["asset_allocation"] = None
        else:
            result["asset_allocation"] = None

    except Exception as e:
        print(f"[WARN] asset allocation calculation failed: {e}", file=sys.stderr)
        result["asset_allocation"] = None

    # 4. 持仓集中度评价
    if result.get("top_10_concentration_pct"):
        concentration = result["top_10_concentration_pct"]
        if concentration > 70:
            result["concentration_level"] = "高"
        elif concentration > 50:
            result["concentration_level"] = "中"
        else:
            result["concentration_level"] = "低"

    return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供基金代码"}, ensure_ascii=False))
        sys.exit(1)
    
    fund_code = sys.argv[1]
    result = fetch_enhanced_holdings(fund_code)
    
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
