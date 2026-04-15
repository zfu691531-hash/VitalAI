# 第十一步：Lightweight Configurable Composition 技术拆解

## 文档目的

这份文档记录第十一步开发工作的技术落点：在已经建立 application composition layer 的基础上，不引入重型容器，只补一层轻量配置钩子，让 assembly 能按需替换依赖。

第十步解决的是：

- workflow 组装应该归 application，而不是 interfaces

第十一步解决的是：

- application assembly 是否需要一点点可配置性
- 以及这个可配置性是否可以在不引入复杂 DI 的前提下完成

---

## 为什么这一步不直接上完整 DI 容器

当前项目虽然已经有：

- runtime typed flow
- 多领域 command / workflow
- API / scheduler / consumer 入口

但它仍然处于早期结构成型阶段。

这时直接引入完整 DI 容器会有几个问题：

1. 配置复杂度上升太快
2. 真正稳定的依赖边界还没完全被现实场景验证
3. 会让当前简单的 in-memory 组装显得过度工程化

所以这一步的策略是：

`只加轻配置点，不加重型容器。`

---

## 文件 1：`VitalAI/application/assembly.py`

### 改动点

新增：

- `ApplicationAssemblyConfig`

并将：

- `build_health_workflow()`
- `build_daily_life_workflow()`

改成支持可选配置对象。

### 技术意义

这个配置对象当前只暴露少量稳定钩子：

- `event_aggregator_factory`
- `decision_core_factory`
- `health_triage_service_factory`
- `daily_life_support_service_factory`
- `feedback_report_service_factory`

这代表当前系统开始拥有“可替换依赖”的能力，但依然保持极简。

换句话说：

- 默认情况下依然是开箱即用
- 真有需要时，也能替换某个 service 做测试、实验或后续装配

---

## 文件 2：`VitalAI/application/__init__.py`

### 改动点

导出了：

- `ApplicationAssemblyConfig`

### 技术意义

让配置化装配成为 application 层正式提供的能力，而不是隐藏实现细节。

---

## 文件 3：`tests/application/test_application_assembly.py`

### 改动点

新增了一个配置化装配测试：

- `test_custom_report_service_can_be_injected_via_config`

同时保留原有两条 builder 可执行性测试。

### 技术意义

这一步真正验证了：

- assembly 不只是“理论上可配置”
- 而是已经可以通过轻配置替换实际依赖

这里选择 `FeedbackReportService` 作为例子，是因为它的替换边界清晰、影响可见、风险低。

---

## 本轮结果

到第十一步结束时，application composition 层已经从：

- 固定 in-memory builder

推进成了：

- 默认简单
- 轻量可配置
- 无需重型 DI 容器

这说明当前项目已经具备一个很实用的中间状态：

`既不僵硬，也不过度设计。`
