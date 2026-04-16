# Current Status

Date: 2026-04-16

## 项目阶段定位

VitalAI 当前处于“工程化基线阶段”。

这意味着：

- 已经不再只是架构草图或目录原型。
- 也还没有进入可直接上线的生产阶段。
- 当前最重要的事情，是把现有架构收敛成一个可持续开发、可持续验证、可逐步落地的后端基线。

## 当前架构判断

当前 `application / platform / domains / interfaces / shared` 加 `Base/` 的总体架构方向是合理的，当前不建议推翻重做。

当前应坚持的判断：

- VitalAI 继续按“有清晰边界的 modular monolith”推进。
- `Base` 继续作为通用基础能力层复用，不把 VitalAI 特有业务逻辑反向塞回 `Base`。
- `platform/runtime` 继续保持拆分组件，不回退成单个超级 `supervisor`。

当前最需要改进的不是架构重构，而是：

- 文档治理
- 工程化边界
- 持久化与权限能力
- 真实领域纵切深度

## 当前已经具备的基础

### 架构与分层

- 分层结构已经稳定：`application / platform / domains / interfaces / shared`
- `application/assembly.py` 已经形成轻量组合根
- API、scheduler、consumer 已具备同一套 typed flow 适配方式

### 平台与运行时

- `platform/messaging`、`feedback`、`arbitration`、`interrupt` 已有 typed contract
- `platform/runtime` 已具备 decision、snapshot、failover、degradation 等基础骨架
- `platform/observability` 和 `platform/security` 已经进入真实运行链路
- runtime diagnostics 与 health failover drill 已改为显式 `POST /admin/...` 控制面路径
- admin 控制面已经具备最小 token/header 权限基线
- runtime snapshot 已具备本地文件持久化 store，可通过 `VITALAI_RUNTIME_SNAPSHOT_STORE_PATH` 启用跨实例历史读取与版本延续

### 业务流与领域

