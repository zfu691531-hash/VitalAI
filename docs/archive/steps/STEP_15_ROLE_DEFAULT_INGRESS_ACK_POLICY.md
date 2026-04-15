# 第15步：基于角色默认值的 Ingress Ack 策略

## 目标

增加第二个真正的 runtime-role 策略，但这次不落在 reporting 边界，而是落在消息 ingress 边界。

## 为什么做这一步

到第14步时，运行角色已经会影响一个真实行为：

- `scheduler` 默认关闭 reporting

这很有价值，但 message contract 本身还有一个明显缺口。

当前每条 typed flow 的起点都是：

1. command object
2. `MessageEnvelope`
3. runtime ingestion

这使得 ingress message 成为了最自然的下一个角色策略落点。

问题在于：这个策略应该放哪一层。

这里我**有意识地没有**把角色行为塞进 domain command：

- `HealthAlertCommand`
- `DailyLifeCheckInCommand`

这些 command 应该继续表达业务意图，而不是承载 transport/runtime deployment policy。

所以这一步把策略放在 application assembly 层，位置是：

- 在 `command.to_message_envelope()` 之后
- 在 `use_case.run(message)` 之前

## 引入了什么行为

新的角色默认 ingress 策略是：

- `scheduler` -> `require_ack=False`
- `consumer` -> `require_ack=True`
- `api` -> 保留 command 默认值
- `default` -> 保留 command 默认值

这个策略故意保持很小。

它合理的地方在于：

- consumer 风格的事件摄取最适合强制要求 ack
- scheduler 触发的内部任务最适合默认避免 ack 负担
- API/default 路径现在还可以继续尊重 command 自己的默认值

## 改了哪些文件

### 1. `VitalAI/application/assembly.py`

新增：

- `ApplicationIngressPolicy`
- `ApplicationAssembly.ingress_policy`
- `ApplicationAssembly.apply_ingress_policy()`

同时，`ApplicationAssemblyEnvironment` 新增了：

- `to_ingress_policy()`

这让角色策略继续集中在 assembly，而不是散落到各个接口实现里。

### 2. Workflow 文件

更新：

- `VitalAI/application/workflows/health_alert_workflow.py`
- `VitalAI/application/workflows/daily_life_checkin_workflow.py`

两个 workflow 现在都接收一个很轻的 `message_transformer`，默认是 identity。

assembly 层注入的是：

- `self.apply_ingress_policy`

这样 workflow 仍然可以复用，但 runtime-role 行为依然由 assembly 控制。

### 3. 测试

新增覆盖：

- scheduler 角色把 `require_ack=True` 改成 `False`
- consumer 角色把 `require_ack=False` 改成 `True`
- interface-facing consumer assembly 确实应用了这条策略

回归命令：

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.application.test_health_alert_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

结果：

- `Ran 28 tests ... OK`

## 为什么这一层是对的

这个策略属于 application assembly，因为它具备这些特征：

- 它对 runtime role 敏感
- 它紧贴 transport/message boundary
- 它不是业务领域逻辑
- 它也不是基础设施持久化逻辑

所以，正确答案仍然不是：

- persistence-backed composition
- service registry
- 更重的 DI

而是：

- 再加一条精确的 assembly-boundary policy

## 结果状态

系统现在已经有两条真实的角色驱动行为：

1. reporting 策略
2. ingress ack 策略

这让 role-aware assembly stop point 更可信了，因为运行角色现在同时影响：

- 输出/reporting 行为
- 输入/message 行为
