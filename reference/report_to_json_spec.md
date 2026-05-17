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
7. ⚠️ **必需字段检查**：以下字段绝对不能遗漏：
  - `exclusionCheck`: 必须输出完整的10项排除法检查数组（见第10章规范）
  - `scoring`: 包含total/grade/dimensions/risks等完整评分数据
  - `stageAnalysis.stages`: 至少包含5个阶段的分析
  - `risk.radarDimensions`: 评分雷达图数据（可从scoring.dimensions推断，但建议明确输出）

8. 🔢 **数值字段规范**：
  - 所有数值字段（如`inceptionReturn`、`growthRate`、`nav`等）**绝对不能为 null**
  - 如果数据缺失或无法计算，应输出 `0` 或合理的默认值
  - 前端代码直接调用 `.toFixed()` 方法，null会导致运行时错误

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
        "level": "cautious",
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
        "period": "2017-03 → 2018-10",
        "returnPct": 16.03,
        "hs300Pct": 21.78,
        "excessPct": -5.75,
        "driverType": "beta",      // 常见值："beta" | "alpha" | "both" | "double_loss" | "defense"
        "driverLabel": "🌊 行业Beta主导",
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
**注意**：
- `period` 必须使用 `YYYY-MM → YYYY-MM`，不要输出 `2018Q2 → 2019Q2`、`2017.03—2018.10` 等旧格式
- `returnPct` / `hs300Pct` / `excessPct` 必须直接对应第3.1表格中的“基金收益 / 沪深300 / 超额”列，不能用 AI 自行重述替代
- `driverType` / `driverLabel` 必须来自第3.1表格“驱动属性”的结构化归纳，至少保证 `driverLabel` 可直接渲染
- `id/name/period` 要与 A 类中 `inflectionPoints[]` 的顺序对应
- 如果未来扩展 A 类 `inflectionPoints[]`，优先补 `stageId` 做精确阶段映射；在未提供 `stageId` 时，前端会退回使用这里的 `period`

### 2.1 `stageAnalysis.inflectionPoints`（增强字段）— 来自第三章 3.2

```json
{
  "stageAnalysis": {
    "inflectionPoints": [
      {
        "id": 1,
        "stageId": 1,
        "startDate": "2012-10-22",
        "endDate": "2012-12-03",
        "startNav": 1.008,
        "endNav": 0.872,
        "changePct": -13.49,
        "type": "trough",          // 保持与 A 类一致："peak" | "trough"
        "holdingsSummary": "指数跟踪为主，主动行业暴露较弱",
        "env": "欧债危机尾声叠加国内增长承压，风险偏好偏弱。",
        "managerAction": "仍按指数化框架跟踪中证500，主动调整空间有限。",
        "attribution": "主要是系统性回撤驱动，基金并无明显 Alpha 缓冲。"
      }
    ]
  }
}
```

**提取来源**：第3.2节「阶段分析（关键拐点复盘）」每一个拐点条目  
**注意**：
- 必须输出完整数组，数量与报告中的拐点条目一一对应；不要只输出少量“代表性拐点”
- `id` 必须与 A 类 `inflectionPoints[]` 编号对齐，保持同一顺序
- `startDate/endDate/startNav/endNav/changePct/type` 必须完整保留，不能只输出 `stageId/env/managerAction/attribution`
- `stageId` 必须映射到第3.1节阶段总览中的阶段 `id`，供前端精确构建阶段区间
- `holdingsSummary/env/managerAction/attribution` 直接服务网页 tooltip 展示，每项控制在 1-2 句，避免大段原文摘抄

---

### 3. `managers.current`（B 类字段）— 来自第四章

