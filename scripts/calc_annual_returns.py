#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于日度净值计算年度收益率
新增功能：原方案通过季度复合计算，新方案直接年初年末比值
"""

import sys
import json
import pandas as pd
from akshare_data_fetcher import AKShareFundFetcher
from datetime import datetime


def calculate_annual_returns(nav_df: pd.DataFrame) -> pd.DataFrame:
    """
    计算每年的收益率
    
    Args:
        nav_df: 包含'date'和'nav'列的DataFrame
        
    Returns:
        年度收益率DataFrame
    """
    if nav_df.empty:
        return pd.DataFrame()
    
    nav_df = nav_df.copy()
    nav_df['date'] = pd.to_datetime(nav_df['date'])
    nav_df['year'] = nav_df['date'].dt.year
    
    annual_returns = []
    
    for year in sorted(nav_df['year'].unique()):
        year_data = nav_df[nav_df['year'] == year].sort_values('date')
        
        if len(year_data) < 2:
            continue
        
        start_nav = year_data.iloc[0]['nav']
        end_nav = year_data.iloc[-1]['nav']
        start_date = year_data.iloc[0]['date']
        end_date = year_data.iloc[-1]['date']
        
        annual_return = (end_nav / start_nav - 1) * 100
        
        annual_returns.append({
            'year': int(year),
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'start_nav': round(start_nav, 4),
            'end_nav': round(end_nav, 4),
            'annual_return_pct': round(annual_return, 2)
        })
    
    return pd.DataFrame(annual_returns)


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供基金代码"}, ensure_ascii=False))
        sys.exit(1)
    
    fund_code = sys.argv[1]
    fetcher = AKShareFundFetcher(fund_code)
    
    # 获取净值历史
    nav_df = fetcher._fetch_nav_history()
    
    # 计算年度收益率
    annual_df = calculate_annual_returns(nav_df)
    
    result = {
        "fund_code": fund_code,
        "fetch_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "data_source": "akshare_calculation",
        "annual_returns": annual_df.to_dict('records')
    }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
