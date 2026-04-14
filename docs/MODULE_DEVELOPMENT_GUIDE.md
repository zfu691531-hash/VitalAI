# VitalAI 分模块开发总纲

## 开发风格

这份风格说明，定义的是当前 VitalAI 项目已经形成的实际开发方式，而不是一套脱离上下文的理想规范。

### 1. 整体风格

- 以“轻量但边界清晰”为优先，而不是为了抽象而抽象
- 优先建立 typed contract，再逐步接线，而不是先堆业务细节
- 保留统一中心调度思路，但避免单体化 Supervisor
- 入口层保持薄，领域层保持高聚合，平台层保持机制纯度
- 优先用小而明确的 helper / policy / snapshot 解决问题，不急于引入重型 container 或 registry

### 2. 代码风格

- 优先使用 dataclass、显式类型、可读的命名
- 不滥用泛型抽象，不为了“通用”牺牲当前语义清晰度
- 新增注释时只在必要位置补“解释设计意图”的注释
- 注释优先写中文，避免中英混杂
- 尽量让一个文件的职责单一，读者看到文件名就能推测它做什么

### 3. 架构推进风格

- 先确认 `Base` 是否已有可复用能力，再决定是否在 `VitalAI` 新建
- 先把协议和边界立稳，再把 flow 串起来
- 先做最小可运行链路，再扩第二条、第三条平行链路
- 只有在模式被真实证明之后，才提取共享抽象
- 每个阶段都要留下文档、状态、下一步建议，方便接力开发

### 4. 验证风格

- 优先做最小但有意义的自动化验证
- 避免为了验证引入 `VitalAI.main`，因为当前 `Base` 有较重初始化副作用
- 优先验证 typed flow 是否真正串通，而不是只验证单点函数
- 每次有意义的推进后，都要同步更新 `docs/CURRENT_STATUS.md` 和 `docs/NEXT_TASK.md`

## 项目总览

VitalAI 是一个建立在 `Base/` 之上的服务端多 Agent 系统，目标场景围绕老人陪护、健康管理、日常生活支持、长期记忆、风险预警和紧急中断。

当前可以把整个仓库理解成两层：

- `Base/`：通用基础能力层
- `VitalAI/`：业务系统与运行时机制本体

### `Base/` 负责什么

- 配置与日志
- LLM 与 AI 基础能力
- 数据库与 Repository
- 外部客户端
- 通用模型
- 通用工具函数

### `VitalAI/` 负责什么

- 系统级平台协议与运行时
- 业务领域能力
- 应用层业务编排
- 外部接口适配
- 少量项目内共享对象

## 当前我们已经做了什么

到目前为止，项目已经完成了 19 个连续步骤，整体推进顺序如下：

### 阶段 1：平台契约与运行时骨架

- 建立了 `platform/messaging`、`platform/feedback`、`platform/arbitration`、`platform/interrupt` 四类 typed contract
- 把 `runtime` 骨架逐步接到了 typed contract 上
- 让 `health_monitor`、`shadow_decision_core`、`degradation`、`failover` 开始共享同一套 runtime 语言

### 阶段 2：第一条与第二条 typed 业务流

- 建立了 health typed flow
- 建立了 daily_life typed flow
- 引入 command / use case / workflow / reporting 的分层链路

### 阶段 3：共享支撑与应用装配

- 提取了最小共享 helper
- 引入 `FeedbackReportRequest`
- 建立了 `application/assembly.py`
- 逐步把 assembly 从本地 builder 推进到环境感知、角色感知、角色策略

### 阶段 4：接口层与策略可见性

- API / scheduler / consumer 都已经能消费同一套 typed flow
- 引入了 reporting / ingress ack / ingress ttl 三条角色策略
- 引入了策略快照
- 引入了单角色与标准角色矩阵的 introspection 入口

## 当前项目主模块总览

```text
VitalAI/
├─ application/
├─ platform/
├─ domains/
├─ interfaces/
├─ shared/
└─ main.py
```

下面按模块分别说明。

## 模块 1：`platform/`

### 模块定位

`platform/` 是系统级平台层，负责所有跨领域共享的运行时机制。

### 当前已完成内容

- `messaging/message_envelope.py`
- `feedback/events.py`
- `arbitration/intents.py`
- `interrupt/signals.py`
- `runtime/decision_core.py`
- `runtime/event_aggregator.py`
- `runtime/health_monitor.py`
- `runtime/shadow_decision_core.py`
- `runtime/snapshots.py`
- `runtime/degradation.py`
- `runtime/failover.py`

### 模块要求

- 必须优先保证协议稳定、typed、轻量
- 不要把具体业务语义塞进 platform
- 不要让某个领域独占 platform 机制
- 不要过早绑定重型基础设施

### 模块风格

