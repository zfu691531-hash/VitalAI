# VitalAI 中文分模块开发计划

Date: 2026-04-16

## 计划定位

这份文档用于让项目开发节奏可跟随、可对照、可验收。

它回答三个问题：

- 当前整体架构往哪个方向走
- 每个模块现在处于什么阶段
- 下一阶段每个模块交付什么、怎么人工验收

它不是历史流水账，也不是最终产品蓝图。历史设计资产仍放在 `docs/archive/`，当前开发判断仍以 `PROJECT_CONTEXT / CURRENT_STATUS / NEXT_TASK` 为准。

## 总体方向

VitalAI 当前继续按“有清晰边界的 modular monolith”推进。

当前主线不是拆微服务，也不是一次性做完整 App / 聊天系统 / 多 Agent 自主规划，而是先把服务端后端基线打牢：

```text
用户输入
-> interfaces 薄入口
-> application command / use case / workflow
-> intent recognition / routing
-> domains 领域能力
-> platform runtime / feedback / security / observability
-> 统一响应与可验证报告
```

当前最重要的架构判断：

- `Base/` 继续作为通用基础能力层，VitalAI 不反向污染 Base。
- `VitalAI/` 继续保持 `application / platform / domains / interfaces / shared` 分层。
- `platform/runtime` 继续保持组件化，不回退为单个超级 supervisor。
- 用户交互先保持 backend-only，不急于做完整前端 UI 或多轮聊天产品。
- BERT 当前作为第一层意图识别，不作为业务调度器。
- LLM 深度拆分是后续阶段能力，不在当前阶段直接接入主链路。

## 当前阶段

当前阶段名称：工程化基线阶段。

阶段目标：

- 让核心后端链路稳定可运行。
- 让至少 1 到 2 条业务纵切具备读写闭环。
- 让用户输入入口、意图识别、领域路由、运行时观测可被测试和人工验收。
- 让文档变成项目跟进工具，而不是噪音。

阶段完成标准：

- `pytest tests -q` 稳定通过。
- `POST /vitalai/interactions` 可完成自然语言输入到领域 workflow 的路由。
- `profile_memory` 具备持久化写入和只读查询闭环。
- `health` 具备 alert 历史写入和只读查询闭环。
- `daily_life` 具备 check-in 历史写入和只读查询闭环。
- `mental_care` 具备 check-in 历史写入和只读查询闭环。
- runtime snapshot 具备本地持久化与历史延续。
- admin/control 具备最小 token 权限。
- 第一层 intent 具备 baseline / holdout 分组评估，且能区分 BERT 直接识别、fallback、clarification 与 decomposition。

## 模块 1：interfaces 接口层

### 模块职责

`interfaces/` 只负责外部入口适配，包括 HTTP API、scheduler、consumer 等。

它不负责业务判断，不维护复杂状态，不直接写数据库，不直接加载模型。

### 当前状态

- `POST /vitalai/interactions` 已作为 backend-only 最小用户交互入口。
- `GET /vitalai/flows/profile-memory/{user_id}` 已支持 profile memory 只读查询。
- `GET /vitalai/flows/health-alerts/{user_id}` 已支持 health 最近 alert 历史只读查询。
- `GET /vitalai/flows/daily-life-checkins/{user_id}` 已支持 daily_life 最近 check-in 历史只读查询。
- `GET /vitalai/flows/mental-care-checkins/{user_id}` 已支持 mental_care 最近 check-in 历史只读查询。
- admin runtime diagnostics 和 health failover drill 已走控制面路径。
- API router 基本保持薄入口。

### 下一阶段交付

- 保持 `interactions.py` 只做请求解析、调用 workflow、返回统一响应。
- 补充用户输入预处理的接口字段承接能力，但不在 router 里实现复杂预处理。
- 人工验收命令继续沉淀到 README。

### 验收标准

