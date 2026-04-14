# 第 21 步：补齐 observability 的最小 typed slice

## 这一步为什么先做 observability

在第 20 步接入 `mental_care` 之后，`health / daily_life / mental_care` 三条真实 typed flow 已经足够证明当前 `application + workflow + assembly` 结构是成立的。

所以下一步不再继续扩 flow 抽象，而是回到还明显偏空的 `platform` 模块。

这一步选择 `observability`，而不是 `security`，原因有三个：

- `observability` 更容易直接消费现有的 `EventSummary`、`InterruptSignal` 和 assembly policy snapshot
- `Base` 里有 config 和通用工具，但没有现成的平台级 typed 观测契约
- 它能做成一个很小但闭环完整的 slice，不需要引入重型日志/指标系统

## 这一步做了什么

新增了三类东西：

### 1. 平台可观测 contract

文件：

- `VitalAI/platform/observability/records.py`

新增：

- `ObservationKind`
- `ObservationSeverity`
- `ObservationRecord`

这一层的目标不是实现监控平台，而是先统一“系统内部的观测记录长什么样”。

目前支持的三类观测对象：

- `EVENT_SUMMARY`
- `INTERRUPT_SIGNAL`
- `POLICY_SNAPSHOT`

### 2. 轻量观测收集器

文件：

- `VitalAI/platform/observability/service.py`

新增：

- `ObservabilityCollector`

它目前提供三个入口：

- `record_event_summary()`
- `record_interrupt()`
- `record_policy_snapshot()`

也就是说，这一层已经能把：

- runtime 聚合后的事件摘要
- interrupt 层的中断信号
- application assembly 的角色策略快照

翻译成统一的 `ObservationRecord`。

### 3. 策略快照的观测视图

文件：

- `VitalAI/interfaces/typed_flow_support.py`
- `VitalAI/interfaces/api/routers/typed_flows.py`

新增：

- `build_policy_observation()`
- `serialize_observation_record()`
- `get_runtime_policy_observation()`
- `GET /flows/policies/{role}/observation`

这一步的作用是把前面已经可见的 policy snapshot，再进一步变成“可观测记录”。

也就是说，接口层现在不只能看：

- 某个角色当前策略是什么

还可以看：

- 这份策略快照在 observability 视角下长什么样

## 为什么这样设计

这里有一个边界刻意保持得很克制：

- `platform/observability` 不直接依赖 `application` 的 snapshot 类型
- 它只接收字段值，生成平台自己的 `ObservationRecord`

这样就不会形成：

- `platform -> application`

这种反向依赖。

也就是说，`application` 负责产生策略状态，`observability` 负责记录它，而不是让平台层反过来认识应用层类型。

## 测试与验证

新增测试：

- `tests/platform/test_observability_contracts.py`

更新测试：

- `tests/interfaces/test_typed_flow_routes.py`

验证命令：

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.platform.test_observability_contracts tests.application.test_health_alert_flow tests.application.test_mental_care_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

结果：

- `Ran 41 tests ... OK`

## 这一步的意义

这一步之后，`platform/observability` 不再只是目录壳。

它已经有了：

- typed contract
- 最小 collector
- 与 runtime / interrupt / assembly policy 的连接点
- 接口层可见的观测视图

这说明我们现在可以开始按同样节奏补平台模块：

- 先定义边界
- 再接一条小的真实消费路径
- 最后补测试和步骤文档

## 对下一步的影响

接下来最自然的方向就是补 `platform/security` 的最小 typed slice。

优先考虑的切入点应该是：

- 敏感字段脱敏 contract
- 输出审查结果 contract
- 对 typed message / feedback / report 的最小安全过滤入口

也就是继续沿用这一步的策略：

- 不做大而全
- 先做一个能落地、能被现有链路消费的小闭环
