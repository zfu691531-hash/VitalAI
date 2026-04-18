# Second-Layer Eval

这套基线只做离线校验，不直接执行领域 workflow。

数据集：

- `data/intent_eval/second_layer_hard_cases.jsonl`
- `data/intent_eval/second_layer_response_snapshots.jsonl`
- `data/intent_eval/second_layer_capture_cases.jsonl`
- `capture_second_layer_response_snapshots.py` 支持 `--id`、`--category`、`--limit` 和 `--list-cases`，可先预览、再按小批次执行真实采样
- `capture_second_layer_response_snapshots.py` 也支持 `--skip-existing`，便于分批补采时跳过已经写进当前输出 JSONL 的 case id
- `capture_second_layer_response_snapshots.py` 现已和主链路保持一致，支持 `VITALAI_INTENT_DECOMPOSER_LLM_PROVIDER=openai_compatible|base_qwen`

脚本：

- `scripts/intent_eval/evaluate_second_layer_hard_cases.py`
- `scripts/intent_eval/capture_second_layer_response_snapshots.py`
- `scripts/intent_eval/build_second_layer_snapshot_review_queue.py`
- `scripts/intent_eval/manage_second_layer_snapshot_review_queue.py`
- `scripts/intent_eval/promote_second_layer_snapshot_review_queue.py`
- `scripts/intent_eval/audit_second_layer_snapshot_baseline.py`

覆盖范围：

- 手写 `raw_payload` hard-case
- 原始模型 `raw_response_text` 回放
- markdown code fence / prose wrapper / parse failure
- 高风险阻断
- `ask_clarification`
- schema 非法输出

评测运行：

```powershell
python scripts\intent_eval\evaluate_second_layer_hard_cases.py --output text
python scripts\intent_eval\evaluate_second_layer_hard_cases.py --dataset data\intent_eval\second_layer_response_snapshots.jsonl --output text
```

真实响应采样：

```powershell
$env:VITALAI_INTENT_DECOMPOSER_LLM_MODEL="glm-5.1"
$env:VITALAI_INTENT_DECOMPOSER_LLM_API_KEY="your_llm_api_key"
$env:VITALAI_INTENT_DECOMPOSER_LLM_BASE_URL="https://open.bigmodel.cn/api/paas/v4/"
python scripts\intent_eval\capture_second_layer_response_snapshots.py
python scripts\intent_eval\capture_second_layer_response_snapshots.py --category profile_memory --limit 2
python scripts\intent_eval\capture_second_layer_response_snapshots.py --list-cases
python scripts\intent_eval\capture_second_layer_response_snapshots.py --category health+medication --limit 2
python scripts\intent_eval\capture_second_layer_response_snapshots.py --category profile_memory --skip-existing --append
python scripts\intent_eval\build_second_layer_snapshot_review_queue.py
python scripts\intent_eval\manage_second_layer_snapshot_review_queue.py summary
python scripts\intent_eval\manage_second_layer_snapshot_review_queue.py triage-report --review-status pending_human_review
python scripts\intent_eval\manage_second_layer_snapshot_review_queue.py list --review-status pending_human_review --bulk-approval eligible_for_bulk_approval
python scripts\intent_eval\evaluate_second_layer_hard_cases.py --dataset .runtime\intent_eval\second_layer_snapshot_review_queue.jsonl --output text
python scripts\intent_eval\promote_second_layer_snapshot_review_queue.py
python scripts\intent_eval\evaluate_second_layer_hard_cases.py --dataset data\intent_eval\second_layer_response_snapshots.jsonl --output text
python scripts\intent_eval\audit_second_layer_snapshot_baseline.py --output text
```

默认行为：

- 采样模板来自 `data/intent_eval/second_layer_capture_cases.jsonl`
- 当前采样模板已扩到 16 条，适合作为第一批真实 GLM 5.1 快照采样包
- 采样输出默认写到 `.runtime/intent_eval/second_layer_captured_snapshots.jsonl`
- 审核队列默认写到 `.runtime/intent_eval/second_layer_snapshot_review_queue.jsonl`
- 正式回放数据集默认写到 `data/intent_eval/second_layer_response_snapshots.jsonl`
- 采样输出会保留 `message`、第一层识别结果、`raw_response_text`、解析结果、validator 结果和 guard 结果
- 审核队列会自动补出建议 `expected`、`review_status`、`review_notes`、`review_recommendation`、`bulk_approval_recommendation` 和来源 metadata
- `review_recommendation` 当前分为 `approve_candidate`、`manual_review_required`、`baseline_negative_candidate`
- `bulk_approval_recommendation` 当前分为 `eligible_for_bulk_approval`、`requires_manual_approval`、`not_applicable_for_bulk_approval`
- recommendation 规则当前集中在 `scripts/intent_eval/review_policy.py`
- 审核队列管理脚本支持 `summary / triage-report / list / show / set-status / bulk-set-status`，便于先看 recommendation / bulk approval 原因分布，再按 `bulk_approval=eligible_for_bulk_approval` 筛出真正可批量放行的候选
- 待审核快照和审核队列都不会自动进入正式回放数据集
- 正式入库脚本只会提升 `review_status=approved_for_baseline` 的项，并保留 recommendation 与 bulk approval provenance
- baseline 审计脚本会额外检查正式数据集里的 provenance 分布、重复 `id`、缺失 `review_metadata` 与缺失 `source_capture`

关键字段：

- `input_kind_counts`
  统计 `raw_payload` 和 `raw_response_text`
- `parse_failure_count`
  统计原始响应在进入 validator 前的解析失败数
- `guard_status_counts`
  统计 validator 通过后 guard 的输出状态
- `expectation_failure_count`
  统计与样本期望不一致的数量；非 0 时评测脚本返回退出码 `1`

当前用途：

- 锁住第二层 schema 和 guard 行为
- 回放真实模型脏响应
- 批量采样真实 GLM/Qwen/DeepSeek 响应，再人工挑选高价值样本补进回放数据集
- 先把采样结果转成 review queue，再人工确认是否纳入正式基线
- 审核通过后再通过 promotion 脚本正式并入回放数据集
