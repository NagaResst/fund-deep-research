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
import numpy as np
from datetime import datetime
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
                    
        for box in boxes:
            title_label = box.find('label', class_='left')
            period = title_label.text.strip() if title_label else f"{year}年未知季度"
                        
            # 使用更灵活的选择器，只要包含 'tzxq' 类的表格都算
            table = box.find('table', class_=lambda c: c and 'tzxq' in c)
            holdings = []
            if table:
                # 动态列检测（与 analyze_holdings.py 保持一致）
                header_row = table.find('tr')
                th_list = [th.get_text(strip=True) for th in header_row.find_all('th')]
                code_col  = next((i for i, h in enumerate(th_list) if '代码' in h), 1)
                name_col  = next((i for i, h in enumerate(th_list) if '名称' in h), 2)
                ratio_col = next((i for i, h in enumerate(th_list) if '占净值' in h or '比例' in h), None)

                for row in table.find_all('tr')[1:11]:
                    cols = row.find_all('td')
                    if len(cols) < 2:
                        continue
                    stock_code = cols[code_col].text.strip() if code_col < len(cols) else ""
                    stock_name = cols[name_col].text.strip() if name_col < len(cols) else ""
                    ratio_str = "0%"
                    if ratio_col is not None and ratio_col < len(cols):
                        ratio_str = cols[ratio_col].text.strip()
                    if stock_name:
                        holdings.append({
                            "code": stock_code,
                            "name": stock_name,
                            "ratio": ratio_str
                        })
            
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
        # 提取前五大股票名称（新结构含 name + code + ratio）
        top_stocks = [h['name'] for h in q.get('holdings', [])[:5]]
        top_with_ratio = [{"name": h['name'], "code": h.get('code',''), "ratio": h.get('ratio','')}
                          for h in q.get('holdings', [])[:5]]
        
        entry = {
            "period": q.get('report_date'),
            "top_holdings": top_stocks,
            "top_holdings_detail": top_with_ratio,
            "action_summary": f"当期重仓: {', '.join(top_stocks)}",
            "risk_flag": "Pending deep search" 
        }
        analysis_report.append(entry)
        
    return analysis_report