- 缺字段、非法 context、unsupported event 都返回统一交互响应。
- 不传 `event_type` 时能通过 intent recognition 路由。
- 使用 BERT 模式启动后，交互入口仍能稳定返回 `intent.source`、`primary_intent`、`routed_event_type`。

### 暂不做

- 不在 router 维护多轮聊天状态。
- 不在 router 做 LLM 调用。
- 不在 router 写入 profile memory repository。

## 模块 2：application 应用编排层

### 模块职责

`application/` 是当前项目最关键的编排层，负责 command、query、use case、workflow、assembly。

它负责把领域能力、平台机制、接口入口串成稳定流程。

### 当前状态

- 已有 health / daily_life / mental_care typed flow。
- 已有 health alert 写入 flow 与历史查询 query/workflow。
- 已有 profile_memory 写入 flow 与查询 query/workflow。
- 已有 daily_life check-in 写入 flow 与历史查询 query/workflow。
- 已有 mental_care check-in 写入 flow 与历史查询 query/workflow。
- 已有 `UserInteractionWorkflow` 作为用户输入中心入口。
- 已有 `IntentRecognizer` 可插拔接口、rule_based / bert / hybrid 模式。
- 已有 BERT 本地 adapter、label mapping、confidence threshold、fallback。
- 已有 intent dataset schema、离线评估 use case、baseline/holdout 分组评估。
- 已有 `needs_decomposition` 复合/多任务/歧义输入边界，workflow 会返回 `decomposition_needed` 占位。
- 已有第二层意图拆分最小 typed contract 和 placeholder use case，当前只输出结构化诊断，不调用 LLM。
- 已有第二层 LLM 输出 schema/validator，非法输出不会生成可路由 result。
- 已有第二层可替换 adapter shell：placeholder 与 LLM backend 边界分离，backend 输出必须先走 validator。
- 已有第二层 assembly 配置开关：`VITALAI_INTENT_DECOMPOSER=placeholder|llm`，默认保持 `placeholder`。
- 已有第二层 workflow 守门逻辑：合法拆解输出只生成非执行型候选，澄清输出生成 clarification candidate，高风险或不满足 route guard 时继续保持非 accepted。
- 已有最小 `InputPreprocessor`：在 workflow 前置执行文本 trim、连续空白收敛、原始输入保留和基础异常标记，API 响应可查看 `preprocessing`。

### 下一阶段交付

- 扩充真实困难样本并评估 hard-case guard 精准度，尤其是用药不适、提醒/记忆写入、记忆查询、日常提醒之间的混淆边界。
- 为第二层 workflow 守门逻辑补充人工验收命令和更多复杂样本，但先不强行改现有主 intent。
- 继续扩充 holdout 困难样本，并让评估报告继续输出 `by_source / fallback / clarification`。

### 验收标准

- `scripts/evaluate_intents.py --recognizer rule_based --group-by-split` 可稳定输出全量报告。
- BERT baseline 与 holdout 能分开评估。
- 低置信 fallback、clarification 和 decomposition 数量能被单独统计。
- 第二层 `decomposition_guard` 能区分 `routing_candidate`、`clarification_candidate` 与 `hold_for_human_review`。
- 交互响应能看到 `preprocessing.original_message` 与 `preprocessing.normalized_message`，且 router 不承载预处理规则。
- workflow 不直接知道模型加载细节。

### 暂不做

- 不在当前阶段直接把真实 LLMIntentDecomposer 接入主链路。
- 不做完整多轮 session persistence。
- 不让 BERT 直接调用领域服务或数据库。

## 模块 3：domains 领域层

### 模块职责

`domains/` 负责业务领域自身语义，不负责外部入口和系统级运行机制。

当前核心领域：

- `health`
- `daily_life`
- `mental_care`
- `reporting`
- `profile_memory`

### 当前状态

