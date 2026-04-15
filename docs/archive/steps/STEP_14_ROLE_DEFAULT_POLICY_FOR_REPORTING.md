# 第14步：基于角色默认值的 Reporting 策略

## 目标

让运行角色从“元数据”真正变成一个会影响行为的 assembly 策略，同时仍然避免引入重型 registry 或 container。

## 为什么做这一步

到第13步时，项目已经知道当前运行角色是什么：

- `api`
- `scheduler`
- `consumer`
- `default`

但那时的角色感知还主要停留在结构层面。assembly 系统虽然已经能区分角色、分开缓存，但角色本身还没有改变行为。

于是下一步就变得比较明确：

- 引入一个小而可信的角色策略
- 让它可逆、容易理解
- 避免过早发明一个庞大的配置矩阵

最后选中的策略是 reporting。

原因：

- workflow 结果里 reporting 本来就是可选的
- 关闭它不会破坏 typed contract
- 对 scheduler 这类后台任务来说，默认不产出同样的 reporting 结果是合理的

## 引入了什么行为

新的默认值是：

- `scheduler` -> 默认关闭 reporting
- `api` -> 默认开启 reporting
- `consumer` -> 默认开启 reporting
- `default` -> 默认开启 reporting

环境变量覆盖依然优先：

- `VITALAI_REPORTING_ENABLED=true` 强制开启
- `VITALAI_REPORTING_ENABLED=false` 强制关闭
- 空值 / 未设置时，回落到角色默认值

## 改了哪些文件

### 1. `VitalAI/application/assembly.py`

新增：

- `_default_reporting_enabled_for_role(runtime_role)`

更新：

- `ApplicationAssemblyEnvironment.from_environment()`
- `_env_to_bool()`

一个关键细节是：

- 空环境值现在会回落到角色默认值，而不是被当成显式输入处理

这使得 `.env.template` 可以保持简洁，同时也让角色默认策略在没有显式覆盖时真正生效。

### 2. `tests/application/test_application_assembly.py`

新增验证：

- scheduler 角色默认关闭 reporting
- 当环境显式设置为 `true` 时，scheduler 可以重新开启 reporting
- 角色感知的环境解析仍然能正确保留角色元数据

### 3. `tests/interfaces/test_scheduler_and_consumer_adapters.py`

更新了 scheduler 的预期：

- scheduler 适配层默认返回 `feedback_report=None`

并补了一个覆盖：

- scheduler 角色下显式 reporting override 的效果

### 4. `.env.template`

把：

- `VITALAI_REPORTING_ENABLED=true`

改成了：

- `VITALAI_REPORTING_ENABLED=`

原因是：

- 留空可以让运行角色默认值更显性地生效
- 但如果要明确覆盖，依然可以写 `true` 或 `false`

## 为什么这一步比上 registry 更对

这一步验证了一个很实用的判断：

- 当前的问题不是“服务定义应该存在哪儿”
- 当前的问题是“不同入口什么时候应该有一点点不同行为”

这仍然是 assembly policy 问题，不是 persistence 问题。

所以正确增量是：

- 补一个小的角色策略

而不是：

- service registry
- DB-backed composition
- DI 框架

## 验证

回归命令：

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.application.test_health_alert_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

结果：

- `Ran 25 tests ... OK`

## 结果状态

系统现在有了：

- typed runtime contracts
- typed application/domain flows
- 薄适配层
- environment-aware assembly
- role-aware assembly
- 第一个真正会影响行为的角色默认策略

这比第13步的 stop point 更有说服力，因为角色已经开始以一种可控、可解释的方式改变系统行为。
