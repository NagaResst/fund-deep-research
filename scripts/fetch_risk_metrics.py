#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从天天基金网页直接抓取已计算好的风险指标
包括：夏普比率、最大回撤、波动率等
"""

import sys
import json
import time
import requests
import numpy as np
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

    # ── tsdata 多期指标解析（标准差/夏普近1年/2年/3年）──────────────────
    try:
        tsdata_url = f"http://fundf10.eastmoney.com/tsdata_{fund_code}.html"
        resp = requests.get(tsdata_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for row in soup.find_all('tr'):
            cells = [c.get_text(strip=True) for c in row.find_all(['th', 'td'])]
            if not cells:
                continue
            if '标准差' in cells[0] and len(cells) >= 4:
                result['volatility_1y']  = cells[1].replace('%', '')
                result['volatility_2y']  = cells[2].replace('%', '')
                result['volatility_3y']  = cells[3].replace('%', '')
                # 向前兼容：保留单值 volatility
                try:
                    result['volatility'] = float(result['volatility_1y'])
                except Exception:
                    pass
            elif '夏普比率' in cells[0] and len(cells) >= 4:
                result['sharpe_1y'] = cells[1]
                result['sharpe_2y'] = cells[2]
                result['sharpe_3y'] = cells[3]
                try:
                    result['sharpe_ratio'] = float(result['sharpe_1y'])
                except Exception:
                    pass
    except Exception as e:
        print(f"[WARN] tsdata parse failed: {e}", file=sys.stderr)

    # ── 日度最大回撤：分页拉取全量净值自行计算 ─────────────────────────
    try:
        nav_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://fundf10.eastmoney.com/'
        }
        all_records = []
        page, page_size, total = 1, 200, 9999
        while len(all_records) < total:
            url = (f"https://api.fund.eastmoney.com/f10/lsjz"
                   f"?fundCode={fund_code}&pageIndex={page}&pageSize={page_size}"
                   f"&startDate=2000-01-01&endDate=2099-12-31")
            data = requests.get(url, headers=nav_headers, timeout=15).json()
            lst = (data.get('Data') or {}).get('LSJZList') or []
            if not lst:
                break
            all_records.extend(lst)
            total = data.get('TotalCount', 0)
            if len(all_records) >= total:
                break
            page += 1
            time.sleep(0.15)

        navs, dates = [], []
        for r in reversed(all_records):           # API 返回时间降序，reversed 得升序
            raw = r.get('LJJZ') or r.get('DWJZ') or ''
            try:
                navs.append(float(raw))
                dates.append(r['FSRQ'])
            except (ValueError, TypeError):
                pass

        if len(navs) >= 10:
            nav_arr = np.array(navs)
            peak    = np.maximum.accumulate(nav_arr)
            dd      = (nav_arr - peak) / peak
            mdd_idx = int(np.argmin(dd))
            peak_idx = int(np.argmax(nav_arr[:mdd_idx + 1]))
            result['max_drawdown']          = round(float(dd[mdd_idx]), 4)
            result['max_drawdown_pct']      = f"{dd[mdd_idx]:.2%}"
            result['max_drawdown_peak_date'] = dates[peak_idx]
            result['max_drawdown_peak_nav']  = round(float(nav_arr[peak_idx]), 4)
            result['max_drawdown_trough_date'] = dates[mdd_idx]
            result['max_drawdown_trough_nav']  = round(float(nav_arr[mdd_idx]), 4)
            result['total_nav_records']     = len(navs)
            print(f"[OK] Daily MDD: {result['max_drawdown_pct']} "
                  f"({result['max_drawdown_peak_date']} → {result['max_drawdown_trough_date']})",
                  file=sys.stderr)

            # ── nav_series：全量日度净值（供 trend_segmentation / 分位数计算使用）
            result['nav_series'] = [{"date": d, "nav": round(float(v), 4)}
                                    for d, v in zip(dates, navs)]

            # ── nav_segments：基于峰谷识别的涨跌波段（阈值 ±15%）
            result['nav_segments'] = _calc_segments(navs, dates, threshold=0.15)
            print(f"[OK] nav_segments: {len(result['nav_segments'])} segments", file=sys.stderr)

    except Exception as e:
        print(f"[WARN] Daily MDD calc failed: {e}", file=sys.stderr)

    return result


def _calc_segments(navs: list, dates: list, threshold: float = 0.15) -> list:
    """
    对日度净值序列进行峰谷识别，输出涨跌波段列表。
    算法：
      1. 从起点出发，记录当前方向（初始为 unknown）
      2. 若当前方向为涨，则寻找从局部最高点下跌超过 threshold 的点 → 确认顶部
      3. 若当前方向为跌，则寻找从局部最低点上涨超过 threshold 的点 → 确认底部
      4. 每确认一个转折点，记录一段波段
    """
    if len(navs) < 2:
        return []

    segments = []
    seg_start_idx = 0
    direction = None   # 'bull' or 'bear'
    extreme_idx = 0    # 当前极值点（最高或最低）

    for i in range(1, len(navs)):
        if direction is None:
            # 初始化方向
            direction = 'bull' if navs[i] >= navs[seg_start_idx] else 'bear'
            extreme_idx = i
            continue

        if direction == 'bull':
            if navs[i] > navs[extreme_idx]:
                extreme_idx = i
            elif navs[extreme_idx] > 0 and (navs[extreme_idx] - navs[i]) / navs[extreme_idx] >= threshold:
                # 从极值跌超阈值 → 记录一段上涨波段
                change = (navs[extreme_idx] - navs[seg_start_idx]) / navs[seg_start_idx]
                segments.append({
                    "start": dates[seg_start_idx],
                    "end": dates[extreme_idx],
                    "start_nav": round(navs[seg_start_idx], 4),
                    "end_nav": round(navs[extreme_idx], 4),
                    "change_pct": round(change * 100, 2),
                    "days": (i - seg_start_idx),
                    "type": "bull"
                })
                seg_start_idx = extreme_idx
                direction = 'bear'
                extreme_idx = i

        else:  # bear
            if navs[i] < navs[extreme_idx]:
                extreme_idx = i
            elif navs[extreme_idx] > 0 and (navs[i] - navs[extreme_idx]) / navs[extreme_idx] >= threshold:
                # 从极值涨超阈值 → 记录一段下跌波段
                change = (navs[extreme_idx] - navs[seg_start_idx]) / navs[seg_start_idx]
                segments.append({
                    "start": dates[seg_start_idx],
                    "end": dates[extreme_idx],
                    "start_nav": round(navs[seg_start_idx], 4),
                    "end_nav": round(navs[extreme_idx], 4),
                    "change_pct": round(change * 100, 2),
                    "days": (extreme_idx - seg_start_idx),
                    "type": "bear"
                })
                seg_start_idx = extreme_idx
                direction = 'bull'
                extreme_idx = i

    # 末段（尚未确认转折的最后一段）
    if seg_start_idx < len(navs) - 1:
        change = (navs[-1] - navs[seg_start_idx]) / navs[seg_start_idx]
        segments.append({
            "start": dates[seg_start_idx],
            "end": dates[-1],
            "start_nav": round(navs[seg_start_idx], 4),
            "end_nav": round(navs[-1], 4),
            "change_pct": round(change * 100, 2),
            "days": len(navs) - 1 - seg_start_idx,
            "type": "bull" if change >= 0 else "bear"
        })

    return segments


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供基金代码"}, ensure_ascii=False))
        sys.exit(1)

    fund_code = sys.argv[1]

    # 解析 --output 参数
    output_path = None
    raw_args = sys.argv[2:]
    for i, arg in enumerate(raw_args):
        if arg == '--output' and i + 1 < len(raw_args):
            output_path = raw_args[i + 1]
            break

    result = fetch_risk_metrics_from_web(fund_code)
    output_str = json.dumps(result, ensure_ascii=False, indent=2)

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
