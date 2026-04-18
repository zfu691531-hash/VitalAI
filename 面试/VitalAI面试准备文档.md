# VitalAI · AI 老人陪护后端

面试准备文档

AI 应用开发工程师  ·  应届  ·  2024.09 - 2026.01


## 一、项目整体介绍

这个项目叫 VitalAI，是一个面向老人陪护场景的 AI 后端系统。核心解决的问题是：老人独居时，健康异常、生活异常、情绪异常往往没人及时发现，即使发现了也没有系统化的跟踪闭环——发现一个问题记一笔，然后就没了，没有人去确认有没有处理、什么时候解决的。系统把老人分散在各个渠道的信号汇聚起来，从发现风险、记录状态、确认响应到跟踪归档，打通一条完整的闭环链路。

系统架构一句话说清楚
四条业务域串成一条主线：Health Alert 是唯一有状态流的域，新预警默认 raised，支持按单条记录 acknowledge 和 resolve，从"写一条记录"变成"跟踪一条预警的完整生命周期"；Daily Life Check-in 是 append-only 时间线，记录每天需要什么帮助；Mental Care Check-in 结构对称但 crisis 信号自动提升优先级为 CRITICAL、锁定 exclusive 资源；Profile Memory 是唯一用 upsert 语义的域，按 (user_id, memory_key) 更新老人关键信息。四条域通过双层意图识别路由——第一层 BERT 分类，第二层 LLM 拆分复合意图，但拆分结果永远不自动执行，只产出 routing_candidate 供人工确认。平台层提供安全守卫、可观测性、运行时快照、故障转移等跨域基础设施。

技术栈
Python · FastAPI · SQLite · Pydantic V2 · BERT (序列分类) · LLM API (OpenAI Compatible / Qwen) · NetworkX · pytest


## 二、各模块面试应答


### 健康预警（Health Alert）

开场定位
Health Alert 是整个系统里第一条具备完整状态流的业务线，也是当前唯一一个从"写入+读取"推进到"写入→状态流转→查询过滤→单条详情"的域。它解决的核心问题不是"记下来"，而是"跟踪下去"——一条预警从发现到确认到解决，状态每一步都可查询、可校验、可审计。

核心流程四步
信号写入：外部事件通过 API 写入一条预警记录，默认 status=raised，alert_id 由 SQLite AUTOINCREMENT 生成（不是 UUID4——这是和最初设计的偏差，后面追问会展开），message_id 做 UNIQUE 约束保证幂等，created_at 和 updated_at 在写入时同为 now(UTC)，之后 created_at 不变、updated_at 在每次状态变更时更新。

状态流转：三态线性状态机 raised → acknowledged → resolved。转换规则定义在 _HEALTH_ALERT_STATUS_TRANSITIONS 字典里：raised 可转到 acknowledged 或 resolved，acknowledged 只能转到 resolved，resolved 是终态不允许任何转换。非法转换抛 HealthAlertStatusTransitionError，alert_id 不存在或与 user_id 不匹配抛 HealthAlertNotFoundError。

确认/解决接口：PATCH /vitalai/flows/health-alerts/{user_id}/{alert_id}/acknowledge 和 resolve，路由同时要求 user_id 和 alert_id——alert_id 虽然全局唯一，但 user_id 在路径中表达资源归属，后续做权限校验时直接用路径参数验证归属关系，不需要额外查库。

查询增强：GET /vitalai/flows/health-alerts/{user_id} 支持 status_filter 过滤和 limit 分页（归一化到 1-100 范围），GET /vitalai/flows/health-alerts/{user_id}/{alert_id} 查单条详情。默认按 id DESC 排序——最新的在最前面。

高频追问
Q：alert_id 为什么用自增整数而不是最初设计的 UUID4？
A：实际落地时 SQLite 的 AUTOINCREMENT 对单表查询和索引效率更高，而且 alert_id 只在系统内部使用，不暴露给前端做全局 ID 猜测的场景。路由里同时有 user_id，即使 ID 可预测也必须匹配用户才能查到数据。如果未来需要分布式生成或跨系统唯一，可以加一个 uuid 字段做外部标识，alert_id 仍然是内部主键。

