# 第 22 步：补齐 security 的最小 typed slice

## 这一步为什么这样切

在第 21 步补了 `observability` 之后，`platform` 里最明显还偏空的是 `security`。

但 `security` 很容易一上来就做大，比如：

- 权限系统
- 合规校验
- 多层输出审查
- 敏感资源访问控制

这些都太重，不适合当前阶段。

所以这一步我选了一个更克制、也更容易形成真实闭环的切口：

- 敏感信息审查与脱敏

而且不是做成独立摆设，而是先接到一个已经存在的真实出口上：

- `FeedbackReportService`

这样就能验证：

- `platform/security` 已经开始消费真实业务产物
- 现有 typed flow 在最终输出阶段，已经有最小安全过滤能力

## 这一步做了什么

### 1. 安全审查 contract

新增文件：

- `VitalAI/platform/security/review.py`

新增类型：

- `SecurityAction`
- `SecuritySeverity`
- `SecurityFinding`
- `SecurityReviewResult`

这一层先解决“安全审查结果怎么表达”的问题。

当前动作只有三种：

- `ALLOW`
- `REDACT`
- `BLOCK`

这意味着后面不管做消息审查、报告审查还是接口输出审查，都可以继续复用这一套结果结构。

### 2. 轻量敏感信息守卫

新增文件：

- `VitalAI/platform/security/service.py`

新增：

- `SensitiveDataGuard`

它目前提供两个最小入口：

- `sanitize_text()`
- `sanitize_mapping()`

当前支持的轻量检测与脱敏规则包括：

- 邮箱
- 电话号码
- 明显的 token / secret 片段
- 命中敏感关键字的字段名

这一步刻意保持了轻量：

- 不做复杂策略引擎
- 不引入 ACL / RBAC
- 不要求依赖外部合规系统

目标只是先把“安全过滤能力”变成平台层的正式 contract。

### 3. reporting 作为第一个真实消费点

更新文件：

- `VitalAI/domains/reporting/services/feedback_report.py`

改动：

- `FeedbackReportService` 现在持有 `SensitiveDataGuard`
- 在构建 report body 后，会先做一次轻量脱敏

这一步的意义非常明确：

- `security` 不再只是平台层空壳
- 它已经开始介入真实输出
- 即使上游 summary 里混入明显敏感文本，reporting 也不会原样吐出去

## 为什么先接 reporting，而不是 message / api

原因有三个：

### 1. reporting 是天然的输出边界

安全过滤最适合先落在“系统准备对外展示或下游消费”的地方。

### 2. 改动范围最小

不会破坏现有 `command -> use case -> workflow -> assembly` 结构。

### 3. 更容易验证

只要给 summary 塞一个邮箱和电话，就能看到脱敏是否生效。

## 测试与验证

新增测试：

- `tests/platform/test_security_contracts.py`

覆盖内容：

- `sanitize_mapping()` 对敏感字段脱敏
- `sanitize_text()` 对邮箱和电话脱敏
- `FeedbackReportService` 在构建 report 时做脱敏

验证命令：

```bash
python -m unittest tests.platform.test_security_contracts tests.platform.test_observability_contracts tests.application.test_health_alert_flow tests.application.test_mental_care_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

结果：

- `Ran 39 tests ... OK`

## 这一步的意义

这一步之后，`platform/security` 不再只是目录占位。

它已经有了：

- typed 审查结果
- 最小敏感信息守卫
- 一个真实消费点：`reporting`

这意味着现在的 `platform` 已经有两块不再是空壳：

- `observability`
- `security`

而且它们都遵循同一个节奏：

1. 先定义 contract
2. 再接一个真实消费点
3. 最后补测试和步骤文档

## 对下一步的影响

接下来有两个自然方向：

- 继续把 `security` 从 reporting 扩到 message / API 输出
- 或回到 `runtime`，让 observability/security 开始感知更多运行时信号

我更推荐第二个方向：

- 让 `runtime` 开始把关键 summary / interrupt 主动交给 observability/security

这样能让平台层两块新能力真正进入主链路，而不只是停在边缘消费点。