```json
{
  "managers": {
    "current": {
      "education": "经济学硕士",      // 学历/专业背景；直接供网页经理卡片展示
      "joinDate": "2011-07",         // 加入基金公司时间，格式 YYYY-MM
      "experience": "14.5年（证券从业）", // 从业年限；允许数字或带口径说明的短文本
      "title": "基金经理",           // 职称（如"基金经理"/"联席基金经理"）
      "style": "成长风格",           // 投资风格标签（3-5字）
      "manageDate": "2016-08-01",    // 开始管理本基金日期 YYYY-MM-DD
      "manageYears": 9.8,            // 管理年数（数字，保留1位小数）
      "bestReturn": 229.04,          // 历史最佳单产品任职回报（百分比数字）
      "worstReturn": -17.05,         // 历史最差单产品任职回报（百分比数字）
      "tenureReturn": 229.04,        // 任期内回报率（百分比数字，如229.04）
      "peerAvgReturn": 45.0,         // 同类平均回报率
      "rankInPeer": "前20%",         // 排名描述或名次文本
      "rankTotal": 1087,
      "historicalFunds": [
        {
          "name": "基金A",
          "code": "000001",
          "type": "股票型",
          "tenure": "2019-01 ~ 2022-12",
          "return": 35.6,
          "rank": 120,
          "rankTotal": 1087,
          "grade": "good",          // "top" | "good" | "ok" | "weak"
          "isCurrent": true
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
    },
    "history": [
      {
        "name": "经理A",
        "role": "独任",              // "独任" | "共管" | 其他简短角色标签
        "start": "2012-09-06",
        "end": "2015-03-11",         // 若仍在任则可为 null
        "tenure": "约2年6个月",
        "return": 71.99,
        "note": "阶段简评，1句即可"
      }
    ]
  }
}
```

**提取来源**：
- `education/joinDate/experience/title/style/manageDate/manageYears/bestReturn/worstReturn/tenureReturn/peerAvgReturn/rankInPeer/rankTotal` → 第4.1节表格与紧随其后的说明文字
- `historicalFunds[]` → 第4.2节历史基金列表；若报告无收益率，不要硬填空对象
- `philosophy` → 第4.3节投资理念与风格
- `consistencyAudit` → 第4.4节言行一致性审计
- `managers.history[]` → 第4.5节经理变更历史
- `abilityProfile` / `strengths/weaknesses` → 第4.6节综合能力画像

**注意**：
- 网页经理主卡片直接消费 `education/joinDate/bestReturn/worstReturn`，缺失时会退化为 `—`，因此这些字段若报告已给出，必须输出
- `historicalFunds[]` 最好补齐 `code/isCurrent/grade`；因为前端实时接口回写时会按 `code` 合并，缺 `code` 会丢失静态增强信息
- `experience` 可保留数字，也可在报告明确区分“证券从业口径/公募管理口径”时输出简短文本；`manageYears` 仍保持“管理本基金时长”的单独口径
- `managers.history[]` 是网页“历任基金经理传承”时间轴的直接数据源，不能只在报告里写表格而不输出到 JSON

---

### 4. `company`（B 类字段）— 来自第五章

```json
{
  "company": {
    "name": "华商基金管理有限公司",
    "shortName": "华商基金",
    "foundYear": 2005,
    "aumDesc": "旗下172只基金，公募管理规模约2029.3亿元，中型公募平台",
    "industryRank": "中型公募，主动权益风格鲜明",
    "complianceResult": "通过",      // "通过" | "风险"
    "complianceSummary": "合规检查通过，无一票否决项触发。管理疲劳是当前唯一需要持续跟踪的风险点。",
    "complianceChecks": [
      {
        "item": "黑名单核查",
        "pass": true,
        "warn": false,
        "detail": "公司和经理均未命中黑名单。"
      },
      {
        "item": "管理疲劳风险",
        "pass": false,
        "warn": true,
        "detail": "经理当前在管产品较多，需要持续跟踪。"
      }
    ]
  }
}
```

**提取来源**：
- `name/shortName/foundYear/aumDesc/industryRank` → 第5.1节基金公司概况
- `complianceChecks[]` → 第5.2节合规检查结果表
- `complianceResult/complianceSummary` → 第5.2节结论引用块 + 第5.3节合规结论

