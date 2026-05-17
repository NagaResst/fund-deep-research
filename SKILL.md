---
name: fund-deep-research
description: 基金深度研究助手。自动抓取最新基金数据、联网搜索补充信息、计算风险指标、生成完整研究报告。**强制要求**：脚本数据缺失时必须联网搜索补全，绝不允许输出N/A过多的报告。
---

> ⚠️ **免责声明**：本工具仅供个人学习和信息整理使用，所有分析内容均不构成任何投资建议。投资有风险，入市需谨慎，请依据自身判断做出投资决策。

# 基金深度研究 Skill（完整版）

> 本 Skill 旨在还原基金的真实样貌与发展规律——穿透表面净值数据，追溯每一次涨跌背后的政策驱动、经理决策与市场环境，从而形成对基金"人、策略、时机"三位一体的立体判断。

## 🎯 核心目标

输入基金代码 → **多步骤数据获取** → **强制完整性检查** → **联网搜索补充** → 生成高质量研究报告

**关键原则**：
1. ✅ 脚本是起点，不是终点
2. ✅ 数据缺失必须联网搜索补充
3. ✅ 报告不能有过多N/A字段
4. ✅ 所有数据必须是最新的

---

## 📂 临时目录规范（必须遵守）

所有中间数据（原始JSON、搜索日志、章节草稿）**统一存入 `/tmp/fund_research_{code}/`**，不得写入仓库目录。  
仓库目录只允许写入**最终报告一个文件**：`基金研究报告/{code}_{基金简称}_{日期}.md`

```
/tmp/fund_research_{code}/
├── raw/
│   ├── fund_enhanced.json          ← ak_fund_basic.py (增强版)
│   ├── risk_metrics.json           ← calc_risk_metrics.py
│   ├── relative_metrics.json       ← calc_relative_metrics.py (新增: Beta/Alpha等)
│   ├── holdings.json               ← ak_holdings.py
│   ├── quarterly.json              ← ak_quarterly_calc.py
│   ├── nav_daily.json              ← ak_nav_history.py
│   ├── manager_info.json           ← fetch_manager_info.py (增强版: AKShare+网页)
│   ├── inflection_points.json      ← calc_inflection_points.py
│   ├── annual_returns.json         ← calc_annual_returns.py
│   ├── institutional_risk.json     ← scan_institutional_risk.py
│   └── blacklist.json              ← check_blacklist.py
├── analysis/
│   └── search_log.md               ← 每轮联网搜索结果追加写入（完整原文）
└── meta.json                       ← 记录当前研究的基金代码和抓取时间戳
```

---

## 🏗️ 数据获取架构（四层混合架构）

本 Skill 采用**四层混合架构**，平衡自动化效率与数据完整性：

### Layer 1: AKShare SDK 获取层（70%结构化数据）

**核心优势**：稳定性高、更新及时、返回标准 DataFrame

| 脚本 | 功能 | 输出字段示例 |
|------|------|------------|
| `ak_fund_basic.py` | 基金基础信息+阶段收益 | 名称、代码、类型、成立日期、规模、经理、费率、风险等级(R1-R5)、赎回费规则(5档)、申购费原价 |
| `ak_nav_history.py` | 日度净值历史 | 2205条日度净值记录 |
| `ak_holdings.py` | 持仓结构+行业配置 | 前十大重仓股、行业分布、资产配置比例 |
| `ak_quarterly_calc.py` | 季度业绩计算 | 近10季收益率、持仓演变 |

### Layer 2: 本地计算层（衍生指标）

**核心优势**：基于原始数据精确计算，支持多期对比

| 脚本 | 功能 | 输出指标 |
|------|------|---------|
| `calc_risk_metrics.py` | 风险指标计算 | 夏普比率(1Y/2Y/3Y)、最大回撤、波动率、索提诺比率、卡玛比率 |
| `calc_relative_metrics.py` | 相对基准指标(新增) | Beta值、Alpha年化、信息比率、跟踪误差、R²、相关系数 |
| `calc_inflection_points.py` | 拐点识别 | 30+个主要拐点、阶段划分 |
| `calc_annual_returns.py` | 年度收益率 | 2017-2025完整年度数据 |

### Layer 3: 旧版爬虫层（特定深度数据）

**核心优势**：补充AKShare无法覆盖的深度信息

| 脚本 | 功能 | 输出字段 |
|------|------|---------|
| `fetch_manager_info.py` | 基金经理信息(增强版) | 在管基金数(14只)、在管总规模(176.16亿)、从业年限(10年)、管理疲劳预警、学历背景(需网页补充) |

**技术亮点**：
- ✅ AKShare优先获取结构化数据（准确率100%）
- ✅ 网页抓取补充非结构化信息（学历、履历）
- ✅ 智能数据合并，自动去重和优先级管理

### Layer 4: 联网搜索层（30%非结构化数据）

**核心优势**：补充政策、舆情、季报原文等非结构化数据

| 搜索内容 | 用途 | 示例 |
|---------|------|------|
| 政策文件及文号 | 第八章政策匹配度评估 | "发改能源〔2025〕XXX号" |
| 季报原文 | 第三章三线叙事、言行一致性审计 | "投资策略和运作分析"原文 |
| 经理投资理念 | 第四章深度分析 | 访谈、路演、媒体报道 |
| 公司合规记录 | 第五章一票否决检查 | 监管处罚、内幕交易传闻 |
| 宏观市场环境 | 第二章维度三、拐点归因 | 流动性、估值、行业景气度 |

---

