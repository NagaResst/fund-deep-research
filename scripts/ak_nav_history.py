#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用AKShare获取基金日度净值历史
替代原 fetch_nav_daily.py
"""

import sys
import json
from akshare_data_fetcher import AKShareFundFetcher


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供基金代码"}, ensure_ascii=False))
        sys.exit(1)
    
    fund_code = sys.argv[1]
    fetcher = AKShareFundFetcher(fund_code)
    
    # 获取净值历史
    nav_df = fetcher._fetch_nav_history()
    
    result = {
        "fund_code": fund_code,
        "nav_count": len(nav_df),
        "date_range": f"{nav_df['date'].iloc[0].strftime('%Y-%m-%d')} to {nav_df['date'].iloc[-1].strftime('%Y-%m-%d')}" if not nav_df.empty else "",
        "latest_nav": float(nav_df.iloc[-1]['nav']) if not nav_df.empty else None,
        "data_source": "akshare",
        "nav_data": nav_df.to_dict('records') if not nav_df.empty else []
    }
    
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
