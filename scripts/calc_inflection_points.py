#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于净值序列识别拐点
替代原 analyze_inflection_points.py
"""

import sys
import json
import numpy as np
import pandas as pd
from akshare_data_fetcher import AKShareFundFetcher
from datetime import datetime


def find_inflection_points(nav_df: pd.DataFrame, threshold: float = 0.05) -> list:
    """
    识别净值拐点（变动幅度 >= threshold）
    
    Args:
        nav_df: 包含'date'和'nav'列的DataFrame
        threshold: 拐点阈值（默认5%）
        
    Returns:
        拐点列表
    """
    if nav_df.empty or len(nav_df) < 40:
        return []
    
    navs = nav_df['nav'].values
    dates = nav_df['date'].values
    
    inflection_points = []
    window = 20
    
    for i in range(window, len(navs) - window):
        local_window = navs[i-window:i+window]
        
        # 检查是否为局部极大值
        if navs[i] == np.max(local_window):
            # 向前寻找最近的极小值
            search_start = max(0, i - window * 2)
            prev_min_idx = np.argmin(navs[search_start:i]) + search_start
            change = (navs[i] - navs[prev_min_idx]) / navs[prev_min_idx]
            
            if abs(change) >= threshold:
                inflection_points.append({
                    'start_date': str(dates[prev_min_idx])[:10],
                    'end_date': str(dates[i])[:10],
                    'start_nav': round(float(navs[prev_min_idx]), 4),
                    'end_nav': round(float(navs[i]), 4),
                    'change_pct': round(change * 100, 2),
                    'type': 'peak'
                })
        
        # 检查是否为局部极小值
        elif navs[i] == np.min(local_window):
            # 向前寻找最近的极大值
            search_start = max(0, i - window * 2)
            prev_max_idx = np.argmax(navs[search_start:i]) + search_start
            change = (navs[i] - navs[prev_max_idx]) / navs[prev_max_idx]
            
            if abs(change) >= threshold:
                inflection_points.append({
                    'start_date': str(dates[prev_max_idx])[:10],
                    'end_date': str(dates[i])[:10],
                    'start_nav': round(float(navs[prev_max_idx]), 4),
                    'end_nav': round(float(navs[i]), 4),
                    'change_pct': round(change * 100, 2),
                    'type': 'trough'
                })
    
    # 按变动幅度排序，保留前30个重要拐点
    inflection_points.sort(key=lambda x: abs(x['change_pct']), reverse=True)
    return inflection_points[:30]


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供基金代码"}, ensure_ascii=False))
        sys.exit(1)
    
    fund_code = sys.argv[1]
    fetcher = AKShareFundFetcher(fund_code)
    
    # 获取净值历史
    nav_df = fetcher._fetch_nav_history()
    
    # 识别拐点
    inflection_points = find_inflection_points(nav_df)
    
    result = {
        "fund_code": fund_code,
        "fetch_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "data_source": "akshare_calculation",
        "inflection_points": inflection_points,
        "total_points": len(inflection_points)
    }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
