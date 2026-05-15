#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于净值序列计算风险指标
替代原 fetch_risk_metrics.py 的网页抓取部分
"""

import sys
import json
import numpy as np
import pandas as pd
from akshare_data_fetcher import AKShareFundFetcher
from datetime import datetime
from typing import Dict, List, Optional, Tuple


def calculate_max_drawdown(values) -> Tuple[Optional[float], Optional[int], Optional[int]]:
    if values is None or len(values) < 2:
        return None, None, None

    peaks = np.maximum.accumulate(values)
    drawdowns = (values - peaks) / peaks
    trough_idx = int(np.argmin(drawdowns))
    peak_idx = int(np.argmax(values[:trough_idx + 1]))
    return round(float(drawdowns[trough_idx]), 4), peak_idx, trough_idx


def calculate_yearly_drawdowns(nav_df: pd.DataFrame) -> List[Dict]:
    if nav_df.empty:
        return []

    yearly = []
    for year, group in nav_df.groupby(nav_df['date'].dt.year):
        series = group['nav'].to_numpy(dtype=float)
        max_drawdown, _, _ = calculate_max_drawdown(series)
        if max_drawdown is None:
            continue
        yearly.append({
            'year': int(year),
            'fund': round(abs(max_drawdown) * 100, 2),
        })

    yearly.sort(key=lambda item: item['year'], reverse=True)
    return yearly


def calculate_risk_metrics(nav_df: pd.DataFrame) -> dict:
    """
    基于日度净值计算风险指标
    
    Args:
        nav_df: 包含'date'和'nav'列的DataFrame
        
    Returns:
        风险指标字典
    """
    if nav_df.empty or len(nav_df) < 30:
        return {"error": "数据不足"}
    
    navs = nav_df['nav'].values
    dates = nav_df['date'].values
    
    result = {}
    
    # 1. 最大回撤
    max_drawdown, peak_idx, max_dd_idx = calculate_max_drawdown(navs)
    
    result['max_drawdown'] = max_drawdown
    result['max_drawdown_pct'] = f"{max_drawdown:.2%}"
    result['max_drawdown_peak_date'] = str(dates[peak_idx])[:10]
    result['max_drawdown_trough_date'] = str(dates[max_dd_idx])[:10]
    result['yearly_drawdowns'] = calculate_yearly_drawdowns(nav_df)
    
    # 2. 年化波动率
    daily_returns = np.diff(navs) / navs[:-1]
    annual_volatility = np.std(daily_returns) * np.sqrt(252)
    result['volatility'] = round(annual_volatility, 4)
    result['volatility_pct'] = f"{annual_volatility:.2%}"
    
    # 3. 年化收益率
    total_days = len(navs)
    annual_return = (navs[-1] / navs[0]) ** (252 / total_days) - 1
    result['annual_return'] = round(annual_return, 4)
    result['annual_return_pct'] = f"{annual_return:.2%}"
    
    # 4. 夏普比率（假设无风险利率3%）
    risk_free_rate = 0.03
    sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0
    result['sharpe_ratio'] = round(sharpe_ratio, 2)
    
    # 5. 索提诺比率
    downside_returns = daily_returns[daily_returns < 0]
    if len(downside_returns) > 0:
        downside_deviation = np.std(downside_returns) * np.sqrt(252)
        sortino_ratio = (annual_return - risk_free_rate) / downside_deviation if downside_deviation > 0 else 0
    else:
        sortino_ratio = 0
    result['sortino_ratio'] = round(sortino_ratio, 2)
    
    # 6. 卡玛比率
    calmar_ratio = annual_return / abs(result['max_drawdown']) if result['max_drawdown'] != 0 else 0
    result['calmar_ratio'] = round(calmar_ratio, 2)
    
    # 7. 多期指标（近1年、2年、3年）
    for period_years in [1, 2, 3]:
        period_days = period_years * 252
        if len(navs) >= period_days:
            period_navs = navs[-period_days:]
            period_returns = np.diff(period_navs) / period_navs[:-1]
            
            # 该期波动率
            period_vol = np.std(period_returns) * np.sqrt(252)
            result[f'volatility_{period_years}y'] = round(period_vol, 4)
            
            # 该期夏普比率
            period_annual_ret = (period_navs[-1] / period_navs[0]) ** (252 / len(period_navs)) - 1
            period_sharpe = (period_annual_ret - risk_free_rate) / period_vol if period_vol > 0 else 0
            result[f'sharpe_{period_years}y'] = round(period_sharpe, 2)

            # 该期最大回撤
            period_max_drawdown, _, _ = calculate_max_drawdown(period_navs)
            result[f'max_drawdown_{period_years}y'] = period_max_drawdown
    
    return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供基金代码"}, ensure_ascii=False))
        sys.exit(1)
    
    fund_code = sys.argv[1]
    fetcher = AKShareFundFetcher(fund_code)
    
    # 获取净值历史
    nav_df = fetcher._fetch_nav_history()
    
    # 计算风险指标
    risk_metrics = calculate_risk_metrics(nav_df)
    
    result = {
        "fund_code": fund_code,
        "fetch_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "data_source": "akshare_calculation",
        **risk_metrics
    }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
