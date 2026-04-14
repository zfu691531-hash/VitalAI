# 第一步：Platform Contracts 技术拆解

## 文档目的

这份文档从纯技术视角解释本轮开发到底做了什么，重点不是讲项目愿景，而是讲：

- 为什么先做这一步
- 具体改了哪些文件
- 每个文件在系统里承担什么职责
- 这些文件之间如何衔接
- 下一步应该如何继续接线

本轮工作的主题可以概括为：

`先为 VitalAI 的 platform 层建立一批轻量、可复用、可扩展的 typed contracts。`

这些 contract 不是业务逻辑，也不是数据库模型，而是系统运行时组件之间的“统一输入输出协议”。

---

## 为什么这一步要先做

在本轮开始前，`VitalAI/platform/runtime/` 已经有了第一批 runtime shell：

- `decision_core.py`
- `event_aggregator.py`
- `health_monitor.py`
- `shadow_decision_core.py`
- `snapshots.py`
- `degradation.py`
- `failover.py`

这些文件已经把运行时职责拆开了，这是正确方向。但它们仍然主要使用原始的 `dict[str, Any]` 作为交换对象。

这种做法在项目很早期能跑得快，但会带来几个技术问题：

1. 结构不稳定
   不同模块都可能各自约定不同字段名，久而久之会形成隐式耦合。

2. 可读性差
   当某个运行时函数收一个普通字典时，读代码的人不知道必填字段是什么、语义边界是什么。

3. 不利于扩展
   后续如果接入消息队列、审计、优先级调度、故障切换、学习反馈，都会需要一套稳定 contract。

4. 不利于仲裁与中断
   arbitration 和 interrupt 这种模块天然要求输入结构清晰，否则后续很容易“边做边猜”。

所以这一步不是在做“更多功能”，而是在做“后续所有功能都要踩到的协议层”。

---

## 先做了哪些上下文确认

正式编码前，先读了下面这些内容：

- `docs/PROJECT_CONTEXT.md`
- `docs/CURRENT_STATUS.md`
- `docs/NEXT_TASK.md`
- `README.md`
- `VitalAI/platform/runtime/*`
- `Base/Models/*`
- `Base/RicUtils/*`

这里的关键判断是：

- `Base` 里有数据库模型、工具函数、基础设施封装
- 但 `Base` 没有现成的 platform runtime contract 层
- 因此这批 contract 不应该硬塞进 `Base`
- 它们更适合留在 `VitalAI/platform`，因为它们承载的是 VitalAI 自身的运行时语义

换句话说，这一轮明确了一个边界：

- `Base` 负责通用基础能力
- `VitalAI/platform` 负责系统运行时协议

---

## 文件 1：`VitalAI/platform/messaging/message_envelope.py`

### 作用

这个文件定义了跨组件、跨 agent 通信时的标准消息信封。

核心类与枚举：

- `MessagePriority`
- `MessageEnvelope`

### 为什么要单独有消息信封

系统后续一定会出现大量内部通信，例如：

- 健康监测组件向决策核心上报风险
- 决策核心向某个 agent 下发执行指令
- 某个 agent 对上一条消息做异步回复

如果没有统一信封，每个模块都可能自己定义：

- 用 `type`
- 或用 `event`
- 或用 `kind`
- 有的带追踪 ID，有的不带
- 有的有 TTL，有的永久有效

结果就是同样叫“消息”，但格式其实不兼容。

### 结构设计

`MessageEnvelope` 当前定义了这些核心字段：

- `msg_id`
- `trace_id`
- `from_agent`
- `to_agent`
- `reply_to`
- `priority`
- `msg_type`
- `version`
- `ttl`
- `require_ack`
- `timestamp`
- `expire_at`
- `payload`

### 关键实现点

1. 使用 `@dataclass(slots=True)`
   这说明对象是轻量 contract，而不是带复杂行为的 service。

2. `msg_id` 和 `trace_id` 默认自动生成
   这样即使调用方不手动传，也能得到最基本的唯一标识和链路标识。

3. `ttl` 与 `expire_at` 自动联动
   在 `__post_init__` 里，如果提供了 `ttl` 但没有传 `expire_at`，会自动算出过期时间。

4. 提供 `is_expired()` 和 `can_reply()`
   这两个方法是很小但很有价值的运行时语义辅助。

### 技术意义

这份 contract 为后续这些能力打地基：

- 消息总线
- ACK / retry
- dead letter queue
- trace 追踪
- 过期消息清理

---

## 文件 2：`VitalAI/platform/feedback/events.py`

### 作用

这个文件定义反馈事件 contract，用于承接 L1/L2/L3 反馈闭环。

核心类与枚举：

- `FeedbackLayer`
- `FailureDetails`
- `FeedbackEvent`

### 为什么 feedback 需要先独立成 contract

VitalAI 不是“执行完就结束”的系统，它需要逐步形成：

