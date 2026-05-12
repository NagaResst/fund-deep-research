#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金持仓结构分析脚本（职责：行业分布 / 资产配置 / 持有人结构 / 申万行业补全）
top10 持仓已由 analyze_quarterly_performance.py 统一管理，本脚本不重复获取。
输出JSON格式，便于AI解析
"""

import sys
import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


# ── 申万行业查询 ──────────────────────────────────────────────────────────────

# 申万一级行业 ID（f136）→ 名称 映射（固定，2021修订版，共31个）
_SW_ID_MAP = {
    801010: "农林牧渔", 801020: "采掘", 801030: "化工", 801040: "钢铁",
    801050: "有色金属", 801080: "电子", 801110: "家用电器", 801120: "食品饮料",
    801130: "纺织服装", 801140: "轻工制造", 801150: "医药生物", 801160: "公用事业",
    801170: "交通运输", 801180: "房地产", 801200: "商业贸易", 801210: "休闲服务",
    801230: "综合", 801710: "建筑材料", 801720: "建筑装饰", 801730: "电气设备",
    801740: "国防军工", 801750: "计算机", 801760: "传媒", 801770: "通信",
    801780: "银行", 801790: "非银金融", 801880: "汽车", 801890: "机械设备",
    # 2021修订后新增/改名
    801960: "电力设备", 801970: "煤炭", 801980: "石油石化", 801990: "环保",
    851010: "基础化工", 851030: "钢铁", 851050: "有色金属",
    851230: "社会服务", 851710: "建筑材料",
}


def _get_shenwan_industry(stock_code: str) -> str:
    """
    查询单只股票的申万一级行业名称。
    数据来源：东方财富行情 API f136 字段（申万行业整数 ID）→ 本地映射表转名称。
    自动判断市场：6 开头=1（沪），其余=0（深/创/北）
    """
    if not stock_code or not stock_code.isdigit():
        return ""
    market = "1" if stock_code.startswith("6") else "0"
    url = (f"https://push2.eastmoney.com/api/qt/stock/get"
           f"?secid={market}.{stock_code}&fields=f136")
    try:
        resp = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://finance.eastmoney.com/'
        }, timeout=8)
        val = resp.json().get("data", {}).get("f136")
        if val is None:
            return ""
        sw_id = int(val)
        return _SW_ID_MAP.get(sw_id, f"申万ID:{sw_id}")
    except Exception:
        return ""


def _batch_shenwan_industry(stock_codes: list) -> dict:
    """串行查询多只股票的申万行业（push2 API 频率敏感，不并发）"""
    result = {}
    for code in stock_codes:
        result[code] = _get_shenwan_industry(code)
        time.sleep(0.3)
    return result


# ── 三个独立接口的抓取函数（供并发调用）────────────────────────────────────

def _fetch_industry_dist(fund_code: str, headers: dict) -> list:
    """type=hypzsy 证监会行业配置"""
    url = (f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx"
           f"?type=hypzsy&code={fund_code}&year={datetime.now().year}&rt={time.time()}")
    resp = requests.get(url, headers=headers, timeout=10)
    text = resp.text
    if 'content:"' not in text:
        return []
    html = text.split('content:"')[1].split('";')[0].replace(r'\"', '"').replace(r'\/', '/')
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    if not table:
        return []
    rows = table.find_all('tr')
    header = [c.get_text(strip=True) for c in rows[0].find_all(['th', 'td'])]
    fund_col = next((i for i, h in enumerate(header) if '基金' in h), 2)
    peer_col = next((i for i, h in enumerate(header) if '同类' in h), 3)
    industry_dist = []
    for row in rows[1:]:
        cols = row.find_all('td')
        if len(cols) < 3:
            continue
        name = cols[1].get_text(strip=True) if len(cols) > 1 else ""
        code = cols[0].get_text(strip=True) if cols else ""
        if name == '合计':
            continue
        def _pct(col_idx):
            s = cols[col_idx].get_text(strip=True).replace('%', '').replace('---', '0') if col_idx < len(cols) else '0'
            try: return float(s)
            except: return 0.0
        fund_ratio = _pct(fund_col)
        peer_ratio = _pct(peer_col)
        if fund_ratio > 0:
            industry_dist.append({
                "industry_code": code,
                "industry_name": name,
                "fund_ratio": fund_ratio,
                "peer_avg_ratio": peer_ratio,
            })
    return sorted(industry_dist, key=lambda x: -x["fund_ratio"])


def _fetch_asset_alloc(fund_code: str, headers: dict) -> dict:
    """type=zcfzb 资产负债表"""
    url = (f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx"
           f"?type=zcfzb&code={fund_code}&year={datetime.now().year}&rt={time.time()}")
    resp = requests.get(url, headers=headers, timeout=10)
    text = resp.text
    if 'content:"' not in text:
        return {}
    html = text.split('content:"')[1].split('";')[0].replace(r'\"', '"').replace(r'\/', '/')
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    if not table:
        return {}
    rows = table.find_all('tr')

    def get_latest(kw):
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all(['th', 'td'])]
            if cells and kw in cells[0]:
                val = cells[1] if len(cells) > 1 else '---'
                return val.replace(',', '').replace('---', '')
        return ''

    def sf(s):
        try: return float(s)
        except: return 0.0

    stock_val = get_latest('股票投资')
    bond_val  = get_latest('债券投资')
    total_val = get_latest('资产总计')
    cash_val  = get_latest('银行存款') or get_latest('结算备付金')
    total = sf(total_val)
    if total <= 0:
        return {}
    sp = round(sf(stock_val) / total * 100, 2)
    bp = round(sf(bond_val)  / total * 100, 2)
    cp = round(sf(cash_val)  / total * 100, 2)
    period = rows[0].find_all(['th', 'td'])[1].get_text(strip=True) if len(rows[0].find_all(['th', 'td'])) > 1 else ""
    return {
        "stock_ratio": sp, "bond_ratio": bp, "cash_ratio": cp,
        "other_ratio": round(100 - sp - bp - cp, 2),
        "total_assets_wan": round(total / 10000, 2),
        "data_period": period,
    }


def _fetch_holder_structure(fund_code: str, headers: dict) -> list:
    """type=cyrjg 持有人结构"""
    url = (f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx"
           f"?type=cyrjg&code={fund_code}&year={datetime.now().year}&rt={time.time()}")
    resp = requests.get(url, headers=headers, timeout=10)
    text = resp.text
    if 'content:"' not in text:
        return []
    html = text.split('content:"')[1].split('";')[0].replace(r'\"', '"').replace(r'\/', '/')
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    if not table:
        return []
    rows = table.find_all('tr')
    header = [c.get_text(strip=True) for c in rows[0].find_all(['th', 'td'])]
    result = []
    for row in rows[1:]:
        cells = [c.get_text(strip=True) for c in row.find_all('td')]
        if len(cells) >= len(header):
            result.append(dict(zip(header, cells)))
    return result


def fetch_holdings(fund_code):
    """
    并发获取：行业分布 / 资产配置 / 持有人结构。
    top10 持仓由 analyze_quarterly_performance.py 统一管理，此处不重复拉取。
    申万行业通过 top10 持仓的股票代码批量并发查询补全（需调用方传入 top10_codes）。
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': f'http://fundf10.eastmoney.com/jjcc_{fund_code}.html'
    }

    result = {
        "fund_code": fund_code,
        "industry_distribution": [],
        "asset_allocation": {},
        "holder_structure": [],
        "data_source": "eastmoney_f10_html",
    }

    # 并发请求三个接口
    tasks = {
        "industry":  (_fetch_industry_dist,  (fund_code, headers)),
        "asset":     (_fetch_asset_alloc,    (fund_code, headers)),
        "holder":    (_fetch_holder_structure,(fund_code, headers)),
    }
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fn, *args): key for key, (fn, args) in tasks.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                val = future.result()
                if key == "industry":
                    result["industry_distribution"] = val
                elif key == "asset":
                    result["asset_allocation"] = val
                elif key == "holder":
                    result["holder_structure"] = val
            except Exception as e:
                print(f"[WARN] {key} fetch failed: {e}", file=sys.stderr)

    return result


def fetch_shenwan_for_top10(top10_codes: list) -> dict:
    """
    对外接口：批量查询 top10 持仓的申万行业。
    返回 {stock_code: shenwan_industry_name} 字典。
    """
    return _batch_shenwan_industry(top10_codes)


def analyze_concentration(holdings_data):
    """
    分析持仓集中度（兼容旧接口，top_10_ratio 由外部传入）
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

    # 获取行业分布 / 资产配置 / 持有人结构（并发）
    holdings_data = fetch_holdings(fund_code)

    # 如果命令行传入 top10 股票代码（逗号分隔），额外查询申万行业
    if len(sys.argv) >= 3:
        top10_codes = [c.strip() for c in sys.argv[2].split(',') if c.strip()]
        shenwan_map = fetch_shenwan_for_top10(top10_codes)
        holdings_data["shenwan_industry_map"] = shenwan_map
        print(f"[INFO] Shenwan industry fetched for {len(shenwan_map)} stocks", file=sys.stderr)

    print(json.dumps(holdings_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
