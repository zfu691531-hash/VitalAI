# Next Task

Date: 2026-04-16

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
- 查询支持可选 `memory_key` 过滤；不传 key 返回完整 snapshot，传 key 返回单 key snapshot 或稳定空 snapshot
- snapshot 响应已增加只读派生字段 `memory_keys` 与 `readable_summary`，方便人工快速确认当前用户记忆内容
- 测试覆盖写入后读取、空用户读取、按 key 读取、可读性字段、HTTP route 读取
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

- `docs/intent_dataset_examples.jsonl` 已扩充到 288 条样本
- 数据集覆盖 health / daily_life / mental_care / profile_memory_update / profile_memory_query / unknown / needs_decomposition
- baseline 每类 intent 固定 30 条，包含 train / dev / test split 字段
- holdout 当前共 108 条，其中 33 条为复合/多任务/歧义表达，18 条为 `hardcase_guard_precision_v1` 困难边界样本，不参与 bootstrap 训练命令
- 数据集包含中文、英文、澄清样本、口语表达、轻量多意图优先级样本和第二层拆分候选样本
- 新增 `RunIntentRecognitionEvaluationUseCase`
- 新增 `scripts/evaluate_intents.py`
- `scripts/evaluate_intents.py` 已支持 `--splits baseline|holdout|all` 与 `--group-by-split`
- 评估报告已增加 `by_source / by_dataset_source / fallback / clarification`，可分开观察 BERT 直接识别、样本来源、低置信 fallback、澄清路径和 `needs_decomposition_detector`
- 当前 `rule_based` 全量离线评估结果为 `288/288` 通过

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
- 新增 `RunIntentDecompositionRoutingGuardUseCase`、`IntentDecompositionRoutingGuardResult` 与非执行型 `IntentDecompositionRoutingCandidate`
- `error_details.decomposition_guard` 已能返回 `status`、`candidate_ready`、`routing_candidate`、`clarification_question`、`blocked_reasons`
- workflow 守门逻辑已覆盖：合法低风险拆解只产生候选，不直接执行；澄清输出转为 clarification candidate；高风险、低置信、缺 primary task 或 route guard 不通过时保持非 accepted
- 测试已覆盖识别器层、workflow 层的 `decomposition_needed` 行为，以及第二层 routing guard 的候选路由、澄清候选、高风险阻断路径

### 最小 InputPreprocessor

当前已完成：

- 新增 `RunUserInputPreprocessingUseCase`
- 支持 trim、连续空白收敛、原始输入保留、空消息保护、长文本标记和非空白控制字符标记
- `UserInteractionWorkflow` 会在 request validation、intent recognition 和领域路由前使用规范化后的 message
- `POST /vitalai/interactions` 响应新增 `preprocessing`
- `preprocessing` 可返回 `original_message`、`normalized_message`、`changed`、`flags`
- router 仍只做请求解析，不承载预处理规则
- 测试已覆盖单独 use case、workflow 层和 HTTP API 层

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

- 已新增 holdout 样本，共 108 条
- holdout 样本使用 `source=holdout_manual_v1` / `source=holdout_hard_manual_v1` / `source=user_complex_multitask_v1` / `source=hardcase_guard_precision_v1` 与 `split=holdout`
- `rule_based --group-by-split` 全量结果为 `288/288`
- bootstrap BERT baseline 结果为 `180/180`，其中 `bert=142`、`bert_hard_case_guard=25`、`bert_low_confidence_fallback=13`
- bootstrap BERT holdout 结果为 `108/108`
- holdout 中 `needs_decomposition_detector=33`，33 条全部成功进入第二层占位
- holdout 中 `bert=33`，33 条全部正确
- holdout 中 `bert_hard_case_guard=27`，27 条全部正确
- holdout 中 `bert_low_confidence_fallback=15`，15 条全部成功路由
- `hardcase_guard_precision_v1` 当前为 `18/18`
- 原先 4 个 BERT 高置信误判已通过 hard-case guard 处理；误判清单与处理结论已记录到 `docs/plans/2026-04-15-bert-intent-high-confidence-errors.md`

注意：当前 `108/108` 依赖 BERT、hard-case guard、fallback 与 decomposition detector 的组合能力，不应被理解为 BERT 模型本体已经生产可用；下一步如果没有真实用户语料，不建议继续人工堆样本。

## 最近已收口的小任务

### 本地四闭环 smoke 验收脚本

已完成：

- 新增 `scripts/manual_smoke_typed_flow_history.py`
- 脚本不启动 `uvicorn`，直接通过 application assembly/workflow 运行本地验收
- 脚本会为 profile_memory、health、daily_life、mental_care 创建临时 `.runtime/manual-smoke-*` SQLite 路径
- 验收覆盖 profile memory 写后读、health alert 写后读、daily_life check-in 写后读、mental_care check-in 写后读
- 默认运行结束会清理临时目录；需要人工查看数据库时可传 `--keep-runtime`
- 人工快速验收可传 `--output text` 输出四条闭环的短摘要；默认仍输出 JSON，供自动化继续使用
- 测试覆盖脚本不会写入默认 `.runtime/*.sqlite3` 持久化文件
- targeted smoke/API/assembly/scheduler 测试已通过：`70 passed`
- full test 已通过：`172 passed`

### 扩充真实困难样本并评估 hard-case guard 精准度

已完成：

- 新增 18 条 `hardcase_guard_precision_v1` holdout 样本，覆盖日常提醒、长期记忆写入、记忆查询、用药后不适
- 收窄英文 `remind me` 规则：`Remind me to ...` 作为一次性日常提醒，`Remind me that ...` 才作为长期记忆写入候选
- 评估报告新增 `by_dataset_source`，可直接观察新增样本来源的通过率
- `rule_based` 全量 `288/288`
- bootstrap BERT baseline `180/180`
- bootstrap BERT holdout `108/108`

