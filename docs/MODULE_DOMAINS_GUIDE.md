# Domains 模块开发手册

## 模块定位

`VitalAI/domains/` 负责业务领域本身的语义、规则与 typed 输出表达。

当前是按领域高聚合组织，而不是按技术类型把所有 service/model/repository 平铺。

## 当前结构

```text
VitalAI/domains/
├─ health/
├─ daily_life/
├─ mental_care/
├─ profile_memory/
└─ reporting/
```

## 当前已完成程度

### 已有真实 flow 接入的领域

- `health`
- `daily_life`
- `reporting`

### 还主要是目录骨架的领域

- `mental_care`
- `profile_memory`

## 每个领域内部建议结构

```text
domain_x/
├─ agents/
├─ models/
├─ policies/
├─ repositories/
└─ services/
```

## 子目录职责

### `services/`

负责：

- 核心领域动作
- 领域判断
- 领域结果封装

### `models/`

负责：

- 领域内部稳定数据结构

### `policies/`

负责：

- 阈值
- 规则
- 约束
- 小型领域策略

### `repositories/`

负责：

- 面向该领域的数据访问封装
- 底层优先复用 `Base/Repository`

### `agents/`

负责：

- 如果未来某领域有独立 agent，这里承载该领域下 agent 相关实现

## 当前已形成的领域模式

### `health`

当前模式：

- 输入 `EventSummary`
- 产出 `HealthTriageOutcome`
- outcome 同时包含：
  - `decision_message`
  - `feedback_event`
  - `escalation_intent`

### `daily_life`

当前模式：

- 输入 `EventSummary`
- 产出 `DailyLifeSupportOutcome`
- outcome 同时包含：
  - `decision_message`
  - `feedback_event`
  - `support_intent`

### `reporting`

当前模式：

- 输入 `FeedbackReportRequest`
- 产出 `FeedbackReport`

## 模块要求

- 每个领域只关心自己的语义
- 不要直接处理接口层问题
- 不要承担 runtime 角色策略
- 尽量通过 typed platform object 对外表达结果

## 模块风格

- outcome 优于散落多个返回值
- 业务术语优先
- 允许和别的领域保持“形似但不强行抽象”
- 注释优先解释业务翻译意图

## 交付标准

- 至少有一个清晰输入
- 至少有一个稳定领域结果对象
- 领域结果可以被 application/reporting/arbitration 消费
- 领域服务不需要知道外部入口来自 API 还是 scheduler

## 推进注意事项

### 1. 不要把领域写成 transport glue

领域服务应该解释业务，而不是只做字典转发。

### 2. 不要过早合并多个领域的 service

如果 `health` 和 `daily_life` 现在只是结构相似，不代表应该立刻抽成一个通用 service 模板。

### 3. 新领域优先复制最小模式

后续若要开发 `mental_care` 或 `profile_memory`，建议优先按现有模式做出：

- command
- use case
- service
- outcome
- workflow

然后再判断哪里值得共享。

### 4. repository 优先复用 Base

不要在领域里重新造一层 ORM 或连接管理。

## 推荐下一个领域开发方式

如果接下来要继续扩展领域，建议优先选择：

- `mental_care`

原因：

- 能验证当前架构是否适用于非 health / daily_life 的第三条业务线
- 仍然适合沿用当前 typed flow 模式

## 测试建议

优先写：

- 领域 service 输入输出测试
- outcome 结构测试
- 与 workflow / reporting 的最小集成测试

## 常见错误

- 把平台策略塞进领域输出
- 把 workflow 逻辑塞进 domain service
- 为了省事直接返回 `dict`

## 当前最适合继续做的点

- 新增第三个真实领域 consumer
- 给 reporting 增加更清晰的模块化输入来源
- 让 `mental_care` 或 `profile_memory` 真正接入 application flow
