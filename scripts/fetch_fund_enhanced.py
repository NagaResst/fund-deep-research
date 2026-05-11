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
        
        return self.result
    
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
        """从业绩页面获取历史收益率（使用API）"""
        try:
            # 使用天天基金API获取阶段涨幅
            url = f"http://api.fund.eastmoney.com/f10/JJYJ?fundCode={self.fund_code}"
            response = requests.get(url, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, dict) and data.get('Data'):
                    perf_data = data['Data']
                    self.result["data_sources"].append("eastmoney_api_performance")
                    
                    # 提取各阶段收益率
                    if perf_data.get('SYL'):
                        syl = perf_data['SYL']
                        if syl.get('Y'):  # 近1月
                            self.result["return_1m"] = f"{syl['Y']}%"
                        if syl.get('3Y'):  # 近3月
                            self.result["return_3m"] = f"{syl['3Y']}%"
                        if syl.get('6Y'):  # 近6月
                            self.result["return_6m"] = f"{syl['6Y']}%"
                        if syl.get('1N'):  # 近1年
                            self.result["return_1y"] = f"{syl['1N']}%"
                        if syl.get('2N'):  # 近2年
                            self.result["return_2y"] = f"{syl['2N']}%"
                        if syl.get('3N'):  # 近3年
                            self.result["return_3y"] = f"{syl['3N']}%"
                        if syl.get('JN'):  # 今年来
                            self.result["return_ytd"] = f"{syl['JN']}%"
                        if syl.get('LN'):  # 成立来
                            self.result["return_since_inception"] = f"{syl['LN']}%"
                    
                    # 提取排名信息
                    if perf_data.get('Rank'):
                        rank_data = perf_data['Rank']
                        if rank_data.get('1N'):
                            self.result["rank_1y"] = rank_data['1N']
                            
        except Exception as e:
            print(f"业绩数据API获取失败: {e}")
            # API失败时尝试HTML解析（备用方案）
            self._fetch_performance_from_html()
    
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
        """从基金详情页面获取风险等级"""
        try:
            # 尝试从天天基金API获取
            url = f"http://api.fund.eastmoney.com/f10/JBGK?fundCode={self.fund_code}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, dict) and data.get('Data'):
                    fund_info = data['Data']
                    
                    # 风险等级
                    if fund_info.get('RISKLEVEL'):
                        self.result["risk_level"] = fund_info['RISKLEVEL']
                        self.result["data_sources"].append("eastmoney_api")
                    
                    # 如果API没有返回，尝试从HTML页面解析
                    if 'risk_level' not in self.result:
                        self._fetch_risk_from_html()
                        
        except Exception as e:
            print(f"风险等级API获取失败: {e}")
            # API失败时尝试HTML解析
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
