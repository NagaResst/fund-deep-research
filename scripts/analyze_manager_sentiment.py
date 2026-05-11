#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金经理言行一致性分析脚本
目标：对比经理在季报中的“观点”与实际的“持仓操作”，识别风格漂移或言行不一。
"""

import sys
import json
import requests
from bs4 import BeautifulSoup

def fetch_report_text(fund_code, report_type="quarterly"):
    """
    获取基金定期报告中的管理人报告章节（简化版：通过关键词抓取）
    """
    url = f"http://fundf10.eastmoney.com/jjgg_{fund_code}_3.html"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'http://fundf10.eastmoney.com/'
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # 尝试提取最新的公告标题和链接
            items = soup.find_all('a', href=True)
            for item in items:
                if "2026" in item.text or "2025" in item.text: # 简单过滤近期报告
                    return item.text, item['href']
    except Exception as e:
        print(f"Fetch report error: {e}", file=sys.stderr)
    
    return None, None

def analyze_consistency(holdings_current, holdings_previous, report_summary):
    """
    简单的言行一致性启发式分析
    """
    analysis = {
        "consistency_score": 80, # 默认分
        "observations": [],
        "risk_flags": []
    }
    
    # 1. 检查行业集中度变化
    if holdings_current and holdings_previous:
        curr_top_industry = holdings_current.get("industry_distribution", [{}])[0].get("industry_name", "")
        prev_top_industry = holdings_previous.get("industry_distribution", [{}])[0].get("industry_name", "")
        
        if curr_top_industry != prev_top_industry:
            analysis["observations"].append(f"第一大重仓行业从 {prev_top_industry} 切换至 {curr_top_industry}")
            if report_summary and curr_top_industry not in report_summary:
                analysis["risk_flags"].append("观点未提及但大幅切换行业，存在隐性漂移风险")
                analysis["consistency_score"] -= 20

    # 2. 检查换手率（如果有数据）
    # 这里可以接入更复杂的逻辑
    
    return analysis

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供基金代码"}, ensure_ascii=False))
        sys.exit(1)
    
    fund_code = sys.argv[1]
    
    # 1. 获取最新报告摘要
    title, link = fetch_report_text(fund_code)
    
    # 2. 模拟获取持仓数据（实际应调用 analyze_holdings.py 的输出）
    # 这里为了演示，返回一个占位符
    holdings_curr = {"industry_distribution": [{"industry_name": "新能源"}]}
    holdings_prev = {"industry_distribution": [{"industry_name": "半导体"}]}
    
    result = {
        "fund_code": fund_code,
        "latest_report_title": title,
        "report_link": link,
        "consistency_analysis": analyze_consistency(holdings_curr, holdings_prev, title)
    }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