## 📋 执行流程（严格按顺序）

### Step 0：🔍 预检与缓存管理（必须最先执行）

> **每次研究开始前**，先运行以下一条命令，脚本会自动完成所有预检、目录创建、旧缓存清理和 meta.json 写入，并输出 `NEXT_ACTION` 指引后续步骤。

```
python skills/fund-deep-research/scripts/precheck.py <基金代码>
```

**脚本自动处理以下所有情况**：

| `NEXT_ACTION` 输出 | 含义 | 后续动作 |
|---|---|---|
| `FULL_FETCH` | 无缓存或已过期或基金代码变更 | 从 Step 1 开始全量拉取 |
| `PARTIAL_FETCH` | 缓存新鲜但部分文件缺失 | 仅补跑缺失文件对应脚本 |
| `REFRESH_NAV` | 缓存存在但净值超过1天 | 重拉 `nav_daily.json` 和 `fund_enhanced.json` |
| `SKIP_TO_STEP2` | 缓存完整且新鲜（T-1内） | 直接跳到 Step 2 执行完整性检查 |

---

### Step 1：运行基础脚本获取初始数据

**Step 1 必须严格跟随 `NEXT_ACTION` 分流执行**：

- `FULL_FETCH`: 使用并行脚本一次性拉齐 11 个文件。
- `PARTIAL_FETCH`: 仅补跑缺失文件对应脚本，不得改成全量重跑。
- `REFRESH_NAV`: 仅刷新 `nav_daily.json` 与 `fund_enhanced.json`；若预检同时提示缺失文件，再补跑对应脚本。
- `SKIP_TO_STEP2`: 不运行 Step 1，直接进入 Step 2。

只有在 `NEXT_ACTION=FULL_FETCH` 时，才默认使用并行脚本，一条命令同时运行 11 个脚本以节省时间：

> ⚠️ **所有脚本输出必须保存到 `/tmp/fund_research_{code}/raw/`，不得写入仓库目录。**

```
CODE=<基金代码>
TMP=/tmp/fund_research_${CODE}/raw

# ✅ 仅用于 NEXT_ACTION=FULL_FETCH
python skills/fund-deep-research/scripts/parallel_data_collection_v2.py ${CODE}
```

### 全局原则：证据留痕与读取纪律（Step 2/3/5/5.5/6 均适用）

- **证据先于结论**：所有分析、判断、章节写作都必须基于实际文件读取，不得依赖对话记忆或上文印象。
- **`search_log.md` 是唯一联网证据账本**：新闻、政策、季报原文、市场对比、失败留痕、阶段 summary 一律写入 `/tmp/fund_research_{code}/analysis/search_log.md`。
- **联网证据每次研究都重查**：即使缓存命中，新闻与搜索数据也必须重新搜索、去重后追加写入。
- **原文完整留痕**：搜索结果必须保存完整原文，禁止只存摘要。格式统一为“带步骤标签的标题 + 原文内容”；各步骤只定义自己的标签规则，不重复定义通用写法。
- **统一去重规则**：以“标题 + 发布日期”为唯一键；已存在条目跳过，新条目追加到文件末尾。
- **对话只报结论，不贴原文**：对话中只写“结论：XXX，已写入 `search_log.md`”，不在对话窗口重复铺开原文。
- **大文件按段读取**：`search_log.md` 可能很大，先用 `grep_search` 定位目标标题或标签，再用 `read_file` 精确读取对应行范围；禁止全量 `read_file`。

### 全局原则：报告生成与文件落地（Step 6 及最终输出适用）

- **报告必须由 AI 直接生成**：严禁使用 `generate_report.py` 等脚本自动生成正文。
- **最终只保留一个报告文件**：全文直接写入 `基金研究报告/{code}_{基金简称}_{日期}.md`，不创建独立章节草稿文件。
- **第二章必须最后编撰**：第二章是对全文的高度提炼，必须在第三章至第十章全部完成后再写，并放回第一章之后。

### 全局原则：模板锁定、数据真实性与考据锚点（Step 6 及模板写作适用）

- **模板锁定**：读取 `reference/report-template.md` 后，必须按模板骨架逐章逐节填写；不得擅自改标题、并章、增章、删章，或跳出模板另起结构。
- **先搭骨架，再填内容**：开始正文前，先确认章节与小节顺序与模板一致；若模板有占位段落，替换后再交付，禁止保留占位语或改写成自由发挥版报告。
- **数据真实性优先于表达流畅**：所有数字、日期、排名、文号、监管结论必须来自已读取文件或 `search_log.md` 原文；找不到依据就回到前序步骤补证，不得凭印象补数。
- **除评分矩阵外禁止自行乱算**：除第二章按 `reference/scoring-matrix.md` 进行规则化加减分外，禁止临时心算或臆造新的收益率、比例、分位、排名、回撤、估值等数值。
- **无法核验就显式说明**：若某个数值或事件经现有文件与外部证据仍无法确认，明确写“数据缺失 / 待补证 / 无法核验”，不得猜测性填空。
- **可考据内容必须带锚点**：政策、季报原话、合规事件、经理变更、里程碑事件等可供考据的内容，必须写出读者可回查的锚点，例如文号+日期、季报季度、监管文书标题+日期、事件标题+日期。

并行脚本包含（共11个，分三层执行）：

**Layer 1: AKShare获取层（4个，并发执行）**
- `ak_fund_basic.py` - 基金基础信息+阶段收益（增强版：含风险等级、赎回费规则）
- `ak_nav_history.py` - 日度净值历史
- `ak_holdings.py` - 持仓结构+行业配置
- `ak_quarterly_calc.py` - 季度业绩计算

