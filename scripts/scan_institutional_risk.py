#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金经理与基金公司风险扫描脚本
目标：全网搜索合规处罚、负面舆情、离职传闻等风险信号。
"""

import sys
import json
import requests

def search_risk_signals(name, fund_company):
    """
    模拟搜索风险信号（实际执行时 AI 会调用 search_web 工具，此处提供关键词逻辑）
    """
    keywords = [
        f"{name} 违规 处罚",
        f"{fund_company} 监管函",
        f"{name} 离职 传闻",
        f"{fund_company} 内幕交易",
        f"{name} 风格漂移"
    ]
    
    # 在实际 Skill 执行中，AI 会根据这些关键词去 search_web
    # 这里我们返回一个结构化的搜索计划
    return {
        "target_person": name,
        "target_company": fund_company,
        "search_keywords": keywords,
        "risk_level": "pending_ai_search" 
    }

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": True, "message": "请提供基金经理姓名和基金公司名称"}, ensure_ascii=False))
        sys.exit(1)
    
    manager_name = sys.argv[1]
    company_name = sys.argv[2]
    
    result = search_risk_signals(manager_name, company_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
