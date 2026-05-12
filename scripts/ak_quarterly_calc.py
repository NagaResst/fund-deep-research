#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用AKShare净值数据计算季度业绩
替代原 analyze_quarterly_performance.py
"""

import sys
import json
import pandas as pd
from akshare_data_fetcher import AKShareFundFetcher


def calculate_quarterly_performance(nav_df: pd.DataFrame) -> pd.DataFrame:
    """基于日度净值计算季度业绩"""
    if nav_df.empty:
        return pd.DataFrame()
    
    nav_df = nav_df.copy()
    nav_df['date'] = pd.to_datetime(nav_df['date'])
    nav_df['year'] = nav_df['date'].dt.year
    nav_df['quarter'] = nav_df['date'].dt.quarter
    
    quarterly_perf = []
    
    for (year, quarter), group in nav_df.groupby(['year', 'quarter']):
        group = group.sort_values('date')
        start_nav = group.iloc[0]['nav']
        end_nav = group.iloc[-1]['nav']
        start_date = group.iloc[0]['date']
        end_date = group.iloc[-1]['date']
        
        quarterly_return = (end_nav / start_nav - 1) * 100
        
        quarterly_perf.append({
            'year': int(year),
            'quarter': int(quarter),
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'start_nav': round(start_nav, 4),
            'end_nav': round(end_nav, 4),
            'quarterly_return_pct': round(quarterly_return, 2)
        })
    
    return pd.DataFrame(quarterly_perf)


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供基金代码"}, ensure_ascii=False))
        sys.exit(1)
    
    fund_code = sys.argv[1]
    fetcher = AKShareFundFetcher(fund_code)
    
    # 获取净值历史
    nav_df = fetcher._fetch_nav_history()
    
    # 计算季度业绩
    quarterly_df = calculate_quarterly_performance(nav_df)
    
    result = {
        "fund_code": fund_code,
        "quarterly_count": len(quarterly_df),
        "data_source": "akshare_calculation",
        "quarterly_performance": quarterly_df.to_dict('records') if not quarterly_df.empty else []
    }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