**Layer 2: 本地计算层（4个，并发执行）**
- `calc_risk_metrics.py` - 风险指标计算（13项）
- `calc_relative_metrics.py` - 相对基准指标（新增：Beta/Alpha/信息比率/跟踪误差）
- `calc_inflection_points.py` - 拐点识别
- `calc_annual_returns.py` - 年度收益率计算

**Layer 3: 旧版爬虫+搜索层（3个，串行执行）**
- `fetch_manager_info.py` - 基金经理信息（增强版：AKShare+网页混合架构）
- `scan_institutional_risk.py` - 机构风险扫描
- `check_blacklist.py` - 黑名单检查

输出文件（11个）：
- `fund_enhanced.json` - 基础信息（含风险等级、赎回费规则）
- `risk_metrics.json` - 风险指标（13项）
- `relative_metrics.json` - 相对基准指标（Beta/Alpha等，新增）
- `holdings.json` - 持仓结构
- `quarterly.json` - 季度业绩
- `nav_daily.json` - 净值历史
- `manager_info.json` - 经理信息（含在管基金统计、疲劳预警）
- `inflection_points.json` - 拐点识别
- `annual_returns.json` - 年度收益
- `institutional_risk.json` - 机构风险
- `blacklist.json` - 黑名单检查

> ⚠️ **政策匹配无法脚本化**，必须在 Step 3/5 联网搜索补充，不存在 `policy_match.py`。

---

### Step 2：🔍 数据完整性与时效性检查（强制执行）

> **先读文件，再检查**。从 `/tmp/fund_research_{code}/raw/` 读取所有 JSON 后再判断。

```
python skills/fund-deep-research/scripts/check_data_integrity.py <基金代码>
```

**检查结果处理**：
- ✅ **全部有数据且时效正常** → 跳到 Step 4
- ⚠️ **字段 N/A** → 进入 Step 3 联网搜索补充
- ⚠️ **净值过期** → 重拉 `nav_daily.json`，重跑 Step 1 第三步
- ⚠️ **相对指标过期/估算值** → 重算 `relative_metrics.json`，禁止带着旧 Beta/Alpha 继续写报告
- ⚠️ **持仓过期** → 重拉 `holdings.json`，重跑 `parallel_data_collection`
- ❌ **文件缺失** → 重跑对应 Step 1 脚本

**Step 2 新增强制判定**：
- `relative_metrics.json.end_date` 若较 `nav_daily.json` 最新日期落后超过 10 个自然日，视为**过期**，必须重算。
- `relative_metrics.json.data_sources` 若包含 `industry_estimate`，视为**降级结果**，不得直接写入第七章和第二章。
- `manager_info.json.manager_identity_conflict == true` 时，第四章和第二章**必须**以 `authoritative_current_manager_names` / `authoritative_current_manager_ids` / `tenure_history` 为准，不得直接引用顶层 `manager_name` / `manager_id` 做结论。
- 若 `calc_relative_metrics.py` 这类脚本将 JSON 输出到 stdout 而不是自动落盘，允许通过终端重定向写回 `/tmp/fund_research_{code}/raw/relative_metrics.json`，然后立刻重跑完整性检查确认修复生效。

---

### Step 3：🌐 联网搜索补充基础数据（强制要求）

**如果Step 2检测到任何N/A，必须执行此步骤！**

> 标题标签：`## [Step3-轮次N] YYYY-MM-DD 搜索关键词\n原文内容`

#### 搜索策略

**第1轮：基础信息补充**（优先级最高）
```
搜索关键词：
- "{基金名称} {基金代码} 基金详情"
- "{基金名称} {基金代码} 成立时间 基金经理"
- "{基金名称} {基金代码} 基金类型 规模"
```

**第2轮：业绩数据补充**
```
搜索关键词：
- "{基金名称} {基金代码} 净值 收益率"
- "{基金名称} {基金代码} 夏普比率 最大回撤"
- "{基金名称} {基金代码} 业绩排名"
```

**第3轮：持仓结构补充**
```
搜索关键词：
- "{基金名称} {基金代码} 持仓 重仓股"
- "{基金名称} {基金代码} 资产配置"
- "{基金名称} {基金代码} 季报"
```

**第4轮：基金经理和公司**
```
搜索关键词：
- "{基金经理姓名} 投资风格 从业经历"
- "{基金公司} 实力 排名"
```

#### 搜索工具使用规范

**必须使用联网搜索工具**，每次搜索后：
1. 读取搜索结果（如需深入阅读某页，使用网页抓取工具获取全文）
2. 提取关键信息
3. 记录数据来源和日期
4. 验证信息的时效性（优先选择最近3个月的信息）

**工具降级规则（强制）**：
- 首选当前会话可用的联网搜索和网页抓取工具。
- 若搜索代理、网页抓取工具或浏览器型工具因网络切换、解析失败、站点限制而不可用，可退回终端直连/API/`requests`/`curl` 获取原文。
- 降级后仍失败时，必须记录：失败来源、失败原因、已尝试的替代源，并据此决定是继续补搜还是在报告中显式标注“数据源缺失/接口失败”。

