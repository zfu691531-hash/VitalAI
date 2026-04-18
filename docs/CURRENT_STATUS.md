# Current Status

Date: 2026-04-16

## Update 2026-04-18

- `tool-agent` is no longer preview-only. It now supports one real read-only internal tool: `user_overview_lookup`.
- The tool agent still keeps preview fallback for unsupported tools, so we gain real execution without opening a broad external-tool surface.
- `scripts/manual_smoke_agents_http.py` now verifies this real execution path instead of only a simulated tool preview.

## Update 2026-04-17

- `health alert` read-side now supports `status_filter`, so we can inspect one user's alerts by lifecycle state without changing the write path.
- Added single-alert detail read path: `GET /vitalai/flows/health-alerts/{user_id}/{alert_id}`.
- This keeps the current direction intact: stronger observability and operability for `health`, without adding new status values, notification systems, or scheduling.
- `daily_life` now follows the same lightweight read-side pattern: entries expose `checkin_id`, history supports `urgency_filter`, and one check-in can be read via `GET /vitalai/flows/daily-life-checkins/{user_id}/{checkin_id}`.
- `mental_care` now follows the same lightweight read-side pattern too: entries expose `checkin_id`, history supports `mood_filter`, and one check-in can be read via `GET /vitalai/flows/mental-care-checkins/{user_id}/{checkin_id}`.
- Added a lightweight consolidated read entry: `GET /vitalai/users/{user_id}/overview` merges `profile_memory`, `health`, `daily_life`, and `mental_care` snapshots without introducing new storage or business rules.
- Added `scripts/manual_smoke_user_overview_http.py` so we can seed the four existing flows and verify the overview contract against a running server.
- The overview now also exposes a lightweight `recent_activity` timeline and `latest_activity_at`, making the cross-domain read more useful for manual triage and frontend integration without adding new workflow logic.
- The overview now also exposes read-only `attention_items` and `attention_summary`, so unresolved health alerts and similar signals can surface in one place without introducing any automatic escalation behavior.
- The web layer is no longer empty: the app root `/` now serves a small read-only overview console for manual checks, built directly on top of the existing overview API rather than a separate frontend stack.
- Added a lightweight agent registry API: `GET /vitalai/agents` and `GET /vitalai/agents/{agent_id}` now expose the current framework-ready agents across domain, reporting, and platform layers.
- Added dry-run feasibility APIs: `POST /vitalai/agents/{agent_id}/dry-run` can now preview `health-domain-agent`, `daily-life-domain-agent`, `mental-care-domain-agent`, `profile-memory-domain-agent`, `intelligent-reporting-agent`, `tool-agent`, and `privacy-guardian-agent`.
- Tool Agent, Intelligent Reporting Agent, and Privacy Guardian Agent are now real code scaffolds wired to existing platform pieces instead of design-only placeholders.
- Added `scripts/manual_smoke_agents_http.py` so one running server can be checked for agent registry, dry-run, and reporting-preview viability through HTTP.

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
- `FileSnapshotStore` 已支持可选历史版本保留上限，可通过 `VITALAI_RUNTIME_SNAPSHOT_MAX_VERSIONS_PER_ID` 只保留单个 `snapshot_id` 最近 N 个版本，并在加载旧文件时做收敛清理

### 业务流与领域

