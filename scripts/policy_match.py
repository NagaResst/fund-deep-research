#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政策匹配度评估脚本
评估基金是否符合"十五五"规划方向
输出JSON格式
"""

import sys
import json


# "十五五"规划重点支持行业
POLICY_SUPPORTED_INDUSTRIES = {
    "新能源": ["新能源", "光伏", "风电", "储能", "锂电池", "电动车"],
    "半导体": ["半导体", "芯片", "集成电路", "微电子"],
    "人工智能": ["人工智能", "AI", "机器学习", "深度学习", "大模型"],
    "高端制造": ["高端制造", "智能制造", "工业母机", "机器人", "航空航天"],
    "生物医药": ["生物医药", "创新药", "医疗器械", "基因技术"],
    "数字经济": ["数字经济", "云计算", "大数据", "物联网", "区块链"],
    "新材料": ["新材料", "纳米材料", "复合材料"],
}


def evaluate_policy_match(industry_info):
    """
    评估政策匹配度
    
    Args:
        industry_info: 行业信息（可以是字符串或列表）
        
    Returns:
        dict: 政策匹配度评估结果
    """
    result = {
        "supported_industries": [],
        "match_score": 0,
        "policy_alignment": "低",
        "recommendation": ""
    }
    
    # 如果输入是持仓数据，提取行业名称
    if isinstance(industry_info, list):
        industries = [item.get("industry_name", "") for item in industry_info]
    elif isinstance(industry_info, str):
        industries = [industry_info]
    else:
        industries = []
    
    # 检查每个行业是否在政策支持列表中
    matched_count = 0
    total_count = len(industries) if industries else 1
    
    for industry in industries:
        for policy_industry, keywords in POLICY_SUPPORTED_INDUSTRIES.items():
            if any(keyword in industry for keyword in keywords):
                if policy_industry not in result["supported_industries"]:
                    result["supported_industries"].append(policy_industry)
                matched_count += 1
                break
    
    # 计算匹配分数（0-100）
    if total_count > 0:
        result["match_score"] = round((matched_count / total_count) * 100)
    
    # 评估政策一致性
    if result["match_score"] >= 70:
        result["policy_alignment"] = "高"
        result["recommendation"] = "强烈推荐 - 高度符合国家战略方向"
    elif result["match_score"] >= 40:
        result["policy_alignment"] = "中"
        result["recommendation"] = "推荐 - 部分符合政策导向"
    else:
        result["policy_alignment"] = "低"
        result["recommendation"] = "谨慎 - 与政策导向关联度较低"
    
    return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": True, "message": "请提供行业信息"}, ensure_ascii=False))
        sys.exit(1)
    
    # 从参数读取行业信息（JSON格式）
    try:
        industry_info = json.loads(sys.argv[1])
    except:
        industry_info = sys.argv[1]
    
    result = evaluate_policy_match(industry_info)
    
    # 输出JSON格式
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
