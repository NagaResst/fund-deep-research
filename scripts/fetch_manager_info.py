#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金经理信息抓取脚本
获取：managerId、任职历史、在管基金数量与总规模、管理疲劳判断
数据来源：
  - fundf10.eastmoney.com/jjjl_{code}.html  → 任职记录 + managerId
  - fund.eastmoney.com/manager/{id}.html     → 在管基金数 + 总规模
用法: python3 fetch_manager_info.py <基金代码>
"""

import sys
import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


HEADERS_PC = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'http://fundf10.eastmoney.com/'
}

FATIGUE_FUND_COUNT = 10   # 在管基金数超过此值视为管理疲劳
FATIGUE_AUM_YI = 500      # 在管规模超过此值（亿元）视为管理疲劳


def _fetch_tenure_page(fund_code: str) -> str:
    """抓取任职记录页面 HTML"""
    url = f"http://fundf10.eastmoney.com/jjjl_{fund_code}.html"
    resp = requests.get(url, headers=HEADERS_PC, timeout=12)
    resp.encoding = 'utf-8'
    return resp.text


def _fetch_manager_detail_page(manager_id: str) -> str:
    """抓取经理详情页 HTML"""
    url = f"http://fund.eastmoney.com/manager/{manager_id}.html"
    resp = requests.get(url, headers=HEADERS_PC, timeout=12)
    resp.encoding = 'utf-8'
    return resp.text


def _parse_tenure_page(html: str) -> dict:
    """
    解析任职记录页面，提取：
    - 当前经理的 managerId（取最新任职行对应链接）
    - 任职历史列表
    """
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', class_=lambda c: c and 'jloff' in c)
    if not table:
        return {"tenure_history": [], "manager_ids": []}

    tenure_history = []
    manager_ids = []

    for row in table.find_all('tr')[1:]:  # 跳过表头
        cells = [c.get_text(strip=True) for c in row.find_all('td')]
        if len(cells) < 5:
            continue
        start_date = cells[0]
        end_date = cells[1]
        names_raw = cells[2]           # 可能是 "姚志鹏" 或 "姚志鹏熊昱洲"
        duration = cells[3]
        return_pct = cells[4]

        # 提取该行所有经理 href
        links = row.find_all('a', href=re.compile(r'manager/\d+\.html'))
        ids_in_row = [re.search(r'manager/(\d+)\.html', a['href']).group(1) for a in links if a.get('href')]

        # 拆分多经理姓名（姓名之间无分隔符，只能靠链接数和文字长度近似切割）
        manager_names = [a.get_text(strip=True) for a in links] if links else [names_raw]

        for mid in ids_in_row:
            if mid not in manager_ids:
                manager_ids.append(mid)

        tenure_history.append({
            "start_date": start_date,
            "end_date": end_date,
            "managers": manager_names,
            "manager_ids": ids_in_row,
            "duration": duration,
            "return_pct": return_pct,
        })

    # 当前经理取第一条（最新任职行）
    current_manager_id = manager_ids[0] if manager_ids else None
    current_managers = tenure_history[0]["managers"] if tenure_history else []

    return {
        "current_manager_id": current_manager_id,
        "current_manager_names": current_managers,
        "tenure_history": tenure_history,
        "all_manager_ids": manager_ids,
    }


def _parse_manager_detail(html: str, manager_id: str) -> dict:
    """
    解析经理详情页，提取：
    - 在管基金数量
    - 在管总规模（亿元）
    - 从业年限
    """
    result = {"manager_id": manager_id}
    soup = BeautifulSoup(html, 'html.parser')

    # 尝试从 infoItem 列表提取
    info_items = soup.find_all('div', class_=re.compile(r'info|detail|manager', re.I))

    # 尝试通用文本匹配
    text = soup.get_text(' ', strip=True)

    # 在管基金数
    m = re.search(r'在管基金[：:\s]*(\d+)\s*只', text)
    if m:
        result['current_fund_count'] = int(m.group(1))

    # 在管规模
    m = re.search(r'在管规模[：:\s]*([\d.]+)\s*亿', text)
    if m:
        result['current_aum_yi'] = float(m.group(1))

    # 从业年限
    m = re.search(r'从业[时间年限]*[：:\s]*([\d.]+)\s*年', text)
    if m:
        result['years_of_experience'] = float(m.group(1))

    # 经理姓名
    title_tag = soup.find('h1') or soup.find('title')
    if title_tag:
        name_m = re.search(r'^([^\s_-]+)', title_tag.get_text(strip=True))
        if name_m:
            result['name'] = name_m.group(1)

    # 备用：从表格提取在管信息
    if 'current_fund_count' not in result or 'current_aum_yi' not in result:
        for tbl in soup.find_all('table'):
            for row in tbl.find_all('tr'):
                cells = [c.get_text(strip=True) for c in row.find_all(['th', 'td'])]
                for i, cell in enumerate(cells):
                    if '在管基金' in cell and 'current_fund_count' not in result:
                        for j in range(i + 1, min(i + 3, len(cells))):
                            m2 = re.search(r'(\d+)', cells[j])
                            if m2:
                                result['current_fund_count'] = int(m2.group(1))
                                break
                    if '规模' in cell and 'current_aum_yi' not in result:
                        for j in range(i + 1, min(i + 3, len(cells))):
                            m2 = re.search(r'([\d.]+)', cells[j])
                            if m2:
                                result['current_aum_yi'] = float(m2.group(1))
                                break

    return result


def fetch_manager_info(fund_code: str) -> dict:
    """
    主函数：并发抓取任职记录页 + 经理详情页
    """
    result = {
        "fund_code": fund_code,
        "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_source": "eastmoney_f10",
    }

    # Step1: 先抓任职记录（需要 managerId 才能抓详情页）
    try:
        tenure_html = _fetch_tenure_page(fund_code)
        tenure_data = _parse_tenure_page(tenure_html)
    except Exception as e:
        print(f"[WARN] tenure page failed: {e}", file=sys.stderr)
        tenure_data = {"current_manager_id": None, "tenure_history": [], "current_manager_names": []}

    result["manager_id"] = tenure_data.get("current_manager_id")
    result["current_manager_names"] = tenure_data.get("current_manager_names", [])
    result["tenure_history"] = tenure_data.get("tenure_history", [])
    result["all_manager_ids"] = tenure_data.get("all_manager_ids", [])

    # Step2: 并发抓取所有出现过的经理详情页（通常 1-3 位）
    manager_ids = tenure_data.get("all_manager_ids", [])
    if not manager_ids and tenure_data.get("current_manager_id"):
        manager_ids = [tenure_data["current_manager_id"]]

    managers_detail = {}
    if manager_ids:
        with ThreadPoolExecutor(max_workers=min(len(manager_ids), 5)) as pool:
            futures = {pool.submit(_fetch_manager_detail_page, mid): mid for mid in manager_ids}
            for future in as_completed(futures):
                mid = futures[future]
                try:
                    detail_html = future.result()
                    managers_detail[mid] = _parse_manager_detail(detail_html, mid)
                except Exception as e:
                    print(f"[WARN] manager detail {mid} failed: {e}", file=sys.stderr)
                    managers_detail[mid] = {"manager_id": mid}

    result["managers_detail"] = managers_detail

    # Step3: 当前经理详情 + 管理疲劳判断
    current_mid = result.get("manager_id")
    if current_mid and current_mid in managers_detail:
        detail = managers_detail[current_mid]
        fund_count = detail.get("current_fund_count")
        aum = detail.get("current_aum_yi")
        fatigue = False
        fatigue_reasons = []
        if fund_count is not None and fund_count > FATIGUE_FUND_COUNT:
            fatigue = True
            fatigue_reasons.append(f"在管基金数 {fund_count} 只，超过 {FATIGUE_FUND_COUNT} 只阈值")
        if aum is not None and aum > FATIGUE_AUM_YI:
            fatigue = True
            fatigue_reasons.append(f"在管规模 {aum} 亿，超过 {FATIGUE_AUM_YI} 亿阈值")
        result["fatigue_risk"] = fatigue
        result["fatigue_reasons"] = fatigue_reasons
        result["current_fund_count"] = fund_count
        result["current_aum_yi"] = aum
    else:
        result["fatigue_risk"] = None
        result["fatigue_reasons"] = ["经理详情页解析失败，需联网搜索核查"]

    # Step4: 经理变更历史摘要（多人任职/历史变更次数）
    history = result.get("tenure_history", [])
    result["manager_change_count"] = max(0, len(history) - 1)
    result["has_co_management"] = any(len(h.get("managers", [])) > 1 for h in history)

    return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供基金代码"}, ensure_ascii=False))
        sys.exit(1)

    fund_code = sys.argv[1]
    data = fetch_manager_info(fund_code)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
