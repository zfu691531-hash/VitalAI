# Docs Index

Date: 2026-04-14

## Purpose

`docs/` 里的文档已经明显多于当前开发阶段真正需要长期维护的数量。

从现在开始，文档分为三层：

1. 当前真源文档
2. 说明性/参考性文档
3. 历史过程文档

不要再把所有 `STEP_*` 文档当成“当前状态说明”来使用。

## Current Source Of Truth

这些文档需要保持短、准、可执行：

- `README.md`
  - 仓库入口、启动方式、基础结构说明。
- `docs/PROJECT_CONTEXT.md`
  - 项目长期定位、架构方向、`Base` 与 `VitalAI` 的边界。
- `docs/CURRENT_STATUS.md`
  - 当前开发阶段、架构判断、当前可做/不该做/可稍后做。
- `docs/NEXT_TASK.md`
  - 最近一个阶段真正推荐推进的事项，不写成长流水账。
- `docs/MODULE_DEVELOPMENT_PLAN.md`
  - 中文分模块开发计划，用于跟随阶段进度、对照交付物和人工验收标准。
- `docs/DOCS_INDEX.md`
  - 文档治理规则与阅读顺序。

## Supporting Docs

这些文档有价值，但不是“当前状态真源”：

- `docs/PROJECT_ISSUE_REPORT_2026-04-14.md`
  - 一次阶段性问题审查报告，用于追踪问题与整改方向。
- `docs/MODULE_DEVELOPMENT_GUIDE.md`
  - 模块开发规范与分层风格说明。
- `docs/MODULE_PLATFORM_GUIDE.md`
- `docs/MODULE_APPLICATION_GUIDE.md`
- `docs/MODULE_DOMAINS_GUIDE.md`
- `docs/MODULE_INTERFACES_GUIDE.md`
- `docs/MODULE_SHARED_GUIDE.md`
- `docs/BASE_REUSE_AND_INTEGRATION_GUIDE.md`
- `docs/NEW_WINDOW_PROMPT.md`
- `docs/intent_dataset_examples.jsonl`

这些文档适合在进入某个模块前阅读，但它们不应该覆盖 `PROJECT_CONTEXT / CURRENT_STATUS / NEXT_TASK` 的判断。

## Historical Docs

以下内容已归档，视为历史记录或阶段拆解材料：

- `docs/archive/steps/STEP_*.md`
- `docs/archive/design-assets/*.docx`
- `docs/archive/design-assets/*.mmd`
- `docs/archive/design-assets/*.png`
- `docs/archive/design-assets/*.xmind`
- `docs/archive/reports/*.md`
- `docs/plans/*.md`

使用规则：

- 只有当当前任务直接依赖某个历史决策或某一步技术拆解时，才去读对应 `STEP_*`。
- `STEP_*` 不再负责描述“项目现在到哪一步了”。
- 新的小修补、小重构，不再默认新增新的 `STEP_*` 文档。

## Current Documentation Policy

### 1. 状态文档要短

`CURRENT_STATUS.md` 应该回答：

- 项目处于什么阶段
- 当前架构是否合理
- 现在该做什么
- 现在不该做什么

它不应该继续充当完整开发日志。

### 2. 下一步文档只写近阶段动作

`NEXT_TASK.md` 只保留当前阶段最有价值的 1 到 3 个方向。

它不应该继续维护“所有可能下一步”的大清单。

### 3. 架构变化先改上下文文档

如果发生下列变化，先更新 `PROJECT_CONTEXT.md`，再继续开发：

- 架构模式变化
- `Base` 复用边界变化
- 当前阶段目标变化
- 开发边界变化

### 4. 问题报告是阶段性文件

`PROJECT_ISSUE_REPORT_2026-04-14.md` 是一次阶段性审查，不代表永远正确。

当其中某些问题已被修复时，应在报告顶部加状态说明，而不是继续让旧结论直接误导后续工作。

## Recommended Reading Order

新会话默认按下面顺序阅读：

1. `docs/DOCS_INDEX.md`
2. `docs/PROJECT_CONTEXT.md`
3. `docs/CURRENT_STATUS.md`
4. `docs/NEXT_TASK.md`
5. `docs/MODULE_DEVELOPMENT_PLAN.md`
6. `README.md`
7. 当前任务直接相关的模块手册；只有需要回溯历史时再看 `docs/archive/steps/STEP_*`

## Cleanup Decision

当前阶段不删除历史文档，只做物理归档，原因是：

- 项目仍在开发期
- 这些历史拆解材料对回溯设计意图仍然有价值
- 当前最紧迫的问题是“文档治理”，不是“历史资料销毁”

当前归档结构：

```text
docs/archive/
├─ steps/          # STEP_* 历史开发步骤
├─ design-assets/  # docx / mmd / png / xmind 设计资料
└─ reports/        # 非当前真源的阶段记录
```

等项目进入更稳定阶段后，可以再考虑是否把归档资料拆分为正式设计文档、ADR 或删除无用材料。
