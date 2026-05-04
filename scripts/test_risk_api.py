#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试天天基金各种API端点，找到包含风险指标的接口
"""

import requests
import json

fund_code = "009520"
headers = {'User-Agent': 'Mozilla/5.0'}

# 可能的API端点
api_endpoints = [
    ("PMDX", "http://api.fund.eastmoney.com/f10/PMDX?fundCode={code}"),  # 排名分析
    ("JDZF", "http://api.fund.eastmoney.com/f10/JDZF?fundCode={code}"),  # 阶段涨幅
    ("MXQJ", "http://api.fund.eastmoney.com/f10/MXQJ?fundCode={code}"),  # 明星基金经理
    ("FSBG", "http://api.fund.eastmoney.com/f10/FSBG?fundCode={code}"),  # 分红送配
    ("JJCC", "http://api.fund.eastmoney.com/f10/JJCC{code}.html"),  # 基金持仓
]

for name, url_template in api_endpoints:
    try:
        url = url_template.format(code=fund_code)
        response = requests.get(url, headers=headers, timeout=5)
        
        print(f"\n{'='*60}")
        print(f"API: {name}")
        print(f"URL: {url}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                # 打印顶层keys
                if isinstance(data, dict):
                    print(f"Top keys: {list(data.keys())[:10]}")
                    # 如果有Data字段，打印Data的keys
                    if 'Data' in data and isinstance(data['Data'], dict):
                        print(f"Data keys: {list(data['Data'].keys())[:15]}")
                elif isinstance(data, list):
                    print(f"List length: {len(data)}")
                    if len(data) > 0:
                        print(f"First item type: {type(data[0])}")
            except:
                print(f"Content preview: {response.text[:200]}")
        else:
            print(f"Failed with status {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")
