#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金经理信息抓取脚本（增强版 - 混合架构）
获取：managerId、任职历史、在管基金数量与总规模、管理疲劳判断、学历背景、历史业绩
数据来源：
  - AKShare: ak.fund_manager_em() → 经理基础信息、在管基金列表
  - fundf10.eastmoney.com/jjjl_{code}.html  → 任职记录 + managerId
  - fund.eastmoney.com/manager/{id}.html     → 深度信息补充
用法: python fetch_manager_info.py <基金代码>
"""

import sys
import json
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False
    print("[WARN] akshare not installed, falling back to web scraping only", file=sys.stderr)

HEADERS_PC = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'http://fundf10.eastmoney.com/'
}

FATIGUE_FUND_COUNT = 10   # 在管基金数超过此值视为管理疲劳
FATIGUE_AUM_YI = 500      # 在管规模超过此值（亿元）视为管理疲劳


def _normalize_name_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    text = str(value).strip()
    if not text:
        return []
    parts = re.split(r'[\/、,，;；]+', text)
    return [part.strip() for part in parts if part.strip()]


def _normalize_id_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _build_identity_audit(akshare_name, akshare_id, tenure_names, tenure_ids) -> dict:
    akshare_names = _normalize_name_list(akshare_name)
    akshare_ids = _normalize_id_list(akshare_id)
    tenure_names = _normalize_name_list(tenure_names)
    tenure_ids = _normalize_id_list(tenure_ids)

    name_conflict = bool(akshare_names and tenure_names and not set(akshare_names).intersection(tenure_names))
    id_conflict = bool(akshare_ids and tenure_ids and not set(akshare_ids).intersection(tenure_ids))
    has_conflict = name_conflict or id_conflict

    reasons = []
    if name_conflict:
        reasons.append(
            f"AKShare经理姓名={','.join(akshare_names)} 与任职表当前经理={','.join(tenure_names)} 不一致"
        )
    if id_conflict:
        reasons.append(
            f"AKShare经理ID={','.join(akshare_ids)} 与任职表当前经理ID={','.join(tenure_ids)} 不一致"
        )

    return {
        "has_conflict": has_conflict,
        "name_conflict": name_conflict,
        "id_conflict": id_conflict,
        "akshare_manager_names": akshare_names,
        "akshare_manager_ids": akshare_ids,
        "tenure_current_manager_names": tenure_names,
        "tenure_current_manager_ids": tenure_ids,
        "authoritative_source": "tenure_history" if tenure_names or tenure_ids else "akshare",
        "reasons": reasons,
    }


def _fetch_akshare_manager_info(fund_code: str) -> dict:
    """
    使用AKShare获取基金经理信息（优先数据源）
    
    Returns:
        {
            "manager_name": "姚志鹏",
            "current_fund_count": int,
            "current_aum_yi": float,
            "years_of_experience": float,
            "managed_funds_list": [...],
            "education": str (if available),
            "biography": str (if available)
        }
    """
    if not HAS_AKSHARE:
        return {}
    
    try:
        print(f"[INFO] 使用AKShare获取经理信息...", file=sys.stderr)
        
        # 获取基金经理数据
        manager_df = ak.fund_manager_em()
        
        if manager_df is None or manager_df.empty:
            print("[WARN] AKShare返回空数据", file=sys.stderr)
            return {}
        
        # 实际列名: ['序号', '姓名', '所属公司', '现任基金代码', '现任基金', '累计从业时间', '现任基金资产总规模', '现任基金最佳回报']
        
        # 查找当前基金的经理
        target_funds = manager_df[manager_df['现任基金代码'].astype(str).str.contains(fund_code, na=False)]
        
        if target_funds.empty:
            print(f"[WARN] 未在AKShare中找到基金 {fund_code} 的经理信息", file=sys.stderr)
            return {}
        
        # 取第一条匹配记录
        manager_row = target_funds.iloc[0]
        
        result = {
            "data_source": "akshare_fund_manager_em",
            "manager_name": manager_row.get('姓名', ''),
            "company": manager_row.get('所属公司', ''),
        }
        
        # 统计该经理的所有在管基金
        manager_name = result["manager_name"]
        if manager_name:
            same_manager = manager_df[manager_df['姓名'] == manager_name]
            result["current_fund_count"] = len(same_manager)
            
            # 总在管规模（单位：亿元）
            total_aum = manager_row.get('现任基金资产总规模')
            if total_aum and pd.notna(total_aum):
                result["current_aum_yi"] = float(total_aum)
            else:
                result["current_aum_yi"] = None
            
            # 从业年限（累计从业时间，单位：天，需要转换成年）
            cumulative_days = manager_row.get('累计从业时间')
            if cumulative_days and pd.notna(cumulative_days):
                result["years_of_experience"] = round(float(cumulative_days) / 365, 1)
            else:
                result["years_of_experience"] = None
            
            # 提取在管基金列表（仅保留代码和名称，任职回报/排名由 eastmoney 详情页补充）
            result["managed_funds_list"] = [
                {"fund_code": r["现任基金代码"], "fund_name": r["现任基金"]}
                for _, r in same_manager.iterrows()
            ]

            # 最佳回报（经理级别整体指标，非单只基金数据）
            best_return = manager_row.get('现任基金最佳回报')
            if best_return and pd.notna(best_return):
                result["manager_best_return"] = f"{float(best_return)}%"
        
        print(f"[INFO] AKShare成功获取经理信息: {result.get('manager_name')}, 在管{result.get('current_fund_count')}只基金", file=sys.stderr)
        return result
        
    except Exception as e:
        print(f"[ERROR] AKShare获取经理信息失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return {}


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
    current_manager_ids = tenure_history[0]["manager_ids"] if tenure_history else []
    current_manager_id = current_manager_ids[0] if current_manager_ids else (manager_ids[0] if manager_ids else None)
    current_managers = tenure_history[0]["managers"] if tenure_history else []

    return {
        "current_manager_id": current_manager_id,
        "current_manager_ids": current_manager_ids,
        "current_manager_names": current_managers,
        "tenure_history": tenure_history,
        "all_manager_ids": manager_ids,
    }


def _parse_managed_funds_tables(soup, manager_id: str) -> list:
    """
    解析经理详情页两张在管基金表格：
    - 任职信息表: 基金代码/名称/类型/规模/任职时间/任职天数/任职回报
    - 阶段业绩表: 近三月/近六月/近一年/近两年/今年来及各期同类排名
    返回按基金代码合并后的列表，用于报告第四章4.2节横向业绩表。

    字段名约定（供报告层读取）:
      start_date, end_date, fund_scale, tenure_days, tenure_return,
      perf_1y, rank_1y, perf_2y, rank_2y, perf_3m, perf_6m, perf_ytd
    """
    all_tables = soup.find_all('table')
    funds_map = {}  # code -> dict

    # ——— 按表头关键字定位表格（比按下标更健壮）———
    tenure_table = None
    perf_table = None
    for tbl in all_tables:
        # 取前两行的全部文本判断表格类型
        header_cells = tbl.find_all(['th', 'td'], limit=20)
        header_text = ''.join(c.get_text(strip=True) for c in header_cells)
        if tenure_table is None and ('任职时间' in header_text or '任职天数' in header_text):
            tenure_table = tbl
        elif perf_table is None and ('近三月' in header_text or '近一年' in header_text or '近1年' in header_text):
            perf_table = tbl
        if tenure_table and perf_table:
            break

    # 降级兜底：按下标
    if tenure_table is None and len(all_tables) > 1:
        tenure_table = all_tables[1]
    if perf_table is None and len(all_tables) > 2:
        perf_table = all_tables[2]

    # ——— 任职信息表 ———
    if tenure_table:
        for row in tenure_table.find_all('tr')[1:]:  # 跳过表头
            cells = [td.get_text(strip=True) for td in row.find_all('td')]
            if len(cells) < 8:
                continue
            code = cells[0].strip()
            if not code or not re.match(r'^\d{6}$', code):
                continue
            tenure_str = cells[5]
            # 解析 "2022-11-29 ~ 至今" 或 "2018-03-01 ~ 2021-06-01"
            if '~' in tenure_str:
                parts = [p.strip() for p in tenure_str.split('~', 1)]
                start_date = parts[0]
                end_date = parts[1]
            else:
                start_date = tenure_str.strip()
                end_date = None
            funds_map[code] = {
                "fund_code": code,
                "fund_name": cells[1],
                "fund_type": cells[3],
                "fund_scale": cells[4],    # 修正：原为 aum_yi
                "start_date": start_date,  # 修正：原为 tenure_start
                "end_date": end_date,      # 修正：原缺失
                "tenure_period": tenure_str,
                "tenure_days": cells[6],
                "tenure_return": cells[7],
            }

    # ——— 阶段业绩及同类排名表 ———
    # 列顺序：代码, 名称, 类型, 近三月, 同类排名, 近六月, 同类排名, 近一年, 同类排名, 近两年, 同类排名, 今年来, 同类排名
    if perf_table:
        for row in perf_table.find_all('tr')[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all('td')]
            if len(cells) < 13:
                continue
            code = cells[0].strip()
            if not code:
                continue
            perf = {
                "perf_3m": cells[3],   "rank_3m": cells[4],
                "perf_6m": cells[5],   "rank_6m": cells[6],
                "perf_1y": cells[7],   "rank_1y": cells[8],
                "perf_2y": cells[9],   "rank_2y": cells[10],
                "perf_ytd": cells[11], "rank_ytd": cells[12],
            }
            if code in funds_map:
                funds_map[code].update(perf)
            else:
                funds_map[code] = perf

    return list(funds_map.values())


def _parse_manager_detail(html: str, manager_id: str) -> dict:
    """
    解析经理详情页，提取：
    - 在管基金数量
    - 在管总规模（亿元）
    - 从业年限
    - 学历背景
    - managed_funds_table: 每只在管基金的完整任职回报与同类排名（用于4.2节）
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

    # 学历背景
    m = re.search(r'(?:学历|教育背景)[：:\s]*([^\n,，]+)', text)
    if m:
        result['education'] = m.group(1).strip()

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

    # ——— 解析每只在管基金的完整业绩表格（4.2节核心数据）———
    result['managed_funds_table'] = _parse_managed_funds_tables(soup, manager_id)

    return result


