# Step 23: Runtime Signal Bridge To Observability And Security

## Why this step

Steps 21 and 22 gave `platform/observability` and `platform/security` their first typed slices, but they were still mostly edge consumers.

The next minimal platform step was to let runtime emit a few first-class signals into those slices without reopening application-flow design:

- `EventSummary`
- `InterruptSignal`
- `RuntimeSnapshot`
- failover transitions

## Base reuse re-check

Before coding, this round re-checked:

- `Base/Config`
- `Base/Models`
- `Base/RicUtils`

Conclusion stayed the same:

- `Base/Config` is useful for logging/config bootstrap, not runtime signal contracts
- `Base/Models` is DB/session oriented, not a match for runtime platform semantics
- `Base/RicUtils` has small generic helpers, but not the typed bridge needed here

So the signal bridge remains in `VitalAI/platform`.

## What was added

### 1. Runtime signal bridge

New file:

- `VitalAI/platform/runtime/signal_wiring.py`

Added:

- `RuntimeSignalBridge`
- `RuntimeSignalDispatch`

This bridge is intentionally small. Its job is only to fan runtime signals into:

- `ObservabilityCollector`
- `SensitiveDataGuard`

### 2. Runtime hooks

Updated runtime components now support an optional bridge:

- `EventAggregator.summarize(signal_bridge=...)`
- `HealthMonitor.build_interrupt(signal_bridge=...)`
- `SnapshotStore.save(signal_bridge=...)`
- `FailoverCoordinator.failover(signal_bridge=...)`
- `FailoverCoordinator.failback(signal_bridge=...)`

This keeps the runtime components usable without a platform bridge, while allowing real signal emission when the caller opts in.

### 3. Observability contract expansion

Updated:

- `VitalAI/platform/observability/records.py`
- `VitalAI/platform/observability/service.py`

Added new observation kinds:

- `SECURITY_REVIEW`
- `RUNTIME_SNAPSHOT`
- `FAILOVER_TRANSITION`

Added collector support for:

- runtime snapshot recording
- failover transition recording
- security review recording

### 4. Security review expansion

Updated:

- `VitalAI/platform/security/service.py`

`SensitiveDataGuard` can now review runtime-native signals directly:

- `review_event_summary()`
- `review_interrupt_signal()`
- `review_runtime_snapshot()`

This preserves the existing lightweight redaction model, but makes it reusable for runtime signals instead of only reporting text.

## Why this shape

The important boundary choice here is that runtime does not directly depend on logging, metrics, or any heavy security engine.

Instead:

- runtime knows only about an optional bridge
- observability keeps translating signals into `ObservationRecord`
- security keeps returning typed review results

That keeps the slice:

- minimal
- typed
- optional
- easy to test without importing `VitalAI.main`

## Verification

Verified with:

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.platform.test_observability_contracts tests.platform.test_security_contracts tests.application.test_health_alert_flow tests.application.test_mental_care_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

Result:

- `Ran 54 tests ... OK`

## Outcome

After this step:

- runtime can emit first-class signals into observability/security
- security can review runtime-native payloads, not only report text
- failover and snapshot transitions now have typed observability support
- the bridge stays optional, so application wiring does not need to change all at once

## Best next step

The next natural step is not to make the bridge bigger, but to connect it to one real typed flow path so runtime observations become visible during actual use-case execution.
