# 第18步：面向 Typed Flows 的策略自检 API

## 目标

把当前 role-aware assembly 的策略集合通过一个薄接口适配层暴露出来，但不新增任何 runtime-role 行为。

## 为什么做这一步

到第17步为止，项目已经有了：

- 多条真实的 role-aware assembly 策略
- 一个 typed 的 `ApplicationAssemblyPolicySnapshot`
- 本地可用的策略描述方法

但还缺一个东西：

- interface-facing 代码还不能直接查看当前策略集合

这个缺口已经开始变得重要，因为当前 stop point 已经足够“可运营”了：

- API、scheduler、consumer 已经共用同一个 assembly 边界
- 不同角色的策略行为也已经可以被比较

所以，这一步真正有价值的增量不是再加一条策略，而是：

- 通过接口层把现有策略暴露出来

## 改了哪些文件

### 1. `VitalAI/interfaces/typed_flow_support.py`

新增：

- `serialize_policy_snapshot()`

这样 interface support 层就形成了对称性：

- workflow result 可以序列化
- policy snapshot 也可以序列化

### 2. `VitalAI/interfaces/api/routers/typed_flows.py`

新增：

- `get_runtime_policy(role="api")`
- `GET /flows/policies/{role}`

这样，某个 runtime role 当前生效的 typed-flow policy set 就可以被外部直接查看。

返回结构包括：

- `runtime_role`
- `reporting_enabled`
- `require_ack_override`
- `ttl_override`

### 3. `tests/interfaces/test_typed_flow_routes.py`

补了一个验证：

- API 层的 policy endpoint 能正确返回 scheduler 角色当前的策略快照

## 为什么这一步是有价值的

这一步把当前 assembly stop point 从：

- 只在内部可理解

推进成了：

- 在接口层也可观察

这件事的实际价值在于：

- 更容易诊断
- 行为本身就能成为文档
- 未来更容易给 admin/ops 提供可见性
- 更容易做出“现在是否应该停”的判断

## 验证

回归命令：

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.application.test_health_alert_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

结果：

- `Ran 32 tests ... OK`

## 结果状态

当前 role-aware assembly stop point 现在已经具备：

- 真实行为
- 本地 typed 表达
- 测试覆盖
- 接口层可见性

这使得当前架构在决定是否继续增加角色策略之前，已经具备了更完整的评估基础。
