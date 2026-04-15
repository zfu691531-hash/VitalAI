# Project Context

## Project Name

VitalAI

## Project Nature

VitalAI 是一个构建在现有 `Base/` 之上的服务端项目，不是独立的 greenfield 小项目。

开发策略保持不变：

- 复用 `Base` 的通用能力
- 在 `VitalAI` 内承载业务编排、平台机制和领域逻辑
- 保持整体结构长期稳定，避免随着功能增加不断推翻重来

## Project Goal

项目目标是构建面向养老照护场景的中心驱动型智能系统，覆盖：

- 日常协助
- 健康监测与风险识别
- 精神关怀与陪伴
- 面向家属的反馈与报告
- 长期画像、记忆与关系演进

## Current Architecture Decision

当前明确采用：

- `Base` 作为基础能力层
- `VitalAI` 作为有清晰边界的 modular monolith
- `application / platform / domains / interfaces / shared` 作为长期结构

当前不做的架构动作：

- 不做微服务拆分
- 不引入重型容器或工作流平台
- 不为了未来假想规模做过度抽象

结论：

当前架构总体合理，重点是工程化收敛，而不是架构翻修。

## Current Stage Boundary

项目当前处于“工程化基线阶段”。

这个阶段的目标是：

- 让现有分层真正可持续开发
- 让关键路径具备最小工程可信度
- 让至少一部分真实业务能力形成闭环

这个阶段暂不追求：

- 完整生产级高可用
- 完整权限体系
- 大规模多服务部署
- 大量新业务域同时展开

## Structure

```text
VitalAI/
├─ application/
├─ platform/
├─ domains/
├─ interfaces/
├─ shared/
└─ main.py
```

## Layer Intent

### `platform/`

承载跨领域平台机制：

- messaging
- feedback
- arbitration
- interrupt
- observability
- security
- runtime

重要边界：

`runtime/` 不应回退成一个超级 `supervisor` 文件，而应保持为一组围绕运行时决策协作的组件：

- decision core
- event aggregator
- health monitor
- shadow decision core
- snapshots
- failover
- degradation

### `domains/`

承载业务领域本身：

- health
- daily_life
- mental_care
- reporting
- profile_memory

### `application/`

承载用例编排、流程组合、工作流组织。

### `interfaces/`

承载 API、scheduler、consumer 等外部入口。

### `shared/`

只放轻量、稳定、跨层可复用的小对象，不变成杂项目录。

## Relationship With `Base`

`Base` 是 VitalAI 的基础能力层。

在新增基础能力前，优先检查 `Base` 是否已经提供：

- `Base/Config`
- `Base/Ai`
- `Base/Client`
- `Base/Repository`
- `Base/Models`
- `Base/Service`
- `Base/RicUtils`

## Base Reuse Rule

实现新模块前遵循这条规则：

1. 先确认 `Base` 是否已有能力
2. 如果已有，优先复用
3. 如果缺的是通用能力，优先补到 `Base`
4. 如果缺的是 VitalAI 特有能力，放在 `VitalAI`

## Practical Boundary

### 适合放进 `Base`

- 通用 client
- 通用数据库抽象
- 通用模型封装
- 通用工具
- 可跨项目复用的基础设施辅助能力

### 适合放进 `VitalAI`

- runtime decision / snapshot / failover 协作机制
- elder-care 业务领域逻辑
- 场景化 use case / workflow
- profile memory 与长期演进逻辑
- VitalAI 特有的平台 contract

## Documentation Source Of Truth

当前文档真源顺序：

1. `docs/DOCS_INDEX.md`
2. `docs/PROJECT_CONTEXT.md`
3. `docs/CURRENT_STATUS.md`
4. `docs/NEXT_TASK.md`
5. `docs/MODULE_DEVELOPMENT_PLAN.md`
6. `README.md`

`STEP_*` 文档是历史拆解记录，已归档到 `docs/archive/steps/`，不再默认承担“当前状态说明”。

## New Session Bootstrap

新会话默认按下面顺序进入上下文：

1. `docs/DOCS_INDEX.md`
2. `docs/PROJECT_CONTEXT.md`
3. `docs/CURRENT_STATUS.md`
4. `docs/NEXT_TASK.md`
5. `docs/MODULE_DEVELOPMENT_PLAN.md`
6. `README.md`
7. 当前任务直接相关的 `Base/` 目录与模块文档

## Module-To-Base Reading Hints

- messaging/config/logging：优先看 `Base/Config`、`Base/RicUtils`
- persistence：优先看 `Base/Repository`、`Base/Models`
- LLM/AI：优先看 `Base/Ai`
- 外部集成：优先看 `Base/Client`、`Base/Service`
