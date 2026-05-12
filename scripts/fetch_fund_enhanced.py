#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版基金基础信息抓取 - 补充缺失的核心字段
包括：基金类型、成立时间、完整业绩数据、风险等级等
用法: python fetch_fund_enhanced.py <基金代码>
"""

import sys
import json
import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup


class EnhancedFundFetcher:
    """增强版基金信息抓取器"""
    
    def __init__(self, fund_code):
        self.fund_code = fund_code
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://fundf10.eastmoney.com/'
        }
        self.result = {
            "fund_code": fund_code,
            "fetch_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data_sources": []
        }
    
    def fetch_complete_info(self):
        """获取完整的基金信息（包含所有核心字段）"""
        
        # 1. 从F10页面获取基础信息
        self._fetch_from_f10_page()
        
        # 2. 从业绩页面获取历史收益
        self._fetch_performance_data()
        
        # 3. 从概况页面获取详细信息
        self._fetch_overview_data()
        
        # 4. 从档案页面获取风险等级
        self._fetch_risk_level()

        # 5. 获取最新日度净值（取 lsjz 第一页第一条，无额外翻页）
        self._fetch_latest_nav()
        
        return self.result

    def _fetch_latest_nav(self):
        """从 lsjz 接口获取最新一条日度净值"""
        try:
            url = (f"https://api.fund.eastmoney.com/f10/lsjz"
                   f"?fundCode={self.fund_code}&pageIndex=1&pageSize=1"
                   f"&startDate=2000-01-01&endDate=2099-12-31")
            nav_headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://fundf10.eastmoney.com/'
            }
            resp = requests.get(url, headers=nav_headers, timeout=10)
            data = resp.json()
            records = (data.get('Data') or {}).get('LSJZList') or []
            if records:
                r = records[0]
                nav_val = r.get('DWJZ') or r.get('LJJZ') or ''
                try:
                    self.result['current_nav'] = float(nav_val)
                except (ValueError, TypeError):
                    self.result['current_nav'] = None
                self.result['current_nav_date'] = r.get('FSRQ', '')
                acc_val = r.get('LJJZ') or r.get('DWJZ') or ''
                try:
                    self.result['current_acc_nav'] = float(acc_val)
                except (ValueError, TypeError):
                    self.result['current_acc_nav'] = None
        except Exception as e:
            print(f"[WARN] _fetch_latest_nav failed: {e}", file=sys.stderr)
    
    def _fetch_from_f10_page(self):
        """从F10概况页面获取基础信息"""
        try:
            url = f"http://fundf10.eastmoney.com/jbgk_{self.fund_code}.html"
            response = requests.get(url, headers=self.headers, timeout=15)
            response.encoding = 'utf-8'  # 强制指定编码
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                self.result["data_sources"].append("eastmoney_f10")
                
                # 提取基本信息表格
                info_table = soup.find('table', class_='info w790')
                if info_table:
                    rows = info_table.find_all('tr')
                    for row in rows:
                        ths = row.find_all('th')
                        tds = row.find_all('td')
                        
                        # F10表格是2列布局：th[0]-td[0], th[1]-td[1]
                        if len(ths) >= 2 and len(tds) >= 2:
                            # 处理第一列
                            label1 = ths[0].get_text(strip=True)
                            value1 = tds[0].get_text(strip=True)
                            self._parse_field(label1, value1)
                            
                            # 处理第二列
                            label2 = ths[1].get_text(strip=True)
                            value2 = tds[1].get_text(strip=True)
                            self._parse_field(label2, value2)
                
                # 提取当前净值和日涨跌幅
                nav_div = soup.find('div', class_='fundDetail-tit')
                if nav_div:
                    # 提取净值
                    nav_span = nav_div.find('span', class_='ui-font-large')
                    if nav_span:
                        nav_text = nav_span.get_text(strip=True)
                        nav_match = re.search(r'([\d\.]+)', nav_text)
                        if nav_match:
                            self.result["current_nav"] = float(nav_match.group(1))
                    
                    # 提取日涨跌幅
                    growth_span = nav_div.find('span', class_='ui-font-green') or nav_div.find('span', class_='ui-font-red')
                    if growth_span:
                        growth_text = growth_span.get_text(strip=True)
                        growth_match = re.search(r'([+-]?[\d\.]+)%', growth_text)
                        if growth_match:
                            self.result["daily_growth"] = float(growth_match.group(1))
                        
        except Exception as e:
            print(f"F10页面抓取失败: {e}")
    
    def _parse_field(self, label, value):
        """解析单个字段"""
        # 基金全称
        if '基金全称' in label:
            self.result["full_name"] = value
        
        # 基金简称
        elif '基金简称' in label:
            self.result["short_name"] = value
        
        # 基金代码
        elif '基金代码' in label:
            code_match = re.search(r'(\d{6})', value)
            if code_match:
                self.result["fund_code_parsed"] = code_match.group(1)
        
        # 基金类型
        elif '基金类型' in label:
            self.result["fund_type"] = value
        
        # 成立日期
        elif '成立日期' in label or '成立日' in label:
            date_match = re.search(r'(\d{4}年\d{2}月\d{2}日)', value)
            if date_match:
                self.result["found_date"] = date_match.group(1).replace('年', '-').replace('月', '-').replace('日', '')
        
        # 基金规模
        elif '基金规模' in label or '资产规模' in label:
            scale_match = re.search(r'([\d.]+)亿元', value)
            if scale_match:
                self.result["fund_scale"] = scale_match.group(1) + "亿元"
            # 份额规模
            shares_match = re.search(r'份额规模([\d.]+)亿份', value)
            if shares_match:
                self.result["shares_scale"] = shares_match.group(1) + "亿份"
        
        # 基金经理
        elif '基金经理' in label:
            self.result["manager_name"] = value
        
        # 基金公司
        elif '管理人' in label or '基金公司' in label:
            self.result["company_name"] = value
        
        # 托管人
        elif '托管人' in label:
            self.result["custodian"] = value
        
        # 风险等级
        elif '风险等级' in label:
            self.result["risk_level"] = value
        
        # 业绩比较基准
        elif '业绩比较基准' in label:
            self.result["benchmark"] = value
        
        # 管理费率
        elif '管理费率' in label:
            fee_match = re.search(r'([\d.]+)%', value)
            if fee_match:
                self.result["management_fee"] = fee_match.group(1) + "%"
        
        # 托管费率
        elif '托管费率' in label:
            fee_match = re.search(r'([\d.]+)%', value)
            if fee_match:
                self.result["custodian_fee"] = fee_match.group(1) + "%"
    
    def _fetch_performance_data(self):
        """从移动端 API 获取各阶段收益率及排名（原 JJYJ 接口已失效）"""
        # title 字段含义：Z=近1周, Y=近1月, 3Y=近3月, 6Y=近6月,
        #                  1N=近1年, 2N=近2年, 3N=近3年, 5N=近5年,
        #                  JN=今年来, LN=成立来
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
        try:
            url = ("https://fundmobapi.eastmoney.com/FundMNewApi/FundMNPeriodIncrease"
                   f"?FCODE={self.fund_code}&deviceid=x&plat=Android&product=EFund&version=1")
            mobile_headers = {'User-Agent': 'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 Mobile Safari/537.36'}
            resp = requests.get(url, headers=mobile_headers, timeout=15)
            data = resp.json()
            items = data.get('Datas') or []
            for item in items:
                title = item.get('title', '')
                syl   = item.get('syl', '')
                rank  = item.get('rank', '')
                sc    = item.get('sc', '')      # 同类总数
                avg   = item.get('avg', '')     # 同类平均
                hs300 = item.get('hs300', '')   # 沪深300
                key = TITLE_MAP.get(title)
                if key and syl not in ('', None):
                    self.result[key] = f"{syl}%"
                    if rank:
                        self.result[f"{key}_rank"] = f"{rank}/{sc}"
                    if avg:
                        self.result[f"{key}_peer_avg"] = f"{avg}%"
                    if hs300:
                        self.result[f"{key}_hs300"] = f"{hs300}%"
            if items:
                self.result['data_sources'].append('eastmoney_mobile_api_performance')
        except Exception as e:
            print(f"业绩数据API获取失败: {e}")
    
    def _fetch_performance_from_html(self):
        """从HTML页面解析业绩数据（备用方案）"""
        try:
            url = f"http://fundf10.eastmoney.com/jjjz_{self.fund_code}.html"
            response = requests.get(url, headers=self.headers, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                # 使用正则表达式直接从HTML中提取数据
                html = response.text
                
                # 匹配阶段涨幅数据
                patterns = {
                    'return_1m': r'近1?[月Y][^\d]*([+-]?[\d.]+)%',
                    'return_3m': r'近3?[月Y][^\d]*([+-]?[\d.]+)%',
                    'return_6m': r'近6?[月Y][^\d]*([+-]?[\d.]+)%',
                    'return_1y': r'近1?[年N][^\d]*([+-]?[\d.]+)%',
                    'return_2y': r'近2?[年N][^\d]*([+-]?[\d.]+)%',
                    'return_3y': r'近3?[年N][^\d]*([+-]?[\d.]+)%',
                }
                
                for key, pattern in patterns.items():
                    match = re.search(pattern, html)
                    if match:
                        self.result[key] = f"{match.group(1)}%"
                
                self.result["data_sources"].append("eastmoney_html_performance")
                        
        except Exception as e:
            print(f"业绩数据HTML解析失败: {e}")
    
    def _fetch_overview_data(self):
        """从档案页面获取更多详细信息"""
        try:
            url = f"http://fundf10.eastmoney.com/jjda_{self.fund_code}.html"
            response = requests.get(url, headers=self.headers, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                self.result["data_sources"].append("eastmoney_archive")
                
                # 提取更多详细信息
                tables = soup.find_all('table', class_='w782 comm tzxq')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        ths = row.find_all('th')
                        tds = row.find_all('td')
                        
                        if len(ths) >= 1 and len(tds) >= 1:
                            label = ths[0].get_text(strip=True)
                            value = tds[0].get_text(strip=True)
                            
                            if '申购状态' in label:
                                self.result["purchase_status"] = value
                            elif '赎回状态' in label:
                                self.result["redemption_status"] = value
                            elif '最低申购' in label:
                                self.result["min_purchase"] = value
                            elif '定投起点' in label:
                                self.result["min_sip"] = value
                                
        except Exception as e:
            print(f"档案数据抓取失败: {e}")
    
    def _fetch_risk_level(self):
        """从基金详情页 fund.eastmoney.com 解析风险等级"""
        # JBGK 私有 API 已失效，改用详情页 HTML
        self._fetch_risk_from_html()
    
    def _fetch_risk_from_html(self):
        """从HTML页面解析风险等级"""
        try:
            url = f"http://fundf10.eastmoney.com/jbgk_{self.fund_code}.html"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                # 搜索包含风险等级的文本
                import re
                risk_match = re.search(r'风险等级[：:]\s*(R\d[^<]*|[^R][^<]*?)<', response.text)
                if risk_match:
                    self.result["risk_level"] = risk_match.group(1).strip()
                    self.result["data_sources"].append("eastmoney_html_risk")
                else:
                    # 默认设置为中高风险（股票型基金）
                    if self.result.get('fund_type') == '股票型':
                        self.result["risk_level"] = "R4（中高风险）"
                    elif self.result.get('fund_type') == '混合型':
                        self.result["risk_level"] = "R3（中风险）"
                    elif self.result.get('fund_type') == '债券型':
                        self.result["risk_level"] = "R2（中低风险）"
                    else:
                        self.result["risk_level"] = "未知"
                        
        except Exception as e:
            print(f"风险等级HTML解析失败: {e}")


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供基金代码"}, ensure_ascii=False))
        sys.exit(1)
    
    fund_code = sys.argv[1]
    fetcher = EnhancedFundFetcher(fund_code)
    result = fetcher.fetch_complete_info()
    
    # 输出JSON格式
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
