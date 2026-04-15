# Next Task

Date: 2026-04-15

## 当前阶段目标

下一阶段的目标，是继续把 VitalAI 从“能跑的架构样板”推进到“可持续迭代的后端基线”。

## 已完成的最近关键项

### admin 控制面最小权限基线

当前已完成：

- runtime diagnostics 与 health failover drill 继续保持 `POST /admin/...` 控制面路径
- admin 控制面增加 `VITALAI_ADMIN_TOKEN` 配置
- 请求必须携带 `X-VitalAI-Admin-Token`
- 未配置 token、缺失 token、错误 token 都会被拒绝
- 生产环境 runtime control 仍然默认关闭，必须显式打开
- 路由测试已覆盖拒绝与成功路径
- README 已补手动验收命令

### `profile_memory` 读查询能力

当前已完成：

- 新增 read-only query 对象：`ProfileMemorySnapshotQuery`
- 新增 query use case / workflow
- assembly 能构建 `profile_memory` 查询 workflow
- API 新增 `GET /vitalai/flows/profile-memory/{user_id}`
- 写入 flow 与查询 flow 复用同一个 repository
- 测试覆盖写入后读取、空用户读取、HTTP route 读取
- README 已补手动读写验收命令

### 最小用户交互入口 backend-only

当前已完成：

- 新增 `UserInteractionCommand`
- 新增 `UserInteractionWorkflow`
- assembly 能构建用户交互 workflow
- API 新增 `POST /vitalai/interactions`
- 支持路由到 health / daily_life / mental_care / profile_memory update / profile_memory query
- 返回统一 `accepted / response / actions / runtime_signals / memory_updates` 形状
- 测试覆盖 profile memory 写读、health alert、unsupported event
- README 已补手动验收命令

### runtime snapshot 本地持久化

当前已完成：

- 新增本地文件型 `FileSnapshotStore`
- 默认仍保持进程内 `SnapshotStore`，避免普通测试和轻量运行被持久化副作用污染
- 通过 `VITALAI_RUNTIME_SNAPSHOT_STORE_PATH` 显式启用持久化 store
- diagnostics / failover drill 继续复用原有 typed snapshot contract
- 测试覆盖跨 store 实例读取历史、assembly 重建后版本延续
- README 已补人工验收命令

### 用户交互入口契约收敛

当前已完成：

- `event_type` 已收敛为 application 层枚举
- 支持少量明确别名，例如 `remember` / `recall`
- `user_id`、`channel`、`message` 已有基础输入校验，`event_type` 现在是可选 hint
- 非对象 `context` 和 profile memory update 缺失 `memory_key` / `memory_value` 会返回稳定错误响应
- 交互响应增加最小 `session` 上下文，但不保存多轮聊天状态
- README 已补人工错误验收命令

### 第一层最小意图识别

当前已完成：

- 新增 `IntentRecognizer` 可插拔接口
- 新增 `RunUserIntentRecognitionUseCase`
- 新增当前阶段可测的 `RuleBasedIntentRecognizer`
- `event_type` 从必填路由字段变为可选 hint
- 不传 `event_type` 时，interaction workflow 会根据 `message` 识别基础意图并路由
- 无法识别时返回 `clarification_needed`
- 响应增加 `intent` 诊断信息，便于人工判断路由原因

### BERT 意图识别接入前工程底座

当前已完成：

- 新增 `IntentDatasetExample` 训练/评估数据 schema
- 新增 `docs/intent_dataset_examples.jsonl` 种子样本
- 新增 `BertIntentRecognizer` adapter 壳，当前不加载真实模型
- 新增 `HybridIntentRecognizer` 预留混合策略边界
- 新增 `VITALAI_INTENT_RECOGNIZER=rule_based|bert|hybrid`
- 新增 `VITALAI_BERT_INTENT_MODEL_PATH`
- 没有模型文件时 `bert` 模式会稳定 fallback 到规则识别器

### docs 轻量治理

当前已完成：

- docs 根目录只保留当前真源、模块手册和少量活跃支撑文件
- 47 个 `STEP_*` 历史步骤文档已移动到 `docs/archive/steps/`
- docx / mmd / png / xmind 设计资产已移动到 `docs/archive/design-assets/`
- 非当前真源的阶段记录已移动到 `docs/archive/reports/`
- `DOCS_INDEX` 已更新归档结构和阅读规则

### 意图识别数据集扩充与离线评估

当前已完成：

