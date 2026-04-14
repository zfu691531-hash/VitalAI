# 第四步：Application + Health Typed Flow 技术拆解

## 文档目的

这份文档记录第四步开发工作的技术落点：把前面已经打好的 platform typed runtime 流，第一次真正接到 `application/` 和 `domains/health/`。

前三步的重点主要在 platform 内部：

- 第一步：定义 contract
- 第二步：让主 runtime 链路使用 contract
- 第三步：让监控、影子、降级也接入 contract

第四步开始，目标变成：

`至少让一条 application/domain 路径真实消费并产出 typed platform objects。`

---

## 本轮目标

本轮选择了一条最小健康预警流作为端到端入口：

- 输入：`MessageEnvelope`
- runtime：`EventAggregator -> DecisionCore`
- domain：`HealthAlertTriageService`
- 输出：
  - `MessageEnvelope`
  - `FeedbackEvent`
  - `IntentDeclaration`

这条链路不追求复杂业务，而是追求“让 contract 真的穿过 application 和 domain”。

---

## 文件 1：`VitalAI/domains/health/services/alert_triage.py`

### 改动点

新增：

- `HealthTriageOutcome`
- `HealthAlertTriageService`

### 技术意义

这个文件是第四步的核心 domain entry。

它把一个健康预警摘要 `EventSummary` 转成 3 类 typed 输出：

1. `decision_message: MessageEnvelope`
2. `feedback_event: FeedbackEvent`
3. `escalation_intent: IntentDeclaration`

这一步非常关键，因为它说明 domain 层不再只是“未来再说”，而是已经开始明确：

- 收什么
- 产什么
- 如何使用 platform contract 表达领域结果

---

## 文件 2：`VitalAI/domains/health/services/__init__.py`

### 改动点

补导出了：

- `HealthAlertTriageService`
- `HealthTriageOutcome`

### 技术意义

让 health domain 的服务边界从包级别可以直接使用，避免调用方深入到具体文件路径。

---

## 文件 3：`VitalAI/domains/health/__init__.py`

### 改动点

补导出了：

- `HealthAlertTriageService`
- `HealthTriageOutcome`

### 技术意义

让 `domains.health` 成为更完整的领域入口，而不只是一个空目录占位。

---

## 文件 4：`VitalAI/application/use_cases/health_alert_flow.py`

### 改动点

新增：

- `HealthAlertFlowResult`
- `RunHealthAlertFlowUseCase`

### 技术意义

这一步第一次把 `application` 层真正用起来了。

`RunHealthAlertFlowUseCase` 负责做最小编排：

1. 接收外部传入的 `MessageEnvelope`
2. 交给 `EventAggregator`
3. 从 aggregator 取出 `EventSummary`
4. 让 `DecisionCore` 处理 summary
5. 让 health domain service 生成完整 typed outcome

它表达的是一个重要边界：

- runtime 负责运行时协议与调度
- domain 负责领域判断与 typed 结果
- application 负责把这两边串起来

---

## 文件 5：`VitalAI/application/use_cases/__init__.py`

### 改动点

补导出了：

- `HealthAlertFlowResult`
- `RunHealthAlertFlowUseCase`

### 技术意义

让 use case 层开始具备稳定的公开入口。

---

## 文件 6：`VitalAI/application/__init__.py`

### 改动点

补导出了：

- `HealthAlertFlowResult`
- `RunHealthAlertFlowUseCase`

### 技术意义

让 application 层不再只是“有目录”，而是开始提供真正可被外部调用的编排对象。

---

## 文件 7：`tests/application/test_health_alert_flow.py`

### 改动点

新增一个 application 级测试，验证第一条端到端 typed flow：

- 输入 `MessageEnvelope`
- 经 runtime 汇总和决策
- 输出健康域的 typed 结果

### 技术意义

这说明第四步不只是加类，而是第一次验证：

- application 确实能调用 runtime
- runtime 确实能把摘要交给 domain
- domain 确实能返回 typed `MessageEnvelope + FeedbackEvent + IntentDeclaration`

---

## 本轮结果

到第四步结束时，系统第一次拥有了一条真正穿过多层的 typed flow：

`MessageEnvelope -> EventSummary -> domain triage -> MessageEnvelope + FeedbackEvent + IntentDeclaration`

这条路径虽然小，但它证明了一件很重要的事：

typed runtime contract 不再只是 platform 内部的结构定义，而是已经开始成为 application 和 domain 层的共同语言。
