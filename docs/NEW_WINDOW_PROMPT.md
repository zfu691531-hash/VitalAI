# New Window Prompt

Date: 2026-04-15

## 用途

这份文档用于新会话交接。新会话应先读取本文，再按阅读顺序补齐项目背景，避免重复探索、误改方向或把尚未到阶段的能力提前做重。

## 新会话阅读顺序

1. `docs/DOCS_INDEX.md`
2. `docs/PROJECT_CONTEXT.md`
3. `docs/CURRENT_STATUS.md`
4. `docs/NEXT_TASK.md`
5. `docs/MODULE_DEVELOPMENT_PLAN.md`
6. `README.md`
7. 与当前任务直接相关的代码和模块手册

## 当前阶段判断

项目处在工程化基线阶段，不是产品 UI 阶段，也不是微服务拆分阶段。

当前主线是：先把后端可验证闭环打稳，再逐步接入模型能力。架构方向保持 modular monolith，以 `application` 编排用例，以 `platform` 承载运行时、仲裁、模型适配等基础能力，以 `domains` 保存领域规则，以 `interfaces` 暴露 API。

## 最近已完成

- 已建立 backend-only 用户交互入口 `POST /vitalai/interactions`，暂不做前端 UI、App 或完整聊天系统。
- 已建立 profile memory 的写入和查询链路。
- 已接入第一层意图识别抽象，支持 rule-based 与 BERT recognizer。
- 已扩充意图评估集到 270 条，其中 `needs_decomposition` 复杂样本 33 条，holdout 90 条。
- 已明确第一层职责：简单单意图可直接识别；复合、模糊、多任务老人表达不强行单分类，而是返回 `requires_decomposition=true`。
- 已新增第二层意图拆解占位能力，包含 typed task、风险标记、placeholder decomposer、LLM decomposer shell、LLM 输出 schema 和 validator。
- 已新增配置开关 `VITALAI_INTENT_DECOMPOSER=placeholder|llm`，默认 `placeholder`。当前即使配置为 `llm`，没有真实 backend 时也会安全回退到 placeholder。
- 已接入第二层 workflow 守门逻辑：合法拆解输出只生成非执行型 `routing_candidate`，澄清输出生成 `clarification_candidate`，高风险、低置信、缺 primary task 或 route guard 不通过时保持非 accepted。
- 已接入最小 `InputPreprocessor`：workflow 前置执行 trim、连续空白收敛、原始输入保留、空消息保护和基础异常标记，HTTP 响应包含 `preprocessing`。
- 已接入 BERT hard-case guard：用药后不适、明确长期提醒/记忆写入、记忆查询等高价值混淆会在 BERT 预测前被可解释规则兜底，复合意图检测仍优先。
- 已为 profile memory 查询增加可选 `memory_key` 精确过滤；不传 key 返回完整 snapshot，传 key 返回单 key snapshot 或稳定空 snapshot。
- 当前测试基线：`pytest tests -q` 通过 155 项；rule-based 评估 270/270；BERT baseline 180/180；BERT holdout 90/90。

## 当前约束

- 不要把 LLM 输出直接接入领域 workflow、数据库写入或高风险动作。
- 不要在当前阶段接真实 LLM backend 到主链路。
- 不要新增前端 UI、App、完整聊天系统。
- 不要拆微服务，不要为了抽象而新增复杂层。
- 不要继续新增大量 `STEP_*` 文档；优先维护 `CURRENT_STATUS.md`、`NEXT_TASK.md`、`MODULE_DEVELOPMENT_PLAN.md`、模块指南和计划文档。
- 不要让 BERT 承担复合意图拆解职责；BERT 是第一层快速分类器，不是复杂推理层。

## 当前下一步

当前要防止过度工程化：意图识别主线先收口，不继续深挖 BERT/LLM；优先做小批量真实困难样本评估，或推进 profile memory 的轻量可读性增强。

目标不是接入真实大模型，也不是为了分数删除困难样本，而是继续验证 hard-case guard 是否过度泛化：

