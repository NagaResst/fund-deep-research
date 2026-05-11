#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并行数据收集脚本 - 同时运行多个数据获取脚本，大幅提升速度
用法: python parallel_data_collection.py <基金代码>
"""

import sys
import json
import subprocess
import threading
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
            errors='ignore'  # 忽略编码错误
        )
        
        if result.returncode == 0:
            # 尝试解析JSON输出
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
    except subprocess.TimeoutExpired:
        return {
            'script': script_name,
            'status': 'timeout',
            'data': None,
            'error': f'脚本执行超时（{timeout}秒）'
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
        print("用法: python parallel_data_collection.py <基金代码>")
        sys.exit(1)
    
    fund_code = sys.argv[1]
    print(f"🚀 开始并行收集基金 {fund_code} 的数据...")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 定义需要并行执行的脚本任务（不同脚本设置不同超时时间）
    tasks = [
        ('fetch_fund_enhanced.py', [fund_code], "基础信息（增强版）", 90),  # 基础信息需要更多时间
        ('fetch_risk_metrics.py', [fund_code], "风险指标", 30),
        ('analyze_holdings.py', [fund_code], "持仓分析", 30),
        ('analyze_quarterly_performance.py', [fund_code], "季度表现", 45),
        ('scan_institutional_risk.py', [fund_code], "机构风险", 30),
    ]
    
    results = {}
    start_time = datetime.now()
    
    # 使用线程池并行执行（最多5个并发）
    with ThreadPoolExecutor(max_workers=5) as executor:
        # 提交所有任务（支持自定义超时时间）
        future_to_task = {}
        for item in tasks:
            if len(item) == 4:
                script, args, desc, timeout = item
            else:
                script, args, desc = item
                timeout = 60
            future_to_task[
                executor.submit(run_script, script, args, timeout)
            ] = (script, desc)
        
        # 收集结果
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
    print(f"✅ 完成时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 保存结果为JSON文件
    output_file = f"fund_data_{fund_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 结果已保存到: {output_file}")
    
    # 检查关键数据是否缺失
    missing_data = []
    if 'fetch_fund_enhanced.py' not in results:
        missing_data.append("基础信息")
    if 'fetch_risk_metrics.py' not in results:
        missing_data.append("风险指标")
    if 'analyze_holdings.py' not in results:
        missing_data.append("持仓数据")
    
    if missing_data:
        print(f"\n⚠️  以下数据获取失败，需要联网搜索补充:")
        for item in missing_data:
            print(f"   - {item}")
        print("\n建议: 立即使用 search_web 工具补充缺失数据")
    else:
        print("\n✅ 所有核心数据已成功获取！")
    
    return results


if __name__ == '__main__':
    main()