Q：为什么状态机不让直接改数据库字段？
A：直接改有三个问题：可以任意跳转状态跳过合法校验（比如从 resolved 回到 raised）；没有日志事后无法追溯谁在什么时候改了什么；状态变更时需要触发副作用（更新 updated_at、校验 user_id 归属），直接改字段触发不了。transition_alert_status 方法把合法性校验、归属校验、副作用触发统一在一个地方处理，是标准的防腐设计。

Q：_ensure_schema 做了什么？为什么需要兼容旧表？
A：health_alert_records 表最初没有 status 和 updated_at 字段，后来做状态纵切时加了这两个列。_ensure_schema 在每次绑定时检查 PRAGMA table_info，如果旧表缺列就用 ALTER TABLE 补上——status 默认 raised，updated_at 从 created_at 复制。这样做是因为开发过程中 SQLite 文件已经存在，不能删了重建，必须兼容已有数据。

Q：为什么 limit 归一化到 1-100？
A：防止客户端传 limit=0 或 limit=999999 导致空结果或全表扫描。1 是最小有意义值，100 是单次查询的合理上限——一个老人不太可能有超过 100 条未处理的预警需要一次看全。如果真需要看更多，应该分页。

一句话总结：Health Alert 的核心价值是把"发现异常"从一次性事件变成可跟踪的状态流——每条预警都有 alert_id、有状态、有归属、有时间戳，不会写了就消失。


### 日常签到（Daily Life Check-in）

开场定位
Daily Life Check-in 记录老人每天的生活状态——今天需要什么帮助、紧迫程度如何。它和 Health Alert 的本质区别是 append-only vs 状态流：日常签到没有"已处理"的概念，老人每天需要用药提醒不会因为昨天提醒过了今天就消失，所以不适合用状态机。

核心流程三步
签到写入：外部事件通过 API 写入一条 check-in 记录，包含 user_id、need（需求描述）、urgency（紧迫度）、source_agent、trace_id、message_id。幂等写入，同一条 message_id 不会产生重复记录。

Service 层翻译：DailyLifeCheckInSupportService 把 EventSummary 翻译成三类平台对象——decision_message（带优先级的决策消息）、feedback_event（反馈事件，让可观测性知道这次处理闭环了）、support_intent（仲裁可消费的意图声明）。和 Health Alert 的 triage 方法结构完全对称，输出三件套。

历史查询：按 user_id 查询，支持 limit，默认 20 条。append-only 模式，不需要状态过滤。

高频追问
Q：为什么不也做成状态流？
A：因为"日常需要"和"异常预警"的生命周期不同。一条健康预警的生命周期是"发现→确认→解决"，有明确的终态。而"老人需要用药提醒"这个需求是持续性的，不会因为今天提醒过了明天就不需要。状态流适合一次性的问题，append-only 时间线适合持续性的记录。

Q：Daily Life 和 Mental Care 的 urgency 判定有什么区别？
A：Daily Life 的优先级来自 urgency 字段本身——urgency 高就高，没有额外的业务规则。Mental Care 不同：当 mood_signal 是 distressed 或 crisis 时，消息优先级自动提升为 CRITICAL、资源锁定为 exclusive。这个判定在 service 层硬编码，不是配置化的——因为 crisis 信号的优先级提升是安全底线，不应该被配置覆盖。

一句话总结：Daily Life 是 append-only 时间线，记录"每天需要什么"，和 Health Alert 的状态流互补——一个关注异常闭环，一个关注日常持续。


### 精神关怀签到（Mental Care Check-in）

开场定位
Mental Care 和 Daily Life 结构对称，但有一个关键差异：危机信号的优先级自动提升。当 mood_signal 是 distressed（痛苦）或 crisis（危机）时，消息优先级直接设为 CRITICAL、资源需求设为 exclusive。这不是配置化的，是硬编码在 service 层的安全底线。

核心流程三步
签到写入：和 Daily Life 对称，多了 mood_signal 和 support_need 两个字段。

优先级判定：service 层检查 mood_signal——如果是 distressed 或 crisis，decision_message 的 priority 设为 CRITICAL，escalation_intent 的 goal_weight 设为 1.0、flexibility 设为 FIXED、resources_needed 的 exclusive 设为 True。如果是其他情绪信号，走正常的 urgency 逻辑。

