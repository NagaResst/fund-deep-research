#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新版并行数据收集脚本
混合架构：AKShare获取 + 本地计算 + 原爬虫保留
"""

import os
import sys
import json

# 脚本名 → 输出文件名映射（Bug1修复：每个脚本单独写文件到 raw/）
OUTPUT_FILE_MAP = {
    'ak_fund_basic.py':          'fund_enhanced.json',
    'ak_nav_history.py':         'nav_daily.json',
    'ak_holdings.py':            'holdings.json',
    'ak_quarterly_calc.py':      'quarterly.json',
    'calc_risk_metrics.py':      'risk_metrics.json',
    'calc_relative_metrics.py':  'relative_metrics.json',
    'calc_inflection_points.py': 'inflection_points.json',
    'calc_annual_returns.py':    'annual_returns.json',
    'fetch_manager_info.py':     'manager_info.json',
    'scan_institutional_risk.py':'institutional_risk.json',
    'check_blacklist.py':        'blacklist.json',
}
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# 脚本名 → /tmp/fund_research_{code}/raw/ 下的输出文件名
OUTPUT_FILE_MAP = {
    'ak_fund_basic.py':          'fund_enhanced.json',
    'ak_nav_history.py':         'nav_daily.json',
    'ak_holdings.py':            'holdings.json',
    'ak_quarterly_calc.py':      'quarterly.json',
    'calc_risk_metrics.py':      'risk_metrics.json',
    'calc_relative_metrics.py':  'relative_metrics.json',
    'calc_inflection_points.py': 'inflection_points.json',
    'calc_annual_returns.py':    'annual_returns.json',
    'fetch_manager_info.py':     'manager_info.json',
    'scan_institutional_risk.py':'institutional_risk.json',
    'check_blacklist.py':        'blacklist.json',
}


def run_script(script_name, args, timeout=60):
    """运行单个脚本并返回结果"""
    try:
        cmd = [sys.executable, f'skills/fund-deep-research/scripts/{script_name}'] + args
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


def run_parallel(tasks, results):
    """并行执行一批任务，结果写入 results dict"""
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_task = {
            executor.submit(run_script, script, args, timeout): (script, desc)
            for script, args, desc, timeout in tasks
        }
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


def main():
    if len(sys.argv) < 2:
        print("用法: python parallel_data_collection_v2.py <基金代码>")
        sys.exit(1)

    fund_code = sys.argv[1]
    raw_dir = f"/tmp/fund_research_{fund_code}/raw"
    os.makedirs(raw_dir, exist_ok=True)

    print(f"🚀 开始混合架构数据收集: {fund_code}")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = {}
    start_time = datetime.now()

    # ── Layer 1+2：并行执行（共8个，互不依赖）──────────────────
    print("\n【Layer 1+2】AKShare获取 + 本地计算（并行）")
    layer12_tasks = [
        ('ak_fund_basic.py',          [fund_code],             "AKShare-基础信息",   30),
        ('ak_nav_history.py',         [fund_code],             "AKShare-净值历史",   120),
        ('ak_holdings.py',            [fund_code],             "AKShare-持仓结构",   120),  # 循环多年API调用，需要更长时间
        ('ak_quarterly_calc.py',      [fund_code],             "AKShare-季度计算",   60),
        ('calc_risk_metrics.py',      [fund_code],             "计算-风险指标",      30),
        ('calc_relative_metrics.py',  [fund_code, "000300"],   "计算-相对基准指标",  60),
        ('calc_inflection_points.py', [fund_code],             "计算-拐点识别",      30),
        ('calc_annual_returns.py',    [fund_code],             "计算-年度收益",      30),
    ]
    run_parallel(layer12_tasks, results)

    # Layer 1+2 完成后立即写入文件，供 Layer 3 读取
    for script_name, data in list(results.items()):
        fname = OUTPUT_FILE_MAP.get(script_name)
        if fname:
            out_path = os.path.join(raw_dir, fname)
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    # ── Layer 3：串行执行，依赖 fund_enhanced.json 中的经理/公司信息 ──
    print("\n【Layer 3】爬虫+搜索层（串行）")

    # 从 fund_enhanced.json 读取经理姓名和公司名称
    manager_name = ""
    company_name = ""
    fe_path = os.path.join(raw_dir, "fund_enhanced.json")
    if os.path.exists(fe_path):
        try:
            with open(fe_path, encoding='utf-8') as f:
                fe = json.load(f)
            manager_name = fe.get("manager_name", "")
            company_name = fe.get("company_name", "")
        except Exception as e:
            print(f"⚠️  读取 fund_enhanced.json 失败: {e}，Layer 3 将跳过风险扫描")

    layer3_tasks = [
        ('fetch_manager_info.py', [fund_code], "爬虫-经理信息", 90),  # 网页爬虫需要更长时间
    ]
    if manager_name and company_name:
        layer3_tasks += [
            ('scan_institutional_risk.py', [manager_name, company_name], "搜索-机构风险", 60),
            ('check_blacklist.py',         [company_name, manager_name], "搜索-黑名单",   60),
        ]
    else:
        print("⚠️  经理/公司信息缺失，跳过 scan_institutional_risk 和 check_blacklist")

    for script, args, desc, timeout in layer3_tasks:
        result = run_script(script, args, timeout)
        status_icon = "✅" if result['status'] == 'success' else "❌"
        print(f"{status_icon} [{desc}] {result['status']}")
        if result['status'] == 'success':
            results[script] = result['data']
        else:
            print(f"   错误: {result['error']}")

    # ── 保存 Layer 3 结果文件 ──────────────────────────────────
    for script_name in ['fetch_manager_info.py', 'scan_institutional_risk.py', 'check_blacklist.py']:
        if script_name in results:
            fname = OUTPUT_FILE_MAP.get(script_name)
            if fname:
                out_path = os.path.join(raw_dir, fname)
                with open(out_path, 'w', encoding='utf-8') as f:
                    json.dump(results[script_name], f, ensure_ascii=False, indent=2, default=str)

    # ── 汇总 ──────────────────────────────────────────────────
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    total_tasks = len(layer12_tasks) + len(layer3_tasks)

    print("\n" + "=" * 60)
    print(f"⏱️  总耗时: {duration:.2f} 秒")
    print(f"📊 成功获取: {len(results)}/{total_tasks} 个数据源")
    print(f"✅ 已写入 {raw_dir}")

    missing_core = []
    if 'ak_fund_basic.py' not in results:
        missing_core.append("基础信息")
    if 'calc_risk_metrics.py' not in results:
        missing_core.append("风险指标")

    if missing_core:
        print(f"\n⚠️  以下数据获取失败，需联网搜索补充:")
        for item in missing_core:
            print(f"   - {item}")
    else:
        print("✅ 所有核心数据已成功获取！")


if __name__ == '__main__':
    main()
