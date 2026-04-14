# Base 复用与接入手册

## 文档定位

这份文档专门说明：

- 在 VitalAI 开发时，如何优先复用 `Base`
- 什么应该进 `Base`
- 什么应该留在 `VitalAI`
- 各类能力应该优先查看 `Base` 的哪个目录

## 基本原则

一句话概括：

- 通用基础能力优先复用 `Base`
- VitalAI 运行时语义与业务专属结构留在 `VitalAI`

## 为什么需要这份手册

当前项目已经进入多模块开发阶段，如果没有明确的 `Base` 复用规则，后面很容易出现：

- 在 `VitalAI` 里重复写一套配置读取
- 在 `VitalAI` 里重复写一套 Repository
- 在 `VitalAI` 里再造一套通用工具
- 反过来又把 VitalAI 专属业务语义错误塞进 `Base`

这两种错误都要避免。

## Base 各目录的推荐用途

### `Base/Config`

优先用于：

- `.env` 读取
- Settings
- logging 初始化

当你要做下面这些事时，先看这里：

- 环境变量
- 日志级别
- 配置项管理

### `Base/Ai`

优先用于：

- LLM 接入
- prompt 基础能力
- AI service 抽象

当你要做下面这些事时，先看这里：

- 模型调用
- 多模型切换
- prompt 复用

### `Base/Client`

优先用于：

- MySQL
- Redis
- MinIO
- 邮件
- 调度
- ASR

当你要接入外部客户端时，优先检查这里，而不是在 `VitalAI` 里直接 new 客户端。

### `Base/Repository`

优先用于：

- 连接管理
- ORM 基类
- 多数据库支持
- repository 相关底座

当某个 domain 需要持久化时，优先围绕这个目录接，而不是重新造数据访问基类。

### `Base/Models`

优先用于：

- 通用数据模型
- 可跨项目复用的基础模型

不适合放：

- VitalAI 的 runtime contract
- 某个领域专属 outcome

### `Base/Service`

优先用于：

- 已沉淀的通用服务能力
- 可跨项目复用的 service 封装

### `Base/RicUtils`

优先用于：

- 路径处理
- 文件处理
- 日期
- HTTP
- PDF
- Redis 辅助

当你想写工具函数时，先检查这里。

## 什么应该继续留在 VitalAI

下面这些内容，原则上不要迁进 `Base`：

### 1. 平台运行时契约

例如：

- `MessageEnvelope`
- `FeedbackEvent`
- `IntentDeclaration`
- `InterruptSignal`

原因：

- 它们承载的是 VitalAI 自己的运行时语义
- 不是通用基础设施

### 2. 角色感知 assembly 策略

例如：

- reporting enablement
- ingress ack
- ingress ttl
- policy snapshot

原因：

- 这是 VitalAI 当前运行模型的专属装配逻辑

### 3. 领域专属输出

例如：

- `HealthTriageOutcome`
- `DailyLifeSupportOutcome`

原因：

- 这些是领域语义，不是跨项目通用模型

## 开发前检查清单

每次开始一个模块前，建议先做这个检查：

### 1. 我现在要解决的问题是什么类型？

- 配置？
- 日志？
- LLM？
- 持久化？
- 外部客户端？
- 通用工具？
- 平台运行时？
- 业务领域？

### 2. 如果是通用基础能力，先检查 `Base`

优先检查：

- `Base/Config`
- `Base/Ai`
- `Base/Client`
- `Base/Repository`
- `Base/Models`
- `Base/Service`
- `Base/RicUtils`

### 3. 如果是 VitalAI 专属运行时语义，就留在 VitalAI

优先考虑：

- `platform`
- `application`
- `domains`
- `interfaces`

## 推荐决策规则

### 该进 `Base` 的判断标准

满足越多越应该进 `Base`：

- 与具体业务场景无关
- 可跨项目复用
- 属于基础设施或通用模型
- 不依赖 VitalAI 的运行角色/业务语义

### 该留在 `VitalAI` 的判断标准

满足越多越应该留在 `VitalAI`：

- 与老人陪护场景直接相关
- 属于运行时协议或角色策略
- 属于应用编排逻辑
- 属于某个业务领域语义

## 接入方式建议

### 配置接入

- 优先通过 `Base/Config/setting.py`
- 不要在多个模块里各自复制环境读取逻辑

### 日志接入

- 优先通过 `Base/Config/logConfig.py`
- 不要在 `VitalAI` 里再造第二套日志初始化

### Repository 接入

- 领域 repository 可以围绕 `Base/Repository` 封装
- 不要在 `VitalAI` 自己重写连接池或 ORM 基类

### 外部客户端接入

- 优先检查 `Base/Client`
- 如果已有能力，直接复用
- 如果没有，再考虑补到 `Base` 或在 `VitalAI` 本地先做薄封装

## 当前项目里的已验证结论

到目前为止，已经验证过的边界结论包括：

- `Base/Models` 没有现成可复用的 platform runtime contract 层
- `Base/RicUtils` 有很多小工具，但没有 typed messaging / arbitration schema
- `Base/Repository` 是持久化底座，不是 application service registry
- 当前 contract 层应继续留在 `VitalAI/platform`
- 当前 assembly 角色策略应继续留在 `VitalAI/application`

## 常见错误

### 错误 1：在 VitalAI 里重复造基础设施

表现：

- 自己再写一套 settings
- 自己再写一套 repository base
- 自己再写一套通用工具

### 错误 2：把 VitalAI 专属语义塞进 Base

表现：

- 把运行角色策略迁进 Base
- 把 MessageEnvelope 当成通用基础模型
- 把某个领域 outcome 当成 Base model

### 错误 3：没检查 Base 就开始编码

表现：

- 做完后才发现 `Base` 已经有现成功能

## 推荐工作流

后续每次进入一个新模块，建议统一这样做：

1. 先读：
   - `docs/PROJECT_CONTEXT.md`
   - `docs/CURRENT_STATUS.md`
   - `docs/NEXT_TASK.md`
   - `README.md`

2. 再判断当前问题类型

3. 先检查对应 `Base` 目录

4. 再决定代码落在：
   - `Base`
   - 或 `VitalAI`

5. 实现后，在文档里明确记录这次复用判断

## 当前建议

短期内，`Base` 最适合继续承载的是：

- 配置
- 日志
- Repository
- 客户端
- 通用服务
- 工具

短期内，VitalAI 最适合继续承载的是：

- 平台 contract
- runtime 组件
- application assembly
- typed flow
- 领域输出
- 角色策略
