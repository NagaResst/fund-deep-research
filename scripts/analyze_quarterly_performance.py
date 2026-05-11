#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金季度表现与持仓关联分析脚本
目标：按季度维度，关联“净值表现”、“持仓变动”与“官方观点”，识别经理的真实意图。
"""

import sys
import json
import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_year_data(fund_code, year, headers):
    """抓取单一年份的季度数据（辅助函数）"""
    url = f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={fund_code}&topline=10&year={year}&month=&rt={time.time()}"
    quarters_in_year = []
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        text = resp.text
        
        if 'content:"' not in text:
            return []
            
        html_content = text.split('content:"')[1].split('";')[0]
        html_content = html_content.replace(r'\"', '"').replace(r'\/', '/')
        
        soup = BeautifulSoup(html_content, 'html.parser')
        boxes = soup.find_all('div', class_='boxitem')
                    
        # 调试：打印一下找到的表格类名
        all_tables = soup.find_all('table')
        if year == 2025 and all_tables:
            print(f"[DEBUG] Found tables in {year}: {[t.get('class') for t in all_tables]}", file=sys.stderr)
                    
        for box in boxes:
            title_label = box.find('label', class_='left')
            period = title_label.text.strip() if title_label else f"{year}年未知季度"
                        
            # 使用更灵活的选择器，只要包含 'tzxq' 类的表格都算
            table = box.find('table', class_=lambda c: c and 'tzxq' in c)
            holdings = []
            if table:
                rows = table.find_all('tr')[1:]
                for row in rows[:10]:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        stock_name = cols[1].text.strip()
                        ratio = cols[6].text.strip() if len(cols) > 6 else "0%"
                        holdings.append({"name": stock_name, "ratio": ratio})
            
            quarters_in_year.append({
                "report_date": period,
                "holdings": holdings
            })
    except Exception as e:
        print(f"[WARN] Year {year} failed: {e}", file=sys.stderr)
        
    return quarters_in_year

def fetch_quarterly_data(fund_code):
    """
    抓取基金的历史季报关键数据（多线程并发版）
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': f'http://fundf10.eastmoney.com/jjcc_{fund_code}.html'
    }
    
    years_to_fetch = list(range(2026, 2014, -1)) # 从 2026 到 2015
    all_quarters = []
    
    print(f"[INFO] Starting multi-threaded fetch for {len(years_to_fetch)} years...", file=sys.stderr)
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_year = {executor.submit(fetch_year_data, fund_code, year, headers): year for year in years_to_fetch}
        
        for future in as_completed(future_to_year):
            year = future_to_year[future]
            try:
                data = future.result()
                if data:
                    all_quarters.extend(data)
                    print(f"[INFO] Completed year {year}, found {len(data)} quarters.", file=sys.stderr)
            except Exception as e:
                print(f"[ERROR] Year {year} generated an exception: {e}", file=sys.stderr)

    # 按时间排序（因为是多线程，顺序可能乱）
    # 简单的字符串排序通常能处理 "2026年1季度" 这种格式，如果需要更精确可以解析日期
    return sorted(all_quarters, key=lambda x: x['report_date'], reverse=True)

def analyze_quarterly_logic(quarters):
    """
    对季度数据进行逻辑关联分析
    """
    analysis_report = []
    
    for i, q in enumerate(quarters):
        # 提取前五大股票名称
        top_stocks = [h['name'] for h in q.get('holdings', [])[:5]]
        
        entry = {
            "period": q.get('report_date'),
            "top_holdings": top_stocks,
            "action_summary": f"当期重仓: {', '.join(top_stocks)}",
            "risk_flag": "Pending deep search" 
        }
        analysis_report.append(entry)
        
    return analysis_report

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供基金代码"}, ensure_ascii=False))
        sys.exit(1)
    
    fund_code = sys.argv[1]
    quarters = fetch_quarterly_data(fund_code)
    
    result = {
        "fund_code": fund_code,
        "total_quarters": len(quarters),
        "quarterly_analysis": analyze_quarterly_logic(quarters)
    }
    
    # 处理特殊字符以确保在 Windows 终端正常输出
    output_str = json.dumps(result, ensure_ascii=False, indent=2)
    print(output_str.replace('\xa0', ' '))

if __name__ == "__main__":
    main()