历史查询：和 Daily Life 完全对称。

高频追问
Q：crisis 信号为什么要硬编码优先级提升，不放在配置里？
A：因为这是安全底线，不是业务偏好。如果放在配置里，管理员可能误改或关闭，导致危机信号被当作普通签到处理。老人说"我不想活了"和"我今天有点无聊"，处理优先级必须有本质区别，这个区别不应该可配置。类似的原则在赵雅坤的学脉项目里也有——心理量表评分极低时实时触发预警，不等月末汇总。

Q：Mental Care 的 crisis 和 Health Alert 的 critical 怎么协调优先级？
A：当前两个域各自独立判定，还没到需要全局仲裁的阶段。platform 层已经预留了 IntentDeclaration（仲裁意图声明）和 DecisionCore（事件路由），但现阶段信号量不够大，过早做全局仲裁增加复杂度却没有收益。等到真实场景中两个域的 CRITICAL 信号真的冲突了，再基于数据设计仲裁策略。

Q：为什么不记录 acknowledged_at / resolved_at 这样的情绪状态时间戳？
A：和 Health Alert 的理由一样——当前 check-in 是 append-only，没有状态流转。如果未来 Mental Care 也加状态流（比如 crisis 信号需要确认已介入），会复用 Health Alert 的模式：created_at + updated_at，不加 per-state 时间戳。精确状态时间走事件日志。

一句话总结：Mental Care 的特殊之处在于 crisis 信号的硬编码优先级提升——不是所有签到都平等，痛苦和危机必须优先处理，这是安全底线不是业务偏好。


### 个人记忆（Profile Memory）

开场定位
Profile Memory 是四个域里唯一使用 upsert 语义的。其他三个域都是 append-only——写一条就多一条。Profile Memory 不同：按 (user_id, memory_key) 做 upsert，key 相同则更新 value，key 不存在则新建。它存储老人的关键信息（用药习惯、饮食偏好、行动能力），供后续交互时直接引用。

核心流程两步
记忆写入/更新：POST /vitalai/flows/profile-memory，传入 user_id、memory_key、memory_value。repository 层先查 (user_id, memory_key) 是否存在，存在则更新 memory_value 和 updated_at，不存在则新建。

记忆查询：GET /vitalai/flows/profile-memory/{user_id} 返回完整快照，支持 memory_key 参数过滤特定记忆。Snapshot 有派生属性 memory_count、memory_keys、readable_summary。

高频追问
Q：为什么记忆不也做 append-only 保留历史版本？
A：记忆的用途是"查询当前状态"——回答"这个老人现在吃什么药"，不需要回答"他三个月前吃什么药"。如果需要历史版本，应该走审计日志，不应该让记忆本身承担版本管理。职责单一：记忆负责"当前是什么"，审计负责"过去是什么"。

Q：Profile Memory 的 upsert 和其他域的 append-only，repository 实现有什么区别？
A：其他域的 add_* 方法先查 message_id 是否存在，存在就返回已有记录，不重复写——幂等但不去更新。Profile Memory 的 remember 方法先查 (user_id, memory_key)，存在就 update memory_value 和 updated_at——不是幂等的，同一个 key 写两次会覆盖。这是语义差异决定的：重复的健康预警不应该覆盖之前的（两次预警是两次不同的事件），重复的记忆写入应该覆盖（老人的用药方案变了，新值覆盖旧值）。

Q：memory_key 是预定义的还是自由填的？
A：当前是自由的，调用方自己定义 key。这意味着可能出现"medication"和"用药"两个 key 指向同一个概念。这是已知的技术债，但当前优先级是让记忆功能能用，不是约束 key 命名规范。未来可以加一个 key 别名映射表，或在写入时做归一化。

一句话总结：Profile Memory 和其他三个域的本质区别是 upsert vs append-only——记忆会被覆盖更新，因为它的用途是"查当前状态"，不是"留历史记录"。


### 双层意图识别

开场定位
意图识别是用户自然语言输入和业务域之间的桥梁。两层设计的原因：第一层解决"用户想做什么"（分类到具体业务域），第二层解决"用户一句话里包含多个意图怎么办"（拆分和仲裁）。两层不是替代关系，第一层处理绝大多数简单意图，只有检测到复合意图时才进第二层。

