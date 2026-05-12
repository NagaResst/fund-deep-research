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
        cmd = ['python3', f'skills/fund-deep-research/scripts/{script_name}'] + args
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
        print("用法: python parallel_data_collection.py <基金代码> [--output-dir <路径>]")
        sys.exit(1)

    fund_code = sys.argv[1]

    # 解析 --output-dir 参数
    output_dir = None
    args = sys.argv[2:]
    for i, arg in enumerate(args):
        if arg == '--output-dir' and i + 1 < len(args):
            output_dir = args[i + 1]
            break

    if output_dir:
        import os
        os.makedirs(output_dir, exist_ok=True)

    print(f"🚀 开始并行收集基金 {fund_code} 的数据...")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if output_dir:
        print(f"📂 输出目录: {output_dir}")
    print("=" * 60)

    # 定义需要并行执行的脚本任务（不同脚本设置不同超时时间）
    # scan_institutional_risk 需要在 fund_enhanced 完成后才能运行，单独处理
    tasks = [
        ('fetch_fund_enhanced.py', [fund_code], "基础信息（增强版）", 90),
        ('fetch_risk_metrics.py', [fund_code], "风险指标", 120),
        ('analyze_holdings.py', [fund_code], "持仓分析", 60),
        ('analyze_quarterly_performance.py', [fund_code], "季度表现", 150),
        ('fetch_manager_info.py', [fund_code], "经理详细信息", 30),
        ('fetch_nav_daily.py', [fund_code], "日频净值历史", 180),
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
    
    # ── 补跑 scan_institutional_risk（需要经理名和公司名）────────────────
    import os
    fe_data = results.get('fetch_fund_enhanced.py', {})
    if isinstance(fe_data, dict):
        _mgr = fe_data.get('manager_name', '')
        _co  = fe_data.get('company_name', '')
    else:
        _mgr, _co = '', ''

    if _mgr and _co:
        risk_result = run_script('scan_institutional_risk.py', [_mgr, _co], timeout=30)
        print(f"{'✅' if risk_result['status'] == 'success' else '❌'} [机构风险] {risk_result['status']}")
        if risk_result['status'] == 'success':
            results['scan_institutional_risk.py'] = risk_result['data']
        else:
            print(f"   错误: {risk_result['error']}")

        bl_result = run_script('check_blacklist.py', [_co, _mgr], timeout=30)
        print(f"{'✅' if bl_result['status'] == 'success' else '❌'} [黑名单检查] {bl_result['status']}")
        if bl_result['status'] == 'success':
            results['check_blacklist.py'] = bl_result['data']
        else:
            print(f"   错误: {bl_result['error']}")
    else:
        print("⚠️  [机构风险/黑名单] 跳过：无法从 fund_enhanced 中获取经理名/公司名")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # ── 将各脚本结果保存为独立 JSON 文件 ────────────────────────────────
    SCRIPT_TO_FILENAME = {
        'fetch_fund_enhanced.py':           'fund_enhanced.json',
        'fetch_risk_metrics.py':            'risk_metrics.json',
        'analyze_holdings.py':              'holdings.json',
        'analyze_quarterly_performance.py': 'quarterly.json',
        'fetch_manager_info.py':            'manager_info.json',
        'scan_institutional_risk.py':       'institutional_risk.json',
        'check_blacklist.py':               'blacklist.json',
        # fetch_nav_daily.py 直接写文件，无需在此保存
    }

    if output_dir:
        for script_key, filename in SCRIPT_TO_FILENAME.items():
            if script_key in results:
                out_path = f"{output_dir}/{filename}"
                try:
                    with open(out_path, 'w', encoding='utf-8') as _f:
                        _data = results[script_key]
                        if isinstance(_data, str):
                            _f.write(_data)
                        else:
                            json.dump(_data, _f, ensure_ascii=False, indent=2)
                    print(f"💾 已保存: {out_path}")
                except Exception as e:
                    print(f"⚠️  保存 {filename} 失败: {e}")
    else:
        # 无 --output-dir 时回退：保存合并文件到当前目录
        output_file = f"fund_data_{fund_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 合并结果已保存到: {output_file}")

    print("=" * 60)
    print(f"⏱️  总耗时: {duration:.2f} 秒")
    print(f"📊 成功获取: {len(results)}/{len(tasks) + 2} 个数据源")
    print(f"✅ 完成时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

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
