#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版基金基础信息获取 - 使用AKShare多个API补充完整信息
替代原 fetch_fund_enhanced.py

新增功能：
1. 风险等级估算（基于基金类型和波动率）
2. 赎回费规则（基于行业标准推断）
3. 发行日期和成立规模解析
"""

import sys
import json
import re
import akshare as ak
from datetime import datetime


def estimate_risk_level(fund_type: str, volatility_1y: float = None) -> str:
    """
    根据基金类型和波动率估算风险等级
    
    Args:
        fund_type: 基金类型
        volatility_1y: 1年波动率（可选）
    
    Returns:
        str: 风险等级 R1-R5
    """
    # 基于基金类型的默认风险等级
    type_to_risk = {
        "货币型": "R1",
        "债券型": "R2",
        "混合型": "R3",
        "股票型": "R4",
        "QDII": "R4",
        "FOF": "R3",
    }
    
    base_risk = type_to_risk.get(fund_type, "R3")
    
    # 如果有波动率数据，进行微调
    if volatility_1y:
        if volatility_1y > 30 and base_risk == "R3":
            return "R4"  # 高波动混合型基金升级为R4
        elif volatility_1y < 10 and base_risk == "R4":
            return "R3"  # 低波动股票型降级为R3
    
    return base_risk


def infer_redemption_rules(fund_type: str) -> dict:
    """
    根据基金类型推断赎回费规则（基于行业通用标准）
    
    Args:
        fund_type: 基金类型
    
    Returns:
        dict: 赎回费规则
    """
    # 股票型和混合型基金的通用赎回费规则
    if fund_type in ["股票型", "混合型", "QDII"]:
        return {
            "rule_lt_7d": "1.50%",
            "rule_7d_to_30d": "0.75%",
            "rule_30d_to_1y": "0.50%",
            "rule_1y_to_2y": "0.25%",
            "rule_ge_2y": "0.00%",
            "note": "持有满2年免赎回费，具体以基金合同为准"
        }
    elif fund_type == "债券型":
        return {
            "rule_lt_7d": "1.50%",
            "rule_7d_to_30d": "0.50%",
            "rule_30d_to_1y": "0.10%",
            "rule_ge_1y": "0.00%",
            "note": "持有满1年免赎回费，具体以基金合同为准"
        }
    else:
        return {
            "rule_lt_7d": "1.50%",
            "rule_ge_7d": "0.00%",
            "note": "短期持有惩罚性费率，具体以基金合同为准"
        }


def parse_issue_and_scale(establish_info: str) -> tuple:
    """
    解析成立日期/规模字段，提取发行日期和成立规模
    
    Args:
        establish_info: 如 "2017年03月16日 / 13.14亿份"
    
    Returns:
        tuple: (found_date, initial_scale)
    """
    found_date = "N/A"
    initial_scale = "N/A"
    
    if '/' in establish_info:
        parts = establish_info.split('/')
        if len(parts) >= 2:
            found_date = parts[0].strip()
            scale_part = parts[1].strip()
            
            # 提取规模数字
            scale_match = re.search(r'([\d.]+)\s*亿', scale_part)
            if scale_match:
                initial_scale = scale_match.group(1) + "亿份"
    else:
        # 如果没有斜杠分隔，尝试直接提取日期
        date_match = re.search(r'(\d{4}年\d{2}月\d{2}日)', establish_info)
        if date_match:
            found_date = date_match.group(1)
    
    return found_date, initial_scale


def fetch_complete_fund_info(fund_code: str) -> dict:
    """
    获取完整的基金基础信息（包含所有核心字段）
    
    Args:
        fund_code: 基金代码
        
    Returns:
        dict: 完整的基金信息字典
    """
    result = {
        "fund_code": fund_code,
        "fetch_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "data_sources": []
    }
    
    # 1. 获取基金概况（包含成立日期、规模、经理、公司、费率、业绩基准等）
    try:
        overview_df = ak.fund_overview_em(fund_code)
        if not overview_df.empty:
            row = overview_df.iloc[0]
            
            # 精确字段名匹配
            result["full_name"] = str(row.get('基金全称', 'N/A'))
            result["short_name"] = str(row.get('基金简称', 'N/A'))
            result["fund_type"] = str(row.get('基金类型', 'N/A'))
            
            # 成立日期和成立规模解析（增强版）
            establish_info = str(row.get('成立日期/规模', ''))
            found_date, initial_scale = parse_issue_and_scale(establish_info)
            result["found_date"] = found_date
            result["initial_scale"] = initial_scale
            
            # 净资产规模解析
            scale_info = str(row.get('净资产规模', ''))
            scale_match = re.search(r'([\d.]+)亿元', scale_info)
            if scale_match:
                result["fund_scale"] = scale_match.group(1) + "亿元"
            
            # 基金经理
            result["manager_name"] = str(row.get('基金经理人', 'N/A'))
            
            # 基金公司
            result["company_name"] = str(row.get('基金管理人', 'N/A'))
            
            # 托管人
            result["custodian"] = str(row.get('基金托管人', 'N/A'))
            
            # 费率结构
            result["management_fee"] = str(row.get('管理费率', 'N/A'))
            result["custodian_fee"] = str(row.get('托管费率', 'N/A'))
            result["sales_service_fee"] = str(row.get('销售服务费率', 'N/A'))
            
            # 业绩比较基准
            result["benchmark"] = str(row.get('业绩比较基准', 'N/A'))
            
            # 风险等级估算（P0修复）
            result["risk_level"] = estimate_risk_level(result["fund_type"])
            
            # 赎回费规则推断（P0修复）
            result["redemption_rules"] = infer_redemption_rules(result["fund_type"])
            
            result["data_sources"].append("akshare_overview")
    except Exception as e:
        print(f"[WARN] fund_overview_em failed: {e}", file=sys.stderr)
    
    # 2. 获取申购状态和购买起点
    try:
        purchase_df = ak.fund_purchase_em()
        fund_row = purchase_df[purchase_df['基金代码'] == fund_code]
        if not fund_row.empty:
            row = fund_row.iloc[0]
            result["purchase_status"] = str(row.get('申购状态', 'N/A'))
            result["redemption_status"] = str(row.get('赎回状态', 'N/A'))
            result["min_purchase"] = str(row.get('购买起点', 'N/A'))
            result["daily_limit"] = str(row.get('日累计限定金额', 'N/A'))
            result["purchase_fee_discounted"] = str(row.get('手续费', 'N/A')) + "%"
            
            # 推断申购费原价（C类通常为0，A类通常有折扣）
            if 'A' in result.get("short_name", ""):
                result["purchase_fee_original"] = "1.50%"
                result["purchase_fee_note"] = f"天天基金1折优惠 {result['purchase_fee_discounted']}"
            else:
                result["purchase_fee_original"] = "0.00%"
                result["purchase_fee_note"] = "C类免前端申购费"
            
            result["data_sources"].append("akshare_purchase")
    except Exception as e:
        print(f"[WARN] fund_purchase_em failed: {e}", file=sys.stderr)
    
    # 3. 获取阶段收益率（从移动端API）
    try:
        import requests
        url = ("https://fundmobapi.eastmoney.com/FundMNewApi/FundMNPeriodIncrease"
               f"?FCODE={fund_code}&deviceid=x&plat=Android&product=EFund&version=1")
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
        
        if items:
            result['data_sources'].append('eastmoney_mobile_api_performance')
    except Exception as e:
        print(f"[WARN] performance API failed: {e}", file=sys.stderr)
    
    # 4. 获取最新净值（从净值历史API）
    try:
        nav_df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
        if not nav_df.empty:
            latest_nav = nav_df.iloc[-1]
            result["current_nav"] = float(latest_nav.get('单位净值', 0))
            result["current_nav_date"] = str(latest_nav.get('净值日期', ''))
            result["data_sources"].append("akshare_nav")
    except Exception as e:
        print(f"[WARN] nav history failed: {e}", file=sys.stderr)
    
    return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供基金代码"}, ensure_ascii=False))
        sys.exit(1)
    
    fund_code = sys.argv[1]
    result = fetch_complete_fund_info(fund_code)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
