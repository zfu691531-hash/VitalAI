# 第13步：角色感知的应用装配

## 目标

把第12步引入的环境感知 assembly 继续推进，让系统能够区分不同运行角色，例如：

- `api`
- `scheduler`
- `consumer`
- `default`

同时仍然不跳到持久化服务注册表这条更重的路线。

## 为什么做这一步

到第12步为止，项目已经可以：

- 构造 `ApplicationAssembly`
- 读取像 reporting enablement 这样的环境开关
- 让 API、scheduler、consumer 这几类接口适配层共享同一个 assembly 边界

但当时还缺一个很关键的概念：

- assembly 层并不知道自己当前在服务哪一种进程角色

这个缺口是真实存在的，因为项目已经同时有几种不同的薄入口：

- HTTP router 适配层
- scheduler 适配层
- consumer 适配层

这些入口当时都在共用一个默认的延迟 assembly 缓存。技术上能跑，但如果后面真的出现角色差异，就没有一个明确位置来承接。

所以，这一步没有上更重的 registry/container，而是补了一个更小、也更合理的抽象：

- 角色感知的 assembly 构造
- 角色感知的接口缓存

## 改了哪些文件

### 1. `VitalAI/application/assembly.py`

`ApplicationAssemblyEnvironment` 现在新增了：

- `runtime_role`

新增 helper：

- `build_application_assembly_for_role()`
- `build_application_assembly_from_environment_for_role()`

同时，`ApplicationAssembly.from_environment()` 现在也支持可选的 runtime role override，`ApplicationAssembly.runtime_role` 则提供了一个明确的 typed 方式来暴露当前角色。

这意味着 assembly 层现在有了两组正交输入：

- 像 reporting enablement 这样的环境选择
- 像 `api` / `scheduler` 这样的运行角色身份

### 2. `VitalAI/interfaces/typed_flow_support.py`

这个文件之前只缓存一个默认 assembly。

现在改成按角色缓存：

- `_DEFAULT_ASSEMBLIES: dict[str, ApplicationAssembly]`

同时新增了几个角色专属 helper：

- `get_api_application_assembly()`
- `get_scheduler_application_assembly()`
- `get_consumer_application_assembly()`

它的价值在于：

- 给每类接口入口一个稳定的组合槽位
- 但暂时还不强迫系统立刻长出角色专属业务逻辑

### 3. 接口适配层

下面这些文件现在会显式请求与自己运行角色对应的 assembly：

- `VitalAI/interfaces/api/routers/typed_flows.py`
- `VitalAI/interfaces/scheduler/typed_flow_jobs.py`
- `VitalAI/interfaces/consumers/typed_flow_consumers.py`

这个变化是有意保持很小的：

- API 使用 `api` 角色的 assembly
- scheduler 使用 `scheduler` 角色的 assembly
- consumer 使用 `consumer` 角色的 assembly

当前行为还没有变化，但边界已经明确了。

## 为什么还不是持久化注册表

这一步里我也重新看了 `Base/Repository`。

结论是：

- `Base/Repository` 很明确是数据库/持久化基础设施
- 它并没有提供一个现成的、可复用的 application service registry 来承接 runtime workflow composition
- 当前 VitalAI 真正需要的仍然是“进程内装配”，而不是“跨进程持久化服务发现”

所以当时正确的下一步不是：

- 把 assembly 定义存进数据库
- 造一个 container
- 造一个 service locator

而是：

- 先让现有 assembly 边界能感知运行角色

## 验证

新增覆盖：

- 环境驱动 assembly builder 的显式角色解析
- 带注入 config 的角色感知 assembly 构造
- `api` / `scheduler` / `consumer` 三类默认 assembly 缓存彼此独立

回归命令：

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.application.test_health_alert_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

结果：

- `Ran 23 tests ... OK`

## 结果状态

现在这个 stop point 比第12步更强了：

- 已经有 environment-aware assembly
- 已经有 runtime-role-aware assembly
- 接口适配层已经在消费角色专属的 assembly 槽位
- 但仍然没有引入重型的 persistence-backed registry

这让我们有了一个更合理的停点，可以先观察：更深的组合机制到底是不是真的需要。