- health / daily_life / mental_care 已有基础服务和 typed flow。
- health 已新增最小历史持久化和只读查询闭环，可写入 alert 历史并通过 API 查询最近记录；该闭环包括领域 entry/snapshot、SQLite record、repository、query/use case/workflow 与 HTTP API。
- daily_life 已新增最小历史持久化和只读查询闭环，可写入 check-in 历史并通过 API 查询最近记录；该闭环包括领域 entry/snapshot、SQLite record、repository、query/use case/workflow 与 HTTP API。
- mental_care 已新增最小历史持久化和只读查询闭环，可写入 check-in 历史并通过 API 查询最近记录；该闭环包括领域 entry/snapshot、SQLite record、repository、query/use case/workflow 与 HTTP API。
- reporting 已接入轻量反馈报告。
- profile_memory 已走通 SQLite 持久化、写入、查询、API 验收链路。

### 下一阶段交付

- 继续按小纵切推进真实领域，不一次性开很多新领域。
- `health` 后续只做极小验收增强；暂不扩展到健康档案、提醒调度、医疗规则引擎或病程管理。
- `daily_life` 后续只做极小验收增强；暂不扩展到提醒调度、任务状态机或服务单系统。
- `mental_care` 后续只做极小验收增强；暂不扩展到心理量表、长期情绪趋势、多轮陪伴或复杂干预系统。

### 验收标准

- 至少 profile_memory、health、daily_life 和 mental_care 可以完成写入后读取。
- 领域服务不依赖 HTTP request。
- 领域服务可被 workflow 和测试直接调用。
- 新增领域能力有对应 use case / workflow / test。

### 暂不做

- 不新增大量新业务域。
- 不把出行规划、PSO、家属 App 等复杂域同时展开。
- 不让领域服务直接处理 BERT 输出。

## 模块 4：platform 平台与运行时层

### 模块职责

`platform/` 承载跨领域系统机制：

- messaging
- feedback
- arbitration
- interrupt
- runtime
- observability
- security

### 当前状态

- typed contract 已覆盖 messaging / feedback / arbitration / interrupt。
- runtime 已具备 decision、snapshot、failover、degradation 等基础骨架。
- runtime snapshot 已支持本地文件持久化 store。
- observability/security 已进入真实 flow。
- admin runtime control 已有最小 token 权限。

### 下一阶段交付

- 补 runtime snapshot 清理策略和迁移策略。
- 继续把 runtime signal 与 API 输出保持一致。
- 为 control/admin 补充更清楚的开发/生产边界说明。

### 验收标准

- `VITALAI_RUNTIME_SNAPSHOT_STORE_PATH` 启用后，重启服务仍能延续历史版本。
- admin 接口无 token、错 token、正确 token 行为明确。
- runtime signal 能在 workflow / API 响应中被人工观察。

### 暂不做

- 不引入分布式高可用 snapshot 存储。
- 不做完整 RBAC / 多租户权限。
- 不把 runtime 合并成单个大 supervisor。

## 模块 5：intent recognition 用户输入与意图识别

### 模块职责

这是当前阶段的主开发线之一，负责把用户自然语言输入转成系统可路由的主 intent，或识别为需要第二层拆分的复合输入。

当前采用：

```text
needs_decomposition_detector
-> RuleBasedIntentRecognizer / BertIntentRecognizer
-> fallback / clarification
-> UserInteractionWorkflow
```

### 当前状态

