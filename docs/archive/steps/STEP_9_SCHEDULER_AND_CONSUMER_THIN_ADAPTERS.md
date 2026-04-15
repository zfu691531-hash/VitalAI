# 第九步：Scheduler 与 Consumer 薄适配层技术拆解

## 文档目的

这份文档记录第九步开发工作的技术落点：继续沿用当前 command/workflow 形状，把 typed flow 扩展到 `scheduler` 和 `consumer` 两种入口。

第八步已经证明：

- 薄 API adapter 可以顺利复用当前结构

第九步要验证的是：

`同样的结构是否也适用于非 HTTP 入口。`

---

## 本轮策略

这一步依然坚持“薄适配层”原则：

- scheduler 不承载业务逻辑
- consumer 不承载业务逻辑
- 两者都只负责把入口数据转成 command，然后交给现有 workflow

同时为了避免 adapter 之间复制 workflow 构造与结果序列化逻辑，本轮增加了一个很小的 interface support 模块。

---

## 文件 1：`VitalAI/interfaces/typed_flow_support.py`

### 改动点

新增：

- `build_health_workflow()`
- `build_daily_life_workflow()`
- `serialize_workflow_result()`

### 技术意义

这不是“大模板”，只是 `interfaces` 层自己的共享 support。

它把三种入口都会重复做的事情收了起来：

- 构造 workflow
- 序列化 workflow 结果

这样 API、scheduler、consumer 都可以复用同一层接口支持，而不用各自复制构造样板。

---

## 文件 2：`VitalAI/interfaces/scheduler/typed_flow_jobs.py`

### 改动点

新增 scheduler 入口：

- `ScheduledHealthAlertJob`
- `ScheduledDailyLifeCheckInJob`
- `run_scheduled_health_alert()`
- `run_scheduled_daily_life_checkin()`

### 技术意义

这一步证明当前 command/workflow 形状不仅能接 API，也能接 scheduler。

scheduler entry 非常薄：

- job input
- command conversion
- workflow execution
- response-shaped result

---

## 文件 3：`VitalAI/interfaces/consumers/typed_flow_consumers.py`

### 改动点

新增 consumer 入口：

- `HealthAlertConsumedEvent`
- `DailyLifeCheckInConsumedEvent`
- `consume_health_alert()`
- `consume_daily_life_checkin()`

### 技术意义

这一步证明当前 command/workflow 形状也能接消息消费入口。

也就是说，当前架构不依赖于 HTTP 特性，而是对多种 entrypoint 都成立。

---

## 文件 4：接口导出更新

更新了：

- `VitalAI/interfaces/scheduler/__init__.py`
- `VitalAI/interfaces/consumers/__init__.py`
- `VitalAI/interfaces/api/routers/typed_flows.py`

### 技术意义

这些更新让 API、scheduler、consumer 三种入口都通过相同 support 复用 workflow，而不是各自散落一套 wiring。

---

## 文件 5：`tests/interfaces/test_scheduler_and_consumer_adapters.py`

### 改动点

新增 4 个测试：

1. scheduled health alert
2. scheduled daily life check-in
3. consumed health alert
4. consumed daily life check-in

### 技术意义

这一步验证的是：

- 当前 command/workflow 形状在三类入口下都能复用
- 不需要为了多入口支持而引入更强模板

---

## 本轮结果

到第九步结束时，当前 typed flow 已经覆盖：

- API
- scheduler
- consumer

这说明我们前面坚持的方向是有效的：

`helper 级抽象 + 薄入口适配层`

已经足够支撑多种 entrypoint，而不需要过早进入更重的模板化设计。
