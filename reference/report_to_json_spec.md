# 研究报告 → JSON 字段提取规范

> **文件用途**：指导 AI（或人工）从基金研究报告（Markdown 格式）中提取 B 类字段，  
> 输出一个可直接合并到 `web-platform/public/data/{code}.json` 的 JSON Patch 文档。

---

## 使用方法

1. 将本规范提供给 AI，同时附上完整报告 MD 文件
2. 要求 AI 输出一个 **JSON 文档**（仅包含 B 类字段，不含 A 类字段）
3. 使用 `merge_b_fields.py` 脚本将输出合并到现有 JSON（不会覆盖已有 B 类字段，除非 `--overwrite` 标志）

---

## Prompt 模板

```
你是一个基金研究数据提取引擎。请从以下 Markdown 格式的基金研究报告中，
严格按照字段规范，提取所有 B 类字段，输出一个 JSON 对象。

规则：
1. 严格按照下面的 JSON Schema 输出，不要添加额外字段
2. 只输出能从报告中找到依据的内容，找不到则用 null
3. 文字内容保持简洁，最多2-3句话
4. 不要输出报告原文大段摘抄，要提炼关键信息
5. 最终只输出一个 JSON 代码块，不要有任何前缀说明

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
    "total": 72,                    // 数字，综合评分（满分100）
    "grade": "B+",                  // 字符串，综合等级（S/A/B+/B/C）
    "recommendation": "谨慎关注",   // 字符串，一句话投资建议
    "rating": "★★★☆☆",             // 字符串，五星制显示
    "logic": "...",                 // 字符串，核心投资逻辑（1-2句）

    "risks": [
      {
        "level": "高",              // "高" | "中" | "低"
        "label": "回撤风险",        // 简短标签
        "text": "..."               // 1-2句风险说明
      }
    ],

    "termAdvice": [
      {
        "term": "短期（1-3月）",
        "rating": "观望",           // "买入" | "加仓" | "持有" | "观望" | "减仓" | "卖出"
        "logic": "...",
        "suggestion": "..."
      },
      {
        "term": "中期（3-12月）",
        "rating": "...",
        "logic": "...",
        "suggestion": "..."
      },
      {
        "term": "长期（1年以上）",
        "rating": "...",
        "logic": "...",
        "suggestion": "..."
      }
    ]
  }
}
```

**提取来源**：
- `total` / `grade` → 第2.1节「综合评级」评分表格
- `risks[]` → 第2.2节「风险信号」汇总表，每行一个对象
- `termAdvice[]` → 第2.3节「短中长期操作建议」表格，每行一个对象

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
      "rankInPeer": "前20%",         // 同类排名描述
      "historicalFunds": ["基金A", "基金B"],  // 历史管理过的基金列表

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
- `historicalFunds` → 第4.2节历史基金列表
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
        "stocks": ["宁德时代", "亿纬锂能"]
      }
    ],

    "evolutionHighlights": [
      {
        "quarter": "2025Q4",
        "action": "减持光伏，加仓储能",
        "implication": "..."
      }
    ],

    "policyLinks": [
      {
        "policy": "新型储能规划",
        "impact": "直接利好",
        "stocks": ["宁德时代"]
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
    "tags": ["十五五规划", "新型储能", "新能源汽车"],

    "adaptability": {
      "overallRating": "高度契合",
      "score": 85,
      "rationale": "..."
    },

    "fifteenFive": {
      "coverage": "重点受益",
      "details": "..."
    },

    "scenarios": [
      {
        "name": "政策超预期落地",
        "probability": "中",          // "高" | "中" | "低"
        "impact": "正面",             // "正面" | "负面" | "中性"
        "description": "..."
      }
    ],

    "policyBreakdown": [
      {
        "policyName": "新型储能行动方案",
        "relevance": "直接受益",
        "details": "..."
      }
    ]
  }
}
```

**提取来源**：第八章各节

---

### 7. `tracking` — 来自第十章

```json
{
  "tracking": {
    "weekly": [
      {
        "dimension": "净值跟踪",
        "indicator": "日涨跌幅",
        "target": "与中证新能源走势对比",
        "action": "偏离>3%即关注"
      }
    ],

    "quarterly": [
      {
        "dimension": "持仓验证",
        "checkItem": "季报持仓是否符合策略承诺",
        "warningLine": "前10与声称方向不符",
        "exitLine": "连续2季偏离"
      }
    ],

    "alerts": [
      {
        "level": "一票否决",          // "一票否决" | "减仓" | "关注"
        "signal": "基金经理离职",
        "action": "立即评估换仓"
      }
    ],

    "positions": [
      {
        "triggerNav": 2.8,
        "action": "加仓",
        "ratio": "10%",
        "condition": "行业景气度向好"
      }
    ]
  }
}
```

**提取来源**：
- `weekly` → 第10.1节日常跟踪要点
- `quarterly` → 第10.2节季度复盘
- `alerts` → 第10.3节预警信号
- `positions` → 第10.4节持仓回顾节点

---

### 8. `exclusionCheck` — 来自第五章

```json
{
  "exclusionCheck": {
    "overallPass": true,
    "items": [
      {
        "item": "基金规模",
        "result": "pass",           // "pass" | "warn" | "fail"
        "detail": "规模12亿，适中"
      }
    ]
  }
}
```

**提取来源**：第五章排除法检查表格，每行一个对象

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
