# VitalAI

VitalAI 是当前仓库的主项目。

这是一个依托 `Base/` 能力层构建的服务端多 Agent 系统，目标是围绕老人陪护场景，建设一个具备统一调度、长期记忆、反馈学习、冲突仲裁和紧急中断能力的中心化智能系统。

## 一句话理解这个仓库

可以把这个仓库理解成两层：

- `Base/` 是地基，负责通用基础能力
- `VitalAI/` 是房子，负责业务系统本身

也就是说：

- `Base` 解决“怎么连、怎么调、怎么存、怎么配”
- `VitalAI` 解决“怎么协作、怎么调度、怎么决策、怎么服务用户”

## 为什么这样设计架构

这个项目后面会很大，而且不是一个单体小功能，而是一个持续增长的服务端系统。它会同时面对：

- 多个业务领域并行开发
- 多 Agent 协作
- 大量跨模块通信
- 复杂状态和长期记忆
- 风险预警与紧急处理
- 后续多人协作和模块扩展

如果一开始就把代码按“接口 / service / utils”简单平铺，短期看快，长期一定会出现这些问题：

1. 业务逻辑散落
   同一个功能会同时分散在 API、service、agent、工具函数里，后面改起来很痛苦。

2. 跨模块边界模糊
   通信、反馈、冲突、中断这些本来是系统级能力，却容易被塞进某个业务目录里，最后没人知道该归谁维护。

3. 很难多人并行开发
   大家会不断改同一层同一堆目录，冲突多，理解成本高。

4. 后续扩展代价高
   一旦想增加新的 Agent、新的领域、新的接入方式，原结构会迅速变乱。

所以我把架构拆成下面这五层，不是为了“好看”，而是为了控制复杂度：

- `application/` 负责业务用例编排
- `platform/` 负责系统级平台机制
- `domains/` 负责业务领域聚合
- `interfaces/` 负责外部接入
- `shared/` 负责少量轻量共享对象

这个设计的核心思想是：

- 让系统机制和业务逻辑分开
- 让领域代码高聚合
- 让入口层保持很薄
- 让 Base 和 VitalAI 的职责边界清晰

## 仓库主结构

```text
.
├─ Base/               # 基础能力层：配置、日志、LLM、Client、Repository、通用工具
├─ VitalAI/            # VitalAI 服务端代码主目录
├─ docs/               # 架构设计、交接文档、设计草案
├─ main.py             # 仓库统一启动入口，转发到 VitalAI.main:app
├─ requirements.txt    # Python 依赖
├─ .env.template       # 环境变量模板
├─ .gitignore          # Git 忽略规则
├─ .dockerignore       # Docker 构建忽略规则
├─ Dockerfile          # 容器镜像构建文件
└─ docker-compose.yml  # 本地容器编排
```

## VitalAI 内部结构

```text
VitalAI/
├─ application/   # 应用层：负责编排完整业务用例，不放底层机制
├─ platform/      # 平台层：承载通信、反馈、仲裁、中断等系统级能力
├─ domains/       # 领域层：按业务领域组织代码，保持高聚合
├─ interfaces/    # 接口层：HTTP、定时任务、消息消费、Web 挂载入口
├─ shared/        # 共享层：少量稳定通用对象，避免变成杂物间
└─ main.py        # VitalAI 应用入口
```

下面我把每一层为什么存在、它负责什么、应该放什么，说清楚。

---

## `application/` 是做什么的

### 为什么需要它

很多项目一开始没有应用层，结果所有“完整流程”都散在 API、service 和 agent 里。

比如“早晨健康检查”这种事情，本质不是某一个单独模块的职责，它通常会涉及：

- 读取用户状态
- 调用健康领域服务
- 调用日常领域服务
- 写入反馈
- 更新记忆
- 触发通知

如果没有 `application/`，这些编排代码就会四处分散。

### 它负责什么

`application/` 负责完整用例和业务流程编排。

它关心的是：

- 先做什么
- 再调谁
- 最后产出什么结果

它不应该负责：

- 底层消息机制
- 数据库存储细节
- 具体某个领域的核心规则

### 适合放什么

- 晨间检查流程
- 用药提醒流程
- 家属日报生成流程
- 健康异常预警流程
- 多 Agent 联合执行流程

### 中文注释理解

- `application/commands/`：命令入口，代表“系统要执行什么动作”
- `application/queries/`：查询入口，代表“系统要获取什么信息”
- `application/use_cases/`：完整业务用例，代表“一个完整功能怎么跑”
- `application/workflows/`：工作流定义，代表“多步流程如何串起来”

---

## `platform/` 是做什么的

### 为什么需要它

这个项目最复杂的不是单个业务功能，而是“整个系统如何像一个系统那样运转”。

比如这些能力：

- Agent 之间怎么通信
- 执行结果怎么回流
- 多个 Agent 冲突时谁说了算
- 紧急情况发生时如何打断所有普通流程

这些都不是某个业务域独有的能力，而是整个系统共享的机制。

所以必须把它们抽成平台层，否则最后会出现：

- 健康模块有一套冲突处理
- 日常模块有一套冲突处理
- 精神模块又有一套中断逻辑

这样后面一定失控。

### 它负责什么

`platform/` 是系统级平台内核，负责跨领域通用机制。

### 它为什么是架构核心

你的 `docs/` 里其实已经很明确了，这个项目不是“几个 Agent + 几个接口”，而是一个带四层基础机制的中心化系统。

所以 `platform/` 就是把这些四层基础机制落到代码结构里。

### 中文注释理解

- `platform/messaging/`
  中文注释：通信层，负责统一消息信封、事件总线、发布订阅、队列、链路追踪、死信队列。

- `platform/feedback/`
  中文注释：反馈层，负责 L1/L2/L3 反馈闭环、置信度评分、聚合和学习信号。

- `platform/arbitration/`
  中文注释：仲裁层，负责意图声明、冲突检测、目标权重仲裁、共享状态锁。

- `platform/interrupt/`
  中文注释：中断层，负责 P0-P3 紧急中断、状态机、快照和恢复。

