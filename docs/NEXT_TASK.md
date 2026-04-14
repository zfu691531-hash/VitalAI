# Next Task

## Goal

The current controlled health failover drill slice has reached a reasonable stable stop point.

The next task should be chosen fresh from a nearby runtime/observability/security slice instead of continuing to polish this same diagnostics result.

Reference for the previous steps:

- `docs/MODULE_DEVELOPMENT_GUIDE.md`
- `docs/MODULE_PLATFORM_GUIDE.md`
- `docs/MODULE_APPLICATION_GUIDE.md`
- `docs/MODULE_INTERFACES_GUIDE.md`
- `docs/BASE_REUSE_AND_INTEGRATION_GUIDE.md`
- `docs/STEP_29_ASSEMBLY_POLICY_FOR_RUNTIME_SIGNALS.md`
- `docs/STEP_30_ROLE_DEFAULT_RUNTIME_SIGNAL_POLICY.md`
- `docs/STEP_31_ASSEMBLY_RUNTIME_DIAGNOSTICS_FOR_SNAPSHOTS_AND_FAILOVER.md`
- `docs/STEP_32_RUNTIME_SNAPSHOT_IN_REAL_HEALTH_FLOW.md`
- `docs/STEP_33_MINIMAL_FAILOVER_SIGNAL_IN_CRITICAL_HEALTH_FLOW.md`
- `docs/STEP_34_INTERRUPT_EXPOSURE_FOR_SNAPSHOT_REFS.md`
- `docs/STEP_35_CONTROLLED_HEALTH_FAILOVER_DRILL.md`
- `docs/STEP_36_RICHER_HEALTH_FAILOVER_DRILL_DIAGNOSTICS.md`
- `docs/STEP_37_DRILL_FOCUSED_SECURITY_DIAGNOSTICS.md`
- `docs/STEP_38_DRILL_FOCUSED_OBSERVABILITY_SIGNAL_ID.md`
- `docs/STEP_39_POLICY_OBSERVATION_ALIGNMENT_FOR_POLICY_SOURCES.md`
- `docs/STEP_40_SNAPSHOT_POLICY_GENERALIZATION_FOR_HIGH_URGENCY_DAILY_LIFE.md`
- `docs/STEP_41_SECURITY_REVIEW_HIGHEST_SEVERITY_DETAIL.md`
- `docs/STEP_42_RUNTIME_SNAPSHOT_TRACE_CORRELATION.md`
- `docs/STEP_43_FAILOVER_OBSERVATION_SNAPSHOT_CORRELATION.md`
- `docs/STEP_44_FAILBACK_SIGNAL_CORRELATION_CONSISTENCY.md`
- `docs/STEP_45_SECURITY_POSTURE_ALIGNMENT_FOR_DIAGNOSTICS.md`

## Scope

Choose one adjacent slice, but do only one:

1. `VitalAI/platform/runtime/`
2. `VitalAI/platform/observability/`
3. `VitalAI/platform/security/`
4. `VitalAI/application/use_cases/runtime_support.py`
5. `VitalAI/application/assembly.py`
6. `VitalAI/interfaces/typed_flow_support.py`
7. `Base/Config/`
8. `Base/Models/`
9. `Base/RicUtils/`

## Base Reuse Checklist Before Coding

Before implementing the next step, re-check whether `Base` already contains reusable parts:

- for config/logging, inspect `Base/Config`
- for common schemas or model patterns, inspect `Base/Models`
- for generic utilities, inspect `Base/RicUtils`

Current conclusion from this round:

- `Base` still does not provide a suitable abstraction for these runtime/observability/security contracts
- the next slice should stay inside `VitalAI/platform` or `VitalAI/application`

## Fresh Next Focus

Pick one new nearby area rather than extending the same drill result again:

### 1. Snapshot Policy Generalization

Status:

- completed for typed snapshot policy plus high-urgency daily-life

What was added:

- runtime snapshot capture now uses `SnapshotCapturePolicy`
- critical `HEALTH_ALERT` and high-urgency `DAILY_LIFE_CHECKIN` are explicit rules
- shared runtime support now derives snapshot and interrupt behavior from the typed capture decision

Do not immediately broaden this again to more flows unless a new neighboring case is clearly worth it.

### 2. Security Review Detail Refinement

Status:

- completed for `highest_severity`

What was added:

- `SecurityReviewResult` now computes strongest finding severity
- `SECURITY_REVIEW` observations now carry `highest_severity`
- runtime signal views now expose that severity directly

Do not continue refining this same signal detail shape unless a clearly missing security posture concept appears.

### 3. Policy Observation Alignment

Status:

- completed for policy-source metadata

What was added:

- policy snapshots now distinguish `assembly_default`, `role_default`, and `environment_override`
- policy observations now carry the same source metadata

Do not continue polishing this same policy-observation shape immediately unless a future runtime policy field creates a clear mismatch again.

## Recommended Next Focus

The seven adjacent slices listed before this step have now each reached a reasonable stop point.

The next task should be chosen fresh from a new nearby runtime/observability/security seam, with the same constraints:

- minimal
- typed
- real
- no reopening of the current result boundaries without strong reason

Candidate directions from the current stop point:

- runtime snapshot retention/versioning rules

## Constraints

- keep implementation minimal and typed
- do not reopen result boundary work unless the new slice truly forces it
- do not drift into adding new business flows yet
- do not introduce a new shared/base layer unless clearly required

## Done Definition

This task is complete when:

- one adjacent runtime/observability/security slice has been implemented
- focused verification has been run for the affected modules
- `docs/CURRENT_STATUS.md` and `docs/NEXT_TASK.md` are updated after completion

## How To Resume In A New Window

Use this prompt:

```text
先阅读：
1. docs/PROJECT_CONTEXT.md
2. docs/CURRENT_STATUS.md
3. docs/NEXT_TASK.md
4. README.md

然后检查本次模块相关的 Base 目录，再继续开发。

当前状态：
1. runtime_signals 结果边界已经稳定
2. runtime_signals_enabled 已经进入 assembly policy，并且 scheduler 默认关闭
3. snapshots / failover signals 已经从 assembly diagnostics 推进到 real health flow 和 controlled failover drill
4. controlled health failover drill 现在已经直接暴露 interrupt posture、security posture、以及 failover-driving signal id
5. 这一小条 diagnostics slice 现在可以先停，不要继续打磨同一个结果对象

当前优先方向：
1. 先查看 VitalAI/platform/runtime/
2. 再查看 VitalAI/platform/observability/ 与 VitalAI/platform/security/
3. 重新挑一个相邻小切片继续推进，推荐从 snapshot policy generalization、security review detail refinement、policy observation alignment 三者里选一个
4. 完成后同步更新步骤文档、docs/CURRENT_STATUS.md、docs/NEXT_TASK.md
```
