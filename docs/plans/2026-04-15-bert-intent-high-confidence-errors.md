# BERT Intent 高置信误判清单

Date: 2026-04-15

## 背景

当前 bootstrap BERT intent 模型路径：

`D:\AI\Models\fine-tuned-bert-intent-vitalai-trained`

本轮将 holdout 扩展到 90 条，其中 33 条为 `needs_decomposition` 复合/多任务/歧义表达。困难 holdout 评估结果：

- 总计：`86/90`
- 第二层占位检测：33 条，全部成功进入 `needs_decomposition_detector`
- BERT 直接识别：41 条，其中 37 条正确、4 条错误
- 低置信 fallback：16 条，全部成功路由
- clarification：10 条，全部为预期 unknown 澄清

这说明 fallback 策略有效，复合输入也已经有了第二层边界；但 bootstrap BERT 仍然出现高置信误判，不能把当前模型视为生产泛化模型。

## 误判清单

| 输入 | 期望 intent | BERT 预测 | 置信度 | 初步判断 |
| --- | --- | --- | --- | --- |
| 刚吃完药以后恶心，晚饭先不安排了 | `health_alert` | `daily_life_checkin` | 0.8904 | 句子同时包含“药/恶心/晚饭”，模型被晚饭语义吸到日常类，但健康风险应优先 |
| 以后提醒我出门前带钥匙 | `profile_memory_update` | `daily_life_checkin` | 0.7927 | “出门”触发日常类，但“以后提醒我”应进入记忆/长期偏好更新 |
| I usually call my daughter after dinner | `profile_memory_update` | `daily_life_checkin` | 0.7125 | `dinner` 干扰，模型未学到 `usually` 代表长期习惯 |
| What did I say about calling my daughter | `profile_memory_query` | `mental_care_checkin` | 0.8004 | `daughter`/家庭关系语义被吸到心理陪护，但 `what did I say` 是记忆查询 |

上一轮清单中的 `I need my medicine later, but right now I feel lonely` 已被重新归类为 `needs_decomposition`，因为它同时包含用药和当前心理主诉，不应强行压成单一主 intent。

## 需要避免的错误处理

- 不删除这些 holdout 样本。
- 不为了短期分数直接调低阈值。
- 不把低置信 fallback 的成功误认为 BERT 本体能力已经足够。
- 不直接把 LLM 输出或模型预测当训练真值。

## 推荐处理方向

1. 增加训练候选样本，覆盖“健康风险 + 日常任务”“长期习惯 + 日常词”“记忆查询 + 家庭关系词”。
2. 保留当前 holdout 作为回归集，不参与 bootstrap 训练。
3. 下一轮训练后同时报告 baseline、holdout、BERT direct、fallback、clarification。
4. 后续设计第二层 `IntentDecompositionResult / sub_intent / slots` 时，为混合表达加入主诉优先级规则，例如健康风险优先、当前情绪主诉优先、记忆动词优先。

## 需要用户协助

后续如果你能提供 20 到 50 条更接近真实老人表达的原始句子，会显著提高 holdout 价值。优先提供这几类：

- 健康不适但同时提到吃饭、出门、买菜。
- 心理孤独但同时提到家人、药、日程。
- 想让系统记住某个习惯，但句子里混有日常任务词。
- 询问系统记不记得某件事，但句子里混有家庭关系或情绪词。
