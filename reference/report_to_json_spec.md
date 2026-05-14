# 研究报告 → JSON 字段提取规范

> **文件用途**：指导 AI（或人工）从基金研究报告（Markdown 格式）中提取 B 类字段，  
> 输出一个可直接合并到 `web-platform/public/data/{code}.json` 的 JSON Patch 文档。

---

## 使用方法

1. 将本规范提供给 AI，同时附上完整报告 MD 文件
2. 要求 AI 输出一个 **JSON 文档**（仅包含 B 类字段，不含 A 类字段）
3. 使用 `merge_b_fields.py` 脚本将输出合并到现有 JSON（不会覆盖已有 B 类字段，除非 `--overwrite` 标志）

> 当前 Web 端的 **canonical schema** 以 `web-platform/public/data/003984.json` 为准。
> 若本规范中的章节示例与历史旧 JSON / 旧提示词冲突，**一律以当前前端实际消费结构为准**。

---

## Prompt 模板

```
你是一个基金研究数据提取引擎。请从以下 Markdown 格式的基金研究报告中，
严格按照字段规范，提取所有 B 类字段，输出一个 JSON 对象。

规则：
1. 严格按照下面的 JSON Schema 输出，不要添加额外字段，也不要沿用旧字段名
2. 只输出能从报告中找到依据的内容，找不到则用 null
3. 文字内容保持简洁，最多2-3句话
4. 不要输出报告原文大段摘抄，要提炼关键信息
5. 最终只输出一个 JSON 代码块，不要有任何前缀说明
6. 输出必须与当前 Web 前端消费结构兼容，例如：
  - `tracking.alerts[]` 使用 `icon/text/level`
  - `exclusionCheck` 是数组，不是 `{overallPass, items}` 对象
  - `scoring.risks[]` 使用 `type/note/level`
  - `scoring.termAdvice[]` 使用 `term/icon/level/advice`

字段规范见下方各章节说明。
报告内容：
[粘贴报告 MD 内容]
```

---

## 字段规范（B 类）

### 1. `scoring` — 来自第二章

```json
{
  "scoring": {
    "total": 77,
    "grade": "良好",
    "recommendation": "观望（谨慎建仓)",
    "recommendationType": "cautious",   // "cautious" | "buy" | "sell" | "strong_buy"
    "rating": "★★★",
    "logic": "...",

    "dimensions": [
      {
        "name": "超额收益能力",
        "score": 24,
        "maxScore": 30,
        "pros": ["..."],
        "cons": ["..."]
      }
    ],

    "risks": [
      {
        "type": "极端回撤风险",
        "level": "high",             // "high" | "medium" | "low"
        "note": "..."
      }
    ],

    "policyItems": [
      {
        "name": "十五五能源规划",
        "date": "2025-03",
        "content": "...",
        "impact": "strong_pos",      // "strong_pos" | "pos" | "neutral" | "light_neg" | "neg"
        "impactLabel": "🟢 强利好"
      }
    ],

    "marketStatus": [
      {
        "dim": "净值位置",
        "status": "81.3% 历史分位",
        "statusType": "warning",     // "positive" | "warning" | "neutral" | "cautious"
        "detail": "..."
      }
    ],

    "allocationSuggestions": [
      {
        "scenario": "新入场投资者",
        "action": "暂不建仓",
        "note": "..."
      }
    ],

    "suitableFor": ["..."],
    "notSuitableFor": ["..."],

    "termAdvice": [
      {
        "term": "短期（1-3月）",
        "icon": "⚠️",
        "level": "cautious",        // "positive" | "neutral" | "cautious"
        "advice": "..."
      }
    ]
  }
}
```

**提取来源**：
- `total` / `grade` / `recommendation` / `logic` / `dimensions[]` → 第2章主结论与评分表
- `risks[]` → 第2章「风险信号」
- `policyItems[]` → 第2章政策红利表格
- `marketStatus[]` → 第2章市场状态表格
- `allocationSuggestions[]` / `suitableFor[]` / `notSuitableFor[]` → 第2章配置建议与适用场景
- `termAdvice[]` → 第2章短中长期建议
- 不要输出旧结构 `label/text`、`rating/logic/suggestion`

---

### 2. `stageAnalysis.stages` — 来自第三章

```json
{
  "stageAnalysis": {
    "stages": [
      {
        "id": 1,
        "name": "蛰伏初建",
        "emoji": "🌱",
        "period": "2017.03—2018.10",
        "color": "#6b7280",
        "description": "...",        // 1-2句该阶段核心特征（市场/基金表现）
        "env": "...",                // 市场环境描述（1句）
        "managerAction": "...",      // 基金经理的操作或策略（1句）
        "attribution": "..."         // 涨跌归因（1句）
      }
    ]
  }
}
```

