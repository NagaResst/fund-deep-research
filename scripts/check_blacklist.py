#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
黑名单检查脚本
检查基金公司和基金经理是否在黑名单中
输出JSON格式
"""

import sys
import json
import os


def load_blacklist():
    """
    加载黑名单配置
    
    Returns:
        dict: 黑名单数据
    """
    # 黑名单配置文件路径
    blacklist_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "日常工作流",
        "投资者画像",
        "投资者画像.md"
    )
    
    blacklist = {
        "companies": [],
        "managers": []
    }
    
    try:
        with open(blacklist_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 提取景顺长城
            if "景顺长城" in content:
                blacklist["companies"].append({
                    "name": "景顺长城",
                    "reason": "2021年购入景顺长城新兴成长混合A后亏损49%，管理风格与风险控制能力不符"
                })
            
            # 提取刘彦春
            if "刘彦春" in content:
                blacklist["managers"].append({
                    "name": "刘彦春",
                    "reason": "投资风格过于集中、风控不足，深度套牢近5年"
                })
        
        return blacklist
        
    except Exception as e:
        # 如果无法读取文件，使用硬编码的黑名单
        return {
            "companies": [
                {
                    "name": "景顺长城",
                    "reason": "管理风格与风险控制能力不符"
                }
            ],
            "managers": [
                {
                    "name": "刘彦春",
                    "reason": "投资风格过于集中、风控不足"
                }
            ]
        }


def check_blacklist(company_name, manager_name):
    """
    检查是否在黑名单中
    
    Args:
        company_name: 基金公司名称
        manager_name: 基金经理姓名
        
    Returns:
        dict: 检查结果
    """
    blacklist = load_blacklist()
    
    result = {
        "company_check": {
            "name": company_name,
            "in_blacklist": False,
            "reason": ""
        },
        "manager_check": {
            "name": manager_name,
            "in_blacklist": False,
            "reason": ""
        },
        "overall_result": "通过"
    }
    
    # 检查公司
    for item in blacklist["companies"]:
        if item["name"] in company_name:
            result["company_check"]["in_blacklist"] = True
            result["company_check"]["reason"] = item["reason"]
            result["overall_result"] = "不通过"
            break
    
    # 检查经理
    for item in blacklist["managers"]:
        if item["name"] in manager_name:
            result["manager_check"]["in_blacklist"] = True
            result["manager_check"]["reason"] = item["reason"]
            result["overall_result"] = "不通过"
            break
    
    return result


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": True, "message": "请提供基金公司和基金经理名称"}, ensure_ascii=False))
        sys.exit(1)
    
    company_name = sys.argv[1]
    manager_name = sys.argv[2]
    
    result = check_blacklist(company_name, manager_name)
    
    # 输出JSON格式
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
