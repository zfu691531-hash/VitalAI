# Step 38: Drill-Focused Observability Signal Id

## Why this step

The controlled health failover drill already exposed:

- interrupt posture
- security posture

One small observability gap remained:

- callers still had to inspect the failover transition signal details to find which interrupt signal actually triggered the transition

This step closes that gap with one compact top-level field.

## What changed

### 1. Added a stable failover signal id field

Updated:

- `VitalAI/application/assembly.py`
- `VitalAI/interfaces/typed_flow_support.py`

`ApplicationRuntimeDiagnostics` now also exposes:

- `latest_failover_signal_id`

This value is derived from the latest `FAILOVER_TRANSITION` observation's `signal_id`.

### 2. Diagnostics can now correlate failover transition and interrupt directly

For diagnostics paths that actually record a failover transition:

- generic `runtime_diagnostics`
- controlled `health_failover_drill`

callers can now directly read the signal id that drove the transition.

When runtime signals are disabled and no transition observation exists:

- `latest_failover_signal_id=None`

## Why this shape

This is the smallest useful observability refinement:

- no execution behavior changed
- no result boundary was reopened
- no extra signal types were added

It simply makes transition-to-trigger correlation explicit.

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

- diagnostics expose interrupt posture
- diagnostics expose security posture
- diagnostics also expose the failover transition's driving signal id

This is a good stable stop point for the current drill-focused slice.