- 协议对象保持显式字段
- 小型运行时组件按职责拆开
- 尽量使用 dataclass 和小方法
- 优先表达“运行时语义”，而不是“实现炫技”

### 交付标准

- 至少有明确输入/输出 contract
- 可以被 application 或 domains 稳定引用
- 有最小测试覆盖关键链路
- 不依赖 `VitalAI.main` 才能验证

### 推进注意事项

- 任何 platform 新增对象，先检查 `Base/Models` 和 `Base/RicUtils` 是否已有合适积木
- 不要把 platform 重新收缩成一个大 `supervisor.py`
- 新增 runtime 行为时，优先考虑是否应该通过 contract 表达，而不是直接写死逻辑

## 模块 2：`application/`

### 模块定位

`application/` 负责完整业务用例的编排，是 domain、platform、interfaces 之间的组织层。

### 当前已完成内容

- `commands/health_alert_command.py`
- `commands/daily_life_checkin_command.py`
- `use_cases/health_alert_flow.py`
- `use_cases/daily_life_checkin_flow.py`
- `use_cases/runtime_support.py`
- `workflows/health_alert_workflow.py`
- `workflows/daily_life_checkin_workflow.py`
- `workflows/reporting_support.py`
- `assembly.py`

### 模块要求

- 负责“怎么把完整流程跑通”
- 不负责底层 transport / persistence 细节
- 不直接承载具体领域规则
- 明确 command、use case、workflow、assembly 的边界

### 模块风格

- command 负责稳定输入
- use case 负责 runtime + domain 编排
- workflow 负责更完整的多步组合
- assembly 负责依赖组合与运行角色策略

### 交付标准

- 至少能从一个稳定输入对象走到一个稳定输出对象
- 关键依赖通过 assembly 可替换
- 有最小自动化测试覆盖
- 对“为什么这样编排”有少量高价值注释

### 推进注意事项

- 不要让 interfaces 持有组装细节
- 不要把 runtime 角色策略塞回 command 或 domain
- 新增抽象前，先确认是否已经有至少两条 flow 真正重复

## 模块 3：`domains/`

### 模块定位

`domains/` 负责业务领域本身的语义与输出表达。

### 当前已完成内容

- `health/services/alert_triage.py`
- `daily_life/services/checkin_support.py`
- `reporting/services/feedback_report.py`

### 模块要求

- 每个领域只关心自己的业务判断和结果表达
- 尽量不要知道外部入口长什么样
- 通过 typed platform object 对外表达结果

### 模块风格

- 高聚合
- 领域对象命名清楚
- 用 outcome 把多种 typed 输出打包
- 业务语义优先于技术抽象

### 交付标准

- 给定一个明确输入，能产出清晰的领域结果
- 领域结果能被 reporting / arbitration / workflow 消费
- 不把领域判断散落在 interfaces 或 platform

### 推进注意事项

- 新增领域时优先复制“health / daily_life”的最小模式，而不是重新发明结构
- domain service 应该解释业务，而不是直接变成 transport glue code
- 同一领域内允许保留适度重复，以换取语义清晰

## 模块 4：`interfaces/`

### 模块定位

`interfaces/` 只负责“外部怎么进入系统”，不负责业务内核。

### 当前已完成内容

- `api/routers/typed_flows.py`
- `api/app.py`
- `scheduler/typed_flow_jobs.py`
- `consumers/typed_flow_consumers.py`
- `typed_flow_support.py`

### 模块要求

- 保持薄
- 只做入参接收、调用 application、返回结构化结果
- 不把业务规则写在接口层

### 模块风格

- API / scheduler / consumer 尽量保持同一形状
- 通过 support 层复用共享逻辑
- 接口层可以暴露 introspection，但不要在这里制造核心策略

### 交付标准

- 能稳定驱动对应 workflow
- 返回结构清楚
- 单元测试能覆盖关键入口
- 不依赖更深层细节才能理解入口行为

### 推进注意事项

- 新接口优先复用 typed flow support
- 不要让接口层重新拥有 workflow 组装权
- 如果接口层逻辑开始变厚，优先检查是不是该下沉到 application

## 模块 5：`shared/`

### 模块定位

`shared/` 只放少量稳定、跨模块复用、但又不适合进入 `Base` 的轻量对象。

### 当前状态

- 当前仍然保持很轻，没有被当成杂物间使用

### 模块要求

- 小而稳
- 不承载大量业务逻辑
- 不成为“我不知道放哪就放这里”的目录

### 模块风格

- 只有真正跨层共享且语义稳定的对象才进入这里

### 交付标准

- 被多个模块稳定复用
- 不依赖某个单独领域
- 命名和用途足够明确

### 推进注意事项

- 如果一个对象明显属于 domain / platform / application，就不要图省事丢进 shared