- 当前主 intent 为 6 类：health_alert、daily_life_checkin、mental_care_checkin、profile_memory_update、profile_memory_query、unknown。
- 当前另有评估标签 `needs_decomposition`，用于复合语言、多任务、模糊和歧义输入，不作为一条领域 workflow。
- baseline 数据集每类 30 条，共 180 条。
- holdout 共 108 条，其中 33 条为 `needs_decomposition`，18 条为 `hardcase_guard_precision_v1`。
- bootstrap BERT 模型已导出并可运行。
- 规则识别器全量当前 `288/288`。
- bootstrap BERT holdout 当前 `108/108`，其中第二层占位 33 条全部命中，hard-case guard 命中 27 条，BERT 直接识别 33 条，低置信 fallback 成功 15 条。
- 评估报告已支持 `by_dataset_source`，可以单独观察 `hardcase_guard_precision_v1` 等样本来源的通过率。
- 第二层 placeholder 当前返回 `pending_second_layer`，并暴露 `candidate_tasks / risk_flags / routing_decision`。
- 第二层 validator 当前可以校验未来 LLM raw payload，并输出 validation issues。
- 第二层 `LLMIntentDecomposer` 当前已有 shell，能校验合法 backend payload、拒绝非法 payload，并在 backend 异常时 fallback 到 placeholder。
- 第二层 `VITALAI_INTENT_DECOMPOSER=llm` 当前只启用 shell；未配置真实 backend 时仍 fallback 到 placeholder。
- 第二层 workflow guard 已接入 `POST /vitalai/interactions` 的复合输入分支，当前只返回可审计候选，不直接执行领域 workflow。

### 下一阶段交付

- 继续维护 BERT hard-case guard 命中清单和误伤清单，并分析类别混淆原因，但没有真实语料时不继续人工堆样本。
- 后续新增样本优先来自真实表达：模糊表达、多意图、误触发、真实老人口语。
- 继续扩充第二层 workflow 守门策略的人工验收命令和复杂样本，但不立刻替换主 intent。
- 评估 `0.65` 置信度阈值是否合理，但不急着为表面准确率调低阈值。

### 验收标准

- `rule_based` 全量评估通过。
- BERT baseline / holdout 分开报告。
- 报告能看到 BERT 直接识别、fallback、clarification、decomposition 数量。
- 复合输入响应能看到 `error_details.decomposition_guard`，并且 route candidate 不会被自动执行。
- unknown / clarification 不能为了提高准确率被牺牲。

### 暂不做

- 不直接接入 LLM 深度拆分主链路；当前只做契约和占位。
- 不做 ASR。
- 不做个人化持续学习自动训练。
- 不把 LLM 输出直接作为训练真值。

## 模块 6：profile memory 长期记忆

### 模块职责

`profile_memory` 是当前最重要的真实业务纵切之一，负责用户长期偏好、习惯、画像信息的写入和查询。

### 当前状态

- 已具备 SQLite 持久化。
- 已具备写入 flow。
- 已具备只读 query / workflow / API。
- 可通过 `POST /vitalai/interactions` 自然语言或显式 event 路由到写读流程。
- 已支持按 `memory_key` 精确查询，作为当前阶段的轻量检索边界。

### 下一阶段交付

- 增加 profile snapshot 输出的人工可读性。
- 保持 key 查询为当前检索边界，暂不扩展模糊搜索。
- 后续再考虑 memory entry 的分类和更新时间策略。

### 验收标准

- 写入后可通过 API 读取。
- 空用户读取返回稳定空 snapshot。
- 按 key 查询可以返回单条命中或稳定空 snapshot。
- 多次写入同 key 时更新时间和覆盖策略明确。

### 暂不做

- 不立即做完整 profile graph。
- 不做复杂 memory retrieval / embedding search。
- 不做跨用户画像聚合。

## 模块 7：security / admin / observability

### 模块职责

这三个能力共同保证系统可控、可观测、可人工验收。

### 当前状态

- admin 控制面有最小 token。
- security 已参与 runtime signal。
- observability 已能记录事件摘要。
- README 中已有部分人工验收命令。

### 下一阶段交付

- 补充 admin token 的配置说明和禁用边界。
- 让关键人工验收命令保持在 README。
- 对高风险输入增加稳定错误响应，而不是框架级异常。

### 验收标准

- 未配置 token / 缺 token / 错 token / 正确 token 都有测试覆盖。
- 生产环境控制面默认不可用。
- 关键流程响应中能看到 runtime signal。

