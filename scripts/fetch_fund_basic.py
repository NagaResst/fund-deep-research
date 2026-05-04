#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金基础信息抓取脚本（增强版）
使用多数据源策略，确保获取最新数据
输出JSON格式，便于AI解析
"""

import sys
import json
import os
sys.path.insert(0, os.path.dirname(__file__))

from fetch_fund_multi_source import FundDataFetcher


def fetch_fund_basic_info(fund_code):
    """
    抓取基金基础信息（多数据源）
    
    Args:
        fund_code: 基金代码
        
    Returns:
        dict: 基金基础信息
    """
    try:
        fetcher = FundDataFetcher(fund_code)
        result = fetcher.fetch_all()
        return result
    except Exception as e:
        return {
            "error": True,
            "message": f"抓取失败: {str(e)}",
            "fund_code": fund_code
        }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供基金代码"}, ensure_ascii=False))
        sys.exit(1)
    
    fund_code = sys.argv[1]
    result = fetch_fund_basic_info(fund_code)
    
    # 输出JSON格式
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