**提取来源**：第3.1节「阶段总览」表格 + 各阶段分析小节  
**注意**：`id/name/period` 要与 A 类中 `inflectionPoints[]` 的顺序对应

---

### 3. `managers.current`（B 类字段）— 来自第四章

```json
{
  "managers": {
    "current": {
      "title": "基金经理",           // 职称（如"基金经理"/"联席基金经理"）
      "style": "成长风格",           // 投资风格标签（3-5字）
      "manageDate": "2016-08-01",    // 开始管理本基金日期 YYYY-MM-DD
      "manageYears": 9.8,            // 管理年数（数字，保留1位小数）
      "tenureReturn": 229.04,        // 任期内回报率（百分比数字，如229.04）
      "peerAvgReturn": 45.0,         // 同类平均回报率
      "rankInPeer": "前20%",         // 排名描述或名次文本
      "rankTotal": 1087,
      "historicalFunds": [
        {
          "name": "基金A",
          "type": "股票型",
          "tenure": "2019-01 ~ 2022-12",
          "return": 35.6
        }
      ],

      "philosophy": [
        { "label": "核心投资理念", "text": "..." },
        { "label": "选股方法论", "text": "..." },
        { "label": "仓位管理风格", "text": "..." },
        { "label": "风格稳定性", "text": "..." }
      ],

      "consistencyAudit": [
        {
          "period": "2026年Q1·策略转型",
          "result": "pass",           // "pass" | "warn" | "fail"
          "label": "一致",            // 简短标签
          "stated": "...",            // 季报/访谈中声称的策略
          "actual": "...",            // 实际持仓/操作
          "evaluation": "..."         // 点评（1句）
        }
      ],

      "abilityProfile": {
        "best": "...",                // 最强能力描述
        "worst": "...",               // 最弱能力描述
        "goodEnv": ["适合的市场环境1", "适合的市场环境2"],
        "badEnv": ["不适合的市场环境1", "不适合的市场环境2"]
      },

      "strengths": ["..."],           // 优势列表
      "weaknesses": ["..."]           // 劣势列表
    }
  }
}
```

**提取来源**：
- `title/style/manageDate/manageYears/tenureReturn/peerAvgReturn/rankInPeer` → 第4.1节表格
- `historicalFunds[]` → 第4.2节历史基金列表；若报告无收益率，不要硬填空对象
- `philosophy` → 第4.3节投资理念与风格
- `consistencyAudit` → 第4.4节言行一致性审计
- `abilityProfile` → 第4.6节综合能力画像
- `strengths/weaknesses` → 第4.5节基金经理评价

---

### 4. `holdings`（B 类字段）— 来自第六章

```json
{
  "holdings": {
    "stockRatio": 92.5,              // 股票仓位比例（%）
    "bondRatio": 0.0,
    "cashRatio": 7.5,

    "themeTitle": "新能源产业链布局",   // 主题标题
    "themeSubtitle": "政策强催化+景气回升", // 副标题
    "concentrationLabel": "高度集中",  // 集中度描述

    "themeGroups": [
      {
        "name": "储能与电池",
        "color": "#3b82f6",
        "ratio": 32.5,
        "stocks": "宁德时代 / 亿纬锂能",
        "note": "..."
      }
    ],

    "evolutionHighlights": [
      {
        "quarter": "2025Q4",
        "type": "positive",         // "positive" | "warning" | "neutral"
        "change": "减持光伏，加仓储能",
        "return": "+12.4%",
        "theme": "聚焦储能链",
        "insight": "..."
      }
    ],

    "policyLinks": [
      {
        "sector": "储能",
        "color": "#58a6ff",
        "stocks": "宁德时代 / 亿纬锂能",
        "policyNote": "..."
      }
    ]
  }
}
```

**提取来源**：
- `stockRatio/bondRatio/cashRatio` → 第6.1节资产配置
- `themeGroups` → 第6.2节持仓主题分析
- `evolutionHighlights` → 第6.3节持仓演变
- `policyLinks` → 第六章政策关联分析
- 不要输出旧结构 `action/implication` 或 `policy/impact`

---

### 5. `performance.milestones` — 来自第九章 9.3

```json
{
  "performance": {
    "milestones": [
      {
        "date": "2021-11-29",
        "nav": 3.8813,
        "label": "历史最高点",
        "type": "peak"               // "peak" | "low" | "current" | "neutral"
      }
    ]
  }
}
```