- `platform/observability/`
  中文注释：可观测层，负责日志、指标、trace、审计。

- `platform/security/`
  中文注释：安全与隐私层，负责脱敏、权限、合规、敏感输出控制。

- `platform/runtime/`
  中文注释：运行时层，负责 Decision Core、事件聚合、健康监控、影子接管、快照和降级运行。

### 为什么不把这些直接放进 `domains/`

因为这些不是某个业务领域自己的逻辑，而是所有领域都会共享的系统机制。

它们应该被复用，而不是被复制。

---

## `domains/` 是做什么的

### 为什么需要它

如果按技术目录组织代码，通常会变成：

- 所有 model 放一起
- 所有 service 放一起
- 所有 repository 放一起

这样做的问题是，一个领域的代码会被拆得很散。你做“健康”模块时，要在 5 个不同目录来回跳。

而这个项目很大，后面一定是按模块、按领域并行开发的，所以最好的方式是：

按业务领域聚合。

### 它负责什么

每个领域只负责自己这部分业务能力和业务规则。

当前规划的领域有：

- `health/`：健康监测、风险识别、慢病与术后管理
- `daily_life/`：购物、饮食、出行、居住、资金安全等日常管理
- `mental_care/`：陪护、情绪识别、社交、反思、智慧传承
- `reporting/`：日报、周报、家属汇报、风险摘要
- `profile_memory/`：个人信息库、画像、长期偏好、关系图谱、记忆检索

### 中文注释理解

每个领域内部建议这样拆：

- `agents/`
  中文注释：这个领域下的业务 Agent 实现

- `models/`
  中文注释：这个领域自己的数据模型和业务对象

- `services/`
  中文注释：这个领域内部的业务服务和组合逻辑

- `repositories/`
  中文注释：这个领域的数据访问层，底层复用 `Base/Repository`

- `policies/`
  中文注释：这个领域的规则、策略、阈值、决策约束

### 为什么这是高聚合

因为做一个领域时，你只需要围绕这个领域本身的目录开发，不用在整个项目里来回找代码。

这对大项目非常重要。

---

## `interfaces/` 是做什么的

### 为什么需要它

很多项目会把 API 写得越来越重，最后：

- API 里有编排逻辑
- API 里有数据库读写
- API 里有业务决策

这样一旦以后多出新的接入方式，比如：

- 定时任务
- 事件消费
- 后台 worker
- Web 页面

你会发现逻辑根本复用不了。

### 它负责什么

`interfaces/` 只负责“外部怎么进入系统”，不负责核心业务规则。

### 中文注释理解

- `interfaces/api/`
  中文注释：HTTP 接口入口，只做参数接收、调用应用层、返回结果。

- `interfaces/scheduler/`
  中文注释：定时任务入口，比如每天 23:00 聚合反馈。

- `interfaces/consumers/`
  中文注释：消息消费入口，比如订阅事件队列或总线。

- `interfaces/web/`
  中文注释：前端页面、静态资源、Web 挂载入口。

### 为什么接口层要薄

因为接口层变化最快，但不应该带走业务核心。

保持它很薄，后面替换接入方式会更容易。

---

## `shared/` 是做什么的

### 为什么需要它

项目里总会有一些轻量、稳定、很多地方都用到的东西，比如：

- 通用错误类型
- 常量
- 基础 schema
- 少量通用工具

这些完全不放会很重复，但放太多又会变成“垃圾桶目录”。

### 它负责什么

只负责真正轻量、稳定、跨层可复用的小对象。

### 中文注释理解

- `shared/constants/`
  中文注释：系统常量、枚举值、固定配置项

- `shared/errors/`
  中文注释：通用错误定义和异常类型

- `shared/schemas/`
  中文注释：跨层复用的轻量数据结构

- `shared/utils/`
  中文注释：少量通用工具函数

### 为什么要严格控制它

因为一旦不控制，最后所有“我不知道放哪”的代码都会被扔进 `shared/`。

所以这个目录要小而精。

---

## 为什么不把所有能力都继续放在一个 Supervisor 身上

虽然“中心调度”是对的，但如果把所有事情都继续塞给一个 Supervisor，会出现明显单点问题：

- 原始事件全量涌入，中心容易过载
- 高频聚合和高价值决策抢同一资源
- 日志 IO 拖慢决策
- 心跳监控、状态同步、调度、决策耦合在一起
- 中心故障时，系统容易整体失能

所以这里要强调：

- 我们保留中心化决策
- 但不保留“单体化 Supervisor”

也就是说，我们采用的是：

- 中心仍然存在
- 但中心只保留最核心的决策能力
- 其他职责拆分为专门的运行时组件

## `platform/runtime/` 为什么要继续拆分

根据 `docs/archive/design-assets/项目单点问题优化方案.docx` 和 `docs/archive/design-assets/项目流程图.mmd`，运行时层不应该只存在一个 `supervisor.py`，而应该拆成几个明确组件：

- `decision_core.py`
  中文注释：真正的决策核心，只接收结构化事件摘要，只负责做出决策和下发指令。

- `event_aggregator.py`
  中文注释：事件聚合器，负责接收各 Agent 原始事件，做去重、合并、优先级排序、TTL 校验、置信度预检，再把摘要送给决策核心。

- `health_monitor.py`
  中文注释：健康监控器，负责心跳检查、失联检测、故障告警和接管触发。

- `shadow_decision_core.py`
  中文注释：影子决策核心，负责热备主决策核心状态，在主节点故障时快速接管。

- `snapshots.py`
  中文注释：快照管理，负责保存决策状态和中断恢复状态。

- `degradation.py`
  中文注释：降级策略，负责中心不可用时的自治惯性和系统保底运行规则。

- `failover.py`
  中文注释：主从切换逻辑，负责从主核心切换到影子核心，并在恢复后切回。

这样设计的原因是：

- 决策核心必须轻量
- 聚合必须独立
- 监控必须独立
- 日志必须异步
- 热备必须明确
- 降级必须有边界

