#!/usr/bin/env python3
"""
Step 1 第三步：抓取日频净值历史（分页全量）
用法：python3 skills/fund-deep-research/scripts/fetch_nav_daily.py <基金代码> --output <路径>

默认输出路径：/tmp/fund_research_{code}/raw/nav_daily.json
"""

import json
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

PAGE_SIZE = 200
MAX_WORKERS = 8


def _build_url(fund_code: str, page: int) -> str:
    return (
        f"https://api.fund.eastmoney.com/f10/lsjz"
        f"?fundCode={fund_code}&pageIndex={page}&pageSize={PAGE_SIZE}"
        f"&startDate=2000-01-01&endDate=2099-12-31"
    )


def _fetch_page(fund_code: str, page: int, headers: dict) -> tuple[int, list]:
    """返回 (page_number, records)，失败返回空列表。"""
    try:
        resp = requests.get(_build_url(fund_code, page), headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        lst = (data.get("Data") or {}).get("LSJZList") or []
        return page, lst
    except Exception as e:
        print(f"[WARN] Page {page} failed: {e}", file=sys.stderr)
        return page, []


def fetch_nav_daily(fund_code: str) -> list:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://fundf10.eastmoney.com/",
    }

    # ── 第1页：获取总记录数 + 实际每页大小 ───────────────────────────
    _, first_page_records = _fetch_page(fund_code, 1, headers)
    if not first_page_records:
        return []

    resp1 = requests.get(_build_url(fund_code, 1), headers=headers, timeout=15)
    total = resp1.json().get("TotalCount", 0) or len(first_page_records)

    # API 实际返回的每页条数（可能小于请求的 PAGE_SIZE）
    actual_page_size = len(first_page_records)
    total_pages = math.ceil(total / actual_page_size)
    print(
        f"[INFO] 总记录数：{total}，实际每页：{actual_page_size}，"
        f"共 {total_pages} 页，并发抓取中...",
        file=sys.stderr,
    )

    # ── 多线程并发抓取剩余页 ──────────────────────────────────────────
    page_results: dict[int, list] = {1: first_page_records}

    if total_pages > 1:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(_fetch_page, fund_code, p, headers): p
                for p in range(2, total_pages + 1)
            }
            for future in as_completed(futures):
                page_no, records = future.result()
                page_results[page_no] = records
                print(
                    f"[INFO] Page {page_no}/{total_pages}: {len(records)} records",
                    file=sys.stderr,
                )

    # ── 按页号顺序合并（API 返回时间降序，页内顺序保留即可）─────────────
    all_records = []
    for p in sorted(page_results):
        all_records.extend(page_results[p])

    nav_list = [
        {
            "date": x["FSRQ"],
            "nav": x["DWJZ"],
            "acc_nav": x["LJJZ"],
            "change": x["JZZZL"],
        }
        for x in all_records
    ]
    return nav_list


def main():
    if len(sys.argv) < 2:
        print("用法：python3 fetch_nav_daily.py <基金代码> [--output <路径>]")
        sys.exit(1)

    fund_code = sys.argv[1].strip()

    # 解析 --output
    output_path = f"/tmp/fund_research_{fund_code}/raw/nav_daily.json"
    raw_args = sys.argv[2:]
    for i, arg in enumerate(raw_args):
        if arg == "--output" and i + 1 < len(raw_args):
            output_path = raw_args[i + 1]
            break

    nav_list = fetch_nav_daily(fund_code)

    if not nav_list:
        print(f"[ERROR] 未获取到任何净值记录，基金代码：{fund_code}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(nav_list, f, ensure_ascii=False)

    latest = nav_list[0]["date"] if nav_list else "N/A"
    earliest = nav_list[-1]["date"] if nav_list else "N/A"
    print(
        f"✅ 已获取 {len(nav_list)} 条净值记录\n"
        f"   最新日期：{latest}　最早日期：{earliest}\n"
        f"   已保存至：{output_path}"
    )


if __name__ == "__main__":
    main()