**新鲜度判定与加搜规则（强制）**：
- 搜到结果不等于搜索完成，必须先判断内容是否足够新。
- 若结果发布时间早于研究日期 90 天，且主题属于政策/监管/行业景气/市场环境，必须至少追加 1 轮“当年/近6个月/最新进展”搜索。
- 若结果只覆盖历史政策、没有研究年份或近6个月的新文件/新部署/新进展，禁止直接收工，必须继续搜索。
- 只有满足以下二选一，才可停止该主题搜索：
   1. 已找到研究年份或近6个月内的高相关新结果；
   2. 已明确验证“近6个月无更高优先级更新”，并把该结论写入 `search_log.md`。

#### 信息整合规则

- ✅ 多个来源一致 → 采用该数据
- ⚠️ 来源冲突 → 采用权威来源（天天基金、晨星、基金公司官网）
- ❌ 无法验证 → 标注"待确认"，不要编造

---

### Step 4：📊 数据验证与交叉核对

> **执行时机**：无论 Step 3 是否执行，Step 4 均必须运行，统一对 Step 1 脚本数据与 Step 3 补充数据进行验证，验证通过后才能进入 Step 5。

**必须验证以下内容**：

1. **数据一致性检查**
   - 基金名称在各处是否一致
   - 净值数据是否合理（不会突然暴涨暴跌）
   - 规模数据是否在合理范围

2. **时效性检查**
   - 净值日期是否是最近的（T-1或当日）
   - 相对基准指标截止日是否与净值窗口对齐（允许滞后最多 10 天）
   - 季报数据是否是最新的
   - 基金经理是否现任

3. **合理性检查**
   - 收益率是否合理（债券基金年化一般3%-8%，股票基金-30%到+50%）
   - 夏普比率是否合理（一般0-3之间）
   - 最大回撤是否符合基金类型

**发现问题时**：
- 重新搜索验证
- 标注数据疑点
- 在报告中说明

**经理口径冲突处理（强制）**：
- 若 `manager_info.json.manager_identity_conflict == true`，先在 Step 4 明确记录冲突原因。
- 章节写作时按以下优先级取值：`authoritative_current_manager_names / ids` > `tenure_history` 当前任职行 > 顶层 `manager_name / manager_id`。
- 顶层字段仅可用于辅助说明 AKShare 侧画像或在管产品画像，不得直接当作“当前经理铁证”。

---

### Step 4.5：📥 研究输入装载（读取已有结构化数据，不属于联网搜索）

> 这一步只负责把 Step 1 已经产出的结构化输入读全、读对，为后续深度搜索提供骨架。**不要把它和联网搜索混在一起。**

#### 4.5A. 读取净值拐点骨架

> `calc_inflection_points.py` 已在 Step 1 并行执行完毕，结果已保存到 `/tmp/fund_research_{code}/raw/inflection_points.json`，**无需重跑脚本**。

直接执行：
```
read_file /tmp/fund_research_{code}/raw/inflection_points.json
```

字段说明：
1. **拐点定义**：从局部极大值到极小值（或反向）净值变动幅度 ≥ 5%，即为一个拐点。
2. **识别算法**：滚动 20 日高低点 → 过滤交替极值 → 按幅度排序保留前 30。
3. **每个拐点格式**：
   ```
   拐点 N：起始日期 → 结束日期，起始净值 → 结束净值，变动幅度 ±X.X%
   ```
4. **阶段划分**：将成立至今的净值历史划分为若干“发展阶段”（通常 3-6 个阶段），每阶段包含若干拐点。

#### 4.5B. 读取季度与年度业绩骨架

> `ak_quarterly_calc.py` 和 `calc_annual_returns.py` 已在 Step 1 运行完毕，**无需重跑**。

- 通过 `read_file` 读取 `/tmp/fund_research_{code}/raw/quarterly.json` 作为逆季复盘骨架（含每季末净值和季度收益率；**注意**：该文件不含持仓数据，逐季持仓对比请读取 `holdings.json` 中的 `holdings_by_period`）。
- 通过 `read_file` 读取 `/tmp/fund_research_{code}/raw/annual_returns.json` 获取完整年度收益数据。

#### 4.5C. 读取相对基准指标骨架

> `calc_relative_metrics.py` 已在 Step 1 运行完毕，输出文件为 `/tmp/fund_research_{code}/raw/relative_metrics.json`。

包含指标：
- Beta值：相对沪深300的系统性风险
- Alpha（年化）：超额收益能力
- 信息比率：单位跟踪误差的超额收益
- 跟踪误差（年化）：与基准的偏离程度
- R²：与基准的相关性

> ✅ 直接读取 JSON 文件即可，无需重新计算。

---

### Step 5：🔍 外部证据采集与验证（只做联网搜索与原文留痕）

> 这一阶段只做一件事：围绕章节需要的外部证据进行**搜索、抓取、验证、留痕**。不要在这里直接写章节结论。

#### 5A. 季报原文与季度动作证据

优先对以下季度执行深度对账：**最新3-5季 + 所有关键拐点对应季度 + 牛熊切换或极端回撤季度**。当历史季度很多、公告页抓取不稳定或站点明显限流时，其余季度允许退回使用 `quarterly.json` + `holdings.json` 做结构化复盘，不强制逐季抓取季报原文。

对选中的重点季度，执行以下流程：
1. 获取官方通告原文：优先使用东财基金公告 API `/f10/JJGG?fundcode={基金代码}&type=3` 拉定期报告列表，再拼详情页抓正文。
2. 绑定持仓变化：对比本季度与上一季度前十大重仓股，识别加仓、减仓、新进、退出。
3. 关联季度盈亏与市场背景：核对季度净值增长率、宏观大事、行业政策和市场风格。
4. 原文留痕要求：每条季报摘录单独写入 `search_log.md`，标签使用 `[Step5-QuarterlyQuote][基金代码][YYYYQX]`。

