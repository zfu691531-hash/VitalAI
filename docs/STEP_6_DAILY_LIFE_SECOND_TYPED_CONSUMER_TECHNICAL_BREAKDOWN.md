# 第六步：Daily Life 第二个 Typed Consumer 技术拆解

## 文档目的

这份文档记录第六步开发工作的技术落点：为 `daily_life` 领域补上第二条 typed consumer 路径，避免当前架构只围绕 health/reporting 这条链路演进。

第五步结束时，系统已经有：

- health command
- health use case
- health workflow
- reporting feedback consumer

但它仍然偏健康域中心。

第六步的目标是：

`让 daily_life 也拥有一条最小但完整的 typed command -> runtime -> domain -> reporting 路径。`

---

## 本轮目标

这次新增的第二条路径是“日常生活 check-in 支持流”：

- `DailyLifeCheckInCommand`
- `RunDailyLifeCheckInFlowUseCase`
- `DailyLifeCheckInSupportService`
- `DailyLifeCheckInWorkflow`

它和 health flow 平行存在，目的是验证当前架构已经不只支持一个特定领域。

---

## 文件 1：`VitalAI/domains/daily_life/services/checkin_support.py`

### 改动点

新增：

- `DailyLifeSupportOutcome`
- `DailyLifeCheckInSupportService`

### 技术意义

这个服务接收 `EventSummary`，输出 3 个 typed 结果：

1. `MessageEnvelope`
2. `FeedbackEvent`
3. `IntentDeclaration`

这样 daily_life 域也开始和 health 域一样，使用 platform contract 表达领域结果，而不是重新发明一套结构。

---

## 文件 2：`VitalAI/application/commands/daily_life_checkin_command.py`

### 改动点

新增：

- `DailyLifeCheckInCommand`

### 技术意义

这让 command 模式不再只属于 health。

它说明 application command 已经开始具备“可扩展到多个领域”的形态，而不是一次性的健康特例。

---

## 文件 3：`VitalAI/application/use_cases/daily_life_checkin_flow.py`

### 改动点

新增：

- `DailyLifeCheckInFlowResult`
- `RunDailyLifeCheckInFlowUseCase`

### 技术意义

这个 use case 和健康流平行，证明当前 runtime + domain 编排方式可以复制到第二个领域，而不需要重写平台协议。

---

## 文件 4：`VitalAI/application/workflows/daily_life_checkin_workflow.py`

### 改动点

新增：

- `DailyLifeCheckInWorkflowResult`
- `DailyLifeCheckInWorkflow`

### 技术意义

workflow 模式现在也不再只服务 health。

它说明 application/workflow 层已经具备承接多个 typed flow 的能力。

---

## 文件 5：导出更新

本轮同步更新了：

- `VitalAI/domains/daily_life/__init__.py`
- `VitalAI/domains/daily_life/services/__init__.py`
- `VitalAI/application/commands/__init__.py`
- `VitalAI/application/use_cases/__init__.py`
- `VitalAI/application/workflows/__init__.py`
- `VitalAI/application/__init__.py`

### 技术意义

这些更新让 daily_life 的 typed flow 也具备与 health flow 同等级的调用入口。

---

## 文件 6：`tests/application/test_health_alert_flow.py`

### 改动点

这个测试文件现在覆盖 4 类应用层验证：

1. health flow
2. health workflow
3. daily life flow
4. daily life workflow

### 技术意义

这一步明确证明：

- 当前系统已经有不止一个 typed consumer
- health 和 daily_life 两个领域都能走 command/use case/workflow 这条路
- reporting 也能消费这两条路径的 feedback

---

## 本轮结果

到第六步结束时，系统的 typed flow 已经从：

`只有 health -> reporting 一条主线`

推进成了：

- `HealthAlertCommand -> ... -> FeedbackReport`
- `DailyLifeCheckInCommand -> ... -> FeedbackReport`

这说明当前 architecture 已经开始具备“多领域共享同一套 typed runtime 语言”的实际形态，而不只是概念上的分层。
