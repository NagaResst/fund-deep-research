#!/usr/bin/env python3
"""
Step 0：预检与缓存管理脚本
用法：python3 skills/fund-deep-research/scripts/precheck.py <基金代码>

功能：
1. 检查 /tmp/fund_research_{code}/ 缓存状态
2. 根据状态自动执行：清空旧缓存 / 创建目录 / 写入 meta.json
3. 输出 NEXT_ACTION 指令，供后续 Step 1 参考
"""

import json
import os
import shutil
import sys
from datetime import date, datetime
from pathlib import Path


def write_meta(tmp_dir: str, code: str) -> None:
    meta = {"fund_code": code, "fetch_date": str(date.today())}
    with open(f"{tmp_dir}/meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"✅ meta.json 已写入：{tmp_dir}/meta.json")


def create_dirs(tmp_dir: str) -> None:
    Path(f"{tmp_dir}/raw").mkdir(parents=True, exist_ok=True)
    Path(f"{tmp_dir}/analysis").mkdir(parents=True, exist_ok=True)
    print(f"✅ 目录已创建：{tmp_dir}/{{raw,analysis}}")


def _is_valid_json_file(path: str) -> bool:
    """文件存在且内容是合法 JSON（非空、非错误信息）。"""
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return False
        json.loads(content)
        return True
    except Exception:
        return False


def check_stale_files(tmp_dir: str) -> list[str]:
    """检查 raw/ 下哪些文件缺失或无效（空文件、非JSON内容）。"""
    required = [
        "fund_enhanced.json",
        "risk_metrics.json",
        "relative_metrics.json",
        "holdings.json",
        "quarterly.json",
        "institutional_risk.json",
        "manager_info.json",
        "blacklist.json",
        "nav_daily.json",
        "inflection_points.json",
        "annual_returns.json",
    ]
    missing = []
    for f in required:
        path = f"{tmp_dir}/raw/{f}"
        if not os.path.exists(path) or not _is_valid_json_file(path):
            missing.append(f)
    return missing


def main():
    if len(sys.argv) < 2:
        print("用法：python3 precheck.py <基金代码>")
        sys.exit(1)

    target_code = sys.argv[1].strip()
    tmp_dir = f"/tmp/fund_research_{target_code}"
    meta_path = f"{tmp_dir}/meta.json"

    print(f"═══════════════════════════════════════")
    print(f"  Step 0 预检：基金代码 {target_code}")
    print(f"═══════════════════════════════════════")

    # ── 情况1：无缓存 ────────────────────────────────────────
    if not os.path.exists(meta_path):
        print("STATUS: NO_CACHE - 无缓存，全新开始")
        create_dirs(tmp_dir)
        write_meta(tmp_dir, target_code)
        print()
        print("NEXT_ACTION: FULL_FETCH")
        print("→ 请从 Step 1 开始，执行全量数据拉取")
        return

    # ── 读取 meta.json ────────────────────────────────────────
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    cached_code = meta.get("fund_code", "")
    fetch_date = meta.get("fetch_date", "")

    # ── 情况2：基金代码不匹配 ─────────────────────────────────
    if cached_code != target_code:
        old_dir = f"/tmp/fund_research_{cached_code}"
        print(f"STATUS: FUND_MISMATCH - 缓存基金={cached_code}，目标={target_code}")
        if os.path.exists(old_dir):
            shutil.rmtree(old_dir)
            print(f"✅ 已清空旧缓存目录：{old_dir}")
        create_dirs(tmp_dir)
        write_meta(tmp_dir, target_code)
        print()
        print("NEXT_ACTION: FULL_FETCH")
        print("→ 旧缓存已清空，请从 Step 1 开始，执行全量数据拉取")
        return

    # ── 情况3：命中缓存，判断时效 ─────────────────────────────
    today = date.today()
    if fetch_date:
        cached_day = datetime.strptime(fetch_date, "%Y-%m-%d").date()
        days_old = (today - cached_day).days
    else:
        days_old = 9999

    print(f"STATUS: CACHE_HIT - 基金匹配，缓存于 {fetch_date}，已 {days_old} 天前")

    missing = check_stale_files(tmp_dir)
    if missing:
        print(f"⚠️  缺失文件（{len(missing)} 个）：{', '.join(missing)}")

    if days_old <= 1 and not missing:
        print("DATA_AGE: FRESH - 净值/基础数据在有效期内（T-1）")
        print()
        print("NEXT_ACTION: SKIP_TO_STEP2")
        print("→ 缓存新鲜且文件完整，直接跳至 Step 2 执行完整性检查")
        print("→ ⚠️ search_log.md 无论缓存多新，必须重新搜索并去重写入")

    elif days_old <= 1 and missing:
        print("DATA_AGE: FRESH_PARTIAL - 缓存新鲜但有文件缺失")
        print()
        print("NEXT_ACTION: PARTIAL_FETCH")
        print(f"→ 仅补跑缺失文件对应的 Step 1 脚本：{', '.join(missing)}")

    elif days_old <= 90:
        print("DATA_AGE: STALE_NAV - 净值可能过期，需重拉")
        print()
        print("NEXT_ACTION: REFRESH_NAV")
        print("→ 重拉 nav_daily.json 和 fund_enhanced.json，并重算 risk_metrics.json / relative_metrics.json")
        print("→ 持仓/季报请检查是否为最新季度")
        if missing:
            print(f"→ 同时补跑缺失文件：{', '.join(missing)}")

    else:
        print("DATA_AGE: EXPIRED - 超过90天，建议全量重拉")
        print()
        print("NEXT_ACTION: FULL_FETCH")
        print("→ 建议全量重拉所有 raw/ 数据，从 Step 1 开始")

    print()
    print(f"─── 文件状态总览 ({tmp_dir}/raw/) ───")
    required_files = [
        "fund_enhanced.json", "risk_metrics.json", "relative_metrics.json",
        "holdings.json", "quarterly.json", "institutional_risk.json",
        "manager_info.json", "blacklist.json", "nav_daily.json",
        "inflection_points.json", "annual_returns.json",
    ]
    for fname in required_files:
        path = f"{tmp_dir}/raw/{fname}"
        if os.path.exists(path):
            size_kb = os.path.getsize(path) / 1024
            if _is_valid_json_file(path):
                mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%m-%d %H:%M")
                print(f"  ✅ {fname:<35} {size_kb:>6.1f} KB  [{mtime}]")
            else:
                print(f"  ❌ {fname:<35} 无效（非法JSON，{size_kb:.1f} KB）")
        else:
            print(f"  ❌ {fname:<35} 缺失")

    search_log = f"{tmp_dir}/analysis/search_log.md"
    if os.path.exists(search_log):
        size_kb = os.path.getsize(search_log) / 1024
        print(f"  📄 search_log.md{'':<19} {size_kb:>6.1f} KB  (每次研究强制重新搜索)")
    else:
        print(f"  📄 search_log.md{'':<19} 不存在（首次研究将自动创建）")


if __name__ == "__main__":
    main()
