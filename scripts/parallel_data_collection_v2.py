#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新版并行数据收集脚本
混合架构：AKShare获取 + 本地计算 + 原爬虫保留
"""

import sys
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


def run_script(script_name, args, timeout=60):
    """运行单个脚本并返回结果"""
    try:
        cmd = ['python', f'skills/fund-deep-research/scripts/{script_name}'] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout.strip())
                return {
                    'script': script_name,
                    'status': 'success',
                    'data': data,
                    'error': None
                }
            except json.JSONDecodeError:
                return {
                    'script': script_name,
                    'status': 'success',
                    'data': result.stdout.strip(),
                    'error': None
                }
        else:
            return {
                'script': script_name,
                'status': 'error',
                'data': None,
                'error': result.stderr.strip()
            }
    except Exception as e:
        return {
            'script': script_name,
            'status': 'exception',
            'data': None,
            'error': str(e)
        }


def main():
    if len(sys.argv) < 2:
        print("用法: python parallel_data_collection_v2.py <基金代码>")
        sys.exit(1)

    fund_code = sys.argv[1]

    print(f"🚀 开始混合架构数据收集: {fund_code}")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 定义任务（混合架构 - P1增强版）
    tasks = [
        # AKShare获取层（4个）
        ('ak_fund_basic.py', [fund_code], "AKShare-基础信息", 30),
        ('ak_nav_history.py', [fund_code], "AKShare-净值历史", 60),
        ('ak_holdings.py', [fund_code], "AKShare-持仓结构", 30),
        ('ak_quarterly_calc.py', [fund_code], "AKShare-季度计算", 30),
        
        # 本地计算层（4个，新增 calc_relative_metrics）
        ('calc_risk_metrics.py', [fund_code], "计算-风险指标", 30),
        ('calc_relative_metrics.py', [fund_code, "000300"], "计算-相对基准指标", 60),  # P1新增
        ('calc_inflection_points.py', [fund_code], "计算-拐点识别", 30),
        ('calc_annual_returns.py', [fund_code], "计算-年度收益", 30),
        
        # 旧版爬虫保留（1个）
        ('fetch_manager_info.py', [fund_code], "爬虫-经理信息", 30),
        
        # 搜索层（2个，保留原样）
        ('scan_institutional_risk.py', [fund_code], "搜索-机构风险", 30),
        ('check_blacklist.py', [fund_code], "搜索-黑名单", 30),
    ]
    
    results = {}
    start_time = datetime.now()
    
    # 并行执行（最多6个并发）
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_task = {}
        for item in tasks:
            script, args, desc, timeout = item
            future_to_task[
                executor.submit(run_script, script, args, timeout)
            ] = (script, desc)
        
        for future in as_completed(future_to_task):
            script, desc = future_to_task[future]
            try:
                result = future.result()
                status_icon = "✅" if result['status'] == 'success' else "❌"
                print(f"{status_icon} [{desc}] {result['status']}")
                
                if result['status'] == 'success':
                    results[script] = result['data']
                else:
                    print(f"   错误: {result['error']}")
            except Exception as e:
                print(f"❌ [{desc}] 异常: {str(e)}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("=" * 60)
    print(f"⏱️  总耗时: {duration:.2f} 秒")
    print(f"📊 成功获取: {len(results)}/{len(tasks)} 个数据源")
    
    # 保存结果
    output_file = f"fund_data_{fund_code}_v2.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 结果已保存到: {output_file}")
    
    # 检查关键数据
    missing = []
    if 'ak_fund_basic.py' not in results:
        missing.append("基础信息")
    if 'calc_risk_metrics.py' not in results:
        missing.append("风险指标")
    
    if missing:
        print(f"\n⚠️  以下数据获取失败，需联网搜索补充:")
        for item in missing:
            print(f"   - {item}")
    else:
        print("\n✅ 所有核心数据已成功获取！")


if __name__ == '__main__':
    main()
