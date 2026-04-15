# Step 24: Runtime Signal Bridge In Real Typed Flow

## Why this step

Step 23 proved the runtime signal bridge at the platform level, but it still lived mostly in isolated runtime tests.

This step connected that bridge to a real typed flow path so runtime observations are produced during actual workflow execution.

## What was changed

### 1. Shared use-case runtime helper

Updated:

- `VitalAI/application/use_cases/runtime_support.py`

`ingest_and_get_latest_summary()` now accepts an optional `RuntimeSignalBridge` and returns:

- whether the event was accepted
- the latest `EventSummary`
- emitted `ObservationRecord` items

This keeps the integration concentrated in one shared helper instead of duplicating runtime bridge logic in each use case.

### 2. Real typed flows now carry runtime observations

Updated:

- `VitalAI/application/use_cases/health_alert_flow.py`
- `VitalAI/application/use_cases/daily_life_checkin_flow.py`
- `VitalAI/application/use_cases/mental_care_checkin_flow.py`

Each flow result now includes:

- `runtime_observations`

And each use case can optionally receive:

- `signal_bridge`

That means the real `health / daily_life / mental_care` typed flows now preserve the runtime observations produced during ingestion.

### 3. Assembly now injects a fresh bridge

Updated:

- `VitalAI/application/assembly.py`

The assembly layer now creates a fresh `RuntimeSignalBridge` per workflow graph using:

- `ObservabilityCollector`
- `SensitiveDataGuard`

This choice avoids global mutable collector state while keeping integration local to one built workflow.

### 4. Interface responses now expose runtime observations

Updated:

- `VitalAI/interfaces/typed_flow_support.py`

`serialize_workflow_result()` now includes:

- `runtime_observations`

So API, scheduler, and consumer adapters can expose the runtime-emitted observation/security records without inventing a separate query API.

## Why this shape

The main design choice here is to keep the bridge optional but real:

- optional at the use-case boundary
- real by default when built through `ApplicationAssembly`

That preserves the platform boundary:

- runtime still emits typed signals
- application decides whether to attach a bridge
- interfaces only serialize the result

## Verification

Verified with:

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.platform.test_observability_contracts tests.platform.test_security_contracts tests.application.test_health_alert_flow tests.application.test_mental_care_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

Result:

- `Ran 54 tests ... OK`

## Outcome

After this step:

- the runtime bridge is no longer only a platform-side concept
- real typed flows now emit runtime observations
- API/scheduler/consumer responses can now surface those observations directly
- the same path carries both observability and security-review records

## Best next step

The next natural step is to tighten the observation surface:

- decide whether all observations should be returned directly
- or whether interfaces should expose a smaller curated runtime-signal view
