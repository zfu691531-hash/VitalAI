# Step 25: Typed Runtime Signal View For Interfaces

## Why this step

Step 24 connected the runtime signal bridge to real typed flows, but the interface layer was still returning raw serialized observation records through `runtime_observations`.

That worked, but it exposed more collector detail than the interface surface really needed:

- observation ids
- timestamps
- trace ids
- raw attribute bags

So this step tightened the public shape into a smaller typed runtime-signal view.

## What changed

### 1. Interface-facing runtime signal serializer

Updated:

- `VitalAI/interfaces/typed_flow_support.py`

Added:

- `serialize_runtime_signal()`
- `serialize_runtime_signals()`

These functions transform a raw `ObservationRecord` into a smaller interface-facing object with:

- `kind`
- `severity`
- `source`
- `summary`
- `details`

### 2. Curated detail mapping

The new serializer keeps only a small stable subset per observation kind.

Examples:

- `EVENT_SUMMARY` keeps `event_type`, `priority`, `target_agent`
- `SECURITY_REVIEW` keeps `signal_type`, `action`, `finding_count`
- `INTERRUPT_SIGNAL` keeps `action`, `priority`, `target`
- `RUNTIME_SNAPSHOT` keeps `snapshot_id`, `version`
- `FAILOVER_TRANSITION` keeps `previous_node`, `current_node`

This keeps the interface surface intentionally small without changing the underlying runtime bridge.

### 3. Workflow result surface updated

`serialize_workflow_result()` now returns:

- `runtime_signals`

instead of the previous raw `runtime_observations`.

The internal application flow results still keep the raw observation records, so this step changes interface shape, not platform storage or bridge behavior.

## Why this shape

This step keeps the layering cleaner:

- runtime still emits `ObservationRecord`
- application still preserves raw records
- interfaces expose a smaller, stable result shape

That means we can keep evolving internals without forcing interface consumers to depend on collector-specific fields.

## Verification

Verified with:

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.platform.test_observability_contracts tests.platform.test_security_contracts tests.application.test_health_alert_flow tests.application.test_mental_care_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

Result:

- `Ran 54 tests ... OK`

## Outcome

After this step:

- real typed flows still emit runtime-derived signals
- interfaces now expose a smaller typed `runtime_signals` view
- the runtime bridge and application flow results remain unchanged underneath

## Best next step

The next natural step is to decide whether this smaller runtime-signal view should become its own explicit typed contract in `application` or `shared`, or remain an interface-only serialization concern.
