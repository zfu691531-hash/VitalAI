# 第16步：基于角色默认值的 Ingress TTL 策略

## 目标

在同一个 ingress 边界上继续增加第三条小型 runtime-role 策略，这次针对的是消息 TTL。

## 为什么做这一步

到第15步时，role-aware assembly 已经会影响：

1. reporting 行为
2. ingress acknowledgement 行为

下一个合理候选，需要继续满足同样几条约束：

- 它应该属于 application/runtime 边界
- 它不应该扭曲 domain command 的语义
- 它应该容易测试
- 它应该比引入 retry 框架或更重的 transport 抽象更小、更克制

TTL 非常符合这些条件。

为什么优先选 TTL，而不是 retry/serialization：

- TTL 本来就是 `MessageEnvelope` 的一部分
- 它在 runtime contract 里已经有明确行为含义
- 相比 retry state 或 transport serialization 规则，它更简单，也更不侵入

## 引入了什么行为

新的角色默认 TTL 策略是：

- `scheduler` -> `ttl=300`
- `consumer` -> `ttl=60`
- `api` -> 保留 command 默认值
- `default` -> 保留 command 默认值

这和当前系统形态是匹配的：

- scheduler 任务更能容忍延迟处理
- consumer 摄取的消息比 scheduler 任务更时间敏感
- API/default 目前仍然依赖 command 自身给出的 TTL

## 改了哪些文件

### 1. `VitalAI/application/assembly.py`

`ApplicationIngressPolicy` 现在新增了：

- `ttl_override`

它的 `apply()` 方法现在同时支持处理：

- `require_ack_override`
- `ttl_override`

同时，`ApplicationAssemblyEnvironment.to_ingress_policy()` 现在会在原有 ack 默认值之外，再返回角色感知的 TTL 默认值。

### 2. 测试

新增验证：

- scheduler 角色会把 TTL 调成 `300`
- consumer 角色会把 TTL 调成 `60`
- API 角色会保留 command 层的 TTL 默认值
- 不同角色 assembly 在接口层会产出不同 TTL 结果

回归命令：

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.application.test_health_alert_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

结果：

- `Ran 29 tests ... OK`

## 为什么这仍然符合当前 stop point

这一步并没有引入：

- service registry
- transport middleware
- message broker 抽象
- persistence-backed assembly

它只是扩展了现有 assembly-boundary ingress policy。

这很重要，因为当前项目真正受益的仍然是：

- 明确的 runtime-role 语义
- 小而 typed 的 policy surface

而不是：

- 更重的组合机制

## 结果状态

role-aware assembly 层现在已经会影响：

1. reporting generation
2. ingress ack 默认值
3. ingress TTL 默认值

这让当前 stop point 更像一个真正的 runtime policy layer，而不是只有命名上的角色区分。
