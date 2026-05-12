# 结构化数据转换（Web 平台 JSON）

研究报告生成后，可选择将其转换为 Web 平台使用的结构化 JSON 数据，用于在线展示。

## 目标文件路径

```
web-platform/public/data/{基金代码}.json   ← 基金详情数据
web-platform/public/data/index.json        ← 基金清单（需同步更新）
```

---

## JSON Schema（14个顶层字段）

```
id, meta, basic, fees, scale, performance, risk,
holdings, managers, policy, exclusionCheck, scoring, navHistory, tracking
```

每个字段的关键子字段：

| 字段 | 关键内容 |
|------|---------|
| `id` | 基金代码字符串 |
| `meta` | reportDate, dataDate, disclaimer |
| `basic` | code, fullName, shortName, type, subType, riskLevel, riskCode(1-5), foundDate, manager(公司), navFallback, inceptionReturn, companyShort |
| `fees` | management, custodian, salesService, subscriptionMax, breakdown数组 |
| `scale` | nav(亿元), shares(亿份), date |
| `performance` | stages数组, annual数组, quarterly数组（每条含fund/peer/hs300/rank/rankTotal/quartile） |
| `risk` | volatility, sharpe, maxDrawdown, radarDimensions, riskBreakdown, positionHistory |
| `holdings` | date, stockRatio, top10数组, sectors数组, bondStructure(债基), policyLinks |
| `managers` | current对象（含historicalFunds数组, managerId）, history数组 |
| `policy` | tags, scenarios(悲观/基准/乐观), policyBreakdown, fifteenFive, longTermRisks, dualTimeline, timeline |
| `exclusionCheck` | 数组，每条含 item, pass(bool), note |
| `scoring` | total(0-100), dimensions数组, recommendation, recommendationType(buy/hold/cautious/sell), reasoning, conclusion, suitableFor, allocationSuggestions |
| `navHistory` | 通常为空数组 [] （由 API 实时填充） |
| `tracking` | weekly数组, quarterly数组, alerts数组（含level: critical/warning/info） |

---

## 转换流程

### Step A：从研究报告提取数据

逐章读取 `.md` 研究报告，按以下 Schema 字段映射：

| 报告章节 | JSON 字段 |
|---------|----------|
| 第一章（基金基本信息） | `basic`, `fees`, `scale` |
| 第二章（研究结论与配置建议） | `scoring` |
| 第三章（基金经理深度分析） | `managers` |
| 第四章（基金公司分析） | `basic.companyShort`（补充） |
| 第五章（政策与宏观环境） | `policy.tags`, `policy.scenarios`, `policy.policyBreakdown`, `policy.fifteenFive`, `policy.longTermRisks` |
| 第六章（持仓分析） | `holdings` |
| 第七章（历史业绩分析） | `performance.stages`, `performance.annual`, `performance.quarterly`, `risk`, `policy.timeline`, `policy.dualTimeline` |
| 第八章（排除法检查） | `exclusionCheck`（9条，每条 pass: true/false） |
| 第九章（后续跟踪计划） | `tracking` |

### Step B：填写关键字段时的注意事项

**riskCode 对照**：
- R1 = 1（低风险）
- R2 = 2（中低风险）
- R3 = 3（中风险）
- R4 = 4（中高风险）
- R5 = 5（高风险）

**recommendationType 枚举**：
- `"buy"` — 推荐/强烈推荐
- `"hold"` — 持有/观望
- `"cautious"` — 谨慎
- `"sell"` — 减持/放弃

**dualTimeline 颜色规则**（type 字段）：
- manager 端：`positive`=红, `highlight`=黄, `warning`=绿(警示), `neutral`=灰
- market 端：bull/policy=`bull`, neutral=`neutral`, bear=`bear`

**null 的使用原则**：
- 数据在报告中明确缺失（如未公开） → 填 `null`
- 不要凭估算填写数字，除非报告有明确说明

**债券型基金特殊字段**：
- `holdings.bondStructure` 数组（政策性金融债/信用债/可转债等分类）
- `basic.riskCode` 通常为 2（中低风险）
- 行业集中度检查项 `exclusionCheck` 通常 pass: true

**ETF/指数基金**：
- `holdings.top10` 的 ratio 若未在报告中逐一列出可全部填 `null`
- 需填写 `tracking`（trackingIndex, trackingError, correspondingETF 等）

**字符串中的引号**：
- JSON 字符串值内不使用英文双引号，改用中文书名号 `「」`

**exclusionCheck 行业集中度**：
- 行业集中度 > 70% → `pass: false`（指数基金也标注，note 中说明为指数设计特性）

### Step C：填写 managerId

基金经理的 managerId 从东方财富页面获取：

```bash
# 从基金f10页面抓取
curl -s "https://fundf10.eastmoney.com/jjjl_{基金代码}.html" | grep -oE 'manager/[0-9]+\.html' | head -3
```

将得到的数字 ID 填入 `managers.current.managerId`（字符串格式）。

多经理基金填主要经理的 ID；填入后前端将自动从东方财富实时拉取该经理名下所有在管基金数据。

---

## 更新 index.json

`index.json` 是首页基金清单，每新增一只基金需同步追加一条记录：

```json
{
  "id": "基金代码",
  "shortName": "基金简称",
  "type": "股票型",
  "subType": "指数型-股票",
  "riskLevel": "中高风险",
  "riskCode": 4,
  "return1Y": 54.83,
  "return3Y": null,
  "score": 82,
  "recommendation": "推荐，科技主题核心配置",
  "recommendationType": "buy",
  "navFallback": 1.5253,
  "reportDate": "2026-05-07",
  "manager": "金泽宇"
}
```

**字段来源**：
- `return1Y` / `return3Y` → 研究报告第七章业绩数据
- `score` → 研究报告第二章综合评分
- `recommendation` / `recommendationType` → 研究报告第二章建议
- `navFallback` → 研究报告第一章当前净值（dataDate 当日）
- `manager` → 现任基金经理姓名（多经理取第一位）

**删除基金**：从 `index.json` 数组中移除对应条目即可（JSON 文件保留备查）。

---

## 验证

JSON 创建完成后运行验证：

```bash
python3 -c "
import json
d = json.load(open('web-platform/public/data/{基金代码}.json'))
print('JSON valid, keys:', list(d.keys()))
print('score:', d['scoring']['total'])
print('exclusions pass:', all(x['pass'] for x in d['exclusionCheck']))
"
```

验证通过后重新构建前端：

```bash
cd web-platform && npm run build
```