这套结构比“一个大 Supervisor 管一切”更符合你文档里的优化方向。

## 当前我们对中心调度的最终理解

现在不再把 Supervisor 理解为“一个大对象”，而是理解成“一个中心化运行时体系”。

这个体系里：

- `Decision Core` 是最小决策核心
- `Event Aggregator` 是输入整理层
- `Health Monitor` 是存活监控层
- `Shadow Decision Core` 是热备层
- `Interrupt` 提供高优先级覆盖能力
- `Degradation` 提供中心失效时的保底运行能力

所以以后如果文档里继续出现 “Supervisor”，在代码层面应默认理解为：

“以 Decision Core 为核心的一组运行时组件”

而不是一个单体类。

## `Base/` 在这套架构里扮演什么角色

`Base` 是你们的地基，这个定位非常关键。

VitalAI 每次开发模块时，不应该默认自己写一套基础能力，而应该先检查 `Base` 有没有现成能力可以复用。

### `Base` 当前适合承载的内容

- `Base/Config`
  中文注释：项目配置和日志初始化

- `Base/Ai`
  中文注释：LLM 抽象、模型接入、Prompt 和 AI 基础服务

- `Base/Client`
  中文注释：MySQL、Redis、MinIO、邮件、调度、ASR 等外部客户端封装

- `Base/Repository`
  中文注释：数据库连接管理、ORM 基类、多数据库支持

- `Base/Models`
  中文注释：通用可复用数据模型

- `Base/Service`
  中文注释：已经沉淀好的可复用服务封装

- `Base/RicUtils`
  中文注释：路径、文件、日期、HTTP、PDF、Redis 等通用工具

## 为什么不把所有东西都继续堆进 `Base`

因为 `Base` 应该保持“通用能力层”属性。

一旦把 VitalAI 的业务逻辑也放进去，地基就会变成业务层，后面所有项目都会被绑死。

所以边界应该是：

- 通用的，放 `Base`
- VitalAI 场景专属的，放 `VitalAI`

---

## 推荐的理解顺序

如果你以后要读这个项目，我建议按这个顺序看：

1. 先看根 `README.md`
   先知道整体定位和分层原因

2. 再看 `docs/PROJECT_CONTEXT.md`
   了解项目长期背景和 `Base` 边界

3. 再看 `docs/CURRENT_STATUS.md`
   看现在做到哪里了

4. 再看 `docs/NEXT_TASK.md`
   看下一步具体做什么

5. 然后根据模块去看相关 `Base` 目录
   避免重复造轮子

---

## 当前开发建议

当前最值得先搭的，不是具体业务 Agent，而是平台基础契约：

- `platform/messaging/message_envelope.py`
  中文注释：统一消息信封协议

- `platform/feedback/events.py`
  中文注释：反馈事件协议

- `platform/arbitration/intents.py`
  中文注释：意图声明与仲裁输入协议

- `platform/interrupt/signals.py`
  中文注释：中断信号与快照协议

- `platform/runtime/decision_core.py`
  中文注释：决策核心协议与运行时外壳

- `platform/runtime/event_aggregator.py`
  中文注释：事件聚合器运行时外壳

- `platform/runtime/health_monitor.py`
  中文注释：健康监控器运行时外壳

- `platform/runtime/shadow_decision_core.py`
  中文注释：影子决策核心外壳

原因很简单：

这几个文件会决定后面所有模块怎么接进系统。

如果协议不先稳住，后面每个业务模块都会按自己的理解来写，最后一定返工。

---

## 启动方式

仓库统一入口为根目录 `main.py`，它会转发到 `VitalAI.main:app`。

本地启动：

```bash
uvicorn main:app --host 127.0.0.1 --port 8124
```

如果你只是想先确认后端能不能跑，不要先接前端，直接用下面两步：

```powershell
python -m uvicorn VitalAI.main:app --host 127.0.0.1 --port 8124
python scripts\manual_smoke_http_api.py --output text
```

预期先看到 `Uvicorn running on http://127.0.0.1:8124`，然后 smoke 脚本返回：

- `VitalAI HTTP smoke: OK`
- `health: OK`
- `profile_memory_write: OK`
- `profile_memory_read: OK`
- `interaction: OK`

## Admin 控制面验收

runtime diagnostics 和 health failover drill 是有副作用的控制面接口，需要显式打开 runtime control，并配置 admin token。

本地开发示例：

```powershell
$env:VITALAI_RUNTIME_CONTROL_ENABLED="true"
$env:VITALAI_ADMIN_TOKEN="dev-admin-token"
$env:VITALAI_RUNTIME_SNAPSHOT_STORE_PATH=".runtime\runtime_snapshots.json"
uvicorn main:app --host 127.0.0.1 --port 8124
```

另开终端调用：

```powershell
$headers = @{ "X-VitalAI-Admin-Token" = "dev-admin-token" }
Invoke-RestMethod -Method Post http://127.0.0.1:8124/vitalai/admin/runtime-diagnostics/api -Headers $headers
Invoke-RestMethod -Method Post http://127.0.0.1:8124/vitalai/admin/runtime-diagnostics/api/health-failover -Headers $headers
```

不带 `X-VitalAI-Admin-Token` 或 token 不匹配时，接口应返回拒绝访问。

## Runtime Snapshot 持久化验收

默认情况下，runtime snapshot 使用进程内轻量 store，适合普通测试。设置 `VITALAI_RUNTIME_SNAPSHOT_STORE_PATH` 后，会启用本地文件持久化 store。
如需限制单个 `snapshot_id` 在文件中的历史版本数量，可额外设置 `VITALAI_RUNTIME_SNAPSHOT_MAX_VERSIONS_PER_ID`；启用后会只保留最近 N 个版本，并在加载旧文件时顺带做一次收敛清理。

本地验收步骤：

```powershell
$env:VITALAI_RUNTIME_CONTROL_ENABLED="true"
$env:VITALAI_ADMIN_TOKEN="dev-admin-token"
$env:VITALAI_RUNTIME_SNAPSHOT_STORE_PATH=".runtime\runtime_snapshots.json"
$env:VITALAI_RUNTIME_SNAPSHOT_MAX_VERSIONS_PER_ID="20"
uvicorn main:app --host 127.0.0.1 --port 8124
```

