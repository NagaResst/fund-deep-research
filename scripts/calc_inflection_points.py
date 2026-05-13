#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于净值序列识别拐点（Zigzag 算法 + 基金类型自适应）

算法保证：
  - 每个区间内趋势方向单一（先上后下 / 先下后上的复合区间会被自动拆分）
  - 所有超过阈值的趋势转折点均分类为 'major'
  - 使用 minor 阈值作为唯一判定门槛（大于 minor 阈值即为 major）

基金类型自适应阈值：
  R4/R5 股票型/偏股混合  → 10%（原 minor 阈值，现为单一判定门槛）
  R3    混合型/灵活配置   → 6%
  R1/R2 债券型/固收类    → 1.5%
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from akshare_data_fetcher import AKShareFundFetcher


def get_fund_params(fund_code: str) -> dict:
    """根据基金风险等级/类型自适应调整分析参数"""
    raw_dir = f"/tmp/fund_research_{fund_code}/raw"
    fe_path = os.path.join(raw_dir, "fund_enhanced.json")

    risk_level = ''
    fund_type = ''
    if os.path.exists(fe_path):
        try:
            with open(fe_path, encoding='utf-8') as f:
                fe = json.load(f)
            risk_level = fe.get('risk_level', '')
            fund_type = str(fe.get('fund_type', '') or fe.get('fund_category', ''))
        except Exception:
            pass

    equity_kw  = ['股票', '指数', '科创', 'ETF', '创业板', '沪深300', '中证']
    bond_kw    = ['债', '固收', '货币', '理财']
    mixed_kw   = ['混合', '灵活', '平衡', '配置']

    if risk_level in ('R4', 'R5') or any(k in fund_type for k in equity_kw):
        return dict(
            major=dict(window=60, threshold=0.20),
            minor=dict(window=20, threshold=0.10),
            dedup_days=15,
            fund_category='equity',
        )
    elif risk_level in ('R1', 'R2') or any(k in fund_type for k in bond_kw):
        return dict(
            major=dict(window=30, threshold=0.03),
            minor=dict(window=10, threshold=0.015),
            dedup_days=7,
            fund_category='bond',
        )
    elif risk_level == 'R3' or any(k in fund_type for k in mixed_kw):
        return dict(
            major=dict(window=40, threshold=0.12),
            minor=dict(window=15, threshold=0.06),
            dedup_days=10,
            fund_category='balanced',
        )
    else:
        # 默认：中等敏感度
        return dict(
            major=dict(window=40, threshold=0.15),
            minor=dict(window=20, threshold=0.08),
            dedup_days=10,
            fund_category='unknown',
        )


def find_zigzag_points(navs: np.ndarray, dates: np.ndarray,
                        threshold: float,
                        include_last: bool = True) -> list:
    """
    Zigzag 算法：识别所有幅度 >= threshold 的趋势转折点。

    保证：每个区间内趋势方向单一。如果旧算法中某个 major 区间内部包含
    方向相反且幅度 >= threshold 的子运动，该子运动的极值会被独立记录为
    一个新的 major 拐点，原区间自动被拆分。

    所有检测到的拐点统一分类为 'major'（超过 minor 阈值即为 major）。

    include_last: 若为 True，则将序列末尾尚未被反向运动确认的极值也纳入输出，
                  避免遗漏最新一段尚未反转的大行情。
    """
    n = len(navs)
    if n < 10:
        return []

    # --- Phase 1: 确定确认序列 (idx, 'peak'|'trough') ---
    # 追踪当前趋势方向；当反向幅度 >= threshold 时，确认当前极值点并切换方向
    confirmed = []        # list of (idx, type)
    extreme_idx = 0
    extreme_nav = float(navs[0])
    direction   = None   # None | 'up' | 'down'

    for i in range(1, n):
        cur = float(navs[i])

        if direction is None:
            if (cur - extreme_nav) / extreme_nav >= threshold:
                direction   = 'up'
                extreme_idx = i
                extreme_nav = cur
            elif (extreme_nav - cur) / extreme_nav >= threshold:
                direction   = 'down'
                extreme_idx = i
                extreme_nav = cur

        elif direction == 'up':
            if cur >= extreme_nav:
                extreme_idx = i
                extreme_nav = cur
            elif (extreme_nav - cur) / extreme_nav >= threshold:
                confirmed.append((extreme_idx, 'peak'))
                direction   = 'down'
                extreme_idx = i
                extreme_nav = cur

        else:  # direction == 'down'
            if cur <= extreme_nav:
                extreme_idx = i
                extreme_nav = cur
            elif (cur - extreme_nav) / extreme_nav >= threshold:
                confirmed.append((extreme_idx, 'trough'))
                direction   = 'up'
                extreme_idx = i
                extreme_nav = cur

    # 末尾未确认的极值：将正在追踪的极值也纳入（反映最新趋势段）
    if include_last and direction is not None:
        if not confirmed or confirmed[-1][0] != extreme_idx:
            pt_type = 'peak' if direction == 'up' else 'trough'
            confirmed.append((extreme_idx, pt_type))

    if not confirmed:
        return []

    # --- Phase 2: 构建区间 ---
    # 每个确认点的 start = 前一个确认点（首个点的 start 取 [0, idx] 中的对向极值）
    result = []
    for k, (idx, pt_type) in enumerate(confirmed):
        if k == 0:
            if pt_type == 'peak':
                start_idx = int(np.argmin(navs[:idx + 1]))
            else:
                start_idx = int(np.argmax(navs[:idx + 1]))
        else:
            start_idx = confirmed[k - 1][0]

        s_nav = float(navs[start_idx])
        e_nav = float(navs[idx])
        result.append({
            'start_date': str(dates[start_idx])[:10],
            'end_date':   str(dates[idx])[:10],
            'start_nav':  round(s_nav, 4),
            'end_nav':    round(e_nav, 4),
            'change_pct': round((e_nav - s_nav) / s_nav * 100, 2),
            'type':       pt_type,
            'level':      'major',
        })

    return result


def find_inflection_points(nav_df: pd.DataFrame, fund_code: str) -> tuple:
    """
    Zigzag 拐点识别（自适应基金类型）。
    使用 minor 阈值作为检测门槛，所有超过该阈值的趋势转折点均为 major。
    Returns: (points_list, params_dict)
    """
    if nav_df.empty or len(nav_df) < 40:
        return [], {}

    params    = get_fund_params(fund_code)
    navs      = nav_df['nav'].values
    dates     = nav_df['date'].values
    threshold = params['minor']['threshold']   # 大于 minor 阈值即为 major

    points = find_zigzag_points(navs, dates, threshold)
    return points, params



def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供基金代码"}, ensure_ascii=False))
        sys.exit(1)

    fund_code = sys.argv[1]
    fetcher = AKShareFundFetcher(fund_code)
    nav_df = fetcher._fetch_nav_history()

    inflection_points, params = find_inflection_points(nav_df, fund_code)

    major_count = sum(1 for p in inflection_points if p['level'] == 'major')
    minor_count  = sum(1 for p in inflection_points if p['level'] == 'minor')

    result = {
        "fund_code":         fund_code,
        "fetch_time":        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "data_source":       "akshare_calculation",
        "fund_category":     params.get('fund_category', 'unknown'),
        "params_used":       params,
        "inflection_points": inflection_points,
        "total_points":      len(inflection_points),
        "major_points":      major_count,
        "minor_points":      minor_count,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
