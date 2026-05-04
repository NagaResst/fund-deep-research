#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金持仓结构分析脚本
分析行业分布、重仓股、集中度等
输出JSON格式，便于AI解析
"""

import sys
import json
import requests


def fetch_holdings(fund_code):
    """
    获取基金持仓数据
    
    Args:
        fund_code: 基金代码
        
    Returns:
        dict: 持仓信息
    """
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'http://fundf10.eastmoney.com/'
    }
    
    result = {
        "fund_code": fund_code,
        "top_10_stocks": [],
        "industry_distribution": [],
        "asset_allocation": {},
        "concentration": {},
    }
    
    try:
        # 获取前十大重仓股
        stock_url = f"http://api.fund.eastmoney.com/f10/CCMX?fundCode={fund_code}"
        stock_response = requests.get(stock_url, headers=headers, timeout=10)
        stock_data = stock_response.json()
        
        if stock_data and stock_data.get("Data"):
            holdings = stock_data["Data"]["fundStocks"]
            if holdings:
                top_10 = []
                total_stock_ratio = 0
                for stock in holdings[:10]:
                    top_10.append({
                        "stock_name": stock.get("GPJC", ""),
                        "stock_code": stock.get("GPDM", ""),
                        "ratio": float(stock.get("JZBL", 0)),
                        "industry": stock.get("HYMC", ""),
                    })
                    total_stock_ratio += float(stock.get("JZBL", 0))
                
                result["top_10_stocks"] = top_10
                result["concentration"]["top_10_ratio"] = round(total_stock_ratio, 2)
        
        # 获取行业分布
        industry_url = f"http://api.fund.eastmoney.com/f10/CCJJ?fundCode={fund_code}"
        industry_response = requests.get(industry_url, headers=headers, timeout=10)
        industry_data = industry_response.json()
        
        if industry_data and industry_data.get("Data"):
            industries = industry_data["Data"].get("IndustryInvestment", [])
            if industries:
                industry_dist = []
                for ind in industries:
                    industry_dist.append({
                        "industry_name": ind.get("IndustryName", ""),
                        "ratio": float(ind.get("Ratio", 0)),
                    })
                result["industry_distribution"] = industry_dist
        
        # 获取资产配置
        asset_url = f"http://api.fund.eastmoney.com/f10/JPBZ?fundCode={fund_code}"
        asset_response = requests.get(asset_url, headers=headers, timeout=10)
        asset_data = asset_response.json()
        
        if asset_data and asset_data.get("Data"):
            allocation = asset_data["Data"].get("AssetAllocation", {})
            if allocation:
                result["asset_allocation"] = {
                    "stock_ratio": float(allocation.get("GP", 0)),
                    "bond_ratio": float(allocation.get("ZQ", 0)),
                    "cash_ratio": float(allocation.get("HB", 0)),
                    "other_ratio": float(allocation.get("QT", 0)),
                }
        
        return result
        
    except Exception as e:
        return {
            "error": True,
            "message": f"抓取失败: {str(e)}",
            "fund_code": fund_code
        }


def analyze_concentration(holdings_data):
    """
    分析持仓集中度
    
    Args:
        holdings_data: 持仓数据
        
    Returns:
        dict: 集中度分析
    """
    top_10_ratio = holdings_data.get("concentration", {}).get("top_10_ratio", 0)
    
    concentration_level = ""
    if top_10_ratio > 60:
        concentration_level = "高度集中"
    elif top_10_ratio > 40:
        concentration_level = "适度集中"
    else:
        concentration_level = "分散配置"
    
    return {
        "top_10_ratio": top_10_ratio,
        "concentration_level": concentration_level,
        "risk_assessment": "高风险" if top_10_ratio > 60 else ("中等风险" if top_10_ratio > 40 else "低风险")
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供基金代码"}, ensure_ascii=False))
        sys.exit(1)
    
    fund_code = sys.argv[1]
    
    # 获取持仓数据
    holdings_data = fetch_holdings(fund_code)
    
    if "error" in holdings_data:
        print(json.dumps(holdings_data, ensure_ascii=False, indent=2))
        sys.exit(1)
    
    # 分析集中度
    holdings_data["concentration_analysis"] = analyze_concentration(holdings_data)
    
    # 输出JSON格式
    print(json.dumps(holdings_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