#### 5B. 市场对比证据

```bash
搜索关键词：
- "{基金名称} vs 沪深300 对比"（股票型）
- "{基金名称} vs 中债指数 对比"（债券型）
- "10年期国债收益率 2026 最新"（债券型必查）
- "信用债 利差 2026"（债券型必查）
- "{基金名称} 股票仓位 可转债仓位 最新"（二级债/固收+必查）
- "{基金名称} Alpha Beta 信息比率"
```

> 债券型在进入第二章前，必须先判断是**纯债 / 一级债 / 二级债 / 固收+**，不得仅用“债券型”一个标签直接套模板。

原文留痕标签：`[Step5-MarketCompare]`

#### 5C. 政策原文与量化目标证据

**第1轮：历史政策文件精确搜索**
```
搜索关键词：
- "{持仓行业} 政策文件 文号 历年"
- "{持仓行业} 指导意见 补贴 退坡 通知 历年"
- "国家发改委 能源局 {持仓行业} 规划 指导意见"
- "发改能源 工信部 {持仓行业} {年份} 文件"
```

**第2轮：政策传导量化搜索**
```
搜索关键词：
- "{基金名称} 政策发布后 净值 涨跌"
- "{持仓行业} 政策红利 股价 反应"
- "{基金代码} 政策敏感度 Beta"
```

**第3轮：最近6个月新政搜索（必须执行）**
```
搜索关键词：
- "{持仓行业} 2026年 最新政策 利好 补贴"
- "工信部 发改委 {持仓行业} 2026 通知 意见"
- "{持仓行业} 省级 地方 补贴 规划 2026"
- "{持仓行业} 供给侧 反内卷 竞争规范 2026"
```

搜索后必须整理：
- 每条政策记录：**文号 / 发布部门 / 发布日期 / 量化目标 / 补贴金额或装机目标**
- 按政策周期分类：**红利期 / 调整期 / 修复期**，标注每段区间的净值涨跌幅
- 若研究日期已进入新年份，政策表不能全部停留在更早年份；必须额外判断研究年份或近6个月内是否存在新政策/续作/实施细则/会议部署。若存在必须纳入；若不存在，必须在 `search_log.md` 明确写出“近6个月未检出更高优先级新政”

原文留痕标签：`[Step5-PolicyRaw]`

#### 5D. 市场周期与环境证据

```bash
搜索关键词：
- "{基金名称} 牛市 熊市 表现"
- "{基金名称} 不同市场环境 适应性"
- "{基金经理姓名} 投资风格 择时能力"
```

原文留痕标签：`[Step5-MarketCycle]`

#### 5E. 合规与机构风险证据

运行 `scan_institutional_risk.py` 获取关键词，再用联网搜索逐一排查：
- **合规红线**：近 3 年是否有证监会处罚或监管函？
- **舆情监控**：是否有内幕交易传闻、维权事件或负面热搜？
- **管理疲劳**：经理在管产品是否超过 10 只或规模超 500 亿？

原文留痕标签：`[Step5-Compliance]`

#### Step 5 统一留痕要求

- 搜索轮次以**证据覆盖**为目标，不以堆轮次为目标：
  - 固定主题至少覆盖 4 类：市场对比 / 政策 / 市场周期 / 合规舆情
  - 季报优先覆盖：最新3-5季、幅度前8-12个主要拐点，以及至少一轮牛熊切换样本
  - 常规总轮次通常为 15-40 轮；只有在关键证据仍不足时才继续扩展
- 若基准数据、季报正文或政策原文经多个来源验证后仍无法稳定获取，允许停止继续横向扩源，但必须把失败原因、已验证来源和留存缺口写入 `search_log.md`，后续章节按“可验证数据 + 显式缺口说明”完成，禁止编造。
- 每轮搜索后如需读取完整页面，使用网页抓取工具获取详细内容。
- 本步骤只额外定义标题格式：`## [Step5-主题标签-轮次N] {日期} {搜索关键词}\n{原文内容}\n`

---

### Step 5.5：🧠 章节素材沉淀（只做分析归档，不重新搜索）

> 这一阶段把 Step 4.5 的结构化骨架和 Step 5 的外部证据合并，沉淀为**章节可直接消费**的 summary 标签。Step 6 只应读取这些 summary 或明确指定的原始证据，不再反向猜测 Step 5 的段落含义。

#### 5.5A. 发展历史与阶段复盘素材

使用 `inflection_points.json`、`quarterly.json`、`annual_returns.json` 以及 `[Step5-QuarterlyQuote]`、`[Step5-MarketCycle]` 原文证据，生成：
- 发展阶段总览
- 关键拐点归因
- 波段层面的外部环境与经理动作映射

写入 `search_log.md` 标签：`[Step5-HistorySummary]`

#### 5.5B. 经理言行一致性与能力画像素材

使用 `manager_info.json`、`[Step5-QuarterlyQuote]` 原文证据以及需要时的历任经理补充搜索，生成：
- 至少 2 个季度的言行一致性审计素材
- 仓位管理风格判断
- 历任经理风格演变与能力画像要点

写入 `search_log.md` 标签：`[Step5-ManagerAudit]`

#### 5.5C. 政策背景与匹配度素材

使用 `[Step5-PolicyRaw]` 原文证据，生成：
- 政策时间轴
- 政策周期判断
- 与基金持仓主线的匹配度结论

写入 `search_log.md` 标签：`[Step5-PolicySummary]`

#### 5.5D. 历史业绩与市场对比素材

