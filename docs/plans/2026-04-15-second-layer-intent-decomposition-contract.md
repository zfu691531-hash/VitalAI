# 第二层意图拆分契约

Date: 2026-04-15

## 背景

用户输入中已经出现大量复合语言场景，例如：

- 健康不适 + 日常任务
- 心理/情绪 + 用药问题
- 记忆退化 + 家庭/日常词
- 老人口语化、啰嗦、模糊、带歧义表达

这些输入不应该被第一层 BERT 或规则模型强行压成单一 intent。当前策略是：

```text
简单单任务输入 -> 第一层 intent recognizer -> 领域 workflow
复合/多任务/歧义输入 -> needs_decomposition_detector -> 第二层意图拆分
```

## 当前交付

本轮新增了第二层意图拆分的 typed contract 与 placeholder use case：

- `IntentDecompositionTask`
- `IntentDecompositionRiskFlag`
- `IntentDecompositionResult`
- `RunIntentDecompositionUseCase`
- `intent_decomposition_payload`
- `IntentDecompositionValidationIssue`
- `IntentDecompositionValidationResult`
- `RunIntentDecompositionValidationUseCase`
- `IntentDecomposer`
- `IntentDecompositionBackend`
- `PlaceholderIntentDecomposer`
- `LLMIntentDecomposer`
- `intent_decomposition_llm_output_schema`
- `validate_intent_decomposition_llm_payload`
- `intent_decomposition_validation_payload`

当前实现不会调用真实 LLM，也不会路由或写库。它只把第一层识别到的候选 intent、风险信号和后续拆分要求结构化返回。

## 当前响应形态

当 `POST /vitalai/interactions` 收到复合输入时，workflow 返回：

- `accepted=false`
- `error=decomposition_needed`
- `intent.requires_decomposition=true`
- `error_details.intent`
- `error_details.decomposition`

`error_details.decomposition` 当前包含：

- `status=pending_second_layer`
- `ready_for_routing=false`
- `routing_decision=hold_for_second_layer_decomposition`
- `candidate_tasks`
- `risk_flags`
- `clarification_question`

## 关键边界

- 第二层输出不能直接调用领域 workflow。
- 第二层输出不能直接写入 profile memory。
- 第二层输出必须先经过 schema 校验、风险规则校验和 workflow 级路由决策。
- 当前 placeholder 的任务只是稳定接口边界，不代表已经具备真实 LLM 拆分能力。

## LLM 输出校验

未来 LLM adapter 的输出必须先通过 `validate_intent_decomposition_llm_payload`。

当前 schema 要求：

- `status`
- `ready_for_routing`
- `routing_decision`
- `primary_task`
- `secondary_tasks`
- `risk_flags`
- `clarification_question`
- `notes`

当前 routing guards：

- `ready_for_routing=true` 时必须有 `primary_task`
- `route_primary` / `route_sequence` 必须有 `primary_task`
- `ask_clarification` 必须有 `clarification_question`
- `ready_for_routing=false` 不允许返回 route 决策

非法输出只返回 validation issues，不生成可路由 result。

## LLM Adapter Shell

当前已新增可替换 adapter shell：

- `IntentDecomposer` 是第二层 decomposer protocol。
- `IntentDecompositionBackend` 是未来真实 LLM backend 的最小接口。
- `PlaceholderIntentDecomposer` 返回当前安全占位结果。
- `LLMIntentDecomposer` 调用 backend 生成 raw payload，然后立即走 schema validator。

当前 fallback 规则：

- backend 缺失：回退到 placeholder。
- backend 抛异常：回退到 placeholder。
- backend 输出不合法：返回 validation issues，不生成可路由 result。
- backend 超过当前同步边界：返回 `timeout` issue，不生成可路由 result。

## Assembly 配置边界

当前已新增环境变量：

`VITALAI_INTENT_DECOMPOSER=placeholder|llm`

默认值为 `placeholder`。

- `placeholder`：继续返回当前非路由占位结果。
- `llm`：启用 `LLMIntentDecomposer` shell，但当前没有真实 backend，因此仍 fallback 到 placeholder。

该配置由 application assembly 读取并注入 workflow。HTTP router 不知道 decomposer 类型。

## 下一步

后续接入真实 LLM 前，必须先完成：

1. 增加第二层输出到 application workflow 的路由守门逻辑。
2. 明确真实 backend 的超时、异常、低置信或输出不完整处理。
3. 继续扩充 `needs_decomposition` holdout 样本，避免用少量样本把第二层调成“看起来能跑”。