- `health`、`daily_life`、`mental_care` 已有真实 typed flow
- `reporting` 已接入轻量安全审查
- `health` 已新增最小历史持久化纵切：alert 写入后会形成 SQLite 历史记录，并可通过只读 query/API 读取最近健康预警历史
- `health` 历史纵切包括 `HealthAlertEntry`、`HealthAlertSnapshot`、SQLite record 与 `HealthAlertRepository`
- `HealthAlertTriageService` 支持可选历史仓储，flow 执行后会生成 `health_alert_entry` 与 `health_alert_snapshot`
- `health` 只读查询链路已走通：`HealthAlertHistoryQuery` -> use case -> workflow -> `GET /vitalai/flows/health-alerts/{user_id}`
- `health` 已补最小状态流：新告警默认 `raised`，支持单条记录 `acknowledged -> resolved` 状态迁移；查询 entries 现已返回 `alert_id / status / created_at / updated_at`
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
- `POST /vitalai/interactions` 现已不再直接硬连各领域 workflow，而是先经过显式的 domain-agent handoff：`health-domain-agent`、`daily-life-domain-agent`、`mental-care-domain-agent`、`profile-memory-domain-agent` 已真实接到主链路
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
- 第二层已接入通用 OpenAI-compatible backend，并新增可显式复用 `Base.Ai` 千问封装的 `base_qwen` provider；可通过 `VITALAI_INTENT_DECOMPOSER_LLM_PROVIDER`、`VITALAI_INTENT_DECOMPOSER_LLM_MODEL`、`VITALAI_INTENT_DECOMPOSER_LLM_API_KEY`、`VITALAI_INTENT_DECOMPOSER_LLM_BASE_URL`、`VITALAI_INTENT_DECOMPOSER_LLM_TEMPERATURE`、`VITALAI_INTENT_DECOMPOSER_LLM_TIMEOUT_SECONDS` 配置
- 二层默认超时已改成 provider-aware：`openai_compatible` 默认 `5s`，`base_qwen` 在未显式配置时默认 `30s`；真实验收已确认 `base_qwen` 在 `30s` 下可返回 `llm_schema_validated`，且仍受非执行型 guard 约束
- 已修正 `Base.Client` 的可选依赖耦合：客户端入口改为懒加载，`Base.Ai.llms.qwenLlm` 不再因为本地未安装 `minio` 而整体不可导入，`base_qwen` 现在可被二层主链路与采样脚本实际复用
- 第二层 decomposer 已接入 assembly 配置边界：`VITALAI_INTENT_DECOMPOSER=placeholder|llm`，默认 `placeholder`；`llm` 模式在配置真实 backend 前仍会安全回退，已配置时会产出 schema-validated 的结构化拆分结果，但仍不直接执行领域 workflow
- 已新增只读状态接口 `GET /vitalai/flows/intent-decomposer-status/{role}`，可直接查看当前二层是 `placeholder` 还是 `llm`、provider 是谁、配置是否齐全，以及它仍处于 `non_executing_second_layer` 安全边界
- 第二层 workflow 守门逻辑已接入：`RunIntentDecompositionRoutingGuardUseCase` 会把合法拆解输出转换为非执行型 `routing_candidate` / `clarification_candidate`，高风险、低置信、缺少 primary task 或 route guard 不通过时保持非 accepted
- `decomposition_needed` 响应已增加 `error_details.decomposition_guard`，可人工查看 `status`、`candidate_ready`、`routing_candidate`、`clarification_question` 与 `blocked_reasons`
- 最小 `InputPreprocessor` 已接入 application workflow：`RunUserInputPreprocessingUseCase` 会在 intent recognition 前执行 trim、连续空白收敛、原始输入保留、空消息保护和基础异常标记
- `POST /vitalai/interactions` 响应已增加 `preprocessing` 字段，可人工查看 `original_message`、`normalized_message`、`changed` 与 `flags`
- `POST /vitalai/interactions` 响应现已增加 `agent_handoffs`，可直接看到一次交互从 ingress agent 到具体 domain agent 的移交流程，不再只是概念上的多 Agent 分层
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
- 已新增 `scripts/manual_smoke_http_api.py`，可在后端服务已启动时直接验收 `GET /vitalai/health`、`POST /vitalai/flows/profile-memory`、`GET /vitalai/flows/profile-memory/{user_id}` 和 `POST /vitalai/interactions`，默认基线地址为 `http://127.0.0.1:8124`
- 已新增 `scripts/manual_smoke_typed_flow_http.py`，可在后端服务已启动时一次性验收 `profile_memory / health / daily_life / mental_care` 四条 typed flow 的 HTTP 闭环；其中 `health` 现已覆盖 `raised -> acknowledged -> resolved`
- 已新增 `scripts/manual_smoke_interactions_http.py`，可在后端服务已启动时一次性验收自然语言 `interactions` 入口的健康路由、记忆路由、澄清、二层拆分拦截与统一无效请求契约
- 已新增 `scripts/dev_start_and_smoke.py`，一键启动后端、等待健康检查、可选执行 smoke、然后自动停止；支持 `--smoke`、`--keep-running`、`--startup-timeout`、`--smoke-output` 等参数；测试覆盖参数解析、健康检查成功/超时、smoke 调用、失败清理
- 已新增 `docs/API_SMOKE_CHECKLIST.md`，把“启动后端 -> 最小 HTTP smoke -> typed flow smoke -> 自然语言 interactions smoke -> 手工请求排查”的推荐顺序收敛成一页，便于新会话、前端联调和人工验收直接照着跑
- 最近 typed flow history smoke/API/assembly/scheduler targeted tests 已通过：`71 passed`
- 最近全量测试已通过：`220 passed`
- 最近 `git diff --check` 无格式错误；仅有 Windows LF/CRLF 提示
- `profile_memory` 已覆盖写入后读取、空用户读取、按 `memory_key` 查询、可读性派生字段、HTTP route 读写验收测试
- 用户交互入口已覆盖 profile memory 写读、health alert、unsupported event、缺失字段、非法 context、输入预处理、无 event_type 自然语言识别、无法识别时澄清响应、复合意图 `decomposition_needed` 响应、第二层拆分 placeholder payload、第二层 routing guard、env-wired OpenAI-compatible backend 澄清路径、BERT adapter fallback、离线 intent evaluation 测试路径
- 已新增离线第二层 hard-case 评测基线：`data/intent_eval/second_layer_hard_cases.jsonl`、`scripts/intent_eval/evaluate_second_layer_hard_cases.py`、`tests/intent_eval/test_second_layer_hard_case_eval.py`
- 第二层 hard-case 评测当前覆盖 22 条样本；离线评测结果为 `22 total / 14 valid / 8 invalid / expectation_failures=0`
- 已新增第二层原始响应快照回放基线：`data/intent_eval/second_layer_response_snapshots.jsonl`、`tests/intent_eval/test_second_layer_response_snapshot_eval.py`
- 原始响应快照回放当前覆盖 5 条样本；离线回放结果为 `5 total / 3 valid / 2 invalid / parse_failures=1 / expectation_failures=0`
- 已新增真实响应采样脚手架：`data/intent_eval/second_layer_capture_cases.jsonl`、`scripts/intent_eval/capture_second_layer_response_snapshots.py`、`tests/intent_eval/test_capture_second_layer_response_snapshots.py`
- 采样脚手架当前会基于第一层 intent recognition 自动构造第二层 prompt，并把 `raw_response_text`、解析结果、validator 结果和 guard 结果写入待审核 JSONL
- 首批真实采样模板当前已扩到 16 条，额外覆盖安全 memory/daily 候选、英文输入、脏响应诱发场景与拒绝/澄清边界，便于第一轮真实 GLM 验收直接使用
- 采样脚本现已支持按 `--id`、`--category`、`--limit` 分批执行，并可用 `--list-cases` 先预览本次会跑哪些模板
- 采样脚本现已支持 `--skip-existing`，便于分批补采时跳过已经写进当前输出 JSONL 的 case id，减少重复快照清理成本
- 采样脚本现已和主链路对齐 provider 选择，支持 `VITALAI_INTENT_DECOMPOSER_LLM_PROVIDER=openai_compatible|base_qwen`，可直接复用 `Base.Ai` 千问封装
- 采样脚本现已按条记录 `request_error` 而不是整批失败；首轮 `base_qwen` 真实采样已把 2 条 `profile_memory` 样本落到 review queue，中断原因确认为阿里侧 `Arrearage` 账务拦截，而不是本地代码或 schema 问题
- 首批 `base_qwen` 正式采样 batch1 已完成：4 条样本中 4/4 解析与校验通过，2 条安全 `profile_memory` 样本已提升入正式 `second_layer_response_snapshots.jsonl` 基线，`daily_life` 低置信与 `health+medication` 风险样本继续保留在 review queue
- `base_qwen` 正式采样 batch2 已完成并复核 bulk approval 边界：`capture_015_clarification_family_schedule` 已提升入正式基线；`capture_002_health_daily` 因 `dizziness` 风险标记改为必须人工审核，`capture_005_daily_mental` 因 `route_sequence` 保留人工审核，`capture_001_medication_emotion` 继续维持 `hold_for_human_review`
- 已补跑一轮 `base_qwen` 风险混合批次真实快照：`capture_001_medication_emotion`、`capture_002_health_daily`、`capture_005_daily_mental`、`capture_016_medication_aftereffect` 共 `4/4` 成功返回、`4/4` schema 校验通过、`0` parse/request error；review queue 分布为 `approve_candidate=3`、`manual_review_required=1`，其中 `capture_016_medication_aftereffect` 继续稳定落在 `hold_for_human_review`
- 第二层正式原始响应快照基线当前为 8 条样本，离线回放结果为 `8 total / 6 valid / 2 invalid / parse_failures=1 / expectation_failures=0`；baseline audit 当前显示 `approved_for_baseline=3`
- 已新增审核队列脚手架：`scripts/intent_eval/build_second_layer_snapshot_review_queue.py`、`tests/intent_eval/test_build_second_layer_snapshot_review_queue.py`
- 审核队列当前会把采样结果转换为 evaluator 兼容的 review queue，并自动填充 `expected` 建议值、`review_status=pending_human_review`、`review_recommendation` 与来源元数据
- `scripts/intent_eval/review_policy.py` 已抽离 recommendation 规则，避免审核标准继续散落在脚本内部
- 已新增审核队列管理脚手架：`scripts/intent_eval/manage_second_layer_snapshot_review_queue.py`、`tests/intent_eval/test_manage_second_layer_snapshot_review_queue.py`
- 审核队列管理脚本当前支持 `summary / triage-report / list / show / set-status / bulk-set-status`，可按 `review_status/category/recommendation/bulk_approval/validation/guard_status/parse_error` 过滤待审项，附带 `raw_response_text` 做人工判断，并把目标样本逐条或批量标记为 `approved_for_baseline`
- 当前 bulk approval 规则已单独固化为三类：`eligible_for_bulk_approval`、`requires_manual_approval`、`not_applicable_for_bulk_approval`，用于收紧真正允许批量入 baseline 的边界
- 当前 recommendation 规则已固化为三类：`approve_candidate`、`manual_review_required`、`baseline_negative_candidate`，可用于第一批真实 GLM 快照的优先级筛选
- 已新增正式入库脚手架：`scripts/intent_eval/promote_second_layer_snapshot_review_queue.py`、`tests/intent_eval/test_promote_second_layer_snapshot_review_queue.py`
- 正式入库脚手架当前只提升 `review_status=approved_for_baseline` 的项，并会合并写回正式回放数据集，同时保留 recommendation 与 bulk approval provenance
- 已新增 baseline 审计脚手架：`scripts/intent_eval/audit_second_layer_snapshot_baseline.py`、`tests/intent_eval/test_audit_second_layer_snapshot_baseline.py`
- baseline 审计脚本会统计 `expected` 分布、review provenance、bulk approval provenance、重复 `id`、缺失 `review_metadata` 与缺失 `source_capture`
- runtime snapshot 持久化已覆盖跨 store 实例读取和 assembly 重建后历史延续测试路径

## 当前还没有达到的状态

当前项目仍然不是生产就绪后端，主要差距在这里：

- runtime snapshot 已有本地开发可用的文件持久化方案，但还不是生产级分布式/高可用持久化方案
- admin/control 目前只有最小 token 基线，还不是完整用户/角色权限体系
- 用户交互入口仍是 backend-only，不是完整多轮对话或产品交互系统
- BERT intent 当前已有可运行 bootstrap 模型，但它是基于当前 180 条工程基线样本训练的快速接入模型，主要用于验证 adapter、label 映射、fallback 与 API 启用链路；当前 108 条 holdout 虽已通过 hard-case guard 达到 `108/108`，但这不代表模型本体已具备生产泛化能力
- 第二层意图拆分当前已有契约、placeholder、JSON schema 校验、OpenAI-compatible backend、assembly 配置开关和非执行型 workflow routing guard；当前仍不会从拆分结果直接执行领域 workflow
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