第一层：意图识别
两种模式：
- 规则识别器（RuleBasedIntentRecognizer）：关键词匹配，零延迟，作为 baseline 和 fallback。当前全量 288/288 全对。
- BERT 识别器（BertIntentRecognizer）：序列分类模型，6 类意图（health_alert / daily_life_checkin / mental_care_checkin / profile_memory_update / profile_memory_query / unknown），置信度低于 0.65 自动回退到规则识别。baseline 180/180，holdout 108/108。
- Hard-case guard：对用药后不适、长期提醒、记忆写入/查询、英文提醒等高混淆场景做可解释兜底——这些场景 BERT 容易分错，规则识别器用硬编码关键词覆盖。
- 复合意图检测：needs_decomposition_detector 检测到复合/多任务表达时，标记 requires_decomposition=True。

第二层：意图拆分
当第一层检测到复合意图时，进入第二层：
- Placeholder 拆分器（默认）：保留第一层 hints，产出 IntentDecompositionResult 但 ready_for_routing=False、routing_decision=hold_for_second_layer_decomposition。不路由，不执行。
- LLM 拆分器：用 OpenAI Compatible 或 Base.Ai 千问后端，把复合意图拆成 primary_task + secondary_tasks（最多 5 个）+ risk_flags（最多 8 个）。LLM 输出的 JSON 必须通过本地 schema validator 校验——包含跨字段校验，比如 route_primary 需要 primary_task、ask_clarification 需要 clarification_question。LLM 输出超时 5 秒自动 fallback 到 placeholder。
- JSON 解析容错：先尝试 json.loads，失败后找第一个 { 和最后一个 } 之间提取再解析——应对 LLM 输出带 markdown code fences 或多余文字。

安全守门（关键设计）
拆分结果永远不会直接执行领域 workflow。必须经过 guard_intent_decomposition_routing 校验：
- ask_clarification → 需要 clarification_question，否则 hold
- reject → 直接拒绝
- route_primary / route_sequence → 需要 ready_for_routing=True + primary_task + confidence >= 0.70 + 无高风险标记（severity=high/critical 的 risk_flag 会阻止路由，medication_signal 类型的风险标记无论 severity 都阻止路由）
- 通过校验后产出 IntentDecompositionRoutingCandidate，但仍然是"非执行态"——只有 candidate_ready=True，没有后续自动执行。

高频追问
Q：为什么不用一个大模型直接做意图识别 + 拆分？
A：延迟和成本。第一层 BERT 推理 10ms 级别，绝大多数简单意图在这里就路由完成。只有复合意图才进第二层调 LLM，延迟 500ms-2s。如果所有请求都交给 LLM，平均延迟从 10ms 涨到 1s+，成本从几乎为零涨到每次几厘钱。而且 LLM 不确定性更高——temperature=0 也不能保证完全确定性的分类结果，BERT 序列分类在 6 类场景下更稳定。

Q：0.65 和 0.70 这两个阈值怎么定的？
A：经验值。0.65 是第一层 BERT 的回退阈值——在 holdout 集上测试，0.65 以下容易分错类，0.65 以上准确率可接受。0.70 是第二层 routing guard 的最低置信度——低于 0.70 意味着拆分结果不确定，不应该产出 routing_candidate。两个阈值都存配置，但目前是硬编码常量，未来可以从配置文件或环境变量读取。

Q：为什么 medication_signal 无论 severity 都阻止路由？
A：因为药物相关的操作风险太高。老人说"我刚吃了降压药头晕"——如果系统自动路由到 daily_life_checkin（记录为"头晕"），就漏掉了药物不良反应这个关键信号。medication_signal 一旦出现，必须人工确认后才能路由，不管 confidence 多高。这是 _ALWAYS_REVIEW_RISK_KINDS 里定义的，和 safety_or_urgent_signal（胸口痛、摔倒、煤气）不同——后者只在 severity=high/critical 时阻止，因为低严重度的安全信号可能是误报。

