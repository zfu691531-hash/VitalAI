# 第19步：标准角色策略矩阵自检

## 目标

在现有单角色策略自检入口之上，再补一个“标准角色策略矩阵”入口，一次返回 `default`、`api`、`scheduler`、`consumer` 四类角色的当前策略状态。

## 为什么做这一步

到第18步为止，我们已经能查看单个角色当前的策略快照了。

这已经有价值，但在真正做 stop point 判断时，还差一点点：

- 我们还不能一次对比所有标准角色

而当前项目又已经有了明确的标准角色集合：

- `default`
- `api`
- `scheduler`
- `consumer`

所以这一步最自然的增量不是继续加第四条运行策略，而是把已有策略的可见性从“单点查询”推进成“角色矩阵查询”。

## 改了哪些文件

### 1. `VitalAI/interfaces/typed_flow_support.py`

新增：

- `_DEFAULT_POLICY_ROLES`
- `get_application_policy_matrix()`

它会按标准角色集合返回序列化后的策略快照字典。

这样 interface support 层现在可以：

- 查询单个角色策略
- 查询全部标准角色的策略矩阵

### 2. `VitalAI/interfaces/api/routers/typed_flows.py`

新增：

- `get_runtime_policy_matrix()`
- `GET /flows/policies`

这样接口层现在提供两种策略可见性：

- `GET /flows/policies/{role}`：查看单个角色
- `GET /flows/policies`：查看标准角色矩阵

### 3. `tests/interfaces/test_typed_flow_routes.py`

新增验证：

- 策略矩阵包含 `default/api/scheduler/consumer`
- `api` 默认 reporting 为开启
- `scheduler` 默认 reporting 为关闭
- `consumer` 默认 `require_ack_override=True`
- `consumer` 默认 `ttl_override=60`

## 为什么这一步比继续加新策略更合适

当前 assembly stop point 已经有：

- reporting 策略
- ingress ack 策略
- ingress TTL 策略
- typed snapshot
- 单角色 introspection

在这个阶段，继续加第四条角色策略的收益，已经不一定高于把现有策略变得更可比较。

而策略矩阵直接提升了：

- 诊断效率
- 文档可读性
- 架构评估能力

## 验证

回归命令：

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.application.test_health_alert_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

结果：

- `Ran 33 tests ... OK`

## 结果状态

当前 role-aware assembly stop point 现在已经具备两层接口可见性：

1. 单角色策略快照
2. 标准角色策略矩阵

这让后续判断“现在是否应该停止继续扩展角色策略”变得更有依据。
