#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多数据源基金信息抓取模块
支持天天基金、新浪财经、腾讯财经等多个数据源
优先使用API，失败时降级到HTML解析
"""

import requests
import json
import re
import sys
from datetime import datetime
from bs4 import BeautifulSoup


class FundDataFetcher:
    """基金数据抓取器"""
    
    def __init__(self, fund_code):
        self.fund_code = fund_code
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://fundf10.eastmoney.com/'
        }
    
    def fetch_from_eastmoney_api(self):
        """从天天基金API获取数据"""
        try:
            # 尝试多个API端点
            apis = [
                f"http://api.fund.eastmoney.com/f10/JBGK?fundCode={self.fund_code}",
                f"http://fundgz.1234567.com.cn/js/{self.fund_code}.js",
            ]
            
            for api_url in apis:
                try:
                    response = requests.get(api_url, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        content = response.text
                        
                        # 处理JavaScript格式
                        if 'jsonpgz' in content:
                            start = content.find('{')
                            end = content.rfind('}') + 1
                            content = content[start:end]
                        
                        data = json.loads(content)
                        
                        if data.get("Data") or data.get("fundcode"):
                            return self._parse_eastmoney_data(data)
                except:
                    continue
            
            return None
        except Exception as e:
            print(f"天天基金API失败: {e}")
            return None
    
    def fetch_from_sina_api(self):
        """从新浪财经API获取数据"""
        try:
            url = f"http://hq.sinajs.cn/list=f_{self.fund_code}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                # 格式：var hq_str_f_009520="基金名称,净值,日期,...";
                match = re.search(r'="([^"]+)"', content)
                if match:
                    fields = match.group(1).split(',')
                    if len(fields) >= 5:
                        return {
                            "fund_name": fields[0],
                            "current_nav": float(fields[1]) if fields[1] else 0,
                            "nav_date": fields[2],
                            "daily_growth": float(fields[3]) if fields[3] else 0,
                        }
            return None
        except Exception as e:
            print(f"新浪财经API失败: {e}")
            return None
    
    def fetch_from_html(self):
        """从HTML页面解析数据（备用方案）"""
        try:
            url = f"http://fundf10.eastmoney.com/jbgk_{self.fund_code}.html"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                result = {}
                
                # 提取基本信息表格
                tables = soup.find_all('table', class_='info w790')
                if tables:
                    table = tables[0]
                    rows = table.find_all('tr')
                    
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True)
                            value = cells[1].get_text(strip=True)
                            
                            if '基金类型' in label:
                                result['fund_type'] = value
                            elif '成立时间' in label:
                                result['establish_date'] = value
                            elif '成立规模' in label or '资产规模' in label:
                                result['fund_scale'] = value
                            elif '基金经理' in label:
                                result['manager_name'] = value
                            elif '基金公司' in label or '管理人' in label:
                                result['company_name'] = value
                
                # 提取费率信息
                fee_table = soup.find('table', class_='tol')
                if fee_table:
                    fee_rows = fee_table.find_all('tr')
                    for row in fee_rows:
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True)
                            value = cells[1].get_text(strip=True)
                            
                            if '管理费' in label:
                                result['management_fee'] = value
                            elif '托管费' in label:
                                result['custodian_fee'] = value
                            elif '销售服务费' in label:
                                result['sales_service_fee'] = value
                
                return result if result else None
            
            return None
        except Exception as e:
            print(f"HTML解析失败: {e}")
            return None
    
    def fetch_from_tencent_api(self):
        """从腾讯财经API获取数据"""
        try:
            url = f"http://web.ifzq.gtimg.cn/fund/newfund/fundSsgz/getFundSsgz?app=web&symbol={self.fund_code}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    fund_data = data["data"]
                    return {
                        "fund_name": fund_data.get("name", ""),
                        "current_nav": float(fund_data.get("dwjz", 0)),
                        "nav_date": fund_data.get("jzrq", ""),
                    }
            return None
        except Exception as e:
            print(f"腾讯财经API失败: {e}")
            return None
    
    def _parse_eastmoney_data(self, data):
        """解析天天基金数据"""
        result = {}
        
        # 处理不同的数据格式
        if data.get("Data"):
            info = data["Data"]
            result.update({
                "fund_type": info.get("FundType", ""),
                "establish_date": info.get("EstablishDate", ""),
                "fund_scale": info.get("EndAssetScale", ""),
                "manager_name": info.get("FundManagerName", ""),
                "company_name": info.get("FundCompanyName", ""),
                "risk_level": info.get("RiskLevel", ""),
            })
        elif data.get("fundcode"):
            result.update({
                "fund_name": data.get("name", ""),
                "current_nav": float(data.get("dwjz", 0)),
                "nav_date": data.get("jzrq", ""),
                "daily_growth": float(data.get("gszzl", 0)),
            })
        
        return result
    
    def fetch_all(self):
        """从所有数据源获取数据并合并"""
        result = {
            "fund_code": self.fund_code,
            "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data_sources": []
        }
        
        # 尝试各个数据源
        sources = [
            ("eastmoney_api", self.fetch_from_eastmoney_api),
            ("sina_api", self.fetch_from_sina_api),
            ("tencent_api", self.fetch_from_tencent_api),
            ("html_parse", self.fetch_from_html),
        ]
        
        for source_name, fetch_func in sources:
            try:
                data = fetch_func()
                if data:
                    result.update(data)
                    result["data_sources"].append(source_name)
                    print(f"[OK] {source_name} success", file=sys.stderr)
                else:
                    print(f"[WARN] {source_name} no data", file=sys.stderr)
            except Exception as e:
                print(f"[ERROR] {source_name} failed: {e}", file=sys.stderr)
        
        return result


def main():
    import sys
    
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供基金代码"}, ensure_ascii=False))
        sys.exit(1)
    
    fund_code = sys.argv[1]
    fetcher = FundDataFetcher(fund_code)
    result = fetcher.fetch_all()
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