**提取来源**：第9.3节「重要节点净值复盘」表格，每行一个对象  
**type 对应规则**：
- `peak` = 历史最高/阶段新高
- `low` = 最低点/回撤谷底
- `current` = 当前净值
- `neutral` = 成立/回到面值等中性节点

---

### 6. `policy` — 来自第八章

```json
{
  "policy": {
    "tags": [
      {
        "label": "十五五规划",
        "strength": "high",        // "high" | "medium" | "low"
        "color": "#F54E48"
      }
    ],

    "industryOverview": [
      {
        "point": "新能源汽车渗透率",
        "detail": "..."
      }
    ],

    "cyclePeriod": "政策红利期",
    "cycleReason": "...",

    "fifteenFive": [
      {
        "direction": "关键矿产安全保障",
        "color": "#F54E48",
        "description": "...",
        "holdings": "盐湖股份 / 赣锋锂业"
      }
    ],

    "longTermRisks": [
      {
        "risk": "碳酸锂产能过剩再现",
        "level": "medium",
        "signal": "..."
      }
    ],

    "adaptability": [
      {
        "env": "🐂 新能源顺风期",
        "perf": "...",
        "color": "#F54E48"
      }
    ],

    "scenarios": [
      {
        "type": "基准",               // "乐观" | "基准" | "悲观"
        "probability": 55,
        "color": "#58a6ff",
        "returnLow": 20,
        "returnHigh": 30,
        "trigger": "..."
      }
    ],

    "policyBreakdown": [
      {
        "sector": "储能",
        "icon": "⚡",
        "color": "#58a6ff",
        "logic": "...",
        "stocks": ["宁德时代"]
      }
    ],

    "note": "..."
  }
}
```

**提取来源**：第八章各节

**注意**：
- `tags` 必须输出对象数组，不是字符串数组
- `fifteenFive` / `adaptability` 必须输出数组，不是单对象
- `scenarios` 必须包含概率和收益区间，不能再使用旧字段 `name/impact/description`
- `policyBreakdown` 必须可直接支撑前端卡片展示

---

### 7. `tracking` — 来自第十章

```json
{
  "tracking": {
    "weekly": [
      "净值方向验证：每日净值涨跌是否与锂电/锂矿/新能源板块行情一致"
    ],

    "quarterly": [
      "持仓变化：新季报前十持仓是否维持主线，锂矿资源占比是否稳定"
    ],

    "alerts": [
      {
        "level": "critical",        // "critical" | "warning"
        "icon": "🚨",
        "text": "基金经理更换：需重新完整评估接任者"
      }
    ]
  }
}
```

**提取来源**：
- `weekly` → 第10.1节日常跟踪要点
- `quarterly` → 第10.2节季度复盘
- `alerts` → 第10.3节预警信号

**注意**：
- `weekly` / `quarterly` 当前前端消费的是 **字符串数组**，不是对象数组
- `alerts` 必须使用 `icon/text/level`，不要再输出 `signal/action`
- 第10.4节「持仓回顾节点」当前不属于 `tracking` canonical schema，如需落库请单独扩展前端后再定义

---

### 8. `exclusionCheck` — 来自第五章

```json
{
  "exclusionCheck": [
    {
      "item": "基金规模是否过小（<2亿元）",
      "pass": true,
      "note": "规模31.51亿元，规模适中，无清盘风险"
    }
  ]
}
```

**提取来源**：第五章排除法检查表格，每行一个对象

**注意**：不要输出旧结构 `overallPass/items/result/detail`，前端当前消费的是对象数组 `[{item, pass, note}]`

---

## 合并脚本说明

提取完成后，使用以下命令将 B 类字段合并到现有 JSON：

```bash
# 首次填充（已有字段不覆盖）
python3 skills/fund-deep-research/scripts/merge_b_fields.py <基金代码> <B类字段JSON文件>

# 强制覆盖更新
python3 skills/fund-deep-research/scripts/merge_b_fields.py <基金代码> <B类字段JSON文件> --overwrite
```

---

## 完整流水线

```bash
# Step 1：运行研究脚本，生成缓存
python3 skills/fund-deep-research/scripts/parallel_data_collection_v2.py 003984

# Step 2：生成研究报告（AI辅助写作）
# → 输出到 基金研究报告/{code}_*.md

# Step 3：用缓存自动填写 A 类字段
python3 skills/fund-deep-research/scripts/build_json_from_cache.py 003984

# Step 4：用报告 AI 提取 B 类字段
# → 使用本规范，将 AI 输出保存为 /tmp/fund_research_003984/b_fields.json

# Step 5：合并 B 类字段
python3 skills/fund-deep-research/scripts/merge_b_fields.py 003984 /tmp/fund_research_003984/b_fields.json
```
