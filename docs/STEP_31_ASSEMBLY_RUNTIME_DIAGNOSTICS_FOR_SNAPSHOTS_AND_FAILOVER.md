# Step 31: Assembly Runtime Diagnostics For Snapshots And Failover

## Why this step

After Step 30, the runtime-signal boundary and its role-aware assembly policy were stable enough to stop refining output shape.

The next useful question was no longer:

- how should runtime signals be shaped
- or which role defaults should exist

It was:

- can `RuntimeSnapshot` and failover transition signals enter a real application-owned path instead of living only in platform tests

The smallest real path was an assembly-driven diagnostics drill.

## What changed

### 1. Added an assembly-owned diagnostics result

Updated:

- `VitalAI/application/assembly.py`
- `VitalAI/application/__init__.py`

Added:

- `ApplicationRuntimeDiagnostics`
- `ApplicationAssembly.run_runtime_diagnostics()`

This gives the assembly layer one minimal runtime-native operation that:

- captures a snapshot through `SnapshotStore`
- builds a typed takeover interrupt
- drives `FailoverCoordinator`
- collects emitted observations as `runtime_signals`

### 2. Snapshot and failover now travel through a real assembly path

`run_runtime_diagnostics()` now emits:

- `RUNTIME_SNAPSHOT`
- `SECURITY_REVIEW` for the snapshot payload
- `FAILOVER_TRANSITION`

This matters because snapshot/failover signals are no longer reachable only through direct platform tests.

They now also move through:

- `application/assembly.py`
- `interfaces/typed_flow_support.py`
- `interfaces/api/routers/typed_flows.py`

### 3. Existing runtime-signal policy still governs emission

The diagnostics path reuses the same `runtime_signal_bridge_factory` already controlled by assembly policy.

That means:

- API diagnostics emit runtime signals by default
- scheduler diagnostics still perform the drill, but emit no runtime-signal records by default

So the new slice extends real behavior without reopening boundary or policy design.

## Why this shape

This keeps the step small and honest:

- it is a real assembly path
- it reuses existing runtime contracts
- it does not invent a new business flow
- it does not change the current `runtime_signals` contract

It also creates a clean bridge toward the next step, where snapshot/failover can move from assembly diagnostics into one real typed business flow.

## Verification

Verified with:

```bash
python -m pytest tests/application/test_application_assembly.py -q
python -m pytest tests/interfaces/test_typed_flow_routes.py -q
python -m pytest tests/interfaces/test_scheduler_and_consumer_adapters.py -q
```

Results:

- `17 passed`
- `7 passed`
- `10 passed`

Pytest emitted cache warnings because `.pytest_cache` could not be created in the current environment, but all tests passed.

## Outcome

After this step:

- assembly can drive a minimal snapshot/failover diagnostics drill
- snapshot/failover runtime signals now appear in a real assembly/interface path
- scheduler still stays quiet by default because runtime-signal policy is reused consistently

## Best next step

The next natural step is to move beyond diagnostics and let one real typed business flow preserve or emit snapshot/failover-related runtime signals during normal runtime execution.