使用 `quarterly.json`、`annual_returns.json`、`[Step5-MarketCompare]`、`[Step5-MarketCycle]` 原文证据，生成：
- 历史业绩的环境解释
- 可验证季度的基准对比结论
- 缺失季度的年度替代说明

写入 `search_log.md` 标签：`[Step5-PerformanceSummary]`

#### 5.5E. 合规结论素材

使用 `institutional_risk.json`、`blacklist.json`、`[Step5-Compliance]` 原文证据，生成：
- 公司与经理的合规结论
- 一票否决项结论
- 已知但未触发一票否决的风险提示

写入 `search_log.md` 标签：`[Step5-ComplianceSummary]`

---

### Step 6：📝 AI逐章生成研究报告

#### 逐章生成协议（严格按此顺序）

> ❌ **禁止**：跳过下方协议直接写整篇报告。
> 每章生成后，首次写入使用 `create_file`，后续追加或修订使用当前会话可用的文件编辑工具（如 `apply_patch`）。

**⚠️ 每章开始前必须执行「预声明-批量读取」协议（防止读取中途发生上下文压缩）：**

> 1. **预声明**：在开始读文件前，先在对话中列出本章需要读取的所有文件路径（完整列表）
> 2. **批量读取**：按列表顺序逐一 `read_file`，**全部读完后确认**："已读取全部 N 个文件，数据加载完毕"
> 3. **确认完整性**：若任何一个文件读取失败或内容为空，立即停止，重新读取该文件，不得跳过继续分析
> 4. **开始写章节**：仅在步骤2确认完成后，才开始生成章节内容
>
> ❌ **禁止**：边读文件边写分析内容（会导致读到一半发生压缩，后半段数据被截断）  
> ❌ **禁止**：读了部分文件就开始写，剩余文件"待会再读"  
> ✅ **正确顺序**：声明 → 全部读完 → 确认 → 写章节

| 生成顺序 | 章节 | 预声明并批量读取的文件（全部读完后再开始写） |
|---------|------|----------------------------------------|
| 1 | **第一章** 基金基本信息 | `raw/fund_enhanced.json` (含风险等级、赎回费规则) · `raw/manager_info.json` (含在管基金统计) |
| 2 | **第三章** 基金发展历史 | `raw/inflection_points.json` · `search_log.md`（grep `[Step5-HistorySummary]` 段） |
| 3 | **第四章** 基金经理深度分析 | `raw/manager_info.json` (含AKShare获取的在管数据) · `search_log.md`（grep `[Step5-QuarterlyQuote]` `[Step5-ManagerAudit]` 段） |

> **第四章强制写作要求**（未满足则章节不合格）：
> 1. **4.2 节**：必须逐行列出经理名下**所有**在管基金（来自 `manager_info.json`），包含代码、任期、总回报、同类排名
> 2. **4.4 节**：必须引用**至少2个季度的季报原始文字**（来自 `search_log.md` 中 `[Step5-QuarterlyQuote]` 段），每条对照实际持仓，给出 ✅⚠️❌ 判断
> 3. **4.3 节**：必须明确写出仓位管理风格（如"全程高仓位约90%+"或"主动择时"），并说明对回撤的影响
> 4. **4.6 节**：必须输出4维能力画像：最强能力、明显短板、适合配置的市场环境、应规避的市场环境
> 5. 若 `manager_identity_conflict == true`，必须在 4.1 或 4.5 节显式说明：当前经理认定以 `tenure_history` 为准，并解释顶层字段为何只作辅助参考
| 4 | **第五章** 基金公司合规评估 | `raw/institutional_risk.json` · `raw/blacklist.json` · `search_log.md`（grep `[Step5-Compliance]` `[Step5-ComplianceSummary]` 段） |
| 5 | **第六章** 持仓分析 | `raw/holdings.json` |
| 6 | **第七章** 风险指标 | `raw/risk_metrics.json` · `raw/relative_metrics.json` (新增: Beta/Alpha等) |
| 7 | **第八章** 行业与政策背景 | `search_log.md`（grep `[Step5-PolicyRaw]` `[Step5-PolicySummary]` 段） |
| 8 | **第九章** 历史业绩分析 | `raw/quarterly.json` · `raw/annual_returns.json` · `search_log.md`（grep `[Step5-MarketCompare]` `[Step5-PerformanceSummary]` 段） |
| 9 | **第十章** 后续跟踪计划 | 已写入的报告文件 |
| **10** | **第二章** 综合评价与配置建议 | 已写入的报告文件 · `reference/scoring-matrix.md` |