- 执行反馈
- 质量反馈
- 学习反馈

例如同一个任务，系统不仅要知道“做没做”，还要知道：

- 完成度是多少
- 质量怎么样
- 置信度高不高
- 失败的话是什么原因
- 这个失败是否可重试

如果这些信息只是散落在日志里，后面就没法做聚合、评分、经验沉淀。

### 结构设计

`FeedbackEvent` 当前包含：

- `event_id`
- `trace_id`
- `agent_id`
- `task_id`
- `event_type`
- `feedback_layer`
- `confidence_score`
- `quality_score`
- `completion_rate`
- `timestamp`
- `duration_ms`
- `summary`
- `payload`
- `failure`

其中 `failure` 使用单独的 `FailureDetails` 表示，避免把失败信息拆成一堆松散字段。

### 关键实现点

1. `FeedbackLayer` 用 `L1 / L2 / L3`
   直接和架构文档中的反馈层概念对齐。

2. 失败信息单独建模
   `FailureDetails` 里包含：
   - `error_code`
   - `message`
   - `retryable`
   - `detail`

3. 提供 `is_failure()` 和 `is_terminal()`
   - `is_failure()` 判断是否携带失败元数据
   - `is_terminal()` 判断事件是否代表一个终止状态

### 技术意义

这份 contract 后面可以自然接到：

- feedback aggregator
- 任务质量评估
- agent 表现统计
- 自动重试判断
- 学习信号沉淀

---

## 文件 3：`VitalAI/platform/arbitration/intents.py`

### 作用

这个文件定义 arbitration 输入 contract，也就是“意图声明”。

核心类与枚举：

- `GoalType`
- `Flexibility`
- `ResourceRequirement`
- `IntentDeclaration`

### 为什么先做 intent declaration

只要系统里出现多个 agent、多种任务、多种资源，就一定会遇到冲突：

- 谁先执行
- 谁可以延后
- 谁必须抢占
- 谁要独占资源

如果没有统一的意图声明，仲裁层就只能对着各模块自定义的数据结构做兼容，非常脆弱。

### 结构设计

`IntentDeclaration` 当前包含：

- `intent_id`
- `agent_id`
- `submit_time`
- `action`
- `target_time`
- `content_preview`
- `resources_needed`
- `goal_type`
- `goal_weight`
- `flexibility`

其中资源需求通过 `ResourceRequirement` 表示，而不是直接塞进普通字典。

### 关键实现点

1. `GoalType`
   先定义一批高层目标类型：
   - `SAFETY`
   - `HEALTH`
   - `DAILY_LIFE`
   - `MENTAL_CARE`
   - `REPORTING`
   - `SYSTEM`

2. `Flexibility`
   明确目标是否允许调整：
   - `FIXED`
   - `PREFERRED`
   - `FLEXIBLE`

3. `resources_needed`
   用 `list[ResourceRequirement]` 表示，后续很容易接资源锁和排队机制。

4. 提供：
   - `requires_exclusive_resources()`
   - `is_time_sensitive()`

### 技术意义

这份 contract 为后续这些能力做准备：

- 目标冲突检测
- 权重仲裁
- 时间窗口比较
- 抢占式调度
- 共享资源锁

---

## 文件 4：`VitalAI/platform/interrupt/signals.py`

### 作用

这个文件定义中断层的输入 contract，用于 P0-P3 紧急中断。

核心类与枚举：

- `InterruptPriority`
- `InterruptAction`
- `SnapshotReference`
- `InterruptSignal`

### 为什么 interrupt 也要单独建 contract

中断场景通常比普通调度场景更严格，因为它要求：

- 优先级明确
- 动作明确
- 触发原因明确
- 恢复上下文明确

尤其是在 failover / snapshot / resume 这种流程里，如果没有稳定结构，后面就很容易出现“知道要恢复，但不知道从哪个快照恢复”的问题。

### 结构设计

`InterruptSignal` 当前包含：

- `signal_id`
- `trace_id`
- `source`
- `priority`
- `action`
- `reason`
- `target`
- `timestamp`
- `snapshot_refs`
- `payload`

### 关键实现点

1. 中断分级使用 `P0 ~ P3`
   直接贴合中断层设计文档。

2. 中断动作用枚举表达
   当前支持：
   - `PAUSE`
   - `RESUME`
   - `CANCEL`
   - `TAKEOVER`
   - `ESCALATE`

3. `SnapshotReference`
   专门用来指向恢复或接管所需快照：
   - `snapshot_id`
   - `source`
   - `captured_at`
   - `version`

4. 提供：
   - `needs_interrupt_snapshot()`
   - `has_snapshot_refs()`

### 技术意义

这份 contract 后续能与这些运行时组件对接：

- `snapshots.py`
- `shadow_decision_core.py`
- `failover.py`
- 未来的 interrupt state machine

---

## 文件 5 到 8：四个子包的 `__init__.py`

本轮还更新了四个子包的导出文件：

