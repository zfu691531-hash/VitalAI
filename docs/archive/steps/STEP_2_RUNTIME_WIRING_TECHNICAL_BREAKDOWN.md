# 第二步：Runtime Wiring 技术拆解

## 文档目的

这份文档记录第二步开发工作的技术落点：在第一步已经定义好 platform contracts 的基础上，把 runtime shell 开始接到这些 typed objects 上。

第一步解决的是“协议存在吗”。
第二步解决的是“运行时是否真的开始使用这些协议”。

---

## 本轮目标

本轮重点收敛了这条链路：

- `EventAggregator`
- `DecisionCore`
- `SnapshotStore`
- `FailoverCoordinator`

目标不是实现完整业务逻辑，而是把它们从原始 `dict` 边界推进到更明确的 contract 边界。

---

## 文件 1：`VitalAI/platform/runtime/event_aggregator.py`

### 改动点

这个文件原来只保存 `list[dict[str, Any]]`，现在改成了两层结构：

- 入口层接收 `MessageEnvelope`
- 输出层生成 `EventSummary`

新增了：

- `EventSummary`

并调整了：

- `raw_events: list[MessageEnvelope]`
- `ingest(event: MessageEnvelope) -> bool`
- `summarize() -> list[EventSummary]`

### 技术意义

这一步明确了 event aggregator 的边界：

- 它接收的不是任意字典，而是有效的消息信封
- 它输出的不是松散字典，而是给 decision core 消费的结构化摘要

同时 `ingest()` 现在会拒绝已过期消息，这让消息 TTL 第一次真正进入 runtime 流程。

---

## 文件 2：`VitalAI/platform/runtime/decision_core.py`

### 改动点

这个文件原来处理 `dict[str, Any]`，现在改为：

- `DecisionHandler = Callable[[EventSummary], MessageEnvelope | None]`
- `process_summary(summary: EventSummary) -> MessageEnvelope | None`

### 技术意义

这一步让 decision core 的输入输出第一次变得对称而明确：

- 输入：`EventSummary`
- 输出：`MessageEnvelope | None`

也就是说，decision core 不再面对原始事件堆，而是面对 event aggregator 已经整理过的摘要对象。

---

## 文件 3：`VitalAI/platform/runtime/snapshots.py`

### 改动点

这个文件新增了：

- `RuntimeSnapshot.to_reference()`
- `SnapshotStore.get_reference()`

并引入了：

- `SnapshotReference`

### 技术意义

这一步把 snapshot 存储层和 interrupt 层第一次接通。

以前快照只是内部对象，现在它可以显式转换成 interrupt/failover 可识别的 `SnapshotReference`。
这样后续中断恢复流程就不需要自己再拼一份“快照描述字典”。

---

## 文件 4：`VitalAI/platform/runtime/failover.py`

### 改动点

这个文件现在开始显式感知 `InterruptSignal`：

- `last_signal: InterruptSignal | None`
- `should_failover(signal: InterruptSignal | None = None) -> bool`
- `failover(signal: InterruptSignal | None = None) -> bool`

并增加了基于中断动作和快照引用的最小判断：

- 只接受 `TAKEOVER`
- 如果该信号需要快照，就必须真的附带快照引用

### 技术意义

这让 failover 不再只是“shadow 有快照就切换”，而是开始具备“中断语义感知”。

虽然现在还很轻，但方向已经对了：

- failover 开始由 interrupt 驱动
- interrupt 是否有效要看 signal 内容
- signal 是否可执行要看 snapshot 是否齐备

---

## 文件 5：`VitalAI/platform/runtime/__init__.py`

### 改动点

补导出了：

- `EventSummary`

### 技术意义

这样 runtime 这一层的公开边界更完整，后续调用方不需要再跳进模块深处拿 summary 类型。

---

## 文件 6：`tests/platform/test_runtime_contract_wiring.py`

### 改动点

新增了 3 个最小测试：

1. `EventAggregator` 能接收 `MessageEnvelope` 并产出 `EventSummary`
2. `DecisionCore` 能消费 `EventSummary` 并产出 `MessageEnvelope`
3. `SnapshotStore + InterruptSignal + FailoverCoordinator` 能串起最小接管流程

### 技术意义

这不是完整测试体系，但足够验证第二步的核心目标：

- typed contract 不只是“定义出来了”
- runtime shell 已经开始真的依赖它们

---

## 本轮结果

到第二步结束时，runtime 这条链路已经从：

`raw dict -> raw dict -> ad hoc failover`

推进成了：

`MessageEnvelope -> EventSummary -> MessageEnvelope -> InterruptSignal/SnapshotReference`

这一步仍然保持极简，但已经把“平台协议层”从定义推进到了使用。
