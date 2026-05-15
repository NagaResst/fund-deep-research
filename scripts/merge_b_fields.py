#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_b_fields.py — 将 AI 提取的 B 类字段合并到 web-platform JSON

用法：
    python3 merge_b_fields.py <基金代码> <b_fields.json路径> [--overwrite]

选项：
    --overwrite   强制覆盖已有 B 类字段（默认不覆盖，只填充空缺）
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../.."))
DATA_DIR = os.path.join(REPO_ROOT, "web-platform/public/data")


REFRESH_BY_DEFAULT_PREFIXES = (
    "policy",
    "exclusionCheck",
    "scoring",
    "tracking",
    "stageAnalysis.stages",
    "stageAnalysis.inflectionPoints",
    "managers.current.education",
    "managers.current.joinDate",
    "managers.current.experience",
    "managers.current.title",
    "managers.current.style",
    "managers.current.manageDate",
    "managers.current.manageYears",
    "managers.current.tenureReturn",
    "managers.current.peerAvgReturn",
    "managers.current.rankInPeer",
    "managers.current.rankTotal",
    "managers.current.historicalFunds",
    "managers.current.philosophy",
    "managers.current.consistencyAudit",
    "managers.current.abilityProfile",
    "managers.current.strengths",
    "managers.current.weaknesses",
    "managers.current.bestReturn",
    "managers.current.worstReturn",
    "managers.history",
    "holdings.stockRatio",
    "holdings.bondRatio",
    "holdings.cashRatio",
    "holdings.themeTitle",
    "holdings.themeSubtitle",
    "holdings.concentrationLabel",
    "holdings.themeGroups",
    "holdings.evolutionHighlights",
    "holdings.policyLinks",
    "holdings.bondStructure",
    "performance.milestones",
    "performance.annualNote",
)


def should_refresh_path(path: str) -> bool:
    return any(
        path == prefix or path.startswith(prefix + ".")
        for prefix in REFRESH_BY_DEFAULT_PREFIXES
    )


def normalize_risk_level(level):
    mapping = {
        "高": "high",
        "中": "medium",
        "低": "low",
        "high": "high",
        "medium": "medium",
        "low": "low",
    }
    return mapping.get(level, level)


def normalize_alert_level(level):
    mapping = {
        "一票否决": "critical",
        "减仓": "warning",
        "关注": "warning",
        "critical": "critical",
        "warning": "warning",
        "info": "warning",
        "high": "critical",
        "medium": "warning",
        "low": "warning",
    }
    return mapping.get(level, level or "warning")


def alert_icon(level):
    return "🚨" if level == "critical" else "⚠️"


def normalize_term_level(level):
    mapping = {
        "买入": "positive",
        "加仓": "positive",
        "积极": "positive",
        "持有": "neutral",
        "中性": "neutral",
        "观望": "cautious",
        "谨慎": "cautious",
        "减仓": "cautious",
        "卖出": "cautious",
        "positive": "positive",
        "neutral": "neutral",
        "cautious": "cautious",
    }
    return mapping.get(level, level)


def term_icon(level):
    mapping = {
        "positive": "🟢",
        "neutral": "🟡",
        "cautious": "⚠️",
    }
    return mapping.get(level, "📌")


def derive_recommendation_type(text):
    if not text:
        return None
    if any(token in text for token in ["强烈买入", "强烈配置"]):
        return "strong_buy"
    if any(token in text for token in ["买入", "建仓", "加仓"]):
        return "buy"
    if any(token in text for token in ["减仓", "卖出", "清仓"]):
        return "sell"
    if any(token in text for token in ["观望", "谨慎"]):
        return "cautious"
    return None


def join_text_parts(item, keys):
    parts = []
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            parts.append(text)
    return "；".join(parts)


def normalize_tracking_list(items, keys):
    normalized = []
    for item in items or []:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            text = join_text_parts(item, keys)
        else:
            text = ""
        if text:
            normalized.append(text)
    return normalized


def normalize_tracking(tracking):
    if not isinstance(tracking, dict):
        return tracking

    normalized = dict(tracking)

    if isinstance(normalized.get("weekly"), list):
        normalized["weekly"] = normalize_tracking_list(
            normalized["weekly"],
            ["dimension", "indicator", "target", "action"],
        )

    if isinstance(normalized.get("quarterly"), list):
        normalized["quarterly"] = normalize_tracking_list(
            normalized["quarterly"],
            ["dimension", "checkItem", "warningLine", "exitLine"],
        )

    alerts = normalized.get("alerts")
    if isinstance(alerts, list):
        normalized_alerts = []
        for alert in alerts:
            if isinstance(alert, dict):
                level = normalize_alert_level(alert.get("level"))
                text = alert.get("text")
                if not text:
                    signal = alert.get("signal") or alert.get("condition")
                    action = alert.get("action")
                    if signal and action:
                        text = f"{signal}：{action}"
                    else:
                        text = signal or action
                if text:
                    normalized_alerts.append({
                        "level": level,
                        "icon": alert.get("icon") or alert_icon(level),
                        "text": text,
                    })
            elif isinstance(alert, str) and alert.strip():
                normalized_alerts.append({
                    "level": "warning",
                    "icon": alert_icon("warning"),
                    "text": alert.strip(),
                })
        normalized["alerts"] = normalized_alerts

    return normalized