> **各章强制写作规则（未满足则章节不合格）：**
>
> **第五章（5.3 一票否决项）**：
> - 若所有否决项全部通过（✅），**不得输出表格**，改用一行引用块：`> 合规检查通过，无一票否决项触发。`
> - 只有存在 ❌ 项时才展示完整否决项表格
>
> **第六章（6.3 持仓演变）**：
> - **输出必须分两层：先给“全量逐季表”，再给“关键调仓解读”**
> - **全量逐季表的覆盖范围：`holdings.json` 中 `holdings_by_period` 的所有季度，从成立首季到最新季报，逐季全部列出，不得截断为"近六期"**
> - 禁止列出当期重仓股名称，仅记录调整本身（新进↑ / 退出↓ / 加仓⬆ / 减仓⬇）
> - 若历史季度可可靠识别行业/产业链，则新增「行业调整（产业链位置移动）」列；若 `holdings.json` 不提供历史行业字段，允许基于标的主营业务人工归类，并注明“基于标的主营业务归类”；若仍无法可靠归类，明确写“历史行业穿透数据缺失”，不得编造
> - 必须新增「前十集中度」列和「当季净值涨跌」列
> - 全量逐季表中的备注/评价列遵循“**有则写、无则 `—`**”原则：只记录真正值得保留的变化或事件，语言必须简明，不得对每个季度机械输出评价
> - 「关键调仓解读」只覆盖重大转型节点（不少于3条），每条说明判断逻辑+事后净值验证，用于突出重点而不是重复季度流水账
>
> **第七章（7.1 绝对风险指标）**：
> - 全期指标与近期夏普指标**必须分两个子表**，不得混排
>
> **第九章（9.2 季度收益）**：
> - 对**已有可靠基准数据**的季度，必须包含**沪深300同期季度收益对比行**（斜体）和**超额行**（加粗）
> - 若早期季度的沪深300数据经缓存重算、API补抓和备用来源验证后仍不可得，可保留可验证区间；缺失季度必须显式标注“数据源缺失/外部基准接口失败”，并用 `annual_returns.json` 补足年度维度比较，不得伪造季度基准
> - 正超额季度标注 ✅，负超额季度标注 ⚠️
>
> **第十章（10.1 跟踪指标）**：
> - 「当前值」列**必须为量化数字或具体日期格式**（如"X.X万元/吨（YYYY-MM-DD）"）
> - 禁止填写"底部修复中"、"N/A"、"待确认"等文字描述；若数据暂缺，填写最近可得值并注明日期

---

#### 📐 报告模板（外部文件）

> **Step 6 开始写报告前**，必须先执行：
> ```
> read_file skills/fund-deep-research/reference/report-template.md
> ```
> 全部加载完毕后，先核对章节标题与小节顺序完全一致，再按模板骨架逐章填写。

---

#### 📊 评分矩阵（外部文件）

> **写第二章前**，必须先执行：
> ```
> read_file skills/fund-deep-research/reference/scoring-matrix.md
> ```
> 按基金类型选择对应矩阵，三轴交叉得出五档建议。

**第二章落笔前的强制判断（尤其是债券型）**：
- 先明确基金子类型：**纯债 / 一级债 / 二级债 / 固收+**。
- 先回答市场轴主驱动：是**利率/信用环境**，还是**权益/转债增强仓位**，或两者共同作用。
- 若出现“净值历史分位较高”，必须先解释它是**真正高估**，还是**票息积累 / 短样本修复 / 新份额扰动导致的赔率收敛**。
- 若 `manager_info.json` 存在经理身份冲突，第二章风险信号或结论中必须点明“当前经理识别需以 tenure_history 为准”，避免把错误经理画像写进配置建议。
- 若这 3 个问题没有回答清楚，不得直接写出“高位谨慎 / 观望 / 谨慎”之类的结论。

---

#### ✅ 质量校验（外部文件）

> **报告完成提交前**，必须先执行：
> ```
> read_file skills/fund-deep-research/reference/checklist-and-faq.md
> ```
> 逐项对照 Checklist 自检，全部打勾后才能提交。

---

## 🗂️ 结构化数据转换（Web 平台 JSON）

> 字段 Schema、B 类字段提取规范、Prompt 模板见：
> **[reference/report_to_json_spec.md](reference/report_to_json_spec.md)**

完成报告后如需转换为 Web 平台 JSON，按下方自动化流水线执行；其中 `index.json` 不由现有脚本自动维护，需人工同步更新后再校验和构建。

---

### 🤖 自动化流水线（报告生成后）

报告写完后，使用以下两步脚本将缓存数据和报告内容自动同步到 Web 平台 JSON，无需手动复制字段。

**字段分类原则**：
- **A 类（确定性字段）**：来自 AKShare 缓存，由脚本直接提取，无歧义
- **B 类（叙述性字段）**：来自研究报告正文，需由 AI 解析后填入

#### Step A：从缓存写入 A 类字段

```bash
python3 skills/fund-deep-research/scripts/build_json_from_cache.py <基金代码>
```

自动提取并写入以下字段（不覆盖 B 类字段）：

| 缓存文件 | → JSON 字段 |
|---|---|
| `fund_enhanced.json` | `basic.*` / `fees.*` / `scale.nav` |
| `nav_daily.json` | `navHistory[]`（仅最近90个交易日，作为前端净值走势图 fallback） |
| `holdings.json` | `holdings.top10[]` / `holdings.sectors[]` / `holdings.date` |
| `annual_returns.json` | `performance.annual[]` |
| `quarterly.json` | `performance.quarterly[]` |
| `risk_metrics.json` | `risk.volatility` / `sharpe` / `calmar` / `maxDrawdown` |
| `relative_metrics.json` | `risk.relativeMetrics.*`（beta/alpha/IR/跟踪误差） |
| `inflection_points.json` | `stageAnalysis.inflectionPoints[]` |
| `manager_info.json` | `managers.current.managerId/name/experience/fundCount/totalScale` |

> 说明：网页概览区只展示“近一段净值走势”，实时优先走 `/api/fund/:code/history`；JSON 中的 `navHistory` 仅保留最近 90 个交易日作为静态 fallback，不再内嵌成立以来全量日度净值。
> 说明：第三章 `stageAnalysis.stages[].period` 必须输出为 `YYYY-MM → YYYY-MM`。现有前端会把它作为拐点走势图背景色阶的 fallback 时间范围，不能再用 `2018Q2 → 2019Q2` 之类季度写法。

