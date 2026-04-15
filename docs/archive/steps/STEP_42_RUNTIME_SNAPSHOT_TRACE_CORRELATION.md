# Step 42: Runtime Snapshot Trace Correlation

## Why this step

Runtime snapshots had already become real in:

- normal typed flows
- assembly runtime diagnostics
- controlled failover drill preparation

But one observability gap still remained:

- snapshot observations did not carry a stable `trace_id`

That made snapshots harder to correlate with the surrounding runtime chain than event summaries, interrupts, and failover transitions.

## What changed

### 1. Runtime snapshots can now carry trace identity directly

Updated:

- `VitalAI/platform/runtime/snapshots.py`

`RuntimeSnapshot` now includes:

- `trace_id`

`SnapshotStore.save()` now also accepts:

- `trace_id`

This keeps trace correlation explicit at the runtime primitive level instead of relying on later payload inspection.

### 2. Real snapshot creation paths now pass trace ids through

Updated:

- `VitalAI/application/use_cases/runtime_support.py`
- `VitalAI/application/assembly.py`

Current paths now propagate trace identity into snapshots:

- typed flow snapshot capture uses the event summary trace id
- assembly runtime diagnostics uses the diagnostics trace id
- controlled health failover drill reconstructs a snapshot with the observed snapshot trace id

### 3. Observability now records snapshot trace correlation directly

Updated:

- `VitalAI/platform/observability/service.py`

`RUNTIME_SNAPSHOT` observations now use the snapshot trace id as their own `trace_id`, making them align better with the rest of the runtime observation chain.

## Why this shape

This stays small and infrastructure-facing:

- no new result object fields
- no new runtime signal type
- no reopening of `runtime_signals` shaping

It only improves runtime-to-observability correlation for an existing signal.

## Verification

Verified with:

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.platform.test_observability_contracts tests.application.test_application_assembly tests.application.test_health_alert_flow tests.interfaces.test_typed_flow_routes
```

Result:

- `Ran 49 tests`
- `OK`

## Outcome

After this step:

- runtime snapshots keep their own trace identity
- snapshot observations can be correlated directly with related runtime events
- snapshot observability is better aligned with the rest of the typed runtime signal chain
