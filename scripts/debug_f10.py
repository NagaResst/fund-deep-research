#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试F10页面结构"""

import requests
from bs4 import BeautifulSoup

url = "http://fundf10.eastmoney.com/jbgk_003984.html"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get(url, headers=headers, timeout=10)
soup = BeautifulSoup(response.text, 'html.parser')

print("=" * 80)
print("查找所有表格:")
tables = soup.find_all('table')
print(f"找到 {len(tables)} 个表格\n")

for i, table in enumerate(tables[:3]):
    print(f"\n表格 {i}:")
    print(f"  class: {table.get('class')}")
    print(f"  id: {table.get('id')}")
    
    rows = table.find_all('tr')
    print(f"  行数: {len(rows)}")
    
    # 打印前3行内容
    for j, row in enumerate(rows[:3]):
        ths = row.find_all('th')
        tds = row.find_all('td')
        print(f"    行{j}: th={len(ths)}, td={len(tds)}")
        if ths:
            print(f"      th文本: {[th.get_text(strip=True)[:20] for th in ths]}")
        if tds:
            print(f"      td文本: {[td.get_text(strip=True)[:20] for td in tds]}")

print("\n" + "=" * 80)
print("查找包含'基金类型'的元素:")
for elem in soup.find_all(string=lambda text: text and '基金类型' in text):
    parent = elem.parent
    print(f"元素: {parent.name}, class: {parent.get('class')}")
    print(f"父元素: {parent.parent.name}")
    print(f"完整文本: {elem.strip()[:100]}")
    print("-" * 40)