def normalize_exclusion_check(exclusion_check):
    if isinstance(exclusion_check, list):
        return exclusion_check
    if not isinstance(exclusion_check, dict):
        return exclusion_check

    items = exclusion_check.get("items") or []
    normalized = []
    for item in items:
        if not isinstance(item, dict):
            continue
        result = str(item.get("result", "")).lower()
        passed = item.get("pass")
        if passed is None:
            passed = result == "pass"
        normalized.append({
            "item": item.get("item"),
            "pass": bool(passed),
            "note": item.get("note") or item.get("detail"),
        })
    return normalized


def normalize_scoring(scoring):
    if not isinstance(scoring, dict):
        return scoring

    normalized = dict(scoring)

    if normalized.get("recommendation") and not normalized.get("recommendationType"):
        recommendation_type = derive_recommendation_type(normalized.get("recommendation"))
        if recommendation_type:
            normalized["recommendationType"] = recommendation_type

    risks = normalized.get("risks")
    if isinstance(risks, list):
        normalized_risks = []
        for risk in risks:
            if not isinstance(risk, dict):
                continue
            normalized_risks.append({
                "type": risk.get("type") or risk.get("label") or risk.get("name") or "风险提示",
                "level": normalize_risk_level(risk.get("level")),
                "note": risk.get("note") or risk.get("text") or risk.get("detail") or "",
            })
        normalized["risks"] = normalized_risks

    term_advice = normalized.get("termAdvice")
    if isinstance(term_advice, list):
        normalized_terms = []
        for item in term_advice:
            if not isinstance(item, dict):
                continue
            level = normalize_term_level(item.get("level") or item.get("rating"))
            advice = item.get("advice")
            if not advice:
                suggestion = item.get("suggestion")
                logic = item.get("logic")
                if suggestion and logic:
                    advice = f"{suggestion}。{logic}"
                else:
                    advice = suggestion or logic
            normalized_terms.append({
                "term": item.get("term"),
                "icon": item.get("icon") or term_icon(level),
                "level": level,
                "advice": advice,
            })
        normalized["termAdvice"] = normalized_terms

    return normalized


def normalize_policy(policy):
    if not isinstance(policy, dict):
        return policy

    normalized = dict(policy)
    tags = normalized.get("tags")
    if isinstance(tags, list) and tags and all(isinstance(tag, str) for tag in tags):
        normalized["tags"] = [
            {"label": tag, "strength": "medium", "color": "#E8813A"}
            for tag in tags if str(tag).strip()
        ]
    return normalized


def normalize_b_fields(patch):
    if not isinstance(patch, dict):
        return patch

    normalized = dict(patch)

    if "tracking" in normalized:
        normalized["tracking"] = normalize_tracking(normalized["tracking"])

    if "exclusionCheck" in normalized:
        normalized["exclusionCheck"] = normalize_exclusion_check(normalized["exclusionCheck"])

    if "scoring" in normalized:
        normalized["scoring"] = normalize_scoring(normalized["scoring"])

    if "policy" in normalized:
        normalized["policy"] = normalize_policy(normalized["policy"])

    return normalized


def deep_merge(base: dict, patch: dict, overwrite: bool, path: str = "") -> list:
    """
    深度合并 patch 到 base。
    - 若 overwrite=False，只填充 base 中 None 或不存在的字段
    - 返回变更日志 [(path, old, new)]
    """
    changes = []
    for key, val in patch.items():
        key_path = f"{path}.{key}" if path else key
        refresh_here = overwrite or should_refresh_path(key_path)
        if key not in base or base[key] is None:
            base[key] = val
            changes.append((key_path, None, val))
        elif isinstance(val, dict) and isinstance(base.get(key), dict):
            changes.extend(deep_merge(base[key], val, refresh_here, key_path))
        elif isinstance(val, list) and len(val) > 0:
            if refresh_here or not base[key]:
                changes.append((key_path, base[key], val))
                base[key] = val
        elif refresh_here:
            if base[key] != val:
                changes.append((key_path, base[key], val))
            base[key] = val
    return changes


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print("用法：python3 merge_b_fields.py <基金代码> <b_fields.json> [--overwrite]")
        sys.exit(1)

    code = args[0]
    b_path = args[1]
    overwrite = "--overwrite" in args

    json_path = os.path.join(DATA_DIR, f"{code}.json")
    if not os.path.exists(json_path):
        print(f"❌  目标 JSON 不存在：{json_path}")
        print(f"    请先运行 build_json_from_cache.py {code}")
        sys.exit(1)

    if not os.path.exists(b_path):
        print(f"❌  B 类字段文件不存在：{b_path}")
        sys.exit(1)

    with open(json_path, encoding="utf-8") as f:
        base = json.load(f)

    with open(b_path, encoding="utf-8") as f:
        patch = json.load(f)

    patch = normalize_b_fields(patch)

    print(f"\n═══════════════════════════════════════")
    print(f"  merge_b_fields  基金 {code}  {'（覆盖模式）' if overwrite else '（填充模式）'}")
    print(f"═══════════════════════════════════════\n")

    changes = deep_merge(base, patch, overwrite)

    if not changes:
        print("  没有变更（所有字段已存在，使用 --overwrite 强制更新）")
    else:
        for path, old, new in changes:
            if old is None:
                print(f"  ✅ 新增  {path}")
            else:
                old_preview = str(old)[:40].replace("\n", " ")
                new_preview = str(new)[:40].replace("\n", " ")
                print(f"  🔄 更新  {path}")
                print(f"          旧: {old_preview}")
                print(f"          新: {new_preview}")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, indent=2)

    print(f"\n✅  已写入 {json_path}（变更 {len(changes)} 项）")


if __name__ == "__main__":
    main()
