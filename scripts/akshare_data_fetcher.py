#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare 基金数据获取核心模块
封装所有 AKShare API 调用，提供统一的数据获取接口
"""

import re
import sys
from datetime import datetime
from io import StringIO

import akshare as ak
import pandas as pd
import requests


ARCHIVE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'http://fundf10.eastmoney.com/',
}


class AKShareFundFetcher:
    """AKShare 基金数据获取器"""
    
    def __init__(self, fund_code: str):
        self.fund_code = fund_code
    
    def _fetch_basic_info(self) -> dict:
        """
        获取基金基础信息
        Returns:
            dict: 包含基金全称、类型、成立日期、规模、经理、公司等字段
        """
        try:
            # 获取基金基本信息
            fund_info = ak.fund_name_em()
            fund_row = fund_info[fund_info['基金代码'] == self.fund_code]
            
            if fund_row.empty:
                return {
                    "full_name": "N/A",
                    "fund_type": "N/A",
                    "found_date": "N/A",
                    "fund_scale": "N/A",
                    "manager_name": "N/A",
                    "company_name": "N/A"
                }
            
            row = fund_row.iloc[0]
            
            # 精确字段名匹配（避免模糊匹配导致的覆盖问题）
            result = {
                "full_name": str(row.get('基金简称', 'N/A')),
                "fund_type": str(row.get('基金类型', 'N/A')),
                "found_date": str(row.get('成立日期', 'N/A')),
                "fund_scale": str(row.get('最新规模/亿', 'N/A')) + "亿元" if row.get('最新规模/亿') else "N/A",
                "manager_name": str(row.get('基金经理', 'N/A')),
                "company_name": str(row.get('基金公司', 'N/A'))
            }
            
            return result
            
        except Exception as e:
            print(f"[WARN] _fetch_basic_info failed: {e}", file=sys.stderr)
            return {
                "full_name": "N/A",
                "fund_type": "N/A",
                "found_date": "N/A",
                "fund_scale": "N/A",
                "manager_name": "N/A",
                "company_name": "N/A"
            }
    
    def _fetch_performance(self) -> dict:
        """
        获取阶段收益率数据
        Returns:
            dict: 包含各阶段收益率及排名
        """
        try:
            # 使用东方财富移动端 API 获取阶段涨幅
            url = ("https://fundmobapi.eastmoney.com/FundMNewApi/FundMNPeriodIncrease"
                   f"?FCODE={self.fund_code}&deviceid=x&plat=Android&product=EFund&version=1")
            headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 Mobile Safari/537.36'}
            resp = requests.get(url, headers=headers, timeout=15)
            data = resp.json()
            items = data.get('Datas') or []
            
            TITLE_MAP = {
                'Z':  'return_1w',
                'Y':  'return_1m',
                '3Y': 'return_3m',
                '6Y': 'return_6m',
                '1N': 'return_1y',
                '2N': 'return_2y',
                '3N': 'return_3y',
                '5N': 'return_5y',
                'JN': 'return_ytd',
                'LN': 'return_since_inception',
            }
            
            result = {}
            for item in items:
                title = item.get('title', '')
                syl = item.get('syl', '')
                rank = item.get('rank', '')
                sc = item.get('sc', '')
                avg = item.get('avg', '')
                hs300 = item.get('hs300', '')
                
                key = TITLE_MAP.get(title)
                if key and syl not in ('', None):
                    result[key] = f"{syl}%"
                    if rank:
                        result[f"{key}_rank"] = f"{rank}/{sc}"
                    if avg:
                        result[f"{key}_peer_avg"] = f"{avg}%"
                    if hs300:
                        result[f"{key}_hs300"] = f"{hs300}%"
            
            return result
            
        except Exception as e:
            print(f"[WARN] _fetch_performance failed: {e}", file=sys.stderr)
            return {}

    def _fetch_archives_performance_table(self, table_type: str) -> pd.DataFrame:
        """抓取东方财富基金档案业绩表。"""
        try:
            url = f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type={table_type}&code={self.fund_code}"
            headers = dict(ARCHIVE_HEADERS)
            headers['Referer'] = f"http://fundf10.eastmoney.com/jndzf_{self.fund_code}.html"
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = 'utf-8'

            match = re.search(r'content:"(.*)"\s*(?:,summary:.*)?};?\s*$', resp.text, re.S)
            if not match:
                return pd.DataFrame()

            html = match.group(1).replace('\\"', '"').replace('\\/', '/')
            tables = pd.read_html(StringIO(html))
            return tables[0] if tables else pd.DataFrame()
        except Exception as e:
            print(f"[WARN] _fetch_archives_performance_table({table_type}) failed: {e}", file=sys.stderr)
            return pd.DataFrame()

    def _fetch_quarter_performance_history(self) -> pd.DataFrame:
        """获取最近 8 个季度的业绩比较表。"""
        return self._fetch_archives_performance_table('quarterzf')

    def _fetch_quarter_detail_history(self) -> pd.DataFrame:
        """获取完整季度涨幅明细表。"""
        return self._fetch_archives_performance_table('jdndzf')

    def _fetch_annual_performance_history(self) -> pd.DataFrame:
        """获取年度业绩比较表。"""
        return self._fetch_archives_performance_table('yearzf')
    
    def _fetch_nav_history(self) -> pd.DataFrame:
        """
        获取日度净值历史
        Returns:
            pd.DataFrame: 包含 date 和 nav 列的 DataFrame
        """
        try:
            # 获取开放式基金净值历史（修正参数名：symbol 而非 fund）
            nav_df = ak.fund_open_fund_info_em(symbol=self.fund_code, indicator="单位净值走势")
            
            if nav_df.empty:
                return pd.DataFrame(columns=['date', 'nav'])
            
            # 重命名列并选择需要的字段
            nav_df = nav_df.rename(columns={'净值日期': 'date', '单位净值': 'nav'})
            nav_df = nav_df[['date', 'nav']].copy()
            
            # 转换数据类型
            nav_df['date'] = pd.to_datetime(nav_df['date'])
            nav_df['nav'] = pd.to_numeric(nav_df['nav'], errors='coerce')
            
            # 按日期排序
            nav_df = nav_df.sort_values('date').reset_index(drop=True)
            
            return nav_df
            
        except Exception as e:
            print(f"[WARN] _fetch_nav_history failed: {e}", file=sys.stderr)
            return pd.DataFrame(columns=['date', 'nav'])
    
    def _fetch_holdings(self, year: str = "2024") -> pd.DataFrame:
        """
        获取基金持仓结构
        Args:
            year: 年份，默认 "2024"
        Returns:
            pd.DataFrame: 持仓数据
        """
        try:
            # 获取股票持仓（修正参数名：date 而非 start_year/end_year）
            holdings_df = ak.fund_portfolio_hold_em(symbol=self.fund_code, date=year)
            
            if holdings_df.empty:
                return pd.DataFrame()
            
            return holdings_df
            
        except Exception as e:
            print(f"[WARN] _fetch_holdings failed: {e}", file=sys.stderr)
            return pd.DataFrame()
    
    def _fetch_manager_info(self) -> dict:
        """
        获取基金经理信息
        Returns:
            dict: 经理信息
        """
        try:
            # 获取基金经理信息
            manager_df = ak.fund_manager_em()
            
            if manager_df.empty:
                return {}
            
            # 筛选当前基金的经理
            # 注意：ak.fund_manager_em 返回全市场经理，需要后续过滤
            return {
                "note": "AKShare 返回全市场经理列表，需结合基金代码过滤",
                "total_managers": len(manager_df)
            }
            
        except Exception as e:
            print(f"[WARN] _fetch_manager_info failed: {e}", file=sys.stderr)
            return {}


if __name__ == "__main__":
    # 测试代码
    import sys
    if len(sys.argv) > 1:
        code = sys.argv[1]
        fetcher = AKShareFundFetcher(code)
        
        print("=== 基础信息 ===")
        basic = fetcher._fetch_basic_info()
        print(basic)
        
        print("\n=== 净值历史 ===")
        nav = fetcher._fetch_nav_history()
        print(f"共 {len(nav)} 条记录")
        if not nav.empty:
            print(nav.head())