- `health`、`daily_life`、`mental_care` 已有真实 typed flow
- `reporting` 已接入轻量安全审查
- `health` 已新增最小历史持久化纵切：alert 写入后会形成 SQLite 历史记录，并可通过只读 query/API 读取最近健康预警历史
- `health` 历史纵切包括 `HealthAlertEntry`、`HealthAlertSnapshot`、SQLite record 与 `HealthAlertRepository`
- `HealthAlertTriageService` 支持可选历史仓储，flow 执行后会生成 `health_alert_entry` 与 `health_alert_snapshot`
- `health` 只读查询链路已走通：`HealthAlertHistoryQuery` -> use case -> workflow -> `GET /vitalai/flows/health-alerts/{user_id}`
- `daily_life` 已新增最小历史持久化纵切：check-in 写入后会形成 SQLite 历史记录，并可通过只读 query/API 读取最近历史
- `daily_life` 历史纵切包括 `DailyLifeCheckInEntry`、`DailyLifeCheckInSnapshot`、SQLite record 与 `DailyLifeCheckInRepository`
- `DailyLifeCheckInSupportService` 支持可选历史仓储，flow 执行后会生成 `checkin_entry` 与 `daily_life_snapshot`
- `daily_life` 历史查询已支持可选 `limit`，返回 `checkin_count`、`recent_needs`、`readable_summary` 与 entries，方便人工验收
- `daily_life` 只读查询链路已走通：`DailyLifeCheckInHistoryQuery` -> use case -> workflow -> `GET /vitalai/flows/daily-life-checkins/{user_id}`
- `mental_care` 已新增最小历史持久化纵切：check-in 写入后会形成 SQLite 历史记录，并可通过只读 query/API 读取最近精神关怀历史
- `mental_care` 历史纵切包括 `MentalCareCheckInEntry`、`MentalCareCheckInSnapshot`、SQLite record 与 `MentalCareCheckInRepository`
- `MentalCareCheckInSupportService` 支持可选历史仓储，flow 执行后会生成 `mental_care_entry` 与 `mental_care_snapshot`
- `mental_care` 只读查询链路已走通：`MentalCareCheckInHistoryQuery` -> use case -> workflow -> `GET /vitalai/flows/mental-care-checkins/{user_id}`
- `profile_memory` 已不再是空骨架，已经有真实持久化写入与只读查询纵切
- `profile_memory` 已通过 `Base/Repository` + SQLite 走通 repository/service/use case/workflow/interface/API
- `profile_memory` 查询已支持可选 `memory_key` 过滤；不传 key 时读取完整 snapshot，传 key 时只返回对应记忆或稳定空 snapshot
- `profile_memory` snapshot 已增加只读派生字段 `memory_keys` 与 `readable_summary`，便于人工快速验收，不改变持久化模型
- 已有 backend-only 最小用户交互入口 `POST /vitalai/interactions`
- 交互入口可路由到现有 typed flow，不包含前端 UI / App / 完整聊天系统
- 交互入口已具备事件类型枚举、别名归一化、基础输入校验、非法 context 稳定错误响应和最小 session context
- 已新增第一层最小意图识别能力，当前使用规则型 `RuleBasedIntentRecognizer`，为后续 fine-tuned BERT 适配器预留 `IntentRecognizer` 接口
- BERT 意图识别接入前工程底座已具备：`IntentDatasetExample` schema、`BertIntentRecognizer` adapter 壳、`rule_based/bert/hybrid` 配置入口和无模型 fallback
- `BertIntentRecognizer` 已具备本地模型路径的延迟加载推理边界、BERT label 映射配置和本地 runtime 自检脚本，并在模型缺失、依赖缺失、推理异常、低置信度时 fallback 到规则识别器
- 意图识别数据集已扩充为覆盖 5 类业务 intent、`unknown` 澄清样本、`needs_decomposition` 复合/歧义样本与困难边界样本的 JSONL 数据集：baseline 180 条；holdout 108 条，其中 33 条需要第二层拆分，18 条为 `hardcase_guard_precision_v1`；总计 288 条
- 已新增离线评估入口 `scripts/evaluate_intents.py`，支持 `--splits baseline|holdout|all` 与 `--group-by-split`，并输出 `by_dataset_source` 以便按样本来源观察质量；当前 `rule_based` 在全量 288 条上评估为 `288/288` 通过，其中 `needs_decomposition_detector` 为 `33/33`
- 已新增本地 BERT intent 训练脚本 `scripts/train_bert_intent_classifier.py`
- 已基于 `D:\AI\Models\fine-tuned-bert-intent` 导出可运行的 6 类 bootstrap intent sequence-classification 模型：`D:\AI\Models\fine-tuned-bert-intent-vitalai-trained`
- 新导出的 bootstrap 模型已通过 `scripts/check_bert_intent_runtime.py` 自检，`ready=true`，并在当前 180 条基线样本上离线评估为 `180/180`
- 已用 bootstrap BERT 模型完成 `POST /vitalai/interactions` API 级烟测：health、daily_life、profile_memory_update 可由 BERT 直接识别，profile_memory_query 与 mental_care 可通过低置信 fallback 成功路由，unknown 可进入澄清
- 已用 bootstrap BERT 模型完成 holdout 分组评估：在 `C:\Users\Windows\miniconda3\python.exe` 环境下，当前 holdout `108/108`；其中 `needs_decomposition_detector` 接住 33 条，`bert_hard_case_guard` 接住 27 条，BERT 直接识别 33 条，低置信 fallback 成功 15 条
- 已新增 BERT hard-case guard：对用药后不适、明确长期提醒/记忆写入、记忆查询、一次性英文提醒 `remind me to ...` 等高价值混淆场景先做可解释兜底，且复合意图检测仍优先于 hard-case guard
- 用户交互 workflow 已具备第二层意图拆分占位：当第一层检测到复合/多任务/模糊表达时，返回 `decomposition_needed`，暂不直接调用 LLM 或路由到领域 workflow
- 第二层意图拆分已具备最小 typed contract：`IntentDecompositionTask`、`IntentDecompositionRiskFlag`、`IntentDecompositionResult`、`RunIntentDecompositionUseCase` 和 `intent_decomposition_payload`
- `decomposition_needed` 响应已增加 `error_details.decomposition`，可人工查看 `pending_second_layer`、`candidate_tasks`、`risk_flags` 和 `routing_decision`
- 第二层 LLM 输出已具备本地 schema/validator：`intent_decomposition_llm_output_schema`、`validate_intent_decomposition_llm_payload`、`RunIntentDecompositionValidationUseCase`，非法输出只返回 validation issues，不会生成可路由 result
- 第二层已具备可替换 adapter shell：`IntentDecomposer`、`IntentDecompositionBackend`、`PlaceholderIntentDecomposer`、`LLMIntentDecomposer`；真实 backend 输出必须通过 validator，backend 缺失或异常会回退到 placeholder
- 第二层 decomposer 已接入 assembly 配置边界：`VITALAI_INTENT_DECOMPOSER=placeholder|llm`，默认 `placeholder`；`llm` 模式当前只有 adapter shell，未配置真实 backend 时仍会安全回退
- 第二层 workflow 守门逻辑已接入：`RunIntentDecompositionRoutingGuardUseCase` 会把合法拆解输出转换为非执行型 `routing_candidate` / `clarification_candidate`，高风险、低置信、缺少 primary task 或 route guard 不通过时保持非 accepted
- `decomposition_needed` 响应已增加 `error_details.decomposition_guard`，可人工查看 `status`、`candidate_ready`、`routing_candidate`、`clarification_question` 与 `blocked_reasons`
- 最小 `InputPreprocessor` 已接入 application workflow：`RunUserInputPreprocessingUseCase` 会在 intent recognition 前执行 trim、连续空白收敛、原始输入保留、空消息保护和基础异常标记
- `POST /vitalai/interactions` 响应已增加 `preprocessing` 字段，可人工查看 `original_message`、`normalized_message`、`changed` 与 `flags`
- Windows PowerShell 中文人工验收需要用 UTF-8 byte body，否则请求或响应可能出现乱码并误导意图识别结果

