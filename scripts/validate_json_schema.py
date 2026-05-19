#!/usr/bin/env python3
"""
验证基金 JSON 文件格式是否符合前端期望

使用方法：
    python3 validate_json_schema.py <基金代码>

验证内容：
1. exclusionCheck 必须是数组，每个元素包含 item/pass/note
2. scoring.risks 必须是数组
3. stageAnalysis.stages 必须是数组
4. managers.current.philosophy 必须是数组
5. holdings.themeGroups 必须是数组
6. performance.milestones 必须是数组
7. company 必须是对象，且包含 complianceChecks
8. 其他关键数组字段的类型检查
"""

import json
import sys
import os


def load_json(code):
    """加载基金 JSON 文件"""
    json_path = f"web-platform/public/data/{code}.json"
    if not os.path.exists(json_path):
        print(f"❌ 文件不存在: {json_path}")
        print(f"   请先运行: python3 skills/fund-deep-research/scripts/build_json_from_cache.py {code}")
        sys.exit(1)
    
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_exclusion_check(data):
    """验证 exclusionCheck 字段"""
    ec = data.get('exclusionCheck')
    
    if ec is None:
        return False, "exclusionCheck 字段缺失"
    
    if not isinstance(ec, list):
        return False, f"exclusionCheck 应为数组，实际为 {type(ec).__name__}"
    
    if len(ec) == 0:
        return False, "exclusionCheck 数组为空"
    
    for i, item in enumerate(ec):
        if not isinstance(item, dict):
            return False, f"exclusionCheck[{i}] 应为对象，实际为 {type(item).__name__}"
        
        if 'item' not in item:
            return False, f"exclusionCheck[{i}] 缺少 'item' 字段"
        
        if 'pass' not in item:
            return False, f"exclusionCheck[{i}] 缺少 'pass' 字段"
        
        if not isinstance(item['pass'], bool):
            return False, f"exclusionCheck[{i}].pass 应为布尔值，实际为 {type(item['pass']).__name__}: {item['pass']}"
        
        if 'note' not in item:
            return False, f"exclusionCheck[{i}] 缺少 'note' 字段"
    
    passed_count = sum(1 for item in ec if item['pass'])
    total_count = len(ec)
    
    return True, f"exclusionCheck 格式正确（{passed_count}/{total_count} 项通过）"


def validate_scoring(data):
    """验证 scoring 字段"""
    scoring = data.get('scoring')
    
    if scoring is None:
        return False, "scoring 字段缺失"
    
    if not isinstance(scoring, dict):
        return False, f"scoring 应为对象，实际为 {type(scoring).__name__}"
    
    # 检查 risks 数组
    risks = scoring.get('risks')
    if risks is None:
        return False, "scoring.risks 字段缺失"
    if not isinstance(risks, list):
        return False, f"scoring.risks 应为数组，实际为 {type(risks).__name__}"
    
    # 检查 termAdvice 数组
    term_advice = scoring.get('termAdvice')
    if term_advice is None:
        return False, "scoring.termAdvice 字段缺失"
    if not isinstance(term_advice, list):
        return False, f"scoring.termAdvice 应为数组，实际为 {type(term_advice).__name__}"
    
    return True, f"scoring 格式正确（{len(risks)}个风险项，{len(term_advice)}个期限建议）"


def validate_stage_analysis(data):
    """验证 stageAnalysis 字段"""
    sa = data.get('stageAnalysis')
    
    if sa is None:
        return False, "stageAnalysis 字段缺失"
    
    stages = sa.get('stages')
    if stages is None:
        return False, "stageAnalysis.stages 字段缺失"
    if not isinstance(stages, list):
        return False, f"stageAnalysis.stages 应为数组，实际为 {type(stages).__name__}"
    
    return True, f"stageAnalysis.stages 格式正确（{len(stages)}个阶段）"


def validate_managers(data):
    """验证 managers 字段"""
    managers = data.get('managers')
    
    if managers is None:
        return False, "managers 字段缺失"
    
    current = managers.get('current')
    if current is None:
        return False, "managers.current 字段缺失"
    
    # 检查 philosophy 数组
    philosophy = current.get('philosophy')
    if philosophy is not None and not isinstance(philosophy, list):
        return False, f"managers.current.philosophy 应为数组，实际为 {type(philosophy).__name__}"
    
    # 检查 consistencyAudit 数组
    audit = current.get('consistencyAudit')
    if audit is not None and not isinstance(audit, list):
        return False, f"managers.current.consistencyAudit 应为数组，实际为 {type(audit).__name__}"
    
    return True, "managers.current 格式正确"


def validate_holdings(data):
    """验证 holdings 字段"""
    holdings = data.get('holdings')
    
    if holdings is None:
        return False, "holdings 字段缺失"
    
    # 检查 themeGroups 数组
    theme_groups = holdings.get('themeGroups')
    if theme_groups is not None and not isinstance(theme_groups, list):
        return False, f"holdings.themeGroups 应为数组，实际为 {type(theme_groups).__name__}"
    
    return True, "holdings 格式正确"


def validate_performance(data):
    """验证 performance 字段"""
    perf = data.get('performance')
    
    if perf is None:
        return False, "performance 字段缺失"
    
    # 检查 milestones 数组
    milestones = perf.get('milestones')
    if milestones is not None and not isinstance(milestones, list):
        return False, f"performance.milestones 应为数组，实际为 {type(milestones).__name__}"
    
    return True, "performance 格式正确"