## 模块 6：`Base/`

### 模块定位

`Base/` 是 VitalAI 的默认基础能力层。

### 使用要求

开发任何模块前，必须先判断：

- 配置 / 日志 -> `Base/Config`
- LLM / AI -> `Base/Ai`
- 外部客户端 -> `Base/Client`
- 持久化 -> `Base/Repository`
- 通用模型 -> `Base/Models`
- 通用服务 -> `Base/Service`
- 通用工具 -> `Base/RicUtils`

### 推进注意事项

- 通用能力尽量复用 `Base`
- VitalAI 运行时专属契约不要硬塞进 `Base`
- 避免把 `Base` 用成“所有代码都能放”的超大杂物层

## 分模块开发建议顺序

后续如果进入分模块推进，建议按下面顺序：

### 第一优先级：继续稳住平台与应用边界

- `platform/runtime/`
- `application/assembly.py`
- `application/use_cases/`
- `interfaces/typed_flow_support.py`

目标：

- 明确当前 stop point 是否已经足够
- 避免继续无节制增加角色策略

### 第二优先级：补充新的领域流

- 新增第三个真实领域 consumer
- 让它复用现有 command / use case / workflow / reporting 模式

目标：

- 用真实业务再验证一次当前结构
- 而不是只围绕 health / daily_life 打转

### 第三优先级：按需补持久化与基础设施接线

- 只有当真实场景需要持久化、注册表、配置来源切换时，才考虑往 `Base/Repository` 或更深 assembly 演进

目标：

- 把复杂度建立在真实需求上

## 每个模块的交付清单模板

后续谁接手一个模块，都建议按下面清单交付：

### 1. 边界说明

- 这个模块属于哪一层
- 它不负责什么
- 它依赖哪些上游/下游模块

### 2. 核心对象

- 主要 dataclass / service / workflow / contract 有哪些
- 输入输出分别是什么

### 3. 运行链路

- 一条最小输入如何进入模块
- 模块内部如何变换
- 最终如何输出给下游

### 4. 复用判断

- 本模块是否先检查过 `Base`
- 哪些能力复用了 `Base`
- 哪些能力必须留在 `VitalAI`

### 5. 测试与验证

- 最小测试命令
- 已覆盖什么
- 还未覆盖什么

### 6. 文档同步

- 更新 `docs/CURRENT_STATUS.md`
- 更新 `docs/NEXT_TASK.md`
- 如有明显阶段结果，新增一步技术拆解文档

## 当前阶段的统一交付标准

接下来所有模块开发，建议统一按下面标准验收：

- 有明确层级归属
- 有清晰 typed 输入输出
- 代码里有少量高价值中文注释
- 不重复造 `Base` 已有能力
- 有最小自动化验证
- 有文档沉淀
- 不引入无证明价值的重型抽象

## 当前阶段的推进注意事项

### 1. 不要急着继续堆抽象

目前项目最大的风险不是“抽象不够”，而是“过早抽象”。

### 2. 不要把接口层写厚

API / scheduler / consumer 必须继续保持薄。

### 3. 不要把运行角色策略塞回业务对象

像 reporting / ack / ttl 这类差异，应该继续留在 assembly boundary。

### 4. 不要绕开 typed contract

新模块一旦又开始满天飞 `dict[str, Any]`，后面会迅速返工。

### 5. 不要忘记文档是交付物的一部分

这个项目已经进入多阶段、多模块、可接力开发状态。没有文档，同步成本会迅速上升。

## 推荐新模块启动流程

后续每次开始一个新模块，建议统一按下面顺序：

1. 阅读：
   - `docs/PROJECT_CONTEXT.md`
   - `docs/CURRENT_STATUS.md`
   - `docs/NEXT_TASK.md`
   - `README.md`

2. 检查对应 `Base` 目录，确认是否已有可复用能力

3. 明确模块归属：
   - 是 `platform`？
   - 是 `application`？
   - 是 `domains`？
   - 是 `interfaces`？

4. 先定义 typed 输入输出边界

5. 再实现最小可运行链路

6. 补测试

7. 补中文注释

8. 更新文档

## 建议文档位置

这份文档建议作为后续分模块开发的总入口文档使用。

如果以后继续扩展，可以围绕它再补两类文档：

- 模块级开发手册
- 阶段性 ADR / 决策记录

当前已补的模块级开发手册：

- `docs/MODULE_PLATFORM_GUIDE.md`
- `docs/MODULE_APPLICATION_GUIDE.md`
- `docs/MODULE_DOMAINS_GUIDE.md`
- `docs/MODULE_INTERFACES_GUIDE.md`
- `docs/MODULE_SHARED_GUIDE.md`
- `docs/BASE_REUSE_AND_INTEGRATION_GUIDE.md`