### 文档治理

- docs 根目录已经收敛为当前真源、模块手册和少量活跃支撑文件
- 47 个 `STEP_*` 历史步骤文档已归档到 `docs/archive/steps/`
- docx / mmd / png / xmind 等大体积设计资产已归档到 `docs/archive/design-assets/`
- 非当前真源的阶段记录已归档到 `docs/archive/reports/`
- 历史材料仍保留，但不再干扰新窗口默认阅读顺序

### 工程基线

- 默认测试入口已经可用：`pytest tests -q`
- 运行时安全误报/漏报与重复领域执行等关键问题已开始收敛
- `Base` 的导入副作用已做第一轮收敛，不再适合继续用“导入即初始化”模式扩散
- admin 控制面接口已覆盖无 token、错误 token、正确 token、生产禁用等测试路径
- `health` 已覆盖 alert 写入后读取、空用户读取、limit 限制、HTTP route 读写验收测试
- 最近 health/daily_life/API/assembly/scheduler/consumer targeted tests 已通过：`66 passed`
- `daily_life` 已覆盖 check-in 写入后读取、空用户读取、limit 限制、HTTP route 读写验收测试
- `mental_care` 已覆盖 check-in 写入后读取、空用户读取、limit 限制、HTTP route 读写验收测试
- 最近 mental_care/API/assembly/scheduler/consumer targeted tests 已通过：`65 passed`
- 最近 daily_life/API/assembly/scheduler/consumer targeted tests 已通过：`64 passed`
- 已新增 `scripts/manual_smoke_typed_flow_history.py`，可不启动服务直接用临时 `.runtime/manual-smoke-*` SQLite 路径验收 profile_memory、health、daily_life、mental_care 四条写后读闭环，并支持 `--output text` 输出人工可读短摘要
- 最近 typed flow history smoke/API/assembly/scheduler targeted tests 已通过：`70 passed`
- 最近全量测试已通过：`172 passed`
- 最近 `git diff --check` 无格式错误；仅有 Windows LF/CRLF 提示
- `profile_memory` 已覆盖写入后读取、空用户读取、按 `memory_key` 查询、可读性派生字段、HTTP route 读写验收测试
- 用户交互入口已覆盖 profile memory 写读、health alert、unsupported event、缺失字段、非法 context、输入预处理、无 event_type 自然语言识别、无法识别时澄清响应、复合意图 `decomposition_needed` 响应、第二层拆分 placeholder payload、第二层 routing guard、BERT adapter fallback、离线 intent evaluation 测试路径
- runtime snapshot 持久化已覆盖跨 store 实例读取和 assembly 重建后历史延续测试路径

