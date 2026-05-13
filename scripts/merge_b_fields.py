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


def deep_merge(base: dict, patch: dict, overwrite: bool, path: str = "") -> list:
    """
    深度合并 patch 到 base。
    - 若 overwrite=False，只填充 base 中 None 或不存在的字段
    - 返回变更日志 [(path, old, new)]
    """
    changes = []
    for key, val in patch.items():
        key_path = f"{path}.{key}" if path else key
        if key not in base or base[key] is None:
            base[key] = val
            changes.append((key_path, None, val))
        elif isinstance(val, dict) and isinstance(base.get(key), dict):
            changes.extend(deep_merge(base[key], val, overwrite, key_path))
        elif isinstance(val, list) and len(val) > 0:
            if overwrite or not base[key]:
                changes.append((key_path, base[key], val))
                base[key] = val
        elif overwrite:
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