def validate_tracking(data):
    """验证 tracking 字段"""
    tracking = data.get('tracking')
    
    if tracking is None:
        return False, "tracking 字段缺失"
    
    # 检查 weekly 数组
    weekly = tracking.get('weekly')
    if weekly is not None and not isinstance(weekly, list):
        return False, f"tracking.weekly 应为数组，实际为 {type(weekly).__name__}"
    
    # 检查 quarterly 数组
    quarterly = tracking.get('quarterly')
    if quarterly is not None and not isinstance(quarterly, list):
        return False, f"tracking.quarterly 应为数组，实际为 {type(quarterly).__name__}"
    
    # 检查 alerts 数组
    alerts = tracking.get('alerts')
    if alerts is not None and not isinstance(alerts, list):
        return False, f"tracking.alerts 应为数组，实际为 {type(alerts).__name__}"
    
    # 检查 positions 数组
    positions = tracking.get('positions')
    if positions is not None and not isinstance(positions, list):
        return False, f"tracking.positions 应为数组，实际为 {type(positions).__name__}"
    
    return True, "tracking 格式正确"


def validate_policy(data):
    """验证 policy 字段"""
    policy = data.get('policy')
    
    if policy is None:
        return False, "policy 字段缺失"
    
    # 检查 tags 数组
    tags = policy.get('tags')
    if tags is not None and not isinstance(tags, list):
        return False, f"policy.tags 应为数组，实际为 {type(tags).__name__}"
    
    # 检查 scenarios 数组
    scenarios = policy.get('scenarios')
    if scenarios is not None and not isinstance(scenarios, list):
        return False, f"policy.scenarios 应为数组，实际为 {type(scenarios).__name__}"
    
    return True, "policy 格式正确"


def validate_company(data):
    """验证 company 字段"""
    company = data.get('company')

    if company is None:
        return False, "company 字段缺失"

    if not isinstance(company, dict):
        return False, f"company 应为对象，实际为 {type(company).__name__}"

    if company.get('complianceResult') is None:
        return False, "company.complianceResult 字段缺失"

    if company.get('complianceSummary') is None:
        return False, "company.complianceSummary 字段缺失"

    checks = company.get('complianceChecks')
    if checks is None:
        return False, "company.complianceChecks 字段缺失"
    if not isinstance(checks, list):
        return False, f"company.complianceChecks 应为数组，实际为 {type(checks).__name__}"
    if len(checks) == 0:
        return False, "company.complianceChecks 数组为空"

    for i, item in enumerate(checks):
        if not isinstance(item, dict):
            return False, f"company.complianceChecks[{i}] 应为对象，实际为 {type(item).__name__}"
        if 'item' not in item:
            return False, f"company.complianceChecks[{i}] 缺少 'item' 字段"
        if 'detail' not in item:
            return False, f"company.complianceChecks[{i}] 缺少 'detail' 字段"
        if 'pass' not in item:
            return False, f"company.complianceChecks[{i}] 缺少 'pass' 字段"
        if 'warn' not in item:
            return False, f"company.complianceChecks[{i}] 缺少 'warn' 字段"
        if not isinstance(item['pass'], bool):
            return False, f"company.complianceChecks[{i}].pass 应为布尔值，实际为 {type(item['pass']).__name__}"
        if not isinstance(item['warn'], bool):
            return False, f"company.complianceChecks[{i}].warn 应为布尔值，实际为 {type(item['warn']).__name__}"

    return True, f"company 格式正确（{len(checks)}个检查项）"


def main():
    if len(sys.argv) != 2:
        print("用法: python3 validate_json_schema.py <基金代码>")
        print("示例: python3 validate_json_schema.py 023056")
        sys.exit(1)
    
    code = sys.argv[1]
    print(f"\n{'='*50}")
    print(f"  验证基金 {code} 的 JSON 格式")
    print(f"{'='*50}\n")
    
    data = load_json(code)
    
    validators = [
        ("exclusionCheck", validate_exclusion_check),
        ("scoring", validate_scoring),
        ("stageAnalysis", validate_stage_analysis),
        ("managers", validate_managers),
        ("holdings", validate_holdings),
        ("performance", validate_performance),
        ("tracking", validate_tracking),
        ("policy", validate_policy),
        ("company", validate_company),
    ]
    
    results = []
    for name, validator in validators:
        try:
            passed, message = validator(data)
            results.append((passed, name, message))
            status = "✅" if passed else "❌"
            print(f"{status} {name}: {message}")
        except Exception as e:
            results.append((False, name, f"验证异常: {str(e)}"))
            print(f"❌ {name}: 验证异常 - {str(e)}")
    
    print(f"\n{'='*50}")
    passed_count = sum(1 for p, _, _ in results if p)
    total_count = len(results)
    
    if passed_count == total_count:
        print(f"✅ 所有验证通过 ({passed_count}/{total_count})")
        print(f"\nJSON 文件格式正确，可以安全使用。")
        sys.exit(0)
    else:
        print(f"❌ 存在验证失败 ({passed_count}/{total_count} 通过)")
        print(f"\n请修复上述错误后重新运行验证。")
        sys.exit(1)


if __name__ == '__main__':
    main()
