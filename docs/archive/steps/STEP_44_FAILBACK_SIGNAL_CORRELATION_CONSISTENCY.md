# Step 44: Failback Signal Correlation Consistency

## Why this step

The previous failover-correlation refinement made `FAILOVER_TRANSITION` observations richer for failover paths:

- `signal_id`
- `has_snapshot_refs`
- `snapshot_ids`

But failback still had a nearby consistency gap:

- `failback()` could not accept a triggering interrupt signal
- so failback observations could not carry the same correlation metadata even when a real resume signal existed

## What changed

### 1. Failback now accepts an optional interrupt signal

Updated:

- `VitalAI/platform/runtime/failover.py`

`FailoverCoordinator.failback()` now accepts:

- `signal: InterruptSignal | None`
- `signal_bridge: RuntimeSignalBridge | None`

When a signal is provided, failback now updates `last_signal` and forwards the signal into the existing failover-transition observation path.

### 2. Failback observations now reuse the same correlation path as failover

No new observation type was introduced.

Instead, failback now reuses the existing transition wiring so it can preserve:

- `trace_id`
- `signal_id`
- `has_snapshot_refs`
- `snapshot_ids`

That keeps failover and failback aligned under one typed correlation model.

### 3. Added direct runtime verification for signal-backed failback

Updated:

- `tests/platform/test_runtime_contract_wiring.py`

The new coverage verifies that a signal-backed failback transition:

- switches the node back to `primary`
- emits a `FAILOVER_TRANSITION` observation
- preserves the signal trace id
- preserves snapshot-backed correlation details

## Why this shape

This stays intentionally small:

- no new top-level diagnostics fields
- no new interface contract
- no new workflow path

It only closes an inconsistency inside the existing runtime and observability wiring.

## Verification

Verified with:

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.platform.test_observability_contracts tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes
```

Result:

- `Ran 46 tests`
- `OK`

## Outcome

After this step:

- failover and failback transitions share the same correlation model
- signal-backed failback is no longer a blind spot
- the remaining nearby seams can move on from signal-correlation consistency
