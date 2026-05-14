# 基金公告 API 速查

## 最小流程

`/f10/JJGG?fundcode={code}&type=3` 拉定期报告列表 -> 取 `ID=AN...` -> 拼详情页 `https://fund.eastmoney.com/gonggao/{code},{AN_ID}.html` -> 必要时回退 PDF。

## 列表 API

- 接口：`https://api.fund.eastmoney.com/f10/JJGG`
- 参数：`fundcode`、`pageIndex`、`pageSize`、`type`、`callback`(可选)
- 分类：`1=发行运作 2=分红公告 3=定期报告 4=人事调整 5=基金销售 6=其他公告`
- 约束：`type` 必填；`type=0` 不能取全部公告；要全量时循环 `type=1..6`
- 常用字段：`TITLE`、`ID`、`PUBLISHDATEDesc`

## 详情页

- 地址：`https://fund.eastmoney.com/gonggao/{code},{AN_ID}.html`
- 用途：抓正文、资产配置、前十重仓、份额变动
- 详情页通常带 PDF 原文链接，HTML 不稳时直接回退 PDF

## 最小示例

```bash
curl -L -s -A 'Mozilla/5.0' -e 'https://fundf10.eastmoney.com/jjgg_024212_3.html' \
    'https://api.fund.eastmoney.com/f10/JJGG?fundcode=024212&pageIndex=1&pageSize=5&type=3'
```
