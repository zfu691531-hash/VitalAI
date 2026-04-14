# Application 模块开发手册

## 模块定位

`VitalAI/application/` 负责完整业务用例编排，是：

- domain 的组织层
- platform 的消费层
- interfaces 的下游

它解决的是：

- 一个完整业务动作怎么跑通
- 命令如何进入系统
- runtime 与 domain 如何被串起来
- workflow 如何产出最终结果

## 当前结构

```text
VitalAI/application/
├─ commands/
├─ queries/
├─ use_cases/
├─ workflows/
└─ assembly.py
```

## 当前已完成内容

### commands

- `health_alert_command.py`
- `daily_life_checkin_command.py`

### use_cases

- `health_alert_flow.py`
- `daily_life_checkin_flow.py`
- `runtime_support.py`

### workflows

- `health_alert_workflow.py`
- `daily_life_checkin_workflow.py`
- `reporting_support.py`

### assembly

- `assembly.py`
- 环境感知
- 角色感知
- reporting / ack / ttl 策略
- policy snapshot

## 子模块要求

### `commands/`

要求：

- 表达稳定输入
- 贴近业务动作
- 不承载运行角色策略

不要做：

- 在 command 里写 scheduler / consumer 特化
- 把 transport 调整逻辑放进 command

交付标准：

- 能稳定转成 typed message / input object

### `use_cases/`

要求：

- 负责编排 runtime 与 domain
- 处理完整业务链路中的主逻辑路径
- 输出清晰的 result 对象

不要做：

- 在这里混入 HTTP / scheduler / consumer 细节
- 把 domain service 的判断直接内联

交付标准：

- 输入清晰
- 流程闭合
- 输出可被 workflow 消费

### `workflows/`

要求：

- 负责更完整的多步组合
- 可以在 use case 基础上接 reporting / policy transform / 其他后处理

不要做：

- 把 workflow 做成第二套 use case
- 引入和 interface 强耦合的逻辑

交付标准：

- workflow 层输出应清晰表达“流程结果 + 附加产物”

### `assembly.py`

要求：

- 负责组合依赖
- 负责运行角色策略
- 负责把 environment / role 映射为当前装配行为

不要做：

- 发展成重型容器
- 让 interfaces 重新拥有装配权

交付标准：

- 能按角色构建 workflow
- 能描述当前策略快照
- 能在不引入重型机制的前提下支持轻量替换

## 代码风格

- command / use case / workflow / assembly 层级分明
- 同一层只做同一层的事
- 注释解释“为什么这样分层”
- 保持 result / outcome / snapshot 这些对象的命名一致性

## 开发边界

### 可以依赖谁

- `platform`
- `domains`
- `shared`
- `Base` 的通用基础设施

### 不应该依赖谁

- 不应该直接知道接口细节
- 不应该承载领域内核本身

## 推进步骤建议

1. 先定义 command 或输入对象
2. 明确 use case 的 typed result
3. 串接 runtime 与 domain
4. 再补 workflow
5. 最后决定是否需要 assembly 扩展

## 测试建议

优先写：

- use case 级测试
- workflow 级测试
- assembly 策略测试

避免：

- 所有逻辑只靠接口层测试覆盖

## 常见错误

- 把 interfaces 逻辑写进 use case
- 把领域判断写进 assembly
- 为了复用而过早把两条 flow 抽成一个泛型模板

## 当前最适合继续做的点

- 再引入一个真实领域 flow，验证现在的 application 结构
- 在真正有必要前，不继续增加新角色策略
- 如果后续需要更多策略，优先先问一句：这是不是 assembly 问题，而不是 domain 问题
