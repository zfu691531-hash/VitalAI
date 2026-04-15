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
- `mental_care_checkin_command.py`
- `profile_memory_update_command.py`
- `user_interaction_command.py`，包含 backend-only 交互事件枚举、别名归一化、基础输入校验和最小 session context

### queries

- `profile_memory_snapshot_query.py`

### use_cases

- `health_alert_flow.py`
- `intent_recognition.py`
- `daily_life_checkin_flow.py`
- `mental_care_checkin_flow.py`
- `profile_memory_flow.py`
- `profile_memory_query.py`
- `runtime_support.py`

### workflows

- `health_alert_workflow.py`
- `daily_life_checkin_workflow.py`
- `mental_care_checkin_workflow.py`
- `profile_memory_workflow.py`
- `profile_memory_query_workflow.py`
- `user_interaction_workflow.py`
- `reporting_support.py`

### assembly

- `assembly.py`
- 环境感知
- 角色感知
- reporting / ack / ttl 策略
- policy snapshot
- runtime snapshot store 工厂选择

当前环境变量接入：

- `VITALAI_RUNTIME_ROLE`：选择当前运行角色
- `VITALAI_REPORTING_ENABLED`：控制 reporting 支持链路
- `VITALAI_RUNTIME_CONTROL_ENABLED`：控制 admin runtime 控制面是否开放
- `VITALAI_ADMIN_TOKEN`：admin 控制面最小 token
- `VITALAI_RUNTIME_SIGNALS_ENABLED`：控制 runtime signal 输出
- `VITALAI_RUNTIME_SNAPSHOT_STORE_PATH`：启用本地文件型 runtime snapshot store
- `VITALAI_PROFILE_MEMORY_DB_PATH`：配置 profile memory SQLite 路径
- `VITALAI_INTENT_RECOGNIZER`：选择 `rule_based` / `bert` / `hybrid`
- `VITALAI_BERT_INTENT_MODEL_PATH`：BERT 意图模型本地路径，只从本地加载，不下载模型
- `VITALAI_BERT_INTENT_CONFIDENCE_THRESHOLD`：BERT 意图置信度阈值，低于阈值时 fallback 到规则识别器
- `VITALAI_BERT_INTENT_LABELS`：BERT 输出标签映射，支持有序标签或 `LABEL_0=health_alert` 显式映射

## 子模块要求

### `commands/`

要求：

- 表达稳定输入
- 贴近业务动作
- 不承载运行角色策略
- 对用户交互这类入口型 command，允许承载轻量契约校验和枚举归一化

不要做：

- 在 command 里写 scheduler / consumer 特化
- 把 transport 调整逻辑放进 command
- 把自然语言意图识别或多轮对话状态塞进 command

交付标准：

- 能稳定转成 typed message / input object
- 校验失败时能给 workflow 稳定的错误原因

### `queries/`

要求：

- 表达只读请求
- 不承载运行时写入语义
- 不伪装成 command

不要做：

- 在 query 里触发持久化写入
- 为了复用把读写都塞进同一个 command

交付标准：

- 能稳定驱动只读 use case / workflow
- 输出由 workflow 或 serializer 统一封装

### `use_cases/`

要求：

- 负责编排 runtime 与 domain
- 处理完整业务链路中的主逻辑路径
- 输出清晰的 result 对象
- 意图识别这类应用级理解能力应通过可替换接口表达，当前规则实现不得阻塞后续 BERT adapter
- BERT 接入前必须先稳定数据 schema、adapter 边界、fallback 和评估入口
- 离线评估应复用 `RunIntentRecognitionEvaluationUseCase`，不要为 BERT 另写一套评估逻辑
- BERT adapter 只能从本地路径加载模型，不允许在主链路里下载模型

不要做：

- 在这里混入 HTTP / scheduler / consumer 细节
- 把 domain service 的判断直接内联
- 把模型文件、tokenizer 下载、GPU 推理细节硬编码进主 workflow
- 在 import 或 assembly 构建阶段加载大模型

交付标准：

- 输入清晰
- 流程闭合
- 输出可被 workflow 消费
- 没有模型依赖时仍能通过 fallback 识别器运行
- 数据集样本应遵循 `IntentDatasetExample`，当前基线文件是 `docs/intent_dataset_examples.jsonl`，每类 intent 至少保留 30 条 baseline，并用 `split=holdout` 标记不参与训练的验收样本
- 手动评估入口是 `python scripts\evaluate_intents.py --recognizer rule_based --group-by-split`
- BERT 手动评估入口是 `python scripts\evaluate_intents.py --recognizer bert --bert-model-path <path> --splits holdout --group-by-split`
- BERT 本地自检入口是 `python scripts\check_bert_intent_runtime.py --model-path <path> --bert-labels <labels>`

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
- 负责根据环境配置选择轻量内存实现或本地持久化实现

不要做：

- 发展成重型容器
- 让 interfaces 重新拥有装配权
- 让具体 API route 直接 new 平台或领域依赖

交付标准：

- 能按角色构建 workflow
- 能描述当前策略快照
- 能在不引入重型机制的前提下支持轻量替换
- 能通过环境变量启用或关闭 runtime snapshot 持久化

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

- 保持 runtime snapshot store 的选择逻辑集中在 assembly
- 后续如扩展用户交互，优先在 application workflow 层编排，不把业务判断写进 interface
- 当前交互入口只保持 backend-only 契约，不急于增加完整聊天 session persistence
- 下一步如接 BERT，复用现有离线评估入口，不直接把模型推理耦合进 workflow
- 在真正有必要前，不继续增加新角色策略
