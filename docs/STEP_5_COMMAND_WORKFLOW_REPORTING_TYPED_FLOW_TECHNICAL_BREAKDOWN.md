# 第五步：Command / Workflow / Reporting Typed Flow 技术拆解

## 文档目的

这份文档记录第五步开发工作的技术落点：在第四步已经有第一条 application/domain typed flow 的基础上，把它继续抽成更稳定的 command 和 workflow 入口，并让 reporting 领域开始消费 typed `FeedbackEvent`。

第四步解决的是：

`application 和 domain 能不能开始说 typed runtime 语言。`

第五步解决的是：

`这条语言能不能形成更像真实系统入口的 command -> workflow -> reporting 消费链。`

---

## 本轮目标

本轮把健康预警流继续扩成三段：

1. `Command`
2. `UseCase`
3. `Workflow + Reporting`

这意味着后续不管来自：

- API
- scheduler
- consumer

都更容易从稳定命令对象进入，而不是直接手写 `MessageEnvelope`。

---

## 文件 1：`VitalAI/application/commands/health_alert_command.py`

### 改动点

新增：

- `HealthAlertCommand`

### 技术意义

这个对象是第五步的入口稳定器。

它把应用层输入固定成：

- `source_agent`
- `trace_id`
- `user_id`
- `risk_level`
- `target_agent`

并通过 `to_message_envelope()` 转成 platform runtime 入口对象。

这样以后 API/scheduler 不需要了解 runtime 细节，只需要构造 command。

---

## 文件 2：`VitalAI/domains/reporting/services/feedback_report.py`

### 改动点

新增：

- `FeedbackReport`
- `FeedbackReportService`

### 技术意义

这一步让 reporting 领域第一次真正参与 typed flow。

它现在直接消费 `FeedbackEvent`，并产出一个最小报告对象。

这很重要，因为它证明 typed flow 不只是“health 自己内部闭环”，而是已经能把反馈向下游领域传播。

---

## 文件 3：`VitalAI/application/workflows/health_alert_workflow.py`

### 改动点

新增：

- `HealthAlertWorkflowResult`
- `HealthAlertWorkflow`

### 技术意义

workflow 这一层让系统更接近真实多步编排。

它做的事情是：

1. 接收 `HealthAlertCommand`
2. 调用 `RunHealthAlertFlowUseCase`
3. 如果有 `FeedbackEvent`，再交给 `FeedbackReportService`
4. 返回 workflow 级结果

这一步让 application 分层更清晰：

- command 负责稳定输入
- use case 负责运行时编排
- workflow 负责多步组合

---

## 文件 4：`VitalAI/application/use_cases/health_alert_flow.py`

### 改动点

清理了一个小问题：

- 之前对同一个 `summary` 会重复调用两次 `triage()`
- 现在改成先算一次 `outcome`，然后复用

### 技术意义

这不是大改动，但它让 use case 的编排更干净，也避免后面 domain service 变复杂后出现重复计算。

---

## 文件 5：包导出更新

本轮同步更新了：

- `VitalAI/application/__init__.py`
- `VitalAI/application/commands/__init__.py`
- `VitalAI/application/workflows/__init__.py`
- `VitalAI/domains/reporting/__init__.py`
- `VitalAI/domains/reporting/services/__init__.py`

### 技术意义

让 command、workflow、reporting service 都具备包级别的稳定入口，后续集成更自然。

---

## 文件 6：`tests/application/test_health_alert_flow.py`

### 改动点

这次测试从 1 个扩成 2 个：

1. health flow 仍然能产出 typed domain outputs
2. workflow 能基于 `FeedbackEvent` 生成 reporting 输出

### 技术意义

这说明第五步不是单纯加目录结构，而是确实把 reporting consumption 接通了。

---

## 本轮结果

到第五步结束时，这条 typed flow 已经从：

`MessageEnvelope -> runtime -> domain outputs`

推进成了：

`HealthAlertCommand -> MessageEnvelope -> runtime -> HealthTriageOutcome -> FeedbackReport`

这让系统第一次有了更像真实入口的编排形态，也为后续 API、scheduler、consumer 接入打下了稳定接口基础。
