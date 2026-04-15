# 第12步：面向环境的应用装配

## 目标

在现有 application assembly 层上补一个非常轻的环境入口，但不把它演化成重型依赖注入容器。

## 为什么做这一步

到第11步为止，项目已经有了：

- `VitalAI/application/assembly.py` 里的轻量可配置 builder
- `interfaces/` 里的薄适配层
- 两条稳定的 typed flow：`health` 和 `daily_life`

剩下的缺口已经不是“要不要继续抽象”，而是：

- 真实进程到底怎么决定当前该使用哪种装配形态？

在动手前，我重新检查了 `Base/Config`。结论是：

- `Base/Config` 仍然是共享 `.env` 和日志行为的正确基础层
- 但这批新的 typed-flow 装配开关仍然是 VitalAI 项目内部语义
- 所以 assembly 层暂时不应该把这些应用本地的组合开关推回 `Base`

因此，这一步采用了一个很克制的设计：

1. 继续让 `ApplicationAssemblyConfig` 作为主要 typed hook 面
2. 新增 `ApplicationAssembly` 作为稳定的装配入口
3. 只新增一个很小的环境读取点，且仅面向 assembly 关心的配置
4. 用一个真实的环境开关来证明价值，而不是为了“看起来有配置”而加配置

## 改了哪些文件

### 1. `VitalAI/application/assembly.py`

这个文件现在不只是暴露两个 builder 函数了。

新增内容：

- `ApplicationAssemblyEnvironment`
- `ApplicationAssembly`
- `build_application_assembly()`
- `build_application_assembly_from_environment()`

核心思路：

- `interfaces` 现在可以依赖一个 assembly 对象，而不是自己知道怎么拼 workflow
- 原有的 `build_health_workflow()` / `build_daily_life_workflow()` 仍然保留，但它们现在改为经由 assembly 对象委托构建

这一步的重要意义：

- application 层现在有了一个更正式的组合边界
- 但 workflow 依然是按需新建，不会偷偷复用 runtime 内部有状态对象，比如 aggregator

### 2. `VitalAI/domains/reporting/services/feedback_report.py`

这一步需要一个真正有意义的环境驱动决策。最终我选择了 reporting enablement，原因是：

- 很容易理解
- 在运行上也合理
- 实现风险低

新增：

- `NoOpFeedbackReportService`

这个 service 会返回 `None`，而不是生成 report。这样 workflow 形状保持不变，但在 reporting 被关闭时可以跳过报表生成。

同时，基础 `FeedbackReportService.build_report()` 的返回类型被放宽为：

- `FeedbackReport | None`

这和现有 workflow 契约是兼容的，因为 workflow result 本来就允许 `feedback_report` 为空。

### 3. `VitalAI/interfaces/typed_flow_support.py`

这个文件不再只是一个 serializer helper。

它现在还负责：

- `get_default_application_assembly()`
- 从环境延迟构造默认 assembly

这样 API / scheduler / consumer 适配层依旧保持很薄，但它们都统一消费同一个 assembly 边界。

### 4. `.env.template`

新增：

- `VITALAI_REPORTING_ENABLED=true`

这让第一个面向环境的 assembly 开关变得可发现，也方便后续会话快速理解现有行为。

## 设计判断

这一步我们**有意识地没有**做下面这些事：

- 不引入重型 DI 容器
- 不引入 registry-style 的 service locator
- 不把应用本地的 assembly 开关大规模迁回 `Base/Config`
- 不做带隐式可变状态的 workflow 单例复用

这种克制很重要。

当前阶段，项目真正受益的是：

- 一个稳定的 composition boundary
- 一个有真实意义的环境控制行为
- 继续保持每次按需构建 workflow

而不会真正受益的是：

- 容器框架
- 没有真实运行需求支撑的大量配置面

## 验证

新增覆盖：

- `build_application_assembly_from_environment()`
- 基于环境的 reporting 关闭
- 默认 assembly 从环境重建后，接口适配层仍然能工作

回归命令：

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.application.test_health_alert_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

结果：

- `Ran 20 tests ... OK`

## 结果状态

系统现在有了：

- `platform` 层的 typed contracts
- `application` / `domains` 里的 typed flows
- `interfaces` 里的薄适配层
- `application/assembly.py` 里的轻量可配置装配层
- 第一个真正面向环境的 assembly 入口

在继续深入配置或持久化整合之前，这是一个很不错的阶段性停点。
