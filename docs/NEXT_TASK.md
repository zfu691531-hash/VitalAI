# Next Task

## Goal

Connect the existing runtime shell to the newly created platform contracts and add minimal verification.

## Scope

Use the new contract layer as the input and output shape for the runtime shell where appropriate:

1. `VitalAI/platform/runtime/event_aggregator.py`
2. `VitalAI/platform/runtime/decision_core.py`
3. `VitalAI/platform/runtime/failover.py`
4. `VitalAI/platform/runtime/snapshots.py`

## Base Reuse Checklist Before Coding

Before implementing the next step, re-check whether `Base` already contains reusable parts:

- for config/logging, inspect `Base/Config`
- for common schemas or model patterns, inspect `Base/Models`
- for AI agent interaction patterns, inspect `Base/Ai`
- for persistence abstractions, inspect `Base/Repository`
- for generic utilities, inspect `Base/RicUtils`

Current conclusion from this round:

- `Base/Models` contains DB-oriented reusable models, but not platform-runtime contracts
- `Base/RicUtils` contains small generic helpers, but not typed messaging/arbitration schemas
- the current contract layer should remain in `VitalAI/platform`

## Task Breakdown

### 1. Event Aggregator Alignment

File:

- `VitalAI/platform/runtime/event_aggregator.py`

Purpose:

- switch raw event intake toward `MessageEnvelope` or compatible typed inputs
- keep summarize output minimal, but make the contract explicit

### 2. Decision Core Alignment

File:

- `VitalAI/platform/runtime/decision_core.py`

Purpose:

- clarify whether the decision core consumes summarized envelopes, feedback events, or a shared summary object
- reduce reliance on untyped `dict[str, Any]`

### 3. Snapshot And Interrupt Alignment

Files:

- `VitalAI/platform/runtime/snapshots.py`
- `VitalAI/platform/interrupt/signals.py`
- `VitalAI/platform/runtime/failover.py`

Purpose:

- make snapshot references and failover/takeover flow align cleanly
- confirm the minimum data required for interrupt recovery

### 4. Minimal Verification

Purpose:

- add a small import or unit test pass for the new contracts and runtime wiring
- avoid importing `VitalAI.main` during verification because `Base` still has heavy side effects

## Existing Runtime Shell

These files already exist and should be read before implementing the contracts:

- `VitalAI/platform/runtime/decision_core.py`
- `VitalAI/platform/runtime/event_aggregator.py`
- `VitalAI/platform/runtime/health_monitor.py`
- `VitalAI/platform/runtime/shadow_decision_core.py`
- `VitalAI/platform/runtime/snapshots.py`
- `VitalAI/platform/runtime/degradation.py`
- `VitalAI/platform/runtime/failover.py`

The next implementation should preserve this split runtime direction and start using the contracts already created.

## Constraints

- keep implementation minimal and typed
- focus on contract usage and boundaries
- do not build full business logic yet
- do not duplicate generic infra already suitable for `Base`
- prefer verification paths that avoid `VitalAI.main`

## Done Definition

This task is complete when:

- the runtime shell uses or clearly references the new platform contracts
- the typed contract boundary is clearer than the current raw `dict` approach
- minimal verification has been run for the affected modules
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
```
