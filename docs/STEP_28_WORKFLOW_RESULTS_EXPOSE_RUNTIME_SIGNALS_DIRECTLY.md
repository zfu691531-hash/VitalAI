# Step 28: Workflow Results Expose Runtime Signals Directly

## Why this step

Step 27 tightened the flow-result boundary by letting application flow results expose `runtime_signals` directly.

The remaining small inconsistency was that workflow result objects still required callers to go through:

- `result.flow_result.runtime_signals`

That was workable, but it kept one more layer of nesting than necessary for the current typed workflow shape.

## What changed

### 1. Workflow result convenience boundary

Updated:

- `VitalAI/application/workflows/health_alert_workflow.py`
- `VitalAI/application/workflows/daily_life_checkin_workflow.py`
- `VitalAI/application/workflows/mental_care_checkin_workflow.py`

Each workflow result now exposes:

- `runtime_signals`

as a read-only property that delegates to the underlying flow result.

### 2. Interface serialization got thinner again

Updated:

- `VitalAI/interfaces/typed_flow_support.py`

The interface layer now serializes:

- `result.runtime_signals`

instead of reaching into nested `flow_result.runtime_signals`.

## Why this shape

This keeps the boundary progression consistent:

- `platform` emits raw observations
- `application/use_cases` expose `runtime_signals`
- `application/workflows` keep that same convenience at their own result boundary
- `interfaces` only serialize workflow results

The property-based approach also avoids duplicating data or changing the underlying workflow execution logic.

## Verification

Verified with:

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.platform.test_observability_contracts tests.platform.test_security_contracts tests.application.test_runtime_signal_views tests.application.test_health_alert_flow tests.application.test_mental_care_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

Result:

- `Ran 57 tests ... OK`

## Outcome

After this step:

- workflow results expose `runtime_signals` directly
- interface serialization is thinner than before
- the current runtime-signal result boundary is more ergonomic without widening scope

## Best next step

The next natural step is to pause and assess whether the current runtime-signal boundary is now stable enough to stop tightening and move to the next nearby platform/application concern, instead of continuing to polish the same shape indefinitely.
