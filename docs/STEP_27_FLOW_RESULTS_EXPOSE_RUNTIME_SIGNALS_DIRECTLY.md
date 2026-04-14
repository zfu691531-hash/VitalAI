# Step 27: Flow Results Expose Runtime Signals Directly

## Why this step

Step 26 promoted `runtime_signals` into an explicit application contract, but interface serialization still had to know that raw `runtime_observations` existed on flow results.

That meant the boundary was cleaner than before, but not fully tightened yet.

This step finishes that result-boundary cleanup by letting flow results expose `runtime_signals` directly.

## What changed

### 1. Flow results now expose the application signal view

Updated:

- `VitalAI/application/use_cases/health_alert_flow.py`
- `VitalAI/application/use_cases/daily_life_checkin_flow.py`
- `VitalAI/application/use_cases/mental_care_checkin_flow.py`

Each flow result now has:

- `runtime_observations` as the underlying raw runtime output
- `runtime_signals` as the application-facing property built from that raw output

This keeps the raw records available where needed without forcing outer layers to depend on them.

### 2. Interface layer got thinner again

Updated:

- `VitalAI/interfaces/typed_flow_support.py`

The interface layer now serializes:

- `result.flow_result.runtime_signals`

instead of reaching back into raw `runtime_observations` and rebuilding the contract there.

## Why this shape

This is the cleanest boundary reached so far:

- `platform` emits raw `ObservationRecord`
- `application` owns both the stable signal view and the result object that exposes it
- `interfaces` only serialize application results

That is consistent with the project’s “thin interfaces, explicit application orchestration” direction.

## Verification

Verified with:

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.platform.test_observability_contracts tests.platform.test_security_contracts tests.application.test_runtime_signal_views tests.application.test_health_alert_flow tests.application.test_mental_care_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

Result:

- `Ran 57 tests ... OK`

## Outcome

After this step:

- flow results expose `runtime_signals` directly
- interfaces no longer need raw runtime observation knowledge
- the application result boundary is tighter and more intentional

## Best next step

The next natural step is to decide whether workflow result objects should also surface `runtime_signals` directly as top-level convenience fields, or whether the current `flow_result.runtime_signals` nesting is the right stable stop point.