- `docs/intent_dataset_examples.jsonl` 已扩充到 270 条样本
- 数据集覆盖 health / daily_life / mental_care / profile_memory_update / profile_memory_query / unknown / needs_decomposition
- baseline 每类 intent 固定 30 条，包含 train / dev / test split 字段
- holdout 当前共 90 条，其中 33 条为复合/多任务/歧义表达，不参与 bootstrap 训练命令
- 数据集包含中文、英文、澄清样本、口语表达、轻量多意图优先级样本和第二层拆分候选样本
- 新增 `RunIntentRecognitionEvaluationUseCase`
- 新增 `scripts/evaluate_intents.py`
- `scripts/evaluate_intents.py` 已支持 `--splits baseline|holdout|all` 与 `--group-by-split`
- 评估报告已增加 `by_source / fallback / clarification`，可分开观察 BERT 直接识别、低置信 fallback、澄清路径和 `needs_decomposition_detector`
- 当前 `rule_based` 全量离线评估结果为 `270/270` 通过

### 第一层复合意图边界与第二层占位

当前已完成：

- 新增 `requires_decomposition` 数据集字段
- 新增 `needs_decomposition` 评估标签，用于表达复合语言、多任务、口语模糊和高歧义输入
- 第一层识别器会先检测健康 + 日常、心理/情绪 + 用药、记忆 + 家庭/日常词等复合信号
- `POST /vitalai/interactions` 遇到复合输入时返回 `error=decomposition_needed`
- 当前只做第二层边界占位，不直接调用 LLM，不直接路由到领域 workflow
- 新增 `IntentDecompositionTask`、`IntentDecompositionRiskFlag`、`IntentDecompositionResult`
- 新增 `RunIntentDecompositionUseCase` placeholder 和 `intent_decomposition_payload`
- `error_details.decomposition` 已能返回 `pending_second_layer`、`candidate_tasks`、`risk_flags`、`routing_decision`
- 新增 `intent_decomposition_llm_output_schema`
- 新增 `validate_intent_decomposition_llm_payload` 和 `RunIntentDecompositionValidationUseCase`
- schema validator 会拒绝缺少 primary task 的路由输出、非法 intent、越界 priority/confidence、非法 risk severity
- 新增 `IntentDecomposer` / `IntentDecompositionBackend` protocol
- 新增 `PlaceholderIntentDecomposer` 与 `LLMIntentDecomposer` adapter shell
- backend 缺失或异常会 fallback 到 placeholder，backend 输出非法时只返回 validation issues
- 新增 `VITALAI_INTENT_DECOMPOSER=placeholder|llm` assembly 配置边界
- 默认 `placeholder`；`llm` 当前只启用 adapter shell，未配置真实 backend 时仍 fallback 到 placeholder
- 测试已覆盖识别器层和 workflow 层的 `decomposition_needed` 行为

### BERT 真实模型 adapter 推理边界

当前已完成：

- `BertIntentRecognizer` 已支持本地模型路径存在时的延迟加载
- adapter 只使用本地模型，不下载模型
- 缺模型路径、路径不存在、依赖缺失、推理异常、低置信度都会 fallback 到 `rule_based`
- 新增 `VITALAI_BERT_INTENT_CONFIDENCE_THRESHOLD`
- 新增 `VITALAI_BERT_INTENT_LABELS`，支持 `LABEL_0`/数字标签映射到现有 intent
- 新增 `scripts/check_bert_intent_runtime.py` 本地自检入口
- `scripts/evaluate_intents.py --recognizer bert` 可复用同一离线评估入口

### BERT bootstrap 分类模型导出与离线验收

当前已完成：

- 新增 `scripts/train_bert_intent_classifier.py`，用于从本地 BERT base 与 `docs/intent_dataset_examples.jsonl` 训练 6 类 intent 分类模型
- 原始 base 模型目录 `D:\AI\Models\fine-tuned-bert-intent` 保持不覆盖
- 已导出 bootstrap 分类模型到 `D:\AI\Models\fine-tuned-bert-intent-vitalai-trained`
- 新模型 `config.json` 已声明 `BertForSequenceClassification`、`num_labels=6`、`id2label/label2id`
- `scripts/check_bert_intent_runtime.py` 自检结果为 `ready=true`
- `scripts/evaluate_intents.py --recognizer bert --splits baseline` 在当前 180 条基线样本上评估为 `180/180`

注意：该模型是冻结 BERT base 后基于当前工程基线样本快速训练的 bootstrap 模型，用于验证接入链路，不应被理解为生产泛化模型。

### BERT bootstrap API 级启用烟测

当前已完成：