Q：LLM 输出的 schema 校验做了什么？
A：三层校验。第一层是类型校验——status 必须是 enum 值、confidence 必须是 0-1 的数字、priority 必须是 0-100 的整数。第二层是跨字段校验——ready_for_routing=True 必须有 primary_task、route_primary/route_sequence 必须有 primary_task、ask_clarification 必须有 clarification_question。第三层是容量校验——secondary_tasks 最多 5 个、risk_flags 最多 8 个。任何一个校验失败，整个结果标记为 invalid，fallback 到 placeholder。

一句话总结：双层意图识别的核心原则是"宁可多问一句，不可错做一步"——第二层拆分结果的 routing 是人工确认的候选，不是自动执行的指令；药物和安全信号一旦出现，必须人工介入。


### 平台层基础设施

开场定位
平台层是跨域的公共机制，不是业务逻辑。它解决的问题不是"做什么"，而是"怎么做才安全、可观测、可恢复"。业务域只需要关心自己的领域逻辑，安全、审计、容灾这些横切关注点由平台层统一处理。

关键组件四步
安全守卫（SensitiveDataGuard）：正则匹配邮箱、电话、token 等敏感模式，递归遍历 payload 字典进行脱敏。三级动作：ALLOW（放行）、REDACT（脱敏后放行）、BLOCK（拒绝）。当前默认规则覆盖常见 PII 模式，扩展时只加正则不改框架。

可观测性采集（ObservabilityCollector）：记录六类事件——EVENT_SUMMARY（领域处理摘要）、INTERRUPT_SIGNAL（中断信号）、RUNTIME_SNAPSHOT（运行时快照）、FAILOVER_TRANSITION（故障转移切换）、SECURITY_REVIEW（安全审查）、POLICY_SNAPSHOT（策略快照）。纯记录不消费，后续接 ELK 或 Grafana 只需加一个 consumer。

运行时快照：内存版 SnapshotStore（纯 dict，支持 snapshot_id + version 多版本）+ 文件持久化版 FileSnapshotStore（JSON 文件，启动时加载历史，max_versions_per_snapshot_id 控制版本上限，损坏文件自动备份为 .corrupt.{timestamp}.json）。默认快照捕获策略：CRITICAL 级别的 HEALTH_ALERT 和高紧迫度 DAILY_LIFE_CHECKIN 自动触发快照，其他事件不触发。可通过 VITALAI_RUNTIME_SNAPSHOT_STORE_PATH 配置存储路径。

故障转移（FailoverCoordinator）：primary/shadow 双节点模型，基于 InterruptSignal 的 TAKEOVER 动作和 snapshot_reference 判断是否切换。切换后从快照恢复状态。当前是单进程模拟，真实多进程部署时需要加进程间通信。

高频追问
Q：为什么用 SQLite 而不是 MySQL？
A：当前阶段 SQLite 是正确的选择。四个域各自独立一个 SQLite 文件——health.sqlite3、daily_life.sqlite3、mental_care.sqlite3、profile_memory.sqlite3——零运维成本，开发测试极快，数据就是本地文件可以拷贝和版本管理。等到需要多实例部署或并发写入成为瓶颈时再迁移到 MySQL——Base 层已经有了 MySQL 客户端封装（从另一个项目复用），迁移成本不会很高。过早引入 MySQL 意味着过早引入运维复杂度。

Q：Base 层封装了 MySQL / Redis / Milvus 等客户端但完全没用到，这不就是过度设计吗？
A：是，这是项目的技术债。Base 层是从另一个项目复用过来的，封装了很多 VitalAI 当前不需要的客户端。它们只是被 import 了没有被调用，不影响运行时性能和正确性，但增加了依赖和启动时间。当前优先级是业务纵切，不是依赖清理。等核心功能稳定后会做一轮 requirements.txt 瘦身。

Q：快照为什么不用数据库存？
A：快照的读写模式是"低频写、极低频读"——只在 CRITICAL 事件时写一次，故障转移时才读。这个模式用文件存储最简单、延迟最低、不需要额外的数据库连接。JSON 文件天然可读，出问题时人工打开就能看。如果未来快照频率变高或需要跨节点共享，再换数据库。

一句话总结：平台层的价值是让业务域不需要各自处理安全、可观测、容灾等横切关注点——一次实现，所有域复用。