### 暂不做

- 不做完整用户登录系统。
- 不做 RBAC。
- 不做审计后台 UI。

## 模块 8：docs / testing / delivery

### 模块职责

让项目进度可被新会话和人工持续接上。

### 当前状态

- docs 根目录已完成第一轮治理。
- `STEP_*` 已归档。
- 当前真源文档已收敛。
- 默认测试入口为 `pytest tests -q`。

### 下一阶段交付

- 保持 `CURRENT_STATUS.md` 短、准、可执行。
- 保持 `NEXT_TASK.md` 只写近阶段 1 到 3 个方向。
- 让本计划文档成为阶段验收对照表。

### 验收标准

- 新会话能按 `DOCS_INDEX.md` 快速进入上下文。
- 每轮开发结束能说清楚完成了哪个模块、哪个阶段、怎么验收。
- 文档不再无限新增 STEP。

### 暂不做

- 不把 docs 写回流水账。
- 不把 docx 历史设计资产直接作为当前真源。
- 不为每个小修补新增计划文档。

## 推荐开发顺序

### P0：最近已收口

目标：把用户输入与意图识别打成稳定工程闭环。

顺序：

1. 建立 BERT 高置信误判清单。
2. 引入最小 `InputPreprocessor`。
3. 设计 `sub_intent / slots` 草案。
4. 继续观察 BERT direct / fallback / clarification 比例。
5. 完成 health / daily_life 最小历史持久化/只读查询纵切。

完成标志：

- 全量测试通过。
- baseline / holdout 分组评估稳定。
- README 有人工验收命令。
- `NEXT_TASK.md` 更新到下一模块。

### P1：下一个阶段

目标：收束现有真实领域读写闭环，并改善本地验收体验。

顺序：

1. 使用 `scripts/manual_smoke_typed_flow_history.py` 保持 profile_memory / health / daily_life / mental_care 四条读写闭环可本地快速验收。
2. health / daily_life / mental_care 只做极小人工验收增强，不扩到健康档案、提醒调度、任务状态机、多轮陪伴或复杂干预系统。
3. 有真实语料时再补 health / daily_life / mental_care 的困难输入样本。

完成标志：

- 四条读写链路可以被本地快速验收。
- 三条 typed 领域 flow 不再只是最小占位。

### P2：工程化增强阶段

目标：补足运行时、权限、持久化和交付边界。

顺序：

1. runtime snapshot 清理与迁移策略。
2. admin/control 开发生产边界文档和测试。
3. 更稳定的本地启动与手动验收脚本。

完成标志：

- 本地重启、读写、诊断、测试链路稳定。
- 控制面风险可控。

### P3：智能化增强阶段

目标：在已有后端基线稳定后，再引入更强理解能力。

候选能力：

- LLM 深度意图拆分。
- 多意图 decomposition schema。
- 用户状态注入。
- 多轮 session persistence。
- 更真实的持续学习数据收集。

进入条件：

- P0/P1 的用户输入、意图识别、profile memory、领域 flow 已稳定。
- holdout 足够困难，且 BERT 的 fallback 行为可解释。
- LLM 输出有严格 schema 校验、超时、fallback、审计。

## 人工验收总表

### 基础测试

```powershell
pytest tests -q
```

预期：

- 全部测试通过。
- `.pytest_cache` 权限 warning 不影响功能。

### typed flow history smoke

```powershell
python scripts\manual_smoke_typed_flow_history.py
```

预期：

- 顶层 `ok=true`。
- `flows.profile_memory.ok=true`，且 `memory_keys` 包含 `favorite_drink`。
- `flows.health.ok=true`，且 `recent_risk_levels` 包含 `high`。
- `flows.daily_life.ok=true`，且 `recent_needs` 包含 `meal_support`。
- `flows.mental_care.ok=true`，且 `recent_mood_signals` 包含 `calm`。
- 默认不会写入 `.runtime/profile_memory.sqlite3`、`.runtime/health.sqlite3`、`.runtime/daily_life.sqlite3`、`.runtime/mental_care.sqlite3`。

