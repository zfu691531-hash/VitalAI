# 第七步：Shared Flow Support 与 Reporting Input Contract 技术拆解

## 文档目的

这份文档记录第七步开发工作的技术落点：在 health 和 daily_life 两条并行 typed flow 已经存在的基础上，做一次克制型抽象。

这一步没有试图把两条流硬合成一个“大一统泛型框架”，而是只提取了两类已经明显重复、且领域无关的部分：

- use case 里的 runtime 入口整理逻辑
- workflow 里的 reporting 消费逻辑

同时，为 reporting 增加了一个显式输入 contract，减少它对原始 `FeedbackEvent` 的直接耦合。

---

## 抽象原则

这一步的核心判断是：

- `command` 先不抽象，因为 health 和 daily_life 的业务语义仍然值得保留
- `domain service` 先不抽象，因为 triage/support 的领域语义不同
- `use case` 里“ingest + latest summary”已经完全重复，值得抽
- `workflow` 里“从 outcome 拿 feedback 再生成 report”已经完全重复，值得抽
- `reporting` 不应长期直接耦合完整 `FeedbackEvent`，值得加一层显式输入

---

## 文件 1：`VitalAI/application/use_cases/runtime_support.py`

### 改动点

新增：

- `ingest_and_get_latest_summary()`

### 技术意义

这个 helper 把两条 use case 里完全一致的 runtime 入口逻辑提取出来：

- ingest event
- 判断是否 accepted
- 取最新 summary

这样提取后，health 和 daily_life 的 use case 继续保留领域差异，但不再重复基础 runtime plumbing。

---

## 文件 2：`VitalAI/application/workflows/reporting_support.py`

### 改动点

新增：

- `FeedbackOutcomeProtocol`
- `build_feedback_report()`

### 技术意义

这个 helper 把两条 workflow 里完全一样的 reporting 对接逻辑提取出来：

- outcome 是否存在
- 从 outcome 取 feedback
- 转成 reporting 输入
- 交给 reporting service

这类逻辑是跨领域共用的，提取后比继续复制更清晰。

---

## 文件 3：`VitalAI/domains/reporting/services/feedback_report.py`

### 改动点

新增：

- `FeedbackReportRequest`

并将：

- `FeedbackReportService.build_report()`

从直接接收 `FeedbackEvent` 改成接收 `FeedbackReportRequest`

### 技术意义

这一步明确了 reporting 的输入边界。

以前 reporting service 直接消费完整 `FeedbackEvent`，耦合更深。
现在 workflow 先把 feedback 转成 reporting 所需的最小输入，再传给 reporting service。

这是一种更健康的依赖方向：

- reporting 关心的是“报告所需字段”
- 而不是“完整平台反馈事件对象”

---

## 文件 4：health / daily_life use case 更新

### 改动点

更新了：

- `health_alert_flow.py`
- `daily_life_checkin_flow.py`

这两个 use case 现在都使用：

- `ingest_and_get_latest_summary()`

### 技术意义

这说明当前的共享抽象是“被真实消费”的，而不是单纯为了抽象而抽象。

---

## 文件 5：health / daily_life workflow 更新

### 改动点

更新了：

- `health_alert_workflow.py`
- `daily_life_checkin_workflow.py`

现在统一通过：

- `build_feedback_report()`

来生成 reporting 输出。

### 技术意义

两条 workflow 继续保留各自 command/use case/result 类型，但 reporting bridge 已经共享。

---

## 本轮结果

到第七步结束时，系统没有被过早抽成一个重型泛型框架，但已经完成了两处高价值共享：

- shared runtime-use-case plumbing
- shared workflow-reporting bridge

同时 reporting 也拥有了更明确的输入 contract：

- `FeedbackReportRequest`

这说明当前架构开始进入一个更成熟的阶段：

`保留领域差异，提取真正稳定的跨领域重复。`
