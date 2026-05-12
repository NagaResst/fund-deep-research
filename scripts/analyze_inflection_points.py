#!/usr/bin/env python3
"""
Step 5A：净值拐点识别
用法：python3 skills/fund-deep-research/scripts/analyze_inflection_points.py <基金代码>

输入：/tmp/fund_research_{code}/raw/nav_daily.json
输出：/tmp/fund_research_{code}/analysis/inflection_points.json
"""

import json
import os
import sys


def find_local_extrema(data: list, window: int = 20) -> list:
    """滚动窗口识别局部极值点。"""
    n = len(data)
    extrema = []
    for i in range(window, n - window):
        nav_vals = [d["nav"] for d in data[i - window : i + window + 1]]
        current = data[i]["nav"]
        if current == max(nav_vals):
            extrema.append({"date": data[i]["date"], "nav": current, "type": "peak"})
        elif current == min(nav_vals):
            extrema.append({"date": data[i]["date"], "nav": current, "type": "trough"})
    return extrema


def filter_alternating(extrema: list) -> list:
    """过滤为严格交替的极值序列，同向取幅度更大的那个。"""
    if not extrema:
        return []
    result = [extrema[0]]
    for e in extrema[1:]:
        last = result[-1]
        if e["type"] != last["type"]:
            result.append(e)
        else:
            if e["type"] == "peak" and e["nav"] > last["nav"]:
                result[-1] = e
            elif e["type"] == "trough" and e["nav"] < last["nav"]:
                result[-1] = e
    return result


def calc_max_drawdown(navs: list, dates: list) -> tuple[float, str, str]:
    """计算最大回撤及对应的顶部/底部日期。"""
    peak, peak_date = navs[0], dates[0]
    max_dd, dd_peak_date, dd_trough_date = 0.0, dates[0], dates[0]
    for nav, dt in zip(navs, dates):
        if nav > peak:
            peak, peak_date = nav, dt
        dd = (nav - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd
            dd_peak_date = peak_date
            dd_trough_date = dt
    return round(max_dd, 2), dd_peak_date, dd_trough_date


def main():
    if len(sys.argv) < 2:
        print("用法：python3 analyze_inflection_points.py <基金代码>")
        sys.exit(1)

    code = sys.argv[1].strip()
    tmp = f"/tmp/fund_research_{code}"
    nav_path = f"{tmp}/raw/nav_daily.json"
    out_path = f"{tmp}/analysis/inflection_points.json"

    if not os.path.exists(nav_path):
        print(f"[ERROR] 找不到净值文件：{nav_path}", file=sys.stderr)
        sys.exit(1)

    with open(nav_path, encoding="utf-8") as f:
        records = json.load(f)

    # 解析净值，过滤无效记录，转为升序（最早→最新）
    data = []
    for r in records:
        try:
            data.append({"date": r["date"], "nav": float(r["nav"])})
        except (KeyError, ValueError, TypeError):
            pass
    data = list(reversed(data))  # API 返回降序，reversed 得升序

    if len(data) < 50:
        print(f"[WARN] 净值记录过少（{len(data)} 条），拐点识别可能不准确", file=sys.stderr)

    navs  = [d["nav"]  for d in data]
    dates = [d["date"] for d in data]

    # ── 拐点识别 ──────────────────────────────────────────────────────
    alternating = filter_alternating(find_local_extrema(data))

    segments = []
    for i in range(1, len(alternating)):
        prev, curr = alternating[i - 1], alternating[i]
        pct = (curr["nav"] - prev["nav"]) / prev["nav"] * 100
        segments.append(
            {
                "start_date": prev["date"],
                "start_nav":  prev["nav"],
                "end_date":   curr["date"],
                "end_nav":    curr["nav"],
                "change_pct": round(pct, 2),
                "direction":  "上涨" if pct > 0 else "下跌",
            }
        )

    top30 = sorted(segments, key=lambda x: abs(x["change_pct"]), reverse=True)[:30]
    major_chrono = sorted(
        [s for s in segments if abs(s["change_pct"]) >= 5],
        key=lambda x: x["start_date"],
    )

    # ── 关键统计 ──────────────────────────────────────────────────────
    max_nav       = max(navs)
    min_nav       = min(navs)
    cur_nav       = navs[-1]
    max_nav_date  = dates[navs.index(max_nav)]
    min_nav_date  = dates[navs.index(min_nav)]
    max_dd, dd_peak_date, dd_trough_date = calc_max_drawdown(navs, dates)

    history_pct = round((cur_nav - min_nav) / (max_nav - min_nav) * 100, 1) if max_nav != min_nav else 0.0
    total_return = round((cur_nav - 1.0) / 1.0 * 100, 1)

    result = {
        "fund_code": code,
        "nav_range": {
            "from":          data[0]["date"],
            "to":            data[-1]["date"],
            "total_records": len(data),
        },
        "key_stats": {
            "max_nav":            max_nav,
            "max_nav_date":       max_nav_date,
            "min_nav":            min_nav,
            "min_nav_date":       min_nav_date,
            "current_nav":        cur_nav,
            "current_date":       data[-1]["date"],
            "history_percentile": history_pct,
            "max_drawdown":       max_dd,
            "max_drawdown_peak_date":   dd_peak_date,
            "max_drawdown_trough_date": dd_trough_date,
            "total_return_pct":   total_return,
        },
        "top30_segments":       top30,
        "major_segments_chrono": major_chrono,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ 拐点分析完成，TOP30波段已保存至 {out_path}")
    print(f"   历史最高：{max_nav}（{max_nav_date}）　历史最低：{min_nav}（{min_nav_date}）")
    print(f"   当前净值：{cur_nav}（{data[-1]['date']}）　历史百分位：{history_pct}%")
    print(f"   最大回撤：{max_dd:.2f}%（{dd_peak_date} → {dd_trough_date}）")
    print(f"   主要波段（≥5%）：{len(major_chrono)} 段　TOP30 覆盖：{len(top30)} 段")


if __name__ == "__main__":
    main()
