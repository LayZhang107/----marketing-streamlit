---
name: consumer-insight-skill
version: 0.2
description: 将单条消费者评论编码为可审计的结构化洞察，保留原文证据，无法判断时明确返回 unknown。
---

# Consumer Insight Skill

## 适用范围

输入一条评论或一组评论，输出每条评论一个 JSON 对象。用于蓝牙降噪耳机评论，也可迁移到其他消费品。Skill 只做语义编码，不替代 Python 的计数、排序和百分比计算。

## 输入契约

每条输入至少包含：

- `review_id`：稳定、唯一的评论 ID
- `review_text`：评论原文
- 可选：`brand`、`product`、`review_date`、`rating`

评论为空、只有符号或缺少 `review_id` 时，仍输出记录，但 `confidence=low`，不可推断的字段使用 `unknown`。

## 标签字典

- `sentiment`：`positive`、`neutral`、`negative`、`mixed`、`unknown`
- `need`：主要需求，允许值为 `降噪`、`佩戴舒适`、`续航`、`音质`、`通话`、`连接稳定`、`便携`、`性价比`、`外观`、`unknown`
- `pain_point`：明确的负面问题；没有明确问题时为 `none`，无法判断时为 `unknown`
- `scenario`：使用场景，允许值为 `通勤`、`学习`、`办公`、`运动`、`旅行`、`通话`、`居家`、`unknown`
- `purchase_barrier`：购买阻碍，允许值为 `价格`、`舒适度担忧`、`质量担忧`、`功能不足`、`售后担忧`、`无`、`unknown`
- `evidence`：原评论中的最小充分证据片段，必须逐字摘自原文；没有证据时为 `unknown`
- `confidence`：`high`、`medium`、`low`

## 处理步骤

1. 读取原文，不补写评论没有表达的事实。
2. 先判断情绪，再识别需求、问题、场景和购买阻碍。
3. 每个非 `unknown` 结论都绑定 `evidence`；证据必须能在原文中逐字找到。
4. 同一评论出现正负信息时使用 `mixed`，不得强行压成正面或负面。
5. 只出现“还行”“一般”等弱信息时，相关细分字段使用 `unknown`，情绪可为 `neutral`。
6. 输出严格符合 `schemas/consumer_insight.schema.json`。

## 拒答与边界

- 不从评分单独推断具体痛点。
- 不把“想买”“考虑购买”当作已购买体验。
- 不把品牌、价格、物流等未在原文出现的信息补出来。
- 对讽刺、反话、上下文不足的句子降低置信度并使用 `unknown`。
- 证据无法定位时，结论必须改为 `unknown` 或 `none`。

## 质量检查

- 字段齐全、枚举值合法。
- `evidence` 是 `review_text` 的原文子串（`unknown` 除外）。
- `confidence=high` 需要清楚的直接表达；推断性较强时最多为 `medium`。
- 运行 10 条盲测后，字段格式稳定，误判和缺失均记录在盲测记录中。
