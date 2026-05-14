#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用AKShare净值数据计算季度业绩
替代原 analyze_quarterly_performance.py
"""

import sys
import json
import pandas as pd
from typing import Optional
from akshare_data_fetcher import AKShareFundFetcher
from calc_relative_metrics import _fetch_benchmark_with_freshness_check


DEFAULT_BENCHMARK_CODE = "000300"


def parse_percent(value) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().replace('%', '')
    if text in ('', '---', 'nan', 'None'):
        return None
    try:
        return round(float(text), 2)
    except (TypeError, ValueError):
        return None


def parse_rank(value) -> tuple:
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


def parse_archive_quarter_header(value) -> tuple:
    text = str(value).strip()
    match = pd.Series([text]).str.extract(r'(\d{2,4})年([1-4])季度').iloc[0]
    year = match[0]
    quarter = match[1]
    if pd.isna(year) or pd.isna(quarter):
        return None, None
    year_num = int(year)
    if year_num < 100:
        year_num += 2000
    return year_num, int(quarter)


def build_quarter_compare_map(detail_df: pd.DataFrame, compare_df: pd.DataFrame) -> dict:
    result = {}

    if detail_df is not None and not detail_df.empty:
        for _, row in detail_df.iterrows():
            year_text = str(row.iloc[0]).strip()
            if not year_text.endswith('年'):
                continue
            try:
                year = int(year_text[:-1])
            except ValueError:
                continue

            for quarter_index in range(1, 5):
                column_name = f'{quarter_index}季度涨幅'
                if column_name not in detail_df.columns:
                    continue
                fund_value = parse_percent(row.get(column_name))
                if fund_value is None:
                    continue
                result[(year, quarter_index)] = {
                    'fund': fund_value,
                    'peer': None,
                    'hs300': None,
                    'rank': None,
                    'rankTotal': None,
                    'quartile': None,
                }

    if compare_df is None or compare_df.empty:
        return result

    compare = compare_df.copy()
    first_col = compare.columns[0]
    compare[first_col] = compare[first_col].astype(str).str.strip()
    compare = compare.set_index(first_col)

    for header in compare.columns:
        year, quarter = parse_archive_quarter_header(header)
        if not year or not quarter:
            continue
        key = (year, quarter)
        rank, rank_total = parse_rank(compare.at['同类排名', header] if '同类排名' in compare.index else None)
        result.setdefault(key, {
            'fund': None,
            'peer': None,
            'hs300': None,
            'rank': None,
            'rankTotal': None,
            'quartile': None,
        })
        result[key].update({
            'fund': parse_percent(compare.at['阶段涨幅', header]) if '阶段涨幅' in compare.index else result[key].get('fund'),
            'peer': parse_percent(compare.at['同类平均', header]) if '同类平均' in compare.index else None,
            'hs300': parse_percent(compare.at['沪深300', header]) if '沪深300' in compare.index else None,
            'rank': rank,
            'rankTotal': rank_total,
            'quartile': None if '四分位排名' not in compare.index else str(compare.at['四分位排名', header]).strip().replace('nan', '') or None,
        })

    return result


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


def calculate_period_returns(value_df: pd.DataFrame, value_col: str) -> dict:
    """基于日度数值计算季度收益率。"""
    if value_df is None or value_df.empty:
        return {}

    value_df = value_df.copy()
    value_df['date'] = pd.to_datetime(value_df['date'])
    value_df[value_col] = pd.to_numeric(value_df[value_col], errors='coerce')
    value_df = value_df.dropna(subset=['date', value_col])
    if value_df.empty:
        return {}

    value_df['year'] = value_df['date'].dt.year
    value_df['quarter'] = value_df['date'].dt.quarter

    period_returns = {}
    for (year, quarter), group in value_df.groupby(['year', 'quarter']):
        group = group.sort_values('date')
        start_value = group.iloc[0][value_col]
        end_value = group.iloc[-1][value_col]

        if pd.isna(start_value) or pd.isna(end_value) or start_value == 0:
            continue

        period_returns[(int(year), int(quarter))] = {
            'start_date': group.iloc[0]['date'].strftime('%Y-%m-%d'),
            'end_date': group.iloc[-1]['date'].strftime('%Y-%m-%d'),
            'start_value': round(float(start_value), 4),
            'end_value': round(float(end_value), 4),
            'return_pct': round(float((end_value / start_value - 1) * 100), 2),
        }

    return period_returns


def calculate_quarterly_performance(nav_df: pd.DataFrame, benchmark_df: Optional[pd.DataFrame] = None, compare_map: Optional[dict] = None) -> pd.DataFrame:
    """基于日度净值和基准价格计算季度业绩。"""
    if nav_df.empty:
        return pd.DataFrame()

    fund_returns = calculate_period_returns(nav_df, 'nav')
    benchmark_returns = calculate_period_returns(benchmark_df, 'price') if benchmark_df is not None else {}
    compare_map = compare_map or {}

    quarterly_perf = []
    for (year, quarter), period in sorted(fund_returns.items()):
        benchmark_period = benchmark_returns.get((year, quarter), {})
        compare = compare_map.get((year, quarter), {})
        fund_value = compare.get('fund') if compare.get('fund') is not None else period['return_pct']
        hs300_value = compare.get('hs300') if compare.get('hs300') is not None else benchmark_period.get('return_pct')
        quarterly_perf.append({
            'year': year,
            'quarter': quarter,
            'quarter_label': f'{year}Q{quarter}',
            'start_date': period['start_date'],
            'end_date': period['end_date'],
            'start_nav': period['start_value'],
            'end_nav': period['end_value'],
            'quarterly_return_pct': fund_value,
            'fund': fund_value,
            'peer': compare.get('peer'),
            'hs300': hs300_value,
            'rank': compare.get('rank'),
            'rankTotal': compare.get('rankTotal'),
            'quartile': compare.get('quartile'),
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
    quarter_detail_df = fetcher._fetch_quarter_detail_history()
    quarter_compare_df = fetcher._fetch_quarter_performance_history()
    quarter_compare_map = build_quarter_compare_map(quarter_detail_df, quarter_compare_df)

    benchmark_df = None
    benchmark_source = None
    benchmark_error = None
    if not nav_df.empty:
        try:
            benchmark_df, benchmark_source = _fetch_benchmark_with_freshness_check(
                DEFAULT_BENCHMARK_CODE,
                pd.to_datetime(nav_df['date']).max()
            )
        except Exception as e:
            benchmark_error = str(e)

    # 计算季度业绩
    quarterly_df = calculate_quarterly_performance(nav_df, benchmark_df, quarter_compare_map)
    
    result = {
        "fund_code": fund_code,
        "quarterly_count": len(quarterly_df),
        "data_source": "akshare_calculation",
        "benchmark_code": DEFAULT_BENCHMARK_CODE,
        "benchmark_source": benchmark_source,
        "comparison_source": "eastmoney_fund_archives_quarterzf",
        "quarterly_performance": to_serializable_records(quarterly_df)
    }

    if benchmark_error:
        result["benchmark_error"] = benchmark_error
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