## 最近已收口的领域纵切

### Mental care 最小历史持久化/查询纵切

已完成：

- `mental_care` check-in flow 会写入 SQLite 历史记录，默认路径为 `.runtime/mental_care.sqlite3`，可通过 `VITALAI_MENTAL_CARE_DB_PATH` 覆盖
- 新增 `MentalCareCheckInEntry`、`MentalCareCheckInSnapshot`、SQLite record 与 `MentalCareCheckInRepository`
- `MentalCareCheckInSupportService` 支持可选历史仓储，执行 check-in 后会生成 `mental_care_entry` 与 `mental_care_snapshot`
- 新增 read-only query/workflow/API：`GET /vitalai/flows/mental-care-checkins/{user_id}`
- 查询支持 `limit`，返回 `checkin_count`、`recent_mood_signals`、`recent_support_needs`、`readable_summary` 与 entries
- API 写入响应会带出 `mental_care_entry` 与 `mental_care_snapshot`，方便人工验收
- 该纵切不包含心理量表、长期情绪趋势、多轮陪伴、复杂干预、图谱或复杂搜索
- targeted mental_care/API/assembly/scheduler/consumer 测试已通过：`65 passed`
- full test 已通过：`168 passed`

交接注意：

- mental_care 这次只补最小历史读写闭环；不要顺手扩展到心理评估量表、情绪趋势分析或多轮陪伴系统。
- health / daily_life / mental_care 三条现有 typed flow 现在都具备最小历史/只读查询闭环，下一步建议优先收束验收和本地操作体验。

### Health 最小历史持久化/查询纵切

已完成：

- `health` alert flow 会写入 SQLite 历史记录，默认路径为 `.runtime/health.sqlite3`，可通过 `VITALAI_HEALTH_DB_PATH` 覆盖
- 新增 `HealthAlertEntry`、`HealthAlertSnapshot`、SQLite record 与 `HealthAlertRepository`
- `HealthAlertTriageService` 支持可选历史仓储，执行 alert 后会生成 `health_alert_entry` 与 `health_alert_snapshot`
- 新增 read-only query/workflow/API：`GET /vitalai/flows/health-alerts/{user_id}`
- 查询支持 `limit`，返回 `alert_count`、`recent_risk_levels`、`readable_summary` 与 entries
- API 写入响应会带出 `health_alert_entry` 与 `health_alert_snapshot`，方便人工验收
- 该纵切不包含健康档案、提醒调度、医疗规则引擎、病程管理、图谱或复杂搜索
- targeted health/daily_life/API/assembly/scheduler/consumer 测试已通过：`66 passed`
- full test 已通过：`168 passed`

交接注意：

- health 这次只补最小历史读写闭环；不要顺手扩展到完整健康档案或医疗决策系统。
- 如需继续深化 health，只做极小人工验收增强，不扩到完整健康档案或医疗决策系统。

### Daily life 最小历史持久化/查询纵切

已完成：

- `daily_life` check-in flow 会写入 SQLite 历史记录，默认路径为 `.runtime/daily_life.sqlite3`，可通过 `VITALAI_DAILY_LIFE_DB_PATH` 覆盖
- 新增 `DailyLifeCheckInEntry`、`DailyLifeCheckInSnapshot`、SQLite record 与 `DailyLifeCheckInRepository`
- `DailyLifeCheckInSupportService` 支持可选历史仓储，执行 check-in 后会生成 `checkin_entry` 与 `daily_life_snapshot`
- 新增 read-only query/workflow/API：`GET /vitalai/flows/daily-life-checkins/{user_id}`
- 查询支持 `limit`，返回 `checkin_count`、`recent_needs`、`readable_summary` 与 entries
- API 写入响应会带出 `checkin_entry` 与 `daily_life_snapshot`，方便人工验收
- 该纵切不包含任务状态机、提醒调度、服务单系统、图谱或复杂搜索
- targeted daily_life/API/assembly/scheduler/consumer 测试已通过：`64 passed`
- full test 已通过：`168 passed`
- `git diff --check` 无格式错误；只剩 Windows LF/CRLF 提示

交接注意：

- 工作区里已有的 `docs/archive/design-assets` 删除/新增变更不是本轮 daily_life/health 代码纵切的一部分；除非专门处理文档资产，不要把它和下一条业务纵切混在一起。

### Profile memory 输出可读性小增强

已完成：

- `ProfileMemorySnapshot` 增加只读 `memory_keys` 与 `readable_summary`
- typed flow API 与 `POST /vitalai/interactions` 的 profile snapshot 输出都会带出新增字段
- 没有新增复杂存储结构，也没有扩展到 profile graph / embedding retrieval / 模糊搜索
- `pytest tests -q` 已通过，profile memory route 与 interaction 测试已覆盖新增字段

## 现在不做什么

下面这些事情先不要做：

- 不做微服务拆分
- 不并行新开多个大领域
- 不继续为每个小修补新增一个 `STEP_*` 文档
- 不为了“未来可能很大”继续引入更重的抽象层
- 不把 `CURRENT_STATUS` 和 `NEXT_TASK` 再写回开发流水账

## 选择顺序

当前推荐顺序：

1. 优先使用 `scripts/manual_smoke_typed_flow_history.py` 做本地验收，并保持 README 中的短流程可执行
2. 如需继续领域增强，只给 health / daily_life / mental_care 做极小人工验收增强，不扩健康档案、任务状态机、提醒调度或多轮陪伴
3. 只有拿到新的真实表达样本时，才继续扩充 intent holdout

一次只做一个，做完一个再更新 `CURRENT_STATUS.md` 与 `NEXT_TASK.md`。
