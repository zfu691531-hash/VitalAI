# Step 36: Richer Health Failover Drill Diagnostics

## Why this step

Step 35 introduced a controlled health failover drill that could run:

- real critical health flow
- runtime snapshot
- takeover-ready interrupt
- controlled failover transition

But the diagnostics result still forced callers to infer key drill facts from the `runtime_signals` list.

This step makes the drill result itself a little more explicit.

## What changed

### 1. Added stable interrupt fields to diagnostics result

Updated:

- `VitalAI/application/assembly.py`
- `VitalAI/interfaces/typed_flow_support.py`

`ApplicationRuntimeDiagnostics` now also exposes:

- `interrupt_action`
- `interrupt_has_snapshot_refs`

These fields are derived from the latest `INTERRUPT_SIGNAL` observation when one exists.

### 2. Generic diagnostics and health failover drill stay distinct

The generic runtime diagnostics route still returns:

- no interrupt-specific drill fields

So for that path:

- `interrupt_action=None`
- `interrupt_has_snapshot_refs=None`

The controlled health failover drill now returns:

- `interrupt_action="TAKEOVER"`
- `interrupt_has_snapshot_refs=True`

This keeps the richer fields meaningful instead of pretending all diagnostics carry the same runtime semantics.

## Why this shape

This is a small but useful result refinement:

- no runtime behavior changed
- no new signal types were introduced
- the drill is easier to consume without parsing the whole signal list

It also keeps the contract typed and compact.

## Verification

Verified with:

```bash
python -m pytest tests/application/test_application_assembly.py -q
python -m pytest tests/interfaces/test_typed_flow_routes.py -q
```

Results:

- `19 passed`
- `8 passed`

Pytest emitted cache warnings because `.pytest_cache` could not be created in the current environment, but all tests passed.

## Outcome

After this step:

- the controlled health failover drill exposes its core interrupt posture directly
- interface consumers no longer need to infer that posture only from `runtime_signals`
- the next refinement can stay focused on observability/security detail instead of execution behavior

## Best next step

The next natural step is to decide whether the controlled drill needs a small security/observability exposure refinement, especially around the interrupt and failover transition records.