- 继续收集健康/用药不适、提醒/记忆写入、记忆查询、日常提醒之间的真实混淆样本，但只做小批量，不扩成模型工程。
- 特别补充“提醒我”但不该进入长期记忆的日常提醒样本，避免 guard 过度泛化。
- profile memory 当前只做 snapshot 可读性增强，不做 graph、embedding retrieval 或模糊搜索。
- 保持 `needs_decomposition_detector` 在 BERT 之前运行，不能把复合输入压回单 intent。
- 第一层返回 `requires_decomposition=true` 时，仍进入第二层拆解与 guard。
- 第二层 validator 通过后也不能直接执行动作，只能生成可审计的 routing candidate / clarification candidate。

## 建议实现范围

- 在 `docs/intent_dataset_examples.jsonl` 中补充真实困难样本，必须标注 split/source/notes。
- 补测试或评估断言，观察 `bert_hard_case_guard` 的命中数量、正确率和误伤样本。
- 保持 `interfaces/api/routers/interactions.py` 不承载业务判断或模型细节。
- 更新 `docs/CURRENT_STATUS.md` 和 `docs/NEXT_TASK.md`，只记录阶段性事实和下一步，不写成长流水账。

## 验收命令

```powershell
pytest tests -q
python scripts\evaluate_intents.py --recognizer rule_based --group-by-split
C:\Users\Windows\miniconda3\python.exe scripts\evaluate_intents.py --recognizer bert --bert-model-path D:\AI\Models\fine-tuned-bert-intent-vitalai-trained --bert-labels health_alert,daily_life_checkin,mental_care_checkin,profile_memory_update,profile_memory_query,unknown --splits holdout --group-by-split
```

说明：普通 `python` 当前可能指向缺少 `torch` 的 Anaconda 环境，BERT 评估请优先使用 `C:\Users\Windows\miniconda3\python.exe`。

## 可复制给新会话的提示词

```text
你是 VitalAI 项目的资深后端开发工程师和项目架构掌舵者。当前工作目录是 D:\Users\Windows\PycharmProjects\VitalAI。请先阅读 docs/NEW_WINDOW_PROMPT.md、docs/DOCS_INDEX.md、docs/PROJECT_CONTEXT.md、docs/CURRENT_STATUS.md、docs/NEXT_TASK.md、docs/MODULE_DEVELOPMENT_PLAN.md 和 README.md，再继续开发。

当前项目处在工程化基线阶段，架构方向是 modular monolith，不做微服务拆分、不做前端 UI、不做完整聊天系统。当前主线是后端用户交互入口 + 第一层意图识别 + 第二层复合意图拆解安全边界。

已完成：POST /vitalai/interactions、profile memory 读写、rule/BERT 第一层意图识别、270 条意图评估集、needs_decomposition 复杂样本、第二层意图拆解 typed contract、placeholder decomposer、LLM decomposer shell、schema validator、非执行型 workflow routing guard、最小 InputPreprocessor、BERT hard-case guard、VITALAI_INTENT_DECOMPOSER=placeholder|llm 配置开关。

当前不要接真实 LLM backend 到主链路，不要让 LLM 输出直接调用领域 workflow 或写库，也不要继续在 BERT/LLM 单点上过度工程化。下一步请优先做小批量真实困难样本评估，或推进 profile memory snapshot 的轻量可读性增强；profile memory 当前只允许 key 精确查询，不做 graph、embedding retrieval 或模糊搜索。第二层拆解仍只能生成 routing candidate 或 clarification candidate，高风险健康、用药、安全、记忆异常场景必须保守处理并可审计。

开发时请先检查现有代码和测试，再小步实现。完成后运行 pytest tests -q、rule-based 评估，以及使用 C:\Users\Windows\miniconda3\python.exe 运行 BERT holdout 评估。最后更新 docs/CURRENT_STATUS.md 和 docs/NEXT_TASK.md，保持文档简洁可交接。
```