另开终端连续调用两次 diagnostics：

```powershell
$headers = @{ "X-VitalAI-Admin-Token" = "dev-admin-token" }
$first = Invoke-RestMethod -Method Post http://127.0.0.1:8124/vitalai/admin/runtime-diagnostics/api -Headers $headers
$second = Invoke-RestMethod -Method Post http://127.0.0.1:8124/vitalai/admin/runtime-diagnostics/api -Headers $headers

$first.runtime_signals[0].details
$second.runtime_signals[0].details
```

预期 `.runtime\runtime_snapshots.json` 会被创建，并且第二次 diagnostics 的 snapshot version 会继续递增。停止服务后重新启动，再调用 diagnostics，版本也应基于文件中的历史继续递增，而不是从 1 重新开始。

## Typed Flow History 一键烟测

不启动 `uvicorn`，直接通过 application assembly/workflow 验证当前四条本地读写闭环：

建议从项目根目录运行，脚本默认会把临时验收目录解析到项目根目录下的 `.runtime\manual-smoke-*`。

```powershell
python scripts\manual_smoke_typed_flow_history.py
```

预期输出 JSON，顶层 `ok=true`，并且 `flows.profile_memory`、`flows.health`、`flows.daily_life`、`flows.mental_care` 下的 `ok` 都为 `true`。脚本会把四个 SQLite 数据库和 runtime snapshot 写到 `.runtime\manual-smoke-*` 临时目录，默认运行结束后清理该目录，不会写入默认的 `.runtime\profile_memory.sqlite3`、`.runtime\health.sqlite3`、`.runtime\daily_life.sqlite3`、`.runtime\mental_care.sqlite3`。

人工快速验收时可输出短文本摘要：

```powershell
python scripts\manual_smoke_typed_flow_history.py --output text
```

如果服务已经启动，也可以直接走 HTTP 验收而不是 application 内部验收：

```powershell
python scripts\manual_smoke_http_api.py --output text
```

如果你只是想快速知道“后端现在能不能联调”，优先看 [docs/API_SMOKE_CHECKLIST.md](D:/Users/Windows/PycharmProjects/VitalAI/docs/API_SMOKE_CHECKLIST.md)。

默认会打到 `http://127.0.0.1:8124`，检查：

- `GET /vitalai/health`
- `POST /vitalai/flows/profile-memory`
- `GET /vitalai/flows/profile-memory/{user_id}`
- `POST /vitalai/interactions`
- `GET /vitalai/users/{user_id}/overview`

如果你想对运行中的服务一次性验收四条 typed flow 的写后读闭环，可以直接运行：

```powershell
python scripts\manual_smoke_typed_flow_http.py --output text
```

默认会打到 `http://127.0.0.1:8124`，依次检查：

- `POST /vitalai/flows/profile-memory` + `GET /vitalai/flows/profile-memory/{user_id}`
- `POST /vitalai/flows/health-alert` + `PATCH /acknowledge` + `PATCH /resolve` + `GET /vitalai/flows/health-alerts/{user_id}` + `GET /vitalai/flows/health-alerts/{user_id}/{alert_id}`
- `POST /vitalai/flows/daily-life-checkin` + `GET /vitalai/flows/daily-life-checkins/{user_id}` + `GET /vitalai/flows/daily-life-checkins/{user_id}/{checkin_id}`
- `POST /vitalai/flows/mental-care-checkin` + `GET /vitalai/flows/mental-care-checkins/{user_id}` + `GET /vitalai/flows/mental-care-checkins/{user_id}/{checkin_id}`

```powershell
python scripts\manual_smoke_interactions_http.py --output text
```

For one lightweight cross-domain read after the three domain slices are seeded, we now also have:

```powershell
python scripts\manual_smoke_user_overview_http.py --output text
```

That overview now includes the four aggregated snapshots, a lightweight `recent_activity` timeline ordered by timestamp, and read-only `attention_items` hints for manual triage.

For a browser-based manual check, the app root now serves a small read-only overview console:

```text
http://127.0.0.1:8124/
```

默认会打到 `http://127.0.0.1:8124`，依次检查：

- 健康类自然语言输入能路由到 `HEALTH_ALERT`
- 记忆类自然语言输入能路由到 `PROFILE_MEMORY_UPDATE`
- 普通问候会返回 `clarification_needed`
- 复合输入会返回 `decomposition_needed`
- 缺失必填字段会返回统一 `invalid_request`

预期能看到 `profile_memory`、`health`、`daily_life`、`mental_care` 四行均为 `OK`，并带出各自的计数和 `readable_summary`。

如需保留临时数据库用于人工查看：

```powershell
python scripts\manual_smoke_typed_flow_history.py --keep-runtime
```

也可以显式指定验收目录：

```powershell
python scripts\manual_smoke_typed_flow_history.py --runtime-dir .runtime\manual-smoke-local
```

该脚本只覆盖当前最小闭环：profile memory 写后读、health alert 写后读、daily_life check-in 写后读、mental_care check-in 写后读；不扩展到健康档案、任务状态机、提醒调度、心理量表、多轮陪伴、图谱或复杂搜索。

## 一键启动后端并联调

`scripts/dev_start_and_smoke.py` 是开发辅助脚本，一键启动后端、等待健康检查、可选跑 smoke、然后自动停止。

启动后端并跑 smoke：

```powershell
python scripts\dev_start_and_smoke.py --smoke
```

启动后端并保持服务运行，方便人工联调：

```powershell
python scripts\dev_start_and_smoke.py --smoke --keep-running
```

仅启动后端并保持运行（不跑 smoke）：

```powershell
python scripts\dev_start_and_smoke.py --keep-running
```