- `VitalAI/platform/messaging/__init__.py`
- `VitalAI/platform/feedback/__init__.py`
- `VitalAI/platform/arbitration/__init__.py`
- `VitalAI/platform/interrupt/__init__.py`

### 作用

这些文件的更新目的不是“增加功能”，而是统一包级导出。

例如现在可以直接这样引用：

```python
from VitalAI.platform.messaging import MessageEnvelope
from VitalAI.platform.feedback import FeedbackEvent
from VitalAI.platform.arbitration import IntentDeclaration
from VitalAI.platform.interrupt import InterruptSignal
```

而不是每次都写到具体模块路径。

### 技术意义

这一步能带来几个好处：

- 统一外部调用方式
- 收敛模块边界
- 便于后续替换内部实现而不影响 import 习惯

---

## 文档同步：`docs/CURRENT_STATUS.md`

这个文件被更新，是为了把本轮开发从“临时上下文”变成“持久上下文”。

### 具体补了什么

1. 记录已经阅读过的 `Base` 目录
2. 记录已经完成的四个 platform contracts
3. 记录子包导出已补齐
4. 更新当前技术状态
5. 更新当前风险
6. 更新推荐的下一步方向

### 技术意义

这个更新不是可有可无的，因为这个项目显然会跨 session、跨窗口持续开发。

如果不把这轮边界写回文档，下一次很容易重复做判断：

- 还要不要检查 `Base`
- contract 到底做没做
- 下一步是继续建业务还是先接 runtime

现在这些问题已经在 `CURRENT_STATUS.md` 里被落档了。

---

## 文档同步：`docs/NEXT_TASK.md`

这个文件也被更新了，目的是把任务焦点从“定义 contract”切换到“使用 contract”。

### 更新后的任务方向

下一步不再是继续发明新 contract，而是：

- 让 `event_aggregator.py` 开始接受 typed inputs
- 让 `decision_core.py` 的输入输出边界变清晰
- 让 `failover.py` / `snapshots.py` 和 interrupt contract 对齐
- 加最小验证

### 技术意义

这个变化说明系统已经进入下一阶段：

- 前一阶段：先把协议立住
- 下一阶段：把运行时壳和协议真正接起来

---

## 为什么没有把这些 contract 放进 `Base`

这是本轮一个非常关键的技术判断。

### 已确认的事实

`Base` 目前提供的主要是：

- 配置
- 日志
- LLM 封装
- Repository / DB 抽象
- 通用工具函数
- 通用 service

### 为什么这批 contract 不适合放进去

因为这些对象表达的是 VitalAI 自己的系统运行时语义，例如：

- 跨 agent 消息
- 反馈层事件
- 仲裁层意图
- 中断层信号

它们不是“跨所有项目都适用的底层能力”，而是 VitalAI 当前平台架构的组成部分。

如果把它们提前塞进 `Base`，会带来两个风险：

1. `Base` 被业务运行时语义污染
2. 以后别的项目复用 `Base` 时被迫接受 VitalAI 的架构假设

所以这次刻意保持：

- 使用标准库和轻量 dataclass
- 不依赖 `Base` 的 DB model
- 不引入 import-time side effects

---

## 本轮验证做了什么

本轮没有去跑 `VitalAI.main`，原因是当前已知：

- `Base` 存在较重的 import-time side effects
- 环境里还有缺失依赖，例如 `minio`

所以本轮采用的是“最小验证”策略，只验证新 contract 本身是否可导入、可实例化、语义方法是否正常工作。

### 验证覆盖了什么

- `MessageEnvelope`
- `FeedbackEvent`
- `IntentDeclaration`
- `InterruptSignal`

### 验证价值

这说明本轮不是只把类型写在文件里，而是至少确认了：

- 模块可导入
- 构造函数可用
- 默认值合理
- 辅助判断方法可执行

---

## 当前技术状态总结

到本轮结束时，`VitalAI/platform` 的状态可以这样描述：

1. 目录结构已经稳定
2. runtime shell 已拆分
3. 四类核心 contract 已落地
4. package-level export 已补齐
5. 文档状态已同步
6. 下一步重点已经从“定义协议”转向“让 runtime 使用协议”

---

## 下一步建议

从纯技术衔接角度，最自然的下一步是：

1. 改 `event_aggregator.py`
   让它不再只接收原始 `dict`

2. 改 `decision_core.py`
   明确它到底消费哪种 summary / envelope / event

3. 改 `failover.py` 和 `snapshots.py`
   让中断快照引用真正接入 failover 流程

4. 增加最小测试
   先做 contract 和 runtime wiring 的轻量测试，不碰 `VitalAI.main`

---

## 一句话结论

这一步完成的不是业务功能，而是运行时协议层的第一批正式落地。

从代码层面看，这一步让 `VitalAI/platform` 从“有 runtime 壳”进入到了“有可被后续模块正式依赖的 contract 边界”阶段。