## 当前还没有达到的状态

当前项目仍然不是生产就绪后端，主要差距在这里：

- runtime snapshot 已有本地开发可用的文件持久化方案，但还不是生产级分布式/高可用持久化方案
- admin/control 目前只有最小 token 基线，还不是完整用户/角色权限体系
- 用户交互入口仍是 backend-only，不是完整多轮对话或产品交互系统
- BERT intent 当前已有可运行 bootstrap 模型，但它是基于当前 180 条工程基线样本训练的快速接入模型，主要用于验证 adapter、label 映射、fallback 与 API 启用链路；当前 108 条 holdout 虽已通过 hard-case guard 达到 `108/108`，但这不代表模型本体已具备生产泛化能力
- 第二层意图拆分当前已有契约、placeholder、JSON schema 校验、adapter shell、assembly 配置开关和非执行型 workflow routing guard，但还没有真实 LLM backend，也不会从拆分结果直接执行领域 workflow
- bootstrap 模型在部分意图上仍依赖 `bert_low_confidence_fallback` 与 `bert_hard_case_guard` 成功路由；后续需要继续扩充真实困难样本、观察 guard 精准度，并把误判样本沉淀为训练候选而不是直接覆盖 holdout
- 真实落地领域仍然偏少，整体业务深度仍然需要继续补
- `health` 当前只有历史记录和只读查询闭环，还不是完整健康档案、提醒调度、医疗规则引擎或病程管理系统
- `daily_life` 当前只有历史记录和只读查询闭环，还不是完整提醒调度、任务状态机或服务单系统
- `mental_care` 当前只有历史记录和只读查询闭环，还不是心理量表、长期情绪趋势、多轮陪伴或复杂干预系统
- 交付链路、部署、运维、迁移能力还没有形成完整标准
- docs 根目录噪音已明显降低，但后续仍要避免把 `CURRENT_STATUS` 和 `NEXT_TASK` 写回流水账

## 当前可做的事情

下面这些工作符合当前阶段，应该优先做：

- 继续保持文档真源短、准、可执行，新增历史材料默认进入 `docs/archive/` 或 `docs/plans/`
- 四条现有读写闭环已有本地 smoke 脚本，下一步宜先使用并维护该验收入口，而不是继续开新领域
- 在当前文件型 runtime snapshot store 基础上补充清理策略、迁移策略和生产存储选型
- 后续继续补 `profile_memory` 的检索、画像演进和更丰富业务规则
- 后续推进 BERT 时，应继续扩充更真实、更难的 holdout 样本与误判样本回流，而不是继续只在当前 baseline 上优化
- 继续清理 `Base` 复用边界、依赖边界与测试/启动基线

## 当前不该做的事情

下面这些方向现在不应该优先推进：

- 微服务拆分
- 引入重型工作流引擎或过度复杂的容器化治理
- 为了未来假想规模继续做大而全抽象
- 一次性扩很多新业务域
- 继续把 `CURRENT_STATUS.md` 写成开发流水账
- 继续把 `STEP_*` 文档当成当前状态真源

## 可以稍后再做的事情

这些方向有价值，但应该放到后续阶段：

- 多租户/更完整权限体系
- 更强的部署与运维基线
- 更多真实业务域落地
- 更完整的 memory retrieval / profile graph / long-term evolution
- 更重的异步基础设施与跨进程协作机制

## 当前阶段的完成标准

当下面这些条件大部分成立时，可以认为“工程化基线阶段”基本完成：

- 至少 1 到 2 条真实业务域具备稳定持久化与读写闭环
- admin/control 路径具备最小可接受权限控制
- runtime snapshot 不再只依赖临时内存实现，并具备本地可验收的历史延续路径
- 本地启动、测试、依赖说明、基础交付链路稳定
- 文档真源已经清晰，历史文档已归档且不再主导开发节奏

## 当前有效文档入口

请优先阅读：

1. `docs/DOCS_INDEX.md`
2. `docs/PROJECT_CONTEXT.md`
3. `docs/CURRENT_STATUS.md`
4. `docs/NEXT_TASK.md`
5. `README.md`

历史 `STEP_*` 文档已归档到 `docs/archive/steps/`，只在当前任务直接相关时再阅读。