### 意图识别评估

```powershell
python scripts\evaluate_intents.py --recognizer rule_based --group-by-split
```

预期：

- 全量通过。
- 报告包含 `by_source / fallback / clarification`。

```powershell
C:\Users\Windows\miniconda3\python.exe scripts\evaluate_intents.py `
  --recognizer bert `
  --bert-model-path "D:\AI\Models\fine-tuned-bert-intent-vitalai-trained" `
  --bert-labels "health_alert,daily_life_checkin,mental_care_checkin,profile_memory_update,profile_memory_query,unknown" `
  --splits holdout `
  --group-by-split
```

预期：

- holdout 单独输出。
- 能看到 `bert` 与 `bert_low_confidence_fallback` 的比例。

### 用户交互 API

```powershell
$body = @{
  user_id = "elder-manual-003"
  channel = "manual"
  message = "我刚刚摔倒了，现在有点头晕"
  trace_id = "trace-manual-interaction-intent-health"
} | ConvertTo-Json
$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)

Invoke-RestMethod `
  -Method Post `
  http://127.0.0.1:8000/vitalai/interactions `
  -ContentType "application/json; charset=utf-8" `
  -Body $bytes
```

预期：

- `accepted=true`
- `routed_event_type=HEALTH_ALERT`
- `intent.primary_intent=health_alert`

### profile memory 读写

先写入，再读取。

预期：

- 写入返回 `profile_memory_updated`
- 读取返回 `profile_snapshot.memory_count > 0`

### health alert 历史读写

先执行 `POST /vitalai/flows/health-alert`，再执行 `GET /vitalai/flows/health-alerts/{user_id}`。

预期：

- 写入响应包含 `health_alert_entry` 与 `health_alert_snapshot`。
- 读取返回 `health_alert_snapshot.alert_count > 0`。
- `recent_risk_levels` 中能看到刚写入的 `risk_level`。

### daily_life 历史读写

先执行 `POST /vitalai/flows/daily-life-checkin`，再执行 `GET /vitalai/flows/daily-life-checkins/{user_id}`。

预期：

- 写入响应包含 `checkin_entry` 与 `daily_life_snapshot`。
- 读取返回 `daily_life_snapshot.checkin_count > 0`。
- `recent_needs` 中能看到刚写入的 `need`。

### mental_care 历史读写

先执行 `POST /vitalai/flows/mental-care-checkin`，再执行 `GET /vitalai/flows/mental-care-checkins/{user_id}`。

预期：

- 写入响应包含 `mental_care_entry` 与 `mental_care_snapshot`。
- 读取返回 `mental_care_snapshot.checkin_count > 0`。
- `recent_mood_signals` 中能看到刚写入的 `mood_signal`。

### runtime snapshot 持久化

设置：

```powershell
$env:VITALAI_RUNTIME_SNAPSHOT_STORE_PATH=".runtime\runtime_snapshots.json"
```

预期：

- diagnostics 调用后创建本地 snapshot 文件。
- 重启服务后 snapshot version 能延续。

## 当前不建议做的事

- 不做微服务拆分。
- 不做完整前端 App。
- 不接入 LLM 主链路。
- 不做 ASR。
- 不做自动持续学习训练。
- 不为了未来规模引入重型工作流引擎。
- 不新增大量业务域。

## 如何跟随进度

每次开发结束后，用下面四个问题对照：

1. 这次推进属于哪个模块？
2. 是否符合当前阶段 P0/P1/P2/P3？
3. 交付物是否有自动测试或人工验收命令？
4. `CURRENT_STATUS.md` 和 `NEXT_TASK.md` 是否需要更新？

如果这四个问题答不上来，就说明这次开发还没有形成可交接成果。