脚本运行后会打印 B 类字段的填写状态（✅ 已有 / ❌ 缺失），方便定向补充。

#### Step B：从报告提取 B 类字段（AI 解析）

1. 打开报告 MD 文件
2. 参照 **[reference/report_to_json_spec.md](reference/report_to_json_spec.md)** 中的 Prompt 模板，将规范 + 报告内容一起发给 AI
3. AI 输出一个仅包含 B 类字段的 JSON，保存到 `/tmp/fund_research_{code}/b_fields.json`
4. 运行合并脚本：

**强约束**：
- 以 `web-platform/public/data/003984.json` 作为当前前端渲染的 canonical 样本
- AI 提取时必须遵循 `reference/report_to_json_spec.md` 的最新字段名，禁止沿用旧结构（如 `tracking.alerts.signal/action`、`exclusionCheck.items[]`、`scoring.risks.label/text`）
- `merge_b_fields.py` 现在会对少量旧结构做兼容归一，但这只是兜底，不应再作为默认输出格式

```bash
# 仅填充缺失字段（默认）
python3 skills/fund-deep-research/scripts/merge_b_fields.py <基金代码> /tmp/fund_research_<代码>/b_fields.json

# 强制更新已有字段
python3 skills/fund-deep-research/scripts/merge_b_fields.py <基金代码> /tmp/fund_research_<代码>/b_fields.json --overwrite
```

#### Step C：同步更新 `web-platform/public/data/index.json`

现有脚本只维护 `web-platform/public/data/{code}.json`，**不会自动更新** `web-platform/public/data/index.json`。完成 Step A 与 Step B 后，必须人工检查并同步索引。

`index.json` 最小必备字段如下；若已有该基金条目则更新这些字段，若没有则新增一条：

```json
{
   "id": "基金代码",
   "shortName": "基金简称",
   "type": "基金类型",
   "subType": "基金子类型",
   "riskLevel": "风险等级文本",
   "riskCode": 4,
   "return1Y": 12.34,
   "return3Y": 56.78,
   "score": 77,
   "recommendation": "综合建议",
   "recommendationType": "buy|cautious|sell|strong_buy",
   "navFallback": 1.2345,
   "reportDate": "YYYY-MM-DD",
   "manager": "当前经理"
}
```

字段来源建议：
- `id` / `shortName` / `type` / `subType` / `riskLevel` / `riskCode` / `return1Y` / `return3Y` / `navFallback` / `manager`：以 `web-platform/public/data/{code}.json` 中已落库字段为准。
- `score` / `recommendation` / `recommendationType`：以第二章提取并合并后的 `scoring.*` 为准。
- `reportDate`：以本次报告文件日期为准。

#### Step D：校验与按需构建

```bash
# 校验单基金 JSON 结构
python3 skills/fund-deep-research/scripts/validate_json_schema.py <基金代码>

# 如需更新前端发布产物，再构建
cd web-platform && npm run build
```

B 类字段对应报告章节：

| 报告章节 | → JSON 字段 |
|---|---|
| 第二章 2.1 综合评级 | `scoring.total/grade/recommendation/rating/logic` |
| 第二章 2.2 风险信号 | `scoring.risks[]` |
| 第二章 2.3 操作建议 | `scoring.termAdvice[]` |
| 第三章 3.1 阶段总览 | `stageAnalysis.stages[].description/env/managerAction` |
| 第四章 4.3 投资理念 | `managers.current.philosophy[]` |
| 第四章 4.4 言行审计 | `managers.current.consistencyAudit[]` |
| 第四章 4.6 能力画像 | `managers.current.abilityProfile{}` |
| 第五章 排除法检查 | `exclusionCheck[]`（⚠️ 必须是数组，每个元素包含 item/pass/note） |
| 第六章 持仓主题 | `holdings.themeGroups[]` / `evolutionHighlights[]` |
| 第八章 政策匹配 | `policy.tags` / `policyBreakdown[]` / `scenarios[]` |
| 第九章 9.3 里程碑 | `performance.milestones[]` |
| 第十章 跟踪计划 | `tracking.weekly[]` / `quarterly[]` / `alerts[]` |

#### 完整流水线命令序列

```bash
CODE=003984

# Step 1：数据采集（已有）
python3 skills/fund-deep-research/scripts/parallel_data_collection_v2.py ${CODE}

# Step 2：生成研究报告（AI 写作，参照 SKILL.md Step 6）

# Step 3：A 类字段自动写入
python3 skills/fund-deep-research/scripts/build_json_from_cache.py ${CODE}

# Step 4：AI 解析报告 → 保存 B 类字段 JSON
# ⚠️ 重要：必须参照 reference/report_to_json_spec.md 的规范，确保 exclusionCheck 是数组格式
# 将输出保存到 /tmp/fund_research_${CODE}/b_fields.json

# Step 5：B 类字段合并
python3 skills/fund-deep-research/scripts/merge_b_fields.py ${CODE} /tmp/fund_research_${CODE}/b_fields.json

# Step 6：【新增】验证 JSON 格式是否符合前端期望
python3 skills/fund-deep-research/scripts/validate_json_schema.py ${CODE}

# Step 7：重新构建 Web 平台（可选，仅在需要更新前端时执行）
# cd web-platform && npm run build
```

**⚠️ 重要说明**：
- Step 6 的验证脚本会检查所有数组字段的类型和结构
- 如果验证失败，必须先修复 B 类字段 JSON 后重新合并，不要直接构建
- 构建步骤已改为可选，避免每次研究都强制重新构建前端
