#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从天天基金网页直接抓取已计算好的风险指标
包括：夏普比率、最大回撤、波动率等
"""

import sys
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime


def fetch_risk_metrics_from_web(fund_code):
    """
    从天天基金F10页面抓取风险指标
    
    Args:
        fund_code: 基金代码
        
    Returns:
        dict: 包含风险指标的字典
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'http://fundf10.eastmoney.com/'
    }
    
    result = {
        "fund_code": fund_code,
        "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_source": "eastmoney_web"
    }
    
    # 尝试从不同页面抓取
    pages = [
        f"http://fundf10.eastmoney.com/jbgk_{fund_code}.html",  # 基本概况
        f"http://fundf10.eastmoney.com/tsdata_{fund_code}.html",  # 特色数据（可能有风险指标）
    ]
    
    for url in pages:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 方法1：查找包含指标的表格单元格
            all_td = soup.find_all('td')
            for td in all_td:
                text = td.get_text(strip=True)
                
                # 查找夏普比率
                if '夏普比率' in text:
                    parent_tr = td.find_parent('tr')
                    if parent_tr:
                        sibling_tds = parent_tr.find_all('td')
                        for i, cell in enumerate(sibling_tds):
                            if '夏普比率' in cell.get_text():
                                if i + 1 < len(sibling_tds):
                                    value = sibling_tds[i + 1].get_text(strip=True)
                                    try:
                                        result['sharpe_ratio'] = float(value)
                                        print(f"[OK] Found sharpe_ratio: {value}", file=sys.stderr)
                                    except:
                                        pass
                
                # 查找最大回撤
                elif '最大回撤' in text or '最大回测' in text:
                    parent_tr = td.find_parent('tr')
                    if parent_tr:
                        sibling_tds = parent_tr.find_all('td')
                        for i, cell in enumerate(sibling_tds):
                            if '最大回撤' in cell.get_text() or '最大回测' in cell.get_text():
                                if i + 1 < len(sibling_tds):
                                    value = sibling_tds[i + 1].get_text(strip=True).replace('%', '')
                                    try:
                                        result['max_drawdown'] = -abs(float(value))  # 确保是负值
                                        print(f"[OK] Found max_drawdown: {value}%", file=sys.stderr)
                                    except:
                                        pass
                
                # 查找波动率/标准差
                elif '波动率' in text or '标准差' in text:
                    parent_tr = td.find_parent('tr')
                    if parent_tr:
                        sibling_tds = parent_tr.find_all('td')
                        for i, cell in enumerate(sibling_tds):
                            if '波动率' in cell.get_text() or '标准差' in cell.get_text():
                                if i + 1 < len(sibling_tds):
                                    value = sibling_tds[i + 1].get_text(strip=True).replace('%', '')
                                    try:
                                        result['volatility'] = float(value)
                                        print(f"[OK] Found volatility: {value}%", file=sys.stderr)
                                    except:
                                        pass
                
                # 查找索提诺比率
                elif '索提诺' in text:
                    parent_tr = td.find_parent('tr')
                    if parent_tr:
                        sibling_tds = parent_tr.find_all('td')
                        for i, cell in enumerate(sibling_tds):
                            if '索提诺' in cell.get_text():
                                if i + 1 < len(sibling_tds):
                                    value = sibling_tds[i + 1].get_text(strip=True)
                                    try:
                                        result['sortino_ratio'] = float(value)
                                        print(f"[OK] Found sortino_ratio: {value}", file=sys.stderr)
                                    except:
                                        pass
                
                # 查找卡玛比率
                elif '卡玛比率' in text:
                    parent_tr = td.find_parent('tr')
                    if parent_tr:
                        sibling_tds = parent_tr.find_all('td')
                        for i, cell in enumerate(sibling_tds):
                            if '卡玛比率' in cell.get_text():
                                if i + 1 < len(sibling_tds):
                                    value = sibling_tds[i + 1].get_text(strip=True)
                                    try:
                                        result['calmar_ratio'] = float(value)
                                        print(f"[OK] Found calmar_ratio: {value}", file=sys.stderr)
                                    except:
                                        pass
            
            # 如果找到了关键指标，提前返回
            if result.get('sharpe_ratio'):
                break
                
        except Exception as e:
            print(f"[WARN] Failed to parse {url}: {e}", file=sys.stderr)
            continue
    
    return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供基金代码"}, ensure_ascii=False))
        sys.exit(1)
    
    fund_code = sys.argv[1]
    result = fetch_risk_metrics_from_web(fund_code)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
