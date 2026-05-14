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


def parse_percent(value):
    if value is None:
        return None
    text = str(value).strip().replace('%', '')
    if text in ('', '---', 'nan', 'None'):
        return None
    try:
        return round(float(text), 2)
    except (TypeError, ValueError):
        return None


def parse_rank(value):
    if value is None:
        return None, None
    text = str(value).strip().replace(' ', '')
    if text in ('', '---', 'nan', 'None'):
        return None, None
    separator = '|' if '|' in text else '/'
    if separator not in text:
        try:
            return int(text), None
        except ValueError:
            return None, None
    rank_text, total_text = text.split(separator, 1)
    try:
        rank = int(rank_text)
    except ValueError:
        rank = None
    try:
        total = int(total_text)
    except ValueError:
        total = None
    return rank, total


def build_annual_compare_map(compare_df: pd.DataFrame) -> dict:
    if compare_df is None or compare_df.empty:
        return {}

    compare = compare_df.copy()
    first_col = compare.columns[0]
    compare[first_col] = compare[first_col].astype(str).str.strip()
    compare = compare.set_index(first_col)

    result = {}
    for header in compare.columns:
      year_text = str(header).strip().replace('年度', '')
      if not year_text.isdigit():
          continue
      year = int(year_text)
      rank, rank_total = parse_rank(compare.at['同类排名', header] if '同类排名' in compare.index else None)
      result[year] = {
          'fund': parse_percent(compare.at['阶段涨幅', header]) if '阶段涨幅' in compare.index else None,
          'peer': parse_percent(compare.at['同类平均', header]) if '同类平均' in compare.index else None,
          'hs300': parse_percent(compare.at['沪深300', header]) if '沪深300' in compare.index else None,
          'rank': rank,
          'rankTotal': rank_total,
          'quartile': None if '四分位排名' not in compare.index else str(compare.at['四分位排名', header]).strip().replace('nan', '') or None,
      }
    return result


def merge_annual_comparison(annual_df: pd.DataFrame, annual_compare_map: dict, ytd_data: dict = None) -> pd.DataFrame:
    rows = []
    current_year = datetime.now().year
    ytd_data = ytd_data or {}

    for _, row in annual_df.iterrows():
        year = int(row['year'])
        compare = annual_compare_map.get(year, {})
        fund_value = compare.get('fund') if compare.get('fund') is not None else row['annual_return_pct']
        if year == current_year:
            fund_value = ytd_data.get('fund', fund_value)
            compare = {
                **compare,
                'peer': ytd_data.get('peer', compare.get('peer')),
                'hs300': ytd_data.get('hs300', compare.get('hs300')),
                'rank': ytd_data.get('rank', compare.get('rank')),
                'rankTotal': ytd_data.get('rankTotal', compare.get('rankTotal')),
            }

        rows.append({
            'year': year,
            'start_date': row['start_date'],
            'end_date': row['end_date'],
            'start_nav': row['start_nav'],
            'end_nav': row['end_nav'],
            'annual_return_pct': fund_value,
            'fund': fund_value,
            'peer': compare.get('peer'),
            'hs300': compare.get('hs300'),
            'rank': compare.get('rank'),
            'rankTotal': compare.get('rankTotal'),
            'quartile': compare.get('quartile'),
        })

    return pd.DataFrame(rows)


def to_serializable_records(dataframe: pd.DataFrame) -> list:
    if dataframe is None or dataframe.empty:
        return []

    sanitized = dataframe.astype(object).where(pd.notna(dataframe), None)
    records = sanitized.to_dict('records')
    for record in records:
        for key in ('rank', 'rankTotal'):
            value = record.get(key)
            if isinstance(value, float) and value.is_integer():
                record[key] = int(value)
    return records


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
    annual_compare_df = fetcher._fetch_annual_performance_history()
    stage_performance = fetcher._fetch_performance()
    annual_compare_map = build_annual_compare_map(annual_compare_df)

    ytd_data = {
        'fund': parse_percent(stage_performance.get('return_ytd')),
        'peer': parse_percent(stage_performance.get('return_ytd_peer_avg')),
        'hs300': parse_percent(stage_performance.get('return_ytd_hs300')),
    }
    rank, rank_total = parse_rank(stage_performance.get('return_ytd_rank'))
    ytd_data['rank'] = rank
    ytd_data['rankTotal'] = rank_total
    
    # 计算年度收益率
    annual_df = calculate_annual_returns(nav_df)
    annual_df = merge_annual_comparison(annual_df, annual_compare_map, ytd_data)
    
    result = {
        "fund_code": fund_code,
        "fetch_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "data_source": "akshare_calculation",
        "comparison_source": "eastmoney_fund_archives_yearzf",
        "annual_returns": to_serializable_records(annual_df)
    }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