def fetch_manager_info(fund_code: str) -> dict:
    """
    主函数：混合架构获取经理信息
    1. 优先使用AKShare获取结构化数据
    2. 补充网页抓取深度信息
    3. 智能合并两套数据源
    """
    result = {
        "fund_code": fund_code,
        "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_sources": [],
    }

    # ===== Step 0: AKShare数据源（优先）=====
    akshare_data = {}
    if HAS_AKSHARE:
        akshare_data = _fetch_akshare_manager_info(fund_code)
        if akshare_data:
            result["data_sources"].append("akshare_fund_manager_em")
            # 预填充AKShare获取的字段
            result.update({
                "manager_name": akshare_data.get("manager_name"),
                "manager_id": akshare_data.get("manager_id"),
                "current_fund_count": akshare_data.get("current_fund_count"),
                "current_aum_yi": akshare_data.get("current_aum_yi"),
                "years_of_experience": akshare_data.get("years_of_experience"),
                "education": akshare_data.get("education"),
                "biography": akshare_data.get("biography"),
                "managed_funds_list": akshare_data.get("managed_funds_list", []),
            })

    # ===== Step 1: 网页抓取任职记录（补充managerId和任职历史）=====
    try:
        print(f"[INFO] 抓取任职记录页面...", file=sys.stderr)
        tenure_html = _fetch_tenure_page(fund_code)
        tenure_data = _parse_tenure_page(tenure_html)
        result["data_sources"].append("eastmoney_tenure_page")
    except Exception as e:
        print(f"[WARN] tenure page failed: {e}", file=sys.stderr)
        tenure_data = {
            "current_manager_id": None,
            "current_manager_ids": [],
            "tenure_history": [],
            "current_manager_names": [],
            "all_manager_ids": [],
        }

    result["current_manager_names"] = tenure_data.get("current_manager_names", [])
    result["current_manager_ids"] = tenure_data.get("current_manager_ids", [])
    result["manager_name_akshare"] = akshare_data.get("manager_name") if akshare_data else None
    result["manager_id_akshare"] = akshare_data.get("manager_id") if akshare_data else None

    # 合并manager_id（优先使用AKShare，其次网页）
    if not result.get("manager_id"):
        result["manager_id"] = tenure_data.get("current_manager_id")
    
    result["tenure_history"] = tenure_data.get("tenure_history", [])
    result["all_manager_ids"] = tenure_data.get("all_manager_ids", [])
    
    # 补充经理姓名（如果AKShare未提供）
    if not result.get("manager_name"):
        result["manager_name"] = tenure_data.get("current_manager_names", [])

    identity_audit = _build_identity_audit(
        result.get("manager_name_akshare") or result.get("manager_name"),
        result.get("manager_id_akshare") or result.get("manager_id"),
        tenure_data.get("current_manager_names", []),
        tenure_data.get("current_manager_ids", []),
    )
    result["manager_identity_audit"] = identity_audit
    result["manager_identity_conflict"] = identity_audit["has_conflict"]

    authoritative_names = identity_audit["tenure_current_manager_names"] or identity_audit["akshare_manager_names"]
    authoritative_ids = identity_audit["tenure_current_manager_ids"] or identity_audit["akshare_manager_ids"]
    result["authoritative_current_manager_names"] = authoritative_names
    result["authoritative_current_manager_ids"] = authoritative_ids

    if authoritative_names:
        result["manager_name"] = " / ".join(authoritative_names)
    if authoritative_ids:
        result["manager_id"] = authoritative_ids[0]

    # ===== Step 2: 并发抓取所有出现过的经理详情页（补充深度信息）=====
    manager_ids = tenure_data.get("all_manager_ids", [])
    if not manager_ids and result.get("manager_id"):
        manager_ids = [result["manager_id"]]

    managers_detail = {}
    if manager_ids:
        print(f"[INFO] 抓取 {len(manager_ids)} 位经理详情页...", file=sys.stderr)
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
        
        result["data_sources"].append("eastmoney_manager_detail")

    result["managers_detail"] = managers_detail

    # ===== Step 2.5: 用 eastmoney 详情页的完整基金表替换 AKShare 残缺列表 =====
    current_mid_for_table = result.get("manager_id")
    if not current_mid_for_table and tenure_data.get("current_manager_id"):
        current_mid_for_table = tenure_data["current_manager_id"]
    if current_mid_for_table and current_mid_for_table in managers_detail:
        full_table = managers_detail[current_mid_for_table].get("managed_funds_table", [])
        if full_table:
            result["managed_funds_list"] = full_table  # 覆盖 AKShare 的残缺列表

    # ===== Step 3: 当前经理详情 + 管理疲劳判断（智能合并）=====
    current_mid = result.get("manager_id")
    
    # 如果AKShare已有在管基金数，优先使用；否则从详情页补充
    if current_mid and current_mid in managers_detail:
        detail = managers_detail[current_mid]
        
        # 只在AKShare未提供时才使用网页数据
        if result.get("current_fund_count") is None:
            result["current_fund_count"] = detail.get("current_fund_count")
        
        if result.get("current_aum_yi") is None:
            result["current_aum_yi"] = detail.get("current_aum_yi")
        
        if result.get("years_of_experience") is None:
            result["years_of_experience"] = detail.get("years_of_experience")
        
        # 学历信息（AKShare可能没有，从详情页补充）
        if not result.get("education"):
            result["education"] = detail.get("education")
    
    # 管理疲劳判断
    fund_count = result.get("current_fund_count")
    aum = result.get("current_aum_yi")
    fatigue = False
    fatigue_reasons = []
    
    if fund_count is not None and fund_count > FATIGUE_FUND_COUNT:
        fatigue = True
        fatigue_reasons.append(f"在管基金数 {fund_count} 只，超过 {FATIGUE_FUND_COUNT} 只阈值")
    
    if aum is not None and aum > FATIGUE_AUM_YI:
        fatigue = True
        fatigue_reasons.append(f"在管规模 {aum} 亿，超过 {FATIGUE_AUM_YI} 亿阈值")
    
    result["fatigue_risk"] = fatigue
    result["fatigue_reasons"] = fatigue_reasons if fatigue_reasons else ["无明显管理疲劳风险"]

    # ===== Step 4: 经理变更历史摘要 =====
    history = result.get("tenure_history", [])
    result["manager_change_count"] = max(0, len(history) - 1)
    result["has_co_management"] = any(len(h.get("managers", [])) > 1 for h in history)

    # ===== Step 5: 数据完整性检查与提示 =====
    missing_fields = []
    if not result.get("education"):
        missing_fields.append("education")
    if result.get("current_fund_count") is None:
        missing_fields.append("current_fund_count")
    if result.get("current_aum_yi") is None:
        missing_fields.append("current_aum_yi")
    
    if missing_fields:
        result["missing_fields"] = missing_fields
        result["note"] = f"以下字段需联网搜索补充: {', '.join(missing_fields)}"
    else:
        result["note"] = "所有核心字段已成功获取"

    if result.get("manager_identity_conflict"):
        result["note"] += "；经理顶层字段与任职表存在冲突，第四章与第二章应以 tenure_history 为准"

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
