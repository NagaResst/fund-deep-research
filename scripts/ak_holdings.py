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


def fetch_enhanced_holdings(fund_code: str, year: str = "2024") -> dict:
    """
    获取增强的持仓结构数据
    
    Args:
        fund_code: 基金代码
        year: 查询年份
        
    Returns:
        dict: 包含持仓明细和汇总统计的完整数据
    """
    result = {
        "fund_code": fund_code,
        "report_date": f"{year}年",
        "fetch_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "data_sources": []
    }
    
    # 1. 获取股票持仓明细
    try:
        holdings_df = ak.fund_portfolio_hold_em(symbol=fund_code, date=year)
        
        if not holdings_df.empty:
            # 计算前十大重仓股合计占比
            top_10 = holdings_df.head(10)
            top_10_concentration = top_10['占净值比例'].sum()
            
            result["holdings_count"] = len(holdings_df)
            result["top_10_concentration_pct"] = round(top_10_concentration, 2)
            result["top_10_holdings"] = holdings_df.head(10).to_dict('records')
            result["all_holdings"] = holdings_df.to_dict('records')
            result["data_sources"].append("akshare_holdings")
        else:
            result["holdings_count"] = 0
            result["top_10_concentration_pct"] = 0
            result["top_10_holdings"] = []
            result["all_holdings"] = []
            
    except Exception as e:
        print(f"[WARN] fund_portfolio_hold_em failed: {e}")
        result["holdings_count"] = 0
        result["top_10_concentration_pct"] = 0
        result["top_10_holdings"] = []
        result["all_holdings"] = []
    
    # 2. 获取行业配置
    try:
        industry_df = ak.fund_portfolio_industry_allocation_em(symbol=fund_code, date=year)
        
        if not industry_df.empty:
            # 按报告期分组，取最新的报告
            latest_report = industry_df.iloc[0]['截止时间']
            latest_industry = industry_df[industry_df['截止时间'] == latest_report]
            
            # 计算制造业合计（因为可能有多行制造业）
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
        print(f"[WARN] fund_portfolio_industry_allocation_em failed: {e}")
        result["industry_distribution"] = None
    
    # 3. 估算资产配置比例（基于持仓市值和规模）
    try:
        # 从概况获取净资产规模
        overview_df = ak.fund_overview_em(fund_code)
        if not overview_df.empty:
            scale_info = str(overview_df.iloc[0].get('净资产规模', ''))
            import re
            scale_match = re.search(r'([\d.]+)亿元', scale_info)
            if scale_match:
                total_aum = float(scale_match.group(1)) * 100000000  # 转换为元
                
                # 计算股票持仓总市值（注意：持仓市值单位是万元）
                if not holdings_df.empty:
                    stock_market_value = holdings_df['持仓市值'].sum() * 10000  # 转换为元
                    stock_ratio = (stock_market_value / total_aum * 100) if total_aum > 0 else 0
                    
                    result["asset_allocation"] = {
                        "stock_pct": round(min(stock_ratio, 95), 2),  # 股票型通常不超过95%
                        "bond_and_cash_pct": round(max(100 - stock_ratio, 5), 2),
                        "total_aum_billion": round(total_aum / 100000000, 2)
                    }
                else:
                    result["asset_allocation"] = {
                        "stock_pct": 0,
                        "bond_and_cash_pct": 100,
                        "total_aum_billion": round(total_aum / 100000000, 2)
                    }
                
                result["data_sources"].append("akshare_overview_for_allocation")
        else:
            result["asset_allocation"] = None
            
    except Exception as e:
        print(f"[WARN] asset allocation calculation failed: {e}")
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