完整参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--host` | `127.0.0.1` | 监听地址 |
| `--port` | `8124` | 监听端口 |
| `--smoke` | off | 启动后执行 `manual_smoke_http_api.py` |
| `--keep-running` | off | smoke 后不停止服务，保持运行供人工联调 |
| `--startup-timeout` | `30` | 等待健康检查的最大秒数 |
| `--smoke-output` | `text` | smoke 报告格式：`text` 或 `json` |

启动失败、健康检查超时或 smoke 失败时返回非 0 退出码。按 Ctrl+C 会优雅退出并清理子进程。

## Profile Memory 读写验收

写入一条长期记忆：

```powershell
$body = @{
  source_agent = "manual-profile-test"
  trace_id = "trace-manual-profile-write"
  user_id = "elder-manual-001"
  memory_key = "favorite_drink"
  memory_value = "ginger_tea"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  http://127.0.0.1:8124/vitalai/flows/profile-memory `
  -ContentType "application/json" `
  -Body $body
```

读取当前用户画像快照：

```powershell
Invoke-RestMethod `
  -Method Get `
  "http://127.0.0.1:8124/vitalai/flows/profile-memory/elder-manual-001?source_agent=manual-profile-test&trace_id=trace-manual-profile-read"
```

预期返回 `profile_snapshot.memory_count=1`，并能看到刚写入的 `favorite_drink=ginger_tea`。

按 key 精确读取单条记忆：

```powershell
Invoke-RestMethod `
  -Method Get `
  "http://127.0.0.1:8124/vitalai/flows/profile-memory/elder-manual-001?source_agent=manual-profile-test&trace_id=trace-manual-profile-read-key&memory_key=favorite_drink"
```

预期返回 `profile_snapshot.memory_count=1`，且 `profile_snapshot.entries[0].memory_key=favorite_drink`。如果 `memory_key` 不存在，会返回同一用户的稳定空 snapshot。

## Health Alert 历史验收

写入一条健康预警：

```powershell
$body = @{
  source_agent = "manual-health-test"
  trace_id = "trace-manual-health-write"
  user_id = "elder-manual-health-001"
  risk_level = "high"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  http://127.0.0.1:8124/vitalai/flows/health-alert `
  -ContentType "application/json" `
  -Body $body
```

读取当前用户最近健康预警历史：

```powershell
Invoke-RestMethod `
  -Method Get `
  "http://127.0.0.1:8124/vitalai/flows/health-alerts/elder-manual-health-001?source_agent=manual-health-test&trace_id=trace-manual-health-read&limit=10"
```

预期返回 `health_alert_snapshot.alert_count=1`，并能看到 `recent_risk_levels` 中包含 `high`。写入响应本身也会带出 `health_alert_entry` 与 `health_alert_snapshot`，方便人工确认 SQLite 历史已经落盘。

如果要手动验证最小状态流，可以继续执行：

```powershell
$body = @{
  source_agent = "manual-health-test"
  trace_id = "trace-manual-health-ack"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Patch `
  http://127.0.0.1:8124/vitalai/flows/health-alerts/elder-manual-health-001/1/acknowledge `
  -ContentType "application/json" `
  -Body $body
```

```powershell
$body = @{
  source_agent = "manual-health-test"
  trace_id = "trace-manual-health-resolve"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Patch `
  http://127.0.0.1:8124/vitalai/flows/health-alerts/elder-manual-health-001/1/resolve `
  -ContentType "application/json" `
  -Body $body
```

`acknowledge / resolve` 应只作用于单条 alert 记录，所以请使用写入响应里返回的 `health_alert_entry.alert_id`，不要手填固定 id。

这是当前 health 的最小历史闭环，不包含健康档案、提醒调度、医疗规则引擎或复杂病程管理。实现范围包括领域 entry/snapshot、SQLite record、repository、query/use case/workflow 和只读 HTTP API。

## Daily Life 历史验收

写入一条日常生活 check-in：

```powershell
$body = @{
  source_agent = "manual-daily-test"
  trace_id = "trace-manual-daily-write"
  user_id = "elder-manual-daily-001"
  need = "meal_support"
  urgency = "normal"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  http://127.0.0.1:8124/vitalai/flows/daily-life-checkin `
  -ContentType "application/json" `
  -Body $body
```

读取当前用户最近日常生活历史：

```powershell
Invoke-RestMethod `
  -Method Get `
  "http://127.0.0.1:8124/vitalai/flows/daily-life-checkins/elder-manual-daily-001?source_agent=manual-daily-test&trace_id=trace-manual-daily-read&limit=10"
```

预期返回 `daily_life_snapshot.checkin_count=1`，并能看到 `recent_needs` 中包含 `meal_support`。写入响应本身也会带出 `checkin_entry` 与 `daily_life_snapshot`，方便人工确认 SQLite 历史已经落盘。

这是当前 daily_life 的最小历史闭环，不包含任务状态机、提醒调度或复杂服务单系统。实现范围包括领域 entry/snapshot、SQLite record、repository、query/use case/workflow 和只读 HTTP API。

## Mental Care 历史验收

写入一条精神关怀 check-in：

```powershell
$body = @{
  source_agent = "manual-mental-test"
  trace_id = "trace-manual-mental-write"
  user_id = "elder-manual-mental-001"
  mood_signal = "calm"
  support_need = "companionship"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  http://127.0.0.1:8124/vitalai/flows/mental-care-checkin `
  -ContentType "application/json" `
  -Body $body
```

读取当前用户最近精神关怀历史：

```powershell
Invoke-RestMethod `
  -Method Get `
  "http://127.0.0.1:8124/vitalai/flows/mental-care-checkins/elder-manual-mental-001?source_agent=manual-mental-test&trace_id=trace-manual-mental-read&limit=10"
```

预期返回 `mental_care_snapshot.checkin_count=1`，并能看到 `recent_mood_signals` 中包含 `calm`。写入响应本身也会带出 `mental_care_entry` 与 `mental_care_snapshot`，方便人工确认 SQLite 历史已经落盘。

这是当前 mental_care 的最小历史闭环，不包含心理量表、长期情绪趋势、多轮陪伴或复杂干预系统。实现范围包括领域 entry/snapshot、SQLite record、repository、query/use case/workflow 和只读 HTTP API。

## 用户交互入口验收

最小用户交互入口是 backend-only，不包含前端 UI / App / 完整聊天系统。

当前支持的 `event_type`：

- `health_alert`
- `daily_life_checkin`
- `mental_care_checkin`
- `profile_memory_update`
- `profile_memory_query`

也支持少量别名，例如 `remember` 会归一化为 `profile_memory_update`，`recall` 会归一化为 `profile_memory_query`。

如果不传 `event_type`，系统会先使用第一层意图识别器，从 `message` 中识别基础意图。默认识别器是规则型实现；如果配置本地 BERT intent 模型，也可以切换到 `bert` 或 `hybrid` 模式。

对于健康+日常、心理/情绪+用药、记忆+家庭/日常词等复合语言或多任务输入，第一层不会强行路由到某个领域 workflow，而是返回 `error=decomposition_needed`。当前第二层已经可以接入真实 LLM backend，但仍只返回结构化拆分结果与守门信息，不会直接执行领域 workflow。响应中的 `error_details.decomposition` 会包含 `pending_second_layer`、`candidate_tasks`、`risk_flags` 和 `routing_decision`，方便人工验收。

未来真实 LLM 的第二层输出必须先通过本地 schema validator：`validate_intent_decomposition_llm_payload`。校验会拒绝缺少 `primary_task` 的路由决策、非法 intent、越界 priority/confidence、非法 risk severity 等输出；不合法输出不会进入 workflow 路由。

当前 `LLMIntentDecomposer` 已支持两种接法，并可通过 `VITALAI_INTENT_DECOMPOSER=placeholder|llm` 选择。默认是 `placeholder`；设置为 `llm` 时，如果真实 backend 缺失或异常，也会 fallback 到 placeholder；backend 输出非法时只返回 validation issues，不会进入领域 workflow。默认 provider 是 `openai_compatible`，也支持显式复用 `Base.Ai` 中已经封装好的 `Qwen` 客户端：`VITALAI_INTENT_DECOMPOSER_LLM_PROVIDER=base_qwen`。

为了让真实二层验收更稳，当前默认超时已经按 provider 分开：`openai_compatible` 维持 `5s`，`base_qwen` 在未显式设置 `VITALAI_INTENT_DECOMPOSER_LLM_TIMEOUT_SECONDS` 时会自动放宽到 `30s`。

如果只是想快速确认当前二层是不是还在 `placeholder`、provider 是谁、配置是否齐全，可以直接读：

```text
GET /vitalai/flows/intent-decomposer-status/api
```

这个状态接口只报告当前装配状态和安全边界，不会触发真实 LLM 调用。

意图识别器可通过环境变量选择：

```powershell
$env:VITALAI_INTENT_RECOGNIZER="rule_based"  # 默认
$env:VITALAI_INTENT_RECOGNIZER="bert"        # 使用本地 BERT 模型，失败或低置信时 fallback
$env:VITALAI_INTENT_RECOGNIZER="hybrid"      # 预留混合策略
$env:VITALAI_BERT_INTENT_MODEL_PATH="D:\AI\Models\fine-tuned-bert-intent-vitalai-trained"
$env:VITALAI_BERT_INTENT_CONFIDENCE_THRESHOLD="0.65"
$env:VITALAI_BERT_INTENT_LABELS="health_alert,daily_life_checkin,mental_care_checkin,profile_memory_update,profile_memory_query,unknown"
$env:VITALAI_INTENT_DECOMPOSER="llm"
$env:VITALAI_INTENT_DECOMPOSER_LLM_PROVIDER="openai_compatible"
$env:VITALAI_INTENT_DECOMPOSER_LLM_MODEL="glm-5.1"
$env:VITALAI_INTENT_DECOMPOSER_LLM_API_KEY="your_llm_api_key"
$env:VITALAI_INTENT_DECOMPOSER_LLM_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"
$env:VITALAI_INTENT_DECOMPOSER_LLM_TEMPERATURE="0.0"
$env:VITALAI_INTENT_DECOMPOSER_LLM_TIMEOUT_SECONDS="5.0"
```

如果想直接复用 `Base` 里的千问封装，可以这样配：

```powershell
$env:VITALAI_INTENT_DECOMPOSER="llm"
$env:VITALAI_INTENT_DECOMPOSER_LLM_PROVIDER="base_qwen"
```

第二层 backend 当前使用通用 OpenAI-compatible 调用方式，因此除了 GLM 5.1，也可以按相同模式切换到兼容接口的 Qwen、DeepSeek 或其他模型；只需要替换 model / api_key / base_url。

离线 hard-case 评测基线可直接运行：

```powershell
python scripts\intent_eval\evaluate_second_layer_hard_cases.py --output text
```

当前样本位于 `data/intent_eval/second_layer_hard_cases.jsonl`，评测说明见 `docs/evals/SECOND_LAYER_HARD_CASE_EVAL.md`。

如果要回放真实 GLM 5.1 / Qwen / DeepSeek 的原始响应文本，也可以直接运行：

```powershell
python scripts\intent_eval\evaluate_second_layer_hard_cases.py --dataset data\intent_eval\second_layer_response_snapshots.jsonl --output text
```

这个数据集支持 `raw_response_text`，可用于验证 markdown code fence、JSON 外层解释性文本、schema 非法输出和纯解析失败。

如果要直接采第一批真实响应快照，可以先配置：

```powershell
$env:VITALAI_INTENT_DECOMPOSER_LLM_PROVIDER="openai_compatible"
$env:VITALAI_INTENT_DECOMPOSER_LLM_MODEL="glm-5.1"
$env:VITALAI_INTENT_DECOMPOSER_LLM_API_KEY="your_llm_api_key"
$env:VITALAI_INTENT_DECOMPOSER_LLM_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"
python scripts\intent_eval\capture_second_layer_response_snapshots.py
```

默认案例模板位于 `data/intent_eval/second_layer_capture_cases.jsonl`，当前已扩到 16 条首批采样模板，覆盖 `mental_care + medication`、`health + daily_life`、`profile_memory + family`、`health + safety`、安全 memory/daily 候选、英文输入、脏响应诱发场景和明确拒绝/澄清场景。默认输出位于 `.runtime\intent_eval\second_layer_captured_snapshots.jsonl`。这份输出是待审核快照，不会自动进入回放基线。

如果想让采样脚本直接复用 `Base` 里的千问封装，也可以把 provider 切到 `base_qwen`：

```powershell
$env:VITALAI_INTENT_DECOMPOSER_LLM_PROVIDER="base_qwen"
python scripts\intent_eval\capture_second_layer_response_snapshots.py --category profile_memory --limit 2
```

如果采样脚本走 `base_qwen` 且没有显式设置超时，它也会默认使用 `30s`，避免真实采样时因为默认超时过紧而把有效响应误判成失败。

如果只想先跑一个小批次，可以先列出或过滤采样模板：

```powershell
python scripts\intent_eval\capture_second_layer_response_snapshots.py --list-cases
python scripts\intent_eval\capture_second_layer_response_snapshots.py --category health+medication --limit 2
python scripts\intent_eval\capture_second_layer_response_snapshots.py --id capture_004_chest_pain --id capture_016_medication_aftereffect
python scripts\intent_eval\capture_second_layer_response_snapshots.py --category profile_memory --skip-existing --append
```

`--skip-existing` 会读取当前输出 JSONL 里的已采样 `id`，避免你分批补采时把同一个 case 重复打到模型。

把采样结果转成待审核 queue：

```powershell
python scripts\intent_eval\build_second_layer_snapshot_review_queue.py
python scripts\intent_eval\evaluate_second_layer_hard_cases.py --dataset .runtime\intent_eval\second_layer_snapshot_review_queue.jsonl --output text
```

queue 文件默认位于 `.runtime\intent_eval\second_layer_snapshot_review_queue.jsonl`，会自动带上建议 `expected`、`review_status=pending_human_review` 和来源 metadata。你人工审核后，可以直接继续用同一个评测脚本回放它。

如果你不想手工改 JSONL，可以直接用 review queue 管理脚本：

```powershell
python scripts\intent_eval\manage_second_layer_snapshot_review_queue.py summary
python scripts\intent_eval\manage_second_layer_snapshot_review_queue.py triage-report --review-status pending_human_review
python scripts\intent_eval\manage_second_layer_snapshot_review_queue.py list --review-status pending_human_review --bulk-approval eligible_for_bulk_approval
python scripts\intent_eval\manage_second_layer_snapshot_review_queue.py show --id capture_001_medication_emotion --include-raw-response
python scripts\intent_eval\manage_second_layer_snapshot_review_queue.py set-status --id capture_001_medication_emotion --status approved_for_baseline --notes "human reviewed"
python scripts\intent_eval\manage_second_layer_snapshot_review_queue.py bulk-set-status --review-status pending_human_review --bulk-approval eligible_for_bulk_approval --status approved_for_baseline --notes "bulk reviewed"
```

这个脚本当前支持 `summary / triage-report / list / show / set-status / bulk-set-status`。review queue 现在还会自动给出 `review_recommendation`：
- `approve_candidate`
- `manual_review_required`
- `baseline_negative_candidate`

另外还会单独给出更保守的 `bulk_approval_recommendation`：
- `eligible_for_bulk_approval`
- `requires_manual_approval`
- `not_applicable_for_bulk_approval`

实际使用时，通常先跑 `triage-report` 看 recommendation 和 bulk approval 的原因分布，再 `list` 出 `pending_human_review + bulk_approval=eligible_for_bulk_approval` 的候选，最后决定逐条确认还是批量标成 `approved_for_baseline`。

把审核通过的项正式并入回放数据集：

```powershell
python scripts\intent_eval\promote_second_layer_snapshot_review_queue.py
python scripts\intent_eval\evaluate_second_layer_hard_cases.py --dataset data\intent_eval\second_layer_response_snapshots.jsonl --output text
python scripts\intent_eval\audit_second_layer_snapshot_baseline.py --output text
```

这个步骤只会提升 `review_status=approved_for_baseline` 的项，并按 `id` 合并进正式数据集。最后建议再跑一次 baseline audit，确认正式数据集里的 review provenance、bulk approval provenance 和 source capture 没有缺口。

`bert` / `hybrid` 只会从本地 `VITALAI_BERT_INTENT_MODEL_PATH` 加载模型，不会下载模型。模型路径为空、路径不存在、推理依赖缺失、推理异常或置信度低于阈值时，会 fallback 到 `rule_based`。`VITALAI_BERT_INTENT_LABELS` 可用有序标签，也可用 `LABEL_0=health_alert,LABEL_1=daily_life_checkin` 形式显式映射模型输出。训练/评估样本格式见 `docs/intent_dataset_examples.jsonl`。

当前已导出的 bootstrap 模型路径是 `D:\AI\Models\fine-tuned-bert-intent-vitalai-trained`。它用于验证 BERT adapter、label 映射、fallback 和 API 启用链路；由于它基于当前工程基线样本训练和验收，不能直接视为生产泛化模型。

离线评估当前意图识别器：

```powershell
python scripts\evaluate_intents.py --recognizer rule_based
python scripts\evaluate_intents.py --recognizer rule_based --group-by-split
C:\Users\Windows\miniconda3\python.exe scripts\evaluate_intents.py --recognizer bert --bert-model-path "D:\AI\Models\fine-tuned-bert-intent-vitalai-trained" --bert-labels "health_alert,daily_life_checkin,mental_care_checkin,profile_memory_update,profile_memory_query,unknown"
C:\Users\Windows\miniconda3\python.exe scripts\evaluate_intents.py --recognizer bert --bert-model-path "D:\AI\Models\fine-tuned-bert-intent-vitalai-trained" --bert-labels "health_alert,daily_life_checkin,mental_care_checkin,profile_memory_update,profile_memory_query,unknown" --splits holdout --group-by-split
C:\Users\Windows\miniconda3\python.exe scripts\check_bert_intent_runtime.py --model-path "D:\AI\Models\fine-tuned-bert-intent-vitalai-trained" --bert-labels "health_alert,daily_life_checkin,mental_care_checkin,profile_memory_update,profile_memory_query,unknown"
```

预期输出 JSON 报告，包含 `total / passed / failed / accuracy / by_intent / by_source / by_dataset_source / fallback / clarification / failures`。当前 baseline 数据集覆盖 5 类业务意图和 `unknown` 澄清样本，每类 30 条、共 180 条；另有 holdout 样本 108 条，其中 33 条为 `needs_decomposition` 复合/歧义表达，18 条为 `hardcase_guard_precision_v1` 困难边界样本。`--splits baseline` 会只评估 `train/dev/test`，`--splits holdout` 会只评估 holdout，`--group-by-split` 会按 split 展开报告。

当前 `rule_based` 全量为 `288/288`。当前 bootstrap BERT 模型在 baseline 上为 `180/180`，其中 `142` 条由 BERT 直接识别，`25` 条由 `bert_hard_case_guard` 兜底，`13` 条通过低置信 fallback 成功路由；在 holdout 上为 `108/108`，其中 `33` 条进入 `needs_decomposition_detector`，`33` 条由 BERT 直接识别成功，`27` 条由 `bert_hard_case_guard` 兜底，`15` 条通过低置信 fallback 成功路由。`hardcase_guard_precision_v1` 当前为 `18/18`。

如需从本地 base BERT 重新导出 bootstrap 分类模型：

```powershell
C:\Users\Windows\miniconda3\python.exe scripts\train_bert_intent_classifier.py `
  --base-model-path "D:\AI\Models\fine-tuned-bert-intent" `
  --output-path "D:\AI\Models\fine-tuned-bert-intent-vitalai-trained" `
  --epochs 300 `
  --batch-size 16 `
  --learning-rate 5e-3 `
  --max-length 64 `
  --train-splits train,dev,test `
  --freeze-base `
  --precompute-frozen-base
```

通过自然语言触发健康预警：

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$body = @{
  user_id = "elder-manual-003"
  channel = "manual"
  message = "我刚刚摔倒了，现在有点头晕"
  trace_id = "trace-manual-interaction-intent-health"
} | ConvertTo-Json
$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)

Invoke-RestMethod `
  -Method Post `
  http://127.0.0.1:8124/vitalai/interactions `
  -ContentType "application/json; charset=utf-8" `
  -Body $bytes
```

预期返回 `routed_event_type=HEALTH_ALERT`，并且 `intent.primary_intent=health_alert`。如果当前使用 `VITALAI_INTENT_RECOGNIZER=bert` 和 bootstrap 模型，`intent.source` 应优先为 `bert`；默认规则模式下则为 `rule_based`。

Windows PowerShell 手动发送中文 JSON 时，建议像上面一样把 body 转成 UTF-8 bytes；否则可能出现请求或响应乱码，导致人工验收误判。

通过复合表达触发第二层拆分占位：

```powershell
$body = @{
  user_id = "elder-manual-004"
  channel = "manual"
  message = "我心里老是慌慌的，那个药我到底要不要天天吃啊。"
  trace_id = "trace-manual-interaction-decomposition"
} | ConvertTo-Json
$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)

Invoke-RestMethod `
  -Method Post `
  http://127.0.0.1:8124/vitalai/interactions `
  -ContentType "application/json; charset=utf-8" `
  -Body $bytes
```

预期返回 `accepted=false`、`error=decomposition_needed`、`intent.requires_decomposition=true`、`intent.source=needs_decomposition_detector`，并且 `error_details.decomposition.status=pending_second_layer`、`error_details.decomposition.ready_for_routing=false`。当前这是第二层 LLM 意图拆分的接口边界，不会直接执行用药、心理或健康领域 workflow。

通过交互入口写入记忆：

```powershell
$body = @{
  user_id = "elder-manual-002"
  channel = "manual"
  message = "I like jasmine tea."
  event_type = "profile_memory_update"
  trace_id = "trace-manual-interaction-write"
  context = @{
    memory_key = "favorite_drink"
    memory_value = "jasmine_tea"
  }
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  http://127.0.0.1:8124/vitalai/interactions `
  -ContentType "application/json" `
  -Body $body
```

通过交互入口读取记忆：

```powershell
$body = @{
  user_id = "elder-manual-002"
  channel = "manual"
  message = "What do you remember about me?"
  event_type = "profile_memory_query"
  trace_id = "trace-manual-interaction-read"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  http://127.0.0.1:8124/vitalai/interactions `
  -ContentType "application/json" `
  -Body $body
```

预期返回统一交互响应，其中 `routed_event_type=PROFILE_MEMORY_QUERY`，并且 `memory_updates.profile_snapshot.memory_count` 大于 0。

校验错误验收：

```powershell
$body = @{
  event_type = "health_alert"
  channel = "manual"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  http://127.0.0.1:8124/vitalai/interactions `
  -ContentType "application/json" `
  -Body $body
```

预期仍返回统一交互响应，`accepted=false`，`error=invalid_request`，并在 `error_details.issues` 中说明缺失的 `user_id` 和 `message`。

## 测试方式

在仓库根目录直接运行：

```bash
pytest tests -q
```

最近交接验证结果：

- targeted mental_care/API/assembly/scheduler/consumer 测试：`65 passed`
- targeted health/daily_life/API/assembly/scheduler/consumer 测试：`66 passed`
- typed flow history smoke/API/assembly/scheduler targeted 测试：`71 passed`
- full test：`220 passed`
- `git diff --check`：无格式错误，仅有 Windows LF/CRLF 提示

---

## 新窗口开发前建议阅读

每次新开一个窗口，建议先读：

1. `docs/DOCS_INDEX.md`
2. `docs/PROJECT_CONTEXT.md`
3. `docs/CURRENT_STATUS.md`
4. `docs/NEXT_TASK.md`
5. `README.md`

然后再根据当前模块去读对应的 `Base` 目录。