**注意**：
- 即使第五章结论是“全部通过”，也必须输出完整 `company` 对象，不能只保留 `exclusionCheck`
- `complianceChecks[]` 至少输出网页当前消费的 5 项：`黑名单核查 / 近3年处罚记录 / 内幕交易传闻 / 基金经理离职风险 / 管理疲劳风险`
- `pass/warn` 必须成对表达状态：正常通过使用 `pass=true,warn=false`；观察项使用 `pass=false,warn=true`
- `complianceSummary` 直接用于网页卡片摘要，控制在 1-2 句

---

### 5. `holdings`（B 类字段）— 来自第六章

```json
{
  "holdings": {
    "stockRatio": 92.5,              // 股票仓位比例（%）
    "bondRatio": 0.0,
    "cashRatio": 7.5,

    "top10": [
      {
        "rank": 1,
        "name": "宁德时代",
        "code": "300750",
        "ratio": 8.75,
        "sector": "储能电池",        // 前十大明细里的主题/类别标签，网页直接显示
        "color": "#58a6ff"          // 可选；若报告已能稳定映射主题色则输出
      }
    ],

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
- `top10[]` → 第6.1节前十大持仓表；若报告有“类别/主题/赛道”列，必须映射到 `sector`
- `themeGroups` → 第6.2节持仓主题分析
- `evolutionHighlights` → 第6.3节关键调仓解读
- `policyLinks` → 第六章政策关联分析
- 不要输出旧结构 `action/implication` 或 `policy/impact`

**注意**：
- 网页“前十大重仓股”图表和 tooltip 直接读取 `holdings.top10[].sector`，缺失时会表现为“没有主题”
- `top10[]` 至少应包含 `rank/name/code/ratio/sector`；若已有稳定主题色，可同时输出 `color`

---

### 6. `risk` — 来自第七章

```json
{
  "risk": {
    "maxDrawdownMonths": 26,

    "recentPerf": [
      {
        "period": "近1年",
        "fund": 84.39,
        "peer": 44.75,
        "hs300": 27.18,
        "excess": 39.64,
        "rank": 164,
        "rankTotal": 988,
        "warn": false,
        "note": "前17%"
      }
    ],

    "radarDimensions": [
      {
        "name": "收益能力",
        "score": 90
      },
      {
        "name": "风险控制",
        "score": 45
      }
    ],

    "riskBreakdown": {
      "volatilityRating": "高波动（29.04%，远超宽基指数）",
      "sharpeRating": "近1年极强（2.98），全期偏低（0.40）",
      "drawdownRating": "历史最大 -69.31%（34个月），近1年 -12.97%",
      "historicalMaxDrawdown": 69.31,
      "yearlyMaxDrawdowns": [
        {
          "year": 2025,
          "fund": 18.52,
          "hs300": 10.49
        }
      ]
    },

    "riskWarnings": [
      {
        "level": "high",
        "text": "历史最大回撤过深，持有体验差。",
        "category": "内部"
      },
      {
        "level": "medium",
        "text": "外部政策与行业景气可能压制估值。",
        "category": "外部"
      }
    ]
  }
}
```

**提取来源**：第七章各节

**注意**：
- `radarDimensions[]` 必须使用 `name/score`，不要再输出旧结构 `value/max`
- `riskBreakdown` 必须是对象，不是旧结构的风险条目数组
- `recentPerf[]` 需保留 `warn/note`，以便前端高亮短期异常
- `riskWarnings[]` 必须区分 `内部` / `外部` 风险，供前端分栏展示
- 🔧 **Fallback机制**: 如果AI未生成`radarDimensions`，`merge_b_fields.py`脚本会从`scoring.dimensions`自动计算生成（将score/maxScore转换为百分比）

---

### 7. `performance.milestones` — 来自第九章 9.3

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

**注意**：
- ⚠️ **CRITICAL**: `nav` 字段**绝对不能为 null**，前端代码直接调用 `toFixed(4)` 会报错
- 如果某节点确实没有净值数据（如转型节点），AI应输出 `nav: 0` 或合理的估算值
- 🔧 **Fallback机制**: 如果AI输出的nav为null，`merge_b_fields.py`脚本会自动将其替换为0

---

### 8. `policy` — 来自第八章

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

    "dualTimeline": [
      {
        "period": "2019-01 → 2021-12",
        "manager": {
          "type": "positive",       // "positive" | "highlight" | "warning" | "neutral"
          "event": "科技+顺周期轮动，进入主升浪",
          "return": "+269.66%（HS300 +64.09%）",
          "note": "..."
        },
        "market": {
          "type": "bull",           // "bull" | "policy" | "bear" | "neutral" | "warning"
          "event": "科技成长与新能源主线轮番强化",
          "note": "..."
        }
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
- `dualTimeline` 是第三章 3.1 时间轴的直接数据源，必须输出；不要以为只填 `stageAnalysis.stages` 就够了

---

### 9. `tracking` — 来自第十章

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

### 10. `exclusionCheck` — 来自第五章

```json
{
  "exclusionCheck": [
    {
      "item": "成立时间是否不足3年",
      "pass": true,
      "note": "成立于2017-03-16，已运行超过3年"
    },
    {
      "item": "规模是否过小或过大",
      "pass": true,
      "note": "当前规模31.51亿元，未触发<1亿元或>200亿元红线"
    },
    {
      "item": "基金经理任职是否不足2年",
      "pass": true,
      "note": "现任经理管理本基金超过2年"
    },
    {
      "item": "近3年业绩是否落入后30%",
      "pass": true,
      "note": "近3年业绩排名未落入同类后30%"
    },
    {
      "item": "最大回撤是否显著劣于同类",
      "pass": true,
      "note": "最大回撤未显著高于同类平均20个百分点以上"
    },
    {
      "item": "基金经理是否在黑名单中",
      "pass": true,
      "note": "黑名单核查未命中基金经理"
    },
    {
      "item": "基金公司是否在黑名单中",
      "pass": true,
      "note": "黑名单核查未命中基金公司"
    },
    {
      "item": "是否频繁更换基金经理",
      "pass": true,
      "note": "近3年未出现2次及以上异常更换"
    },
    {
      "item": "是否存在严重风格漂移",
      "pass": true,
      "note": "基金经理表述与实际持仓主线基本一致，未见严重漂移"
    },
    {
      "item": "费率是否显著高于同类平均",
      "pass": true,
      "note": "管理费、托管费与申赎费率未见明显高于同类且无合理解释"
    }
  ]
}
```

**提取来源**：
- 优先取第五章排除法检查表格
- 若第五章只保留摘要或表格未写全，必须回看整份报告可核验事实补齐这10项（如基础信息、业绩、风险、基金经理、黑名单、费率等章节）

**注意**：
- ⚠️ **CRITICAL**: `exclusionCheck` 是必需字段，AI提取时**绝对不能遗漏**
- `exclusionCheck` 必须固定输出 **10项**，且按上面的顺序输出，不得因为第五章省略表格而减少条目数
- `pass=true` 表示 **未触发一票否决**；`pass=false` 表示触发排除条件
- `note` 必须写清楚判断依据，优先引用报告中的具体事实、数字或结论，避免空泛表述
- 若某项在报告中确实找不到足够依据，可写 `pass: null`，但仍必须保留该项，不得删除
- 不要输出旧结构 `overallPass/items/result/detail`，前端当前消费的是对象数组 `[{item, pass, note}]`
- 🔧 **Fallback机制**: 如果AI未生成此字段，`merge_b_fields.py` 脚本会自动生成默认10项检查（但note会是通用提示，建议AI完整提取）

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