### Assembly 组合根

开场定位
Assembly 是整个系统的依赖注入中心，约 970 行。它的核心职责是：知道怎么把 Repository、Service、Workflow、SignalBridge、SnapshotStore 组装到一起，使得其他层不需要知道这些依赖从哪来。

关键设计三步
环境变量驱动配置：VITALAI_INTENT_RECOGNIZER=rule_based|bert、VITALAI_INTENT_DECOMPOSER=placeholder|llm、VITALAI_HEALTH_DB_PATH、VITALAI_RUNTIME_SNAPSHOT_STORE_PATH 等，所有可切换的组件都通过环境变量控制。不改代码，只改环境变量，就能切换 BERT/规则识别器、placeholder/LLM 拆分器、数据库路径。

延迟工厂钩子：ApplicationAssemblyConfig 通过 Callable 延迟创建 Repository 和 Service，避免启动时就创建所有数据库连接。只有真正用到某个域时才创建对应的 repository 和绑定数据库连接。

Workflow 组装：build_health_alert_workflow() 等方法逐个组装各业务流——创建 repository、创建 service（注入 repository）、创建 workflow（注入 service 和 signal bridge），最终产出一个可以处理完整业务流的 Workflow 对象。所有依赖都在这一步注入，Workflow 本身不知道依赖从哪来。

高频追问
Q：970 行的 Assembly 会不会太大了？
A：确实偏大，但当前可接受。970 行里大部分是 build_*_workflow() 方法的组合逻辑，每个方法做的事情很清晰——创建依赖、注入、返回 workflow。如果继续加域，会超过合理范围。到那时应该把每个域的组装逻辑拆到各自的 DomainAssembly 里，顶层 Assembly 只做调度。但现在 4 个域，拆分反而增加间接成本。

Q：为什么用 Callable 延迟创建而不是直接实例化？
A：因为 repository 的数据库连接在创建时就会绑定文件路径。如果启动时就创建所有 repository，即使某个域暂时不用也会建立数据库连接和创建表。延迟创建意味着只有第一次请求该域时才建立连接——对于不常用的域（比如 admin 控制面的诊断功能），可能永远不需要创建。

一句话总结：Assembly 的价值是"一个地方知道所有依赖关系"——改依赖只需要改 Assembly，不需要改业务代码。


## 三、技术选型理由

| 选择 | 理由 |
|------|------|
| FastAPI | 异步支持、自动 OpenAPI 文档、Pydantic 校验一体化，Python API 开发效率最高 |
| SQLite 而非 MySQL | 四个域各自独立 SQLite 文件，零运维，开发测试极快，数据就是本地文件。迁移 MySQL 时 Base 层已有客户端封装 |
| Pydantic V2 | 模型定义 + 校验 + 序列化一体，dataclass 和 BaseModel 配合使用，数据边界清晰 |
| BERT 序列分类 | 意图识别延迟 10ms，远优于 LLM；6 类分类不需要生成能力，序列分类比生成式更稳定 |
| LLM 做意图拆分 | 复合意图拆分需要理解语义和推理，规则难以覆盖；但拆分结果不自动执行，只产出候选 |
| 状态机而非直接改字段 | 状态变更需要合法性校验、归属校验、副作用触发，直接改字段做不到 |
| 独立 SQLite 文件而非共享库 | 域之间数据隔离，一个域的表结构变更不影响其他域，health 的 schema 迁移不影响 daily_life |
| 环境变量驱动切换 | 不改代码只改环境变量就能切换识别器模式、拆分器模式、数据库路径，适合开发/测试/生产三套环境 |


## 四、简历描述与口头表达对照

简历版
设计并实现面向老人陪护的 AI 后端系统，采用五层 Modular Monolith 架构，包含 4 条业务域闭环（健康预警三态状态流 raised→acknowledged→resolved、日常签到 append-only 时间线、精神关怀危机信号自动优先级提升、个人记忆 upsert 语义存储），双层意图识别（BERT 10ms 分类 + LLM 复合意图拆分 + routing guard 安全守门），平台层提供安全守卫、运行时快照、故障转移等跨域基础设施。274 项测试通过，4 套烟测脚本覆盖端到端验收。

