# 第17步：Assembly 策略快照的可观察性

## 目标

在不继续增加第四条 runtime 行为策略的前提下，把当前 role-aware assembly stop point 做得更扎实。

## 为什么做这一步

到第16步时，assembly 层已经控制了多条真实的角色驱动行为：

1. reporting enablement
2. ingress ack 默认值
3. ingress TTL 默认值

到了这个阶段，下一个更有价值的问题就不再只是：

- 我们还能不能再加一条策略？

而是：

- 我们能不能清楚地看到当前到底生效了哪一组策略？

这个问题很重要，因为它直接关系到：

- 测试
- 调试
- 未来接口层诊断
- 判断当前 stop point 是否已经成熟到可以停下来

所以，这一步没有强行加第四条策略，而是补了可观察性。

## 增加了什么

### 1. `ApplicationAssemblyPolicySnapshot`

在 `VitalAI/application/assembly.py` 中新增了一个 typed snapshot：

- `ApplicationAssemblyPolicySnapshot`

它暴露当前生效的策略集合：

- `runtime_role`
- `reporting_enabled`
- `require_ack_override`
- `ttl_override`

### 2. `ApplicationAssembly.describe_policies()`

这个方法会返回当前 assembly 实例对应的策略快照。

这意味着：

- 角色专属 assembly 现在可以用一种稳定、typed 的方式描述自己
- 调用方不再需要分别去看 environment 字段和 ingress policy 再自己拼装理解

### 3. Interface Support 暴露

`VitalAI/interfaces/typed_flow_support.py` 现在新增了：

- `get_application_policy_snapshot(role="default")`

这让 interface-facing 代码和测试都能用统一方式查看某个 runtime role 当前解析出的策略状态。

## 为什么这一步比再加一条策略更值

assembly 层现在已经有足够多的真实行为来证明自己存在的合理性。

它真正缺的是：

- 一个容易回答“scheduler 现在默认是什么行为”的方式
- 一个容易回答“consumer 和 api 现在到底差在哪”的方式
- 一个容易验证“环境覆盖之后当前策略组到底变成什么样”的方式

因此，这一步加可观察性，比再补一条猜测性的角色策略更有价值，因为它能帮助我们判断：

- 当前架构是不是已经到了一个健康的停点

## 验证

新增覆盖：

- `ApplicationAssembly.describe_policies()`
- interface 层对 policy snapshot 的暴露

回归命令：

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.application.test_health_alert_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

结果：

- `Ran 31 tests ... OK`

## 结果状态

当前 assembly stop point 现在在两个维度上更强了：

- 它已经有多条真实的角色驱动行为
- 它已经能显式描述这些行为

这让当前设计更容易维护，也更容易在未来决定：到底要不要继续往更深的组合机制走。