def fetch_quarterly_nav(fund_code: str) -> list:
    """
    从天天基金 API 拉取历史净值，筛选各季末（3-31, 6-30, 9-30, 12-31）净值。
    使用累计净值（LJJZ）计算最大回撤，排除分红再投资干扰。
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://fundf10.eastmoney.com/",
        "Accept": "application/json, text/plain, */*",
    }
    all_records = []
    page = 1
    page_size = 200

    while True:
        url = (
            f"https://api.fund.eastmoney.com/f10/lsjz"
            f"?fundCode={fund_code}&pageIndex={page}&pageSize={page_size}"
            f"&startDate=2015-01-01&endDate=2030-12-31"
        )
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[WARN] fetch_quarterly_nav page={page} failed: {e}", file=sys.stderr)
            break

        if not data or not isinstance(data, dict):
            print(f"[WARN] fetch_quarterly_nav: unexpected response on page {page}", file=sys.stderr)
            break

        page_records = data.get("Data", {}).get("LSJZList", [])
        if not page_records:
            break
        all_records.extend(page_records)
        total = data.get("TotalCount", 0)
        if len(all_records) >= total:
            break
        page += 1

    records = all_records
    QUARTER_END_MONTHS = {3, 6, 9, 12}
    seen = set()
    quarterly = []

    for r in records:  # 数据为时间降序
        d = datetime.strptime(r["FSRQ"], "%Y-%m-%d")
        key = (d.year, (d.month - 1) // 3 + 1)
        if d.month in QUARTER_END_MONTHS and key not in seen:
            seen.add(key)
            acc_nav_raw = r.get("LJJZ") or r.get("DWJZ", "0")
            try:
                acc_nav = float(acc_nav_raw)
            except (ValueError, TypeError):
                acc_nav = float(r.get("DWJZ", 0))
            quarterly.append({
                "date": r["FSRQ"],
                "nav": float(r["DWJZ"]),
                "acc_nav": acc_nav,
                "quarter": f"{d.year}Q{(d.month-1)//3+1}"
            })

    quarterly.sort(key=lambda x: x["date"])  # 改为时间升序
    print(f"[INFO] Fetched {len(quarterly)} quarter-end NAV records.", file=sys.stderr)
    return quarterly


def calc_max_drawdown(quarterly_nav: list) -> dict:
    """
    基于季末累计净值序列计算最大回撤。
    返回回撤幅度、峰值日期/净值、谷值日期/净值。
    注意：季度颗粒度会低估真实最大回撤（季中更大跌幅被忽略），
    应与 fetch_risk_metrics.py 的日度结果交叉验证。
    """
    if len(quarterly_nav) < 2:
        return {"error": "数据不足，至少需要2个季度净值"}

    nav_arr = np.array([q["acc_nav"] for q in quarterly_nav], dtype=float)
    dates = [q["date"] for q in quarterly_nav]
    quarters = [q["quarter"] for q in quarterly_nav]

    peak = np.maximum.accumulate(nav_arr)
    drawdowns = (nav_arr - peak) / peak

    mdd_idx = int(np.argmin(drawdowns))
    peak_idx = int(np.argmax(nav_arr[:mdd_idx + 1]))
    mdd_value = float(drawdowns[mdd_idx])

    # 计算从谷值到下一个峰值的恢复时间（季度数）
    recovery_quarters = None
    for i in range(mdd_idx + 1, len(nav_arr)):
        if nav_arr[i] >= nav_arr[peak_idx]:
            recovery_quarters = i - mdd_idx
            break

    return {
        "max_drawdown": f"{mdd_value:.2%}",
        "max_drawdown_raw": round(mdd_value, 4),
        "peak_date": dates[peak_idx],
        "peak_quarter": quarters[peak_idx],
        "peak_acc_nav": float(nav_arr[peak_idx]),
        "trough_date": dates[mdd_idx],
        "trough_quarter": quarters[mdd_idx],
        "trough_acc_nav": float(nav_arr[mdd_idx]),
        "drawdown_duration_quarters": mdd_idx - peak_idx,
        "recovery_quarters": recovery_quarters,
        "note": "基于季末累计净值，颗粒度为季度；真实最大回撤（日度）通常更大，请与 fetch_risk_metrics.py 交叉验证"
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供基金代码"}, ensure_ascii=False))
        sys.exit(1)

    fund_code = sys.argv[1]

    # 原有：持仓分析
    quarters = fetch_quarterly_data(fund_code)
    analysis = analyze_quarterly_logic(quarters)

    # 新增：季末净值 + 最大回撤
    quarterly_nav = fetch_quarterly_nav(fund_code)
    mdd_result = calc_max_drawdown(quarterly_nav)

    result = {
        "fund_code": fund_code,
        "total_quarters": len(quarters),
        "risk_from_quarterly": mdd_result,
        "quarterly_nav_summary": {
            "count": len(quarterly_nav),
            "earliest": quarterly_nav[0]["date"] if quarterly_nav else None,
            "latest": quarterly_nav[-1]["date"] if quarterly_nav else None,
            "latest_acc_nav": quarterly_nav[-1]["acc_nav"] if quarterly_nav else None,
        },
        "quarterly_nav": quarterly_nav,
        "quarterly_analysis": analysis
    }

    output_str = json.dumps(result, ensure_ascii=False, indent=2).replace('\xa0', ' ')

    # 解析 --output 参数
    output_path = None
    raw_args = sys.argv[2:]
    for i, arg in enumerate(raw_args):
        if arg == '--output' and i + 1 < len(raw_args):
            output_path = raw_args[i + 1]
            break

    if output_path:
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_str)
        print(f"[OK] 已保存到 {output_path}", file=sys.stderr)
    else:
        print(output_str)

if __name__ == "__main__":
    main()