口头版
VitalAI 是一个给老人做 AI 陪护的后端。核心就是四条业务线：健康预警有完整的状态流——从发现到确认到解决，三态线性状态机，每一步都有校验；日常签到和精神关怀记录每天的状态，精神关怀的 crisis 信号会自动提升到 CRITICAL 优先级；个人记忆用 upsert 语义——同一个 key 写两次会覆盖，因为用途是查当前状态不是留历史。用户输入走双层意图识别，第一层 BERT 10ms 分类，检测到复合意图时第二层 LLM 做拆分，但拆分结果不自动执行——药物和安全信号一旦出现必须人工确认。平台层有安全脱敏、运行时快照、故障转移。整个系统 274 个测试全通过，四条线都有端到端烟测。

面试官如果问"项目上线了吗"
直接说"目前完成工程化基线阶段，核心模块完成后端实现，健康预警已经从写入+读取推进到完整状态流。还没上线，但架构和核心能力已经可验证——四条业务线都有端到端烟测，双层意图识别在 288 条样本上全对。"

面试官如果问"项目上遇到了什么困难"
说三个：1) 状态纵切——从 append-only 到状态机，需要兼容旧 SQLite 表结构，用 _ensure_schema 做 ALTER TABLE 兼容；2) 意图识别的 hard-case——BERT 在用药后不适、记忆写入/查询等场景容易分错，用硬编码规则做兜底，但不够优雅；3) 第二层意图拆分的安全性——怎么保证 LLM 的输出不会自动执行，设计了 routing guard 三级校验。


## 五、一句话总结

VitalAI 的核心价值是把老人陪护从"被动记录"变成"主动跟踪"——每条预警都有状态流（不会写了就消失），每次交互都有意图识别（不会错过复合意图），每个危机信号都有优先级提升（不会被当作普通签到处理），每条记忆都是当前状态（不会被历史版本淹没）。


## 六、核心数据库设计

### Health Alert 核心表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK AUTOINCREMENT | alert_id，内部主键 |
| user_id | TEXT NOT NULL | 老人标识 |
| risk_level | TEXT NOT NULL | 风险级别 |
| status | TEXT NOT NULL | 状态：raised / acknowledged / resolved |
| source_agent | TEXT NOT NULL | 来源 Agent 标识 |
| trace_id | TEXT NOT NULL | 链路追踪 ID |
| message_id | TEXT NOT NULL UNIQUE | 幂等去重键 |
| created_at | TEXT NOT NULL | 创建时间，之后不变 |
| updated_at | TEXT NOT NULL | 最后变更时间 |

### 四个域的持久化对比

| 域 | 写入语义 | 去重键 | 默认路径 | 状态流转 |
|----|----------|--------|----------|----------|
| Health Alert | 幂等写入 | message_id | .runtime/health.sqlite3 | raised→acknowledged→resolved |
| Daily Life | 幂等写入 | message_id | .runtime/daily_life.sqlite3 | 无，append-only |
| Mental Care | 幂等写入 | message_id | .runtime/mental_care.sqlite3 | 无，append-only |
| Profile Memory | upsert | (user_id, memory_key) | .runtime/profile_memory.sqlite3 | 无，覆盖更新 |


## 七、面试注意事项

- 面试时不要背简历原文，用口头版展开说，更自然也有深度
- 面试官问到架构设计时，重点说清：为什么五层而不是三层、为什么状态机而不是直接改字段、为什么双层意图识别——每个选择都有 trade-off
- 面试官问到"还有什么可以改进"时，说三个方向：1) 真实用户语料回流到意图识别训练（当前 288 条全是人工编的）2) 健康预警补通知渠道和自动升级（当前只有状态流转，没有主动通知）3) 把状态流模式复制到 mental_care（危机信号也应该有 acknowledge 闭环）——这说明你对下一步有清晰判断
- 不要回避"还没上线"——有完整设计和落地经历已经很有含金量
- 被问到数据库设计时，重点说清：为什么 SQLite 而不是 MySQL、为什么每个域独立文件、幂等写入怎么保证、schema 兼容怎么做的——不需要背所有字段
- 面试时不要背原文，用口头版本展开说，更自然也有深度
