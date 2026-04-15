# 第八步：Typed Flow 薄接口适配层技术拆解

## 文档目的

这份文档记录第八步开发工作的技术落点：在不继续做更强模板抽象的前提下，把现有两条 typed flow 接到一个很薄的接口适配层上。

这一轮的目标不是“做完整 API 系统”，而是验证一件事：

`当前 helper 级抽象，是否已经足够支撑 interface 层入口。`

---

## 为什么这一步比继续抽模板更合适

前一阶段我们已经做出判断：

- 现在不适合继续做重型 typed flow template
- 更适合保留领域语义，只提取稳定重复

那下一步最自然的验证方式，不是再做内部抽象，而是把现有结构接到一个真实入口上看它是否顺手。

如果接口适配层很薄、很自然，说明当前架构已经足够稳定。
如果接口适配层仍然很别扭，再考虑更强抽象也不迟。

---

## 文件 1：`VitalAI/interfaces/api/routers/typed_flows.py`

### 改动点

新增：

- `HealthAlertRequest`
- `DailyLifeCheckInRequest`
- `build_health_workflow()`
- `build_daily_life_workflow()`
- `run_health_alert()`
- `run_daily_life_checkin()`
- 两个 `POST` 路由

### 技术意义

这是第八步的核心。

它把 interface 层做得非常薄：

- request 进入
- 转成 command
- 交给 workflow
- 输出 response-shaped dict

这里没有重新发明业务逻辑，也没有把 runtime 逻辑塞回接口层。
它只是一个 adapter。

这正好符合当前架构目标：

- interface 保持薄
- application 负责编排
- domain 负责领域结果

---

## 文件 2：`VitalAI/interfaces/api/app.py`

### 改动点

把新的 typed flow router 挂到了 HTTP 接口初始化里。

### 技术意义

这意味着当前项目已经不仅有 `/health` 这种存活检查入口，也开始有真正面向 typed flow 的业务入口雏形。

---

## 文件 3：`VitalAI/application/__init__.py`

### 改动点

顺手清理了重复导入：

- 移除了重复的 `HealthAlertCommand` import

### 技术意义

这是一个小修正，但能保持导出层整洁。

---

## 文件 4：`tests/interfaces/test_typed_flow_routes.py`

### 改动点

新增了 2 个接口适配层测试：

1. health route adapter
2. daily_life route adapter

### 技术意义

这一步验证的不是 FastAPI 网络栈本身，而是当前 interface adapter 是否足够薄、是否能正确调用 application flow。

这也是当前阶段更合适的测试粒度。

---

## 本轮结果

到第八步结束时，系统已经有了：

- platform typed contracts
- runtime typed flow
- health / daily_life 两条 application/domain typed flow
- reporting typed consumer
- 薄接口适配层入口

这说明当前“helper 级抽象 + 薄接口适配层”的策略是站得住的。

也就是说，当前阶段继续停在 helper 层是合理的，不需要为了接口接入再去发明更强模板。