- 已用 `VITALAI_INTENT_RECOGNIZER=bert` 和 `D:\AI\Models\fine-tuned-bert-intent-vitalai-trained` 启动后端临时服务
- 已通过 `POST /vitalai/interactions` 验证 health、daily_life、mental_care、profile_memory_update、profile_memory_query、unknown 六类路径
- health、daily_life、profile_memory_update 可由 BERT 直接识别并路由
- profile_memory_query 与 mental_care 当前通过 `bert_low_confidence_fallback` 仍能成功路由
- unknown 可稳定返回澄清响应
- Windows PowerShell 中文请求已验证需要 UTF-8 byte body；使用该方式时，中文“我刚刚摔倒了，现在有点头晕”可由 BERT 直接识别为 `health_alert`

### BERT bootstrap holdout 分组评估

当前已完成：

- 已新增 holdout 样本，共 90 条
- holdout 样本使用 `source=holdout_manual_v1` / `source=holdout_hard_manual_v1` / `source=user_complex_multitask_v1` 与 `split=holdout`
- `rule_based --group-by-split` 全量结果为 `270/270`
- bootstrap BERT baseline 结果为 `180/180`，其中 `bert=161`、`bert_low_confidence_fallback=19`
- bootstrap BERT holdout 结果为 `86/90`
- holdout 中 `needs_decomposition_detector=33`，33 条全部成功进入第二层占位
- holdout 中 `bert=41`，其中 37 条正确、4 条高置信直接误判
- holdout 中 `bert_low_confidence_fallback=16`，16 条全部成功路由
- 当前暴露的 4 个 BERT 高置信误判集中在健康/记忆表达被日常或其他类吸走，尤其是包含 `medicine / dinner / daughter / reminder` 的混合表达
- 误判清单已记录到 `docs/plans/2026-04-15-bert-intent-high-confidence-errors.md`

注意：困难 holdout 已经开始暴露模型泛化边界，但仍是人工构造样本；下一步需要引入真实用户表达或更贴近真实的采样。

## 当前首要任务

### 1. 设计第二层 workflow 守门逻辑

建议方向：

- application assembly 只注入 decomposer，不让 router 直接知道 backend 类型
- 设计 workflow 守门逻辑：只有 validator 通过且 routing guard 允许时，才可能从 decomposition result 回到领域路由
- 第二层输出仍不能直接写库或调用领域服务，必须回到 application workflow 做校验与路由
- 暂时不接真实 LLM backend；先用 stub backend 或测试 fixture 验证守门规则
- 继续补充真实老人表达，特别是“健康+日常”“心理+用药”“记忆+家庭关系”的混合句

交付标准：

- 默认配置下 `POST /vitalai/interactions` 对复合输入仍稳定返回 `decomposition_needed`
- 开关关闭时不调用真实 LLM backend
- 开关打开但 backend 缺失/异常/输出非法时不进入领域路由
- adapter shell、validator、workflow 守门逻辑三者职责分离
- ready_for_routing=false 或 route guard 不通过时，响应必须仍是非 accepted
- baseline / holdout 仍能分开评估
- 能明确区分 BERT 直接识别、fallback、clarification 和 decomposition
- 不为了提高表面分数删除困难 holdout
- 如果重新训练，训练样本不能直接覆盖 holdout 回归集

## 当前第二优先级

### 2. 基于 API smoke 结果调优 BERT 置信度与 fallback 策略

建议方向：

- 记录每类 API smoke 的 `intent.source` 与 `confidence`
- 重点观察 `profile_memory_query` 与 `mental_care_checkin` 为什么更容易落到 `bert_low_confidence_fallback`
- 评估 `VITALAI_BERT_INTENT_CONFIDENCE_THRESHOLD=0.65` 是否适合作为默认阈值
- 保留 fallback，不因为当前 bootstrap 模型短期通过 baseline 就移除规则兜底
- 在困难 holdout 足够之前，不把阈值调优视为生产效果优化

交付标准：

- 低置信 fallback 的触发原因可解释
- 阈值变化必须同时跑 baseline 与 holdout
- fallback 后成功路由与直接 BERT 成功路由要分开统计
- 不为了提高表面准确率牺牲 unknown / clarification 安全边界

## 现在不做什么

下面这些事情先不要做：

- 不做微服务拆分
- 不并行新开多个大领域
- 不继续为每个小修补新增一个 `STEP_*` 文档
- 不为了“未来可能很大”继续引入更重的抽象层
- 不把 `CURRENT_STATUS` 和 `NEXT_TASK` 再写回开发流水账

## 选择顺序

当前推荐顺序：

1. 定义第二层 workflow 守门逻辑
2. 继续扩充复合/歧义 holdout，并保留 BERT 高置信误判清单

一次只做一个，做完一个再更新 `CURRENT_STATUS.md` 与 `NEXT_TASK.md`。
