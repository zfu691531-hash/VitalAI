# 第三步：Health / Shadow / Degradation 技术拆解

## 文档目的

这份文档记录第三步开发工作的技术落点：继续把剩余 runtime shell 往 typed contract 边界推进，重点覆盖健康监控、影子决策核心、降级策略。

如果说：

- 第一步是在定义 contract
- 第二步是在让主运行链路开始使用 contract

那么第三步解决的是：

`让运行时的监控、热备、降级也开始说同一种“平台协议语言”。`

---

## 本轮目标

本轮收敛的重点对象有三个：

- `HealthMonitor`
- `ShadowDecisionCore`
- `DegradationPolicy`

它们之前都还比较“壳”，更多只是占位。
这次的目标不是把它们做重，而是让它们和前两步已经建立的 contract 真正接起来。

---

## 文件 1：`VitalAI/platform/runtime/health_monitor.py`

### 改动点

这个文件原来只记录：

- `component_id -> datetime`

现在改成：

- `component_id -> HeartbeatRecord`

并新增了：

- `HeartbeatRecord`
- `is_stale()`
- `build_interrupt()`

### 技术意义

这一步让 health monitor 从“只记最近心跳时间”变成了“能基于心跳超时发出 typed interrupt”。

也就是说，健康监控第一次开始和 interrupt 层对接。

它现在可以在组件超时后生成：

- `InterruptSignal`
- `priority = P1`
- `action = TAKEOVER`

这为后续把健康异常直接接到 failover 流程，铺平了路。

---

## 文件 2：`VitalAI/platform/runtime/shadow_decision_core.py`

### 改动点

这个文件原来只保存原始 `dict` 快照。
现在改成直接保存：

- `RuntimeSnapshot`

并新增：

- `latest_reference()`

### 技术意义

这一步让影子核心和 snapshot 层真正对齐。

以前 shadow core 虽然“有快照”，但快照只是未约束字典。
现在它保存的是 typed `RuntimeSnapshot`，并且可以直接对外给出：

- `SnapshotReference`

这意味着 shadow core、snapshot store、interrupt/failover 终于共享同一套快照表示方式。

---

## 文件 3：`VitalAI/platform/runtime/degradation.py`

### 改动点

这个文件原来只能手动设定：

- `NORMAL`
- `ALERT`
- `DEGRADED`
- `SURVIVAL`

现在新增了：

- `apply_interrupt(signal: InterruptSignal) -> DegradationLevel`

### 技术意义

这一步让 degradation policy 第一次开始理解 interrupt 语义。

当前映射策略很轻：

- `P0 -> SURVIVAL`
- `P1 -> DEGRADED`
- `P2 -> ALERT`
- `P3 -> NORMAL`

虽然简单，但它表达了一个重要方向：

降级不再只是人工设定的状态，而是可以由运行时中断自动驱动。

---

## 文件 4：`VitalAI/platform/runtime/__init__.py`

### 改动点

这次补导出了：

- `HeartbeatRecord`

### 技术意义

这样 runtime 层对外暴露的类型边界继续变完整，后续其他模块需要引用心跳记录类型时，不需要深入模块内部。

---

## 文件 5：`tests/platform/test_runtime_contract_wiring.py`

### 改动点

这次在原有 3 个测试基础上，扩成了 5 个测试。

新增验证：

1. `HealthMonitor` 能对过期心跳生成 `InterruptSignal`
2. `DegradationPolicy` 能根据 `InterruptSignal.priority` 自动调整 level

并同步把 `ShadowDecisionCore` 测试改成真正接收 `RuntimeSnapshot`

### 技术意义

这意味着第三步不只是代码接线，还把这些接线最基本的行为验证补上了。

---

## 本轮结果

到第三步结束时，runtime 层已经从：

`决策链路 typed，监控/热备/降级仍偏松散`

推进成了：

`决策、快照、热备、监控、中断、降级开始共享同一套 typed runtime 语言`

这仍然是最小实现，但已经把 platform runtime 的几个关键方向接到了一起：

- 监控能触发中断
- 快照能提供统一引用
- 影子核心能消费 typed snapshot
- 降级策略能响应中断优先级
