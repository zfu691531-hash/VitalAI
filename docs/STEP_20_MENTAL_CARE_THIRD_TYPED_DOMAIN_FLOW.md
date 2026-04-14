# 第 20 步：接入第三个真实领域 typed flow（Mental Care）

## 这一步做了什么

这一步没有继续给 `assembly` 增加第四个角色策略，而是回到我们之前判断更值得验证的方向：

- 让第三个真实领域 `mental_care` 接入现有 typed flow 主链路
- 验证当前 `command -> use case -> workflow -> reporting -> interface adapter` 这套结构，不只是对 `health` 和 `daily_life` 有效
- 继续保持当前 `role-aware assembly` 停点，不把项目推进成更重的模板或容器体系

本步新增了完整的第三条领域链路：

- `VitalAI/domains/mental_care/services/checkin_support.py`
- `VitalAI/application/commands/mental_care_checkin_command.py`
- `VitalAI/application/use_cases/mental_care_checkin_flow.py`
- `VitalAI/application/workflows/mental_care_checkin_workflow.py`

同时把这条链路接入了：

- `VitalAI/application/assembly.py`
- `VitalAI/interfaces/api/routers/typed_flows.py`
- `tests/application/test_mental_care_flow.py`
- `tests/application/test_application_assembly.py`
- `tests/interfaces/test_typed_flow_routes.py`

## 为什么这一步比继续抽象更合适

前面我们已经有两条真实 flow：

- `health`
- `daily_life`

但这还不足以证明当前架构真的稳。继续增加模板、容器或更多角色策略，收益会越来越低。

这一步选 `mental_care` 的原因是：

- 它和 `health`、`daily_life` 的语义差异更大
- 更适合验证当前 typed flow 架构是不是“真的够通用”
- 如果第三条流也能顺滑接入，就说明我们前面的 stop point 是成立的

## 按文件说明

### 1. `VitalAI/domains/mental_care/services/checkin_support.py`

新增：

- `MentalCareSupportOutcome`
- `MentalCareCheckInSupportService`

它继续沿用前两条流已经证明有效的模式：把同一个 `EventSummary` 翻译成三类 typed 输出：

- `decision_message`
- `feedback_event`
- `care_intent`

这样做的原因不是“形式统一”，而是让：

- `decision_core` 可以继续消费领域决策消息
- `reporting` 可以继续通过 `FeedbackEvent` 进入统一报告入口
- `arbitration` 可以继续通过 `IntentDeclaration` 理解跨领域资源诉求

这里的 `GoalType` 选用了已有的 `GoalType.MENTAL_CARE`，说明之前的 arbitration contract 已经预留好了第三个领域的空间。

### 2. `VitalAI/application/commands/mental_care_checkin_command.py`

新增：

- `MentalCareCheckInCommand`

这个 command 负责表达精神关怀场景的业务输入：

- `user_id`
- `mood_signal`
- `support_need`

它产出的消息类型是：

- `MENTAL_CARE_CHECKIN`

并沿用现有约定：

- 业务优先级在 command 层给出
- `ack/ttl` 的运行角色差异仍然由 assembly 统一处理

也就是说，command 继续只说“业务语义”，不说“scheduler/consumer/api 运行语义”。

### 3. `VitalAI/application/use_cases/mental_care_checkin_flow.py`

新增：

- `MentalCareCheckInFlowResult`
- `RunMentalCareCheckInFlowUseCase`

结构与前两条 flow 保持一致：

1. 先把 `MessageEnvelope` 交给 `EventAggregator`
2. 拿到 `EventSummary`
3. 交给 `MentalCareCheckInSupportService`
4. 同时保留 `DecisionCore` 在主链路中

这一步很重要，因为它继续坚持了我们前面已经定下来的边界：

- 领域 service 负责翻译语义
- runtime 仍然是统一决策入口

而不是第三条 flow 一上来就绕开 `DecisionCore`。

### 4. `VitalAI/application/workflows/mental_care_checkin_workflow.py`

新增：

- `MentalCareCheckInWorkflow`
- `MentalCareCheckInWorkflowResult`

这层继续承担：

- 从 `command` 出发
- 应用 `message_transformer`
- 运行 use case
- 调用 reporting

也就是说，第三条 flow 没有发明新套路，而是继续验证现在这套路已经够用。

### 5. `VitalAI/application/assembly.py`

新增：

- `mental_care_support_service_factory`
- `ApplicationAssembly.build_mental_care_workflow()`
- `build_mental_care_workflow()`

这一步的意义是：

- 第三个领域也通过同一个 assembly 进入系统
- 没有为 `mental_care` 单独发明新的装配机制
- 也没有因此再新增角色策略

这恰好说明当前 assembly 已经有足够的扩展性，不需要继续放大。

### 6. `VitalAI/interfaces/api/routers/typed_flows.py`

新增：

- `MentalCareCheckInRequest`
- `run_mental_care_checkin()`
- `POST /flows/mental-care-checkin`

这样 API 层现在已经能直接驱动三条真实领域 flow：

- `health`
- `daily_life`
- `mental_care`

这一步再次验证了“薄接口适配层”这个设计是成立的。

## 测试与验证

本步新增或更新了测试：

- `tests/application/test_mental_care_flow.py`
- `tests/application/test_application_assembly.py`
- `tests/interfaces/test_typed_flow_routes.py`

验证命令：

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.application.test_health_alert_flow tests.application.test_mental_care_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

结果：

- `Ran 37 tests ... OK`

## 本步结论

到这一步为止，我们已经有三条真实 typed flow：

- `health`
- `daily_life`
- `mental_care`

这意味着当前架构已经不再只是“对两个相似案例有效”，而是对第三个明显不同语义的领域也成立。

所以这一步的真正价值不是“多了一个 mental_care 文件夹”，而是：

- 进一步证明当前 `application/domain/interface/assembly` 结构是健康的
- 进一步证明当前 helper 级抽象已经够用
- 暂时不需要更重的 flow template 或容器机制

## 对下一步的影响

既然第三个真实领域已经验证通过，下一步就不应该继续围着 typed flow 抽象打转了。

更合理的方向变成：

- 回到 `platform/observability`
- 或回到 `platform/security`

也就是开始补下一批真正值得补的平台模块，而不是继续在已稳定的 flow 模型上叠加抽象。
