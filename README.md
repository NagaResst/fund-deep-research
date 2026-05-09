# 基金深度研究 Skill

> ⚠️ **免责声明**：本工具仅供个人学习和信息整理使用，所有分析内容均不构成任何投资建议。投资有风险，入市需谨慎，请依据自身判断做出投资决策。

## 📖 简介

这是一个自动化的基金深度研究工具，基于晨星5P框架 + 政策驱动型投资理念 + 排除法初筛，能够自动生成完整的基金研究报告。

## 🎯 功能特点

- ✅ **多数据源抓取**：天天基金API + 新浪财经 + 腾讯财经 + HTML解析，确保数据完整
- ✅ **强制联网搜索**：脚本返回N/A时自动联网搜索补充，绝不输出残缺报告
- ✅ **智能指标计算**：自动计算夏普比率、最大回撤、波动率等风险指标
- ✅ **持仓结构分析**：分析行业分布、重仓股、集中度
- ✅ **黑名单检查**：自动检查基金公司和基金经理是否在黑名单中
- ✅ **政策匹配度与未来预测**：多维度、长周期（1-3-5年）政策趋势预测，情景分析
- ✅ **排除法初筛**：10项一票否决规则，快速剔除不合格基金
- ✅ **AI友好输出**：所有脚本输出JSON格式，便于AI解析和整合
- ✅ **完整报告生成**：自动生成9章节Markdown格式的研究报告

## 📁 目录结构

```
fund-deep-research/
├── SKILL.md                    # Skill定义文件
├── README.md                   # 使用说明
├── scripts/                    # Python脚本目录
│   ├── fetch_fund_basic.py    # 基础信息抓取
│   ├── calculate_metrics.py   # 业绩与风险指标计算
│   ├── analyze_holdings.py    # 持仓结构分析
│   ├── check_blacklist.py     # 黑名单检查
│   ├── policy_match.py        # 政策匹配度评估
│   └── generate_report.py     # 主控脚本（生成完整报告）
└── references/                 # 参考文档目录
    └── report-template.md     # 报告模板（待补充）
```

## 🚀 使用方法

### 方式一：使用Skill（推荐）

在Lingma中触发`fund-deep-research` skill，只需提供基金代码：

```
请深度研究基金 003984
```

AI会自动执行以下步骤：
1. 调用各个Python脚本获取数据
2. 整合所有数据
3. 生成完整的研究报告
4. 保存到`基金研究报告/`目录

### 方式二：直接运行脚本

#### 1. 单独运行某个脚本

```bash
# 获取基础信息
python skills/fund-deep-research/scripts/fetch_fund_basic.py 003984

# 计算业绩指标
python skills/fund-deep-research/scripts/calculate_metrics.py 003984

# 分析持仓
python skills/fund-deep-research/scripts/analyze_holdings.py 003984

# 黑名单检查
python skills/fund-deep-research/scripts/check_blacklist.py "中欧基金" "曲径"

# 政策匹配度评估
python skills/fund-deep-research/scripts/policy_match.py '[{"industry_name": "制造业"}]'
```

#### 2. 运行主控脚本（生成完整报告）

```bash
python skills/fund-deep-research/scripts/generate_report.py 003984
```

这会自动：
- 调用所有子脚本
- 整合数据
- 应用排除法规则
- 生成投资建议
- 保存Markdown报告到`基金研究报告/`目录

## 📊 输出示例

### JSON输出（脚本）

所有脚本输出都是JSON格式，例如：

```json
{
  "fund_code": "003984",
  "fund_name": "嘉实新能源新材料股票A",
  "current_nav": 1.2345,
  "nav_date": "2026-05-03",
  ...
}
```

### Markdown报告（generate_report.py）

生成的报告包含以下章节：
1. 基础信息表格
2. 业绩与风险指标表格
3. 持仓结构分析
4. 基金经理与公司评估
5. 政策匹配度评估
6. 排除法初筛结果
7. 投资建议
8. 后续跟踪计划

## 🔧 依赖要求

### Python版本
- Python 3.7+

### Python库
```bash
pip install requests numpy
```

### API依赖
- 天天基金网API（无需密钥）
- 需要网络连接

## ⚙️ 配置说明

### 黑名单配置

黑名单从以下文件自动读取：
```
投资者画像.md
```

当前黑名单：
- ❌ 景顺长城基金公司
- ❌ 刘彦春（基金经理）

如需修改，编辑上述文件或修改`check_blacklist.py`中的硬编码列表。

### 政策支持行业配置

在`policy_match.py`中配置"十五五"规划重点支持行业：

```python
POLICY_SUPPORTED_INDUSTRIES = {
    "新能源": ["新能源", "光伏", "风电", ...],
    "半导体": ["半导体", "芯片", ...],
    ...
}
```

## 📝 注意事项

1. **网络要求**：需要访问天天基金网API，确保网络畅通
2. **API限制**：频繁请求可能被限流，建议间隔使用
3. **数据准确性**：API返回的数据可能与实际有延迟，仅供参考
4. **新基金处理**：成立不满3年的基金会标记警告，但不直接排除
5. **错误处理**：任一脚本失败时，会标注"数据获取失败"并继续其他步骤

## 🐛 故障排查

### 问题1：脚本运行报错"No module named 'requests'"
**解决**：安装依赖库
```bash
pip install requests numpy
```

### 问题2：无法获取基金数据
**解决**：
- 检查网络连接
- 确认基金代码正确
- 查看错误信息（stderr输出）

### 问题3：报告生成失败
**解决**：
- 检查是否有写入权限
- 确认输出目录存在
- 查看详细错误日志

## 📚 相关文档

- [如何深度研究一个基金.md](./如何深度研究一个基金.md) - 完整的研究方法论

## 💡 未来改进方向

- [ ] 增加更多数据源（晨星、Wind等）
- [ ] 添加可视化图表（净值曲线、行业饼图等）
- [ ] 支持批量研究多个基金
- [ ] 增加基金对比功能
- [ ] 集成到投资新闻归档系统
- [ ] 添加机器学习预测模型

## 📄 许可证

本项目仅供个人学习和研究使用。

---

**作者**：Lingma AI Assistant  
**最后更新**：2026-05-03
