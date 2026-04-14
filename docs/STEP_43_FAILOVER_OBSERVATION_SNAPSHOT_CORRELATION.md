# Step 43: Failover Observation Snapshot Correlation

## Why this step

`FAILOVER_TRANSITION` observations already exposed:

- `signal_id`
- transition direction

That was enough to correlate a failover to the interrupt signal that drove it.

But one nearby observability gap still remained:

- callers could not directly see whether the failover transition was backed by snapshot references
- callers could not directly see which snapshot ids were attached to the triggering interrupt

## What changed

### 1. Failover observations now record snapshot correlation details

Updated:

- `VitalAI/platform/observability/service.py`
- `VitalAI/platform/runtime/signal_wiring.py`

`FAILOVER_TRANSITION` observations now also carry:

- `has_snapshot_refs`
- `snapshot_ids`

These values are derived directly from the triggering interrupt signal when one exists.

### 2. Runtime signal views expose the same correlation details

Updated:

- `VitalAI/application/use_cases/runtime_signal_views.py`

Existing `FAILOVER_TRANSITION` runtime signal details now include:

- `previous_node`
- `current_node`
- `signal_id`
- `has_snapshot_refs`
- `snapshot_ids`

This refines an existing signal detail shape instead of adding a new result contract.

### 3. Diagnostics and drill paths now surface richer failover context automatically

Updated verification targets:

- `tests/application/test_application_assembly.py`
- `tests/interfaces/test_typed_flow_routes.py`
- `tests/platform/test_observability_contracts.py`

Both paths now benefit:

- generic `runtime_diagnostics`
- controlled `health_failover_drill`

Callers can now see whether the transition carried snapshot backing, and which snapshot ids were involved.

## Why this shape

This stays intentionally local:

- no new top-level diagnostics fields
- no new signal type
- no reopening of the existing runtime-signal boundary

It only improves failover observation correlation inside the already exposed signal.

## Verification

Verified with:

```bash
python -m unittest tests.platform.test_observability_contracts tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.platform.test_runtime_contract_wiring
```

Result:

- `Ran 45 tests`
- `OK`

## Outcome

After this step:

- failover transitions still correlate to `signal_id`
- they now also correlate to snapshot readiness directly
- snapshot-backed failovers are easier to inspect through the existing runtime signal chain
