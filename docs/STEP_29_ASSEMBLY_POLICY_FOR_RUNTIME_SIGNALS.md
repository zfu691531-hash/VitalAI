# Step 29: Assembly Policy For Runtime Signals

## Why this step

After Steps 27 and 28, the runtime-signal result boundary had become stable enough:

- flow results expose `runtime_signals`
- workflow results expose `runtime_signals`
- interfaces only serialize them

That made it the right moment to stop polishing the result shape and move to the next adjacent concern.

The smallest useful next concern was to bring runtime-signal emission into the same role-aware assembly policy model already used for:

- reporting
- ingress ack
- ingress ttl

## What changed

### 1. New assembly policy field

Updated:

- `VitalAI/application/assembly.py`

Added:

- `runtime_signals_enabled` to `ApplicationAssemblyEnvironment`
- `runtime_signals_enabled` to `ApplicationAssemblyPolicySnapshot`

This means runtime-signal emission is now a first-class assembly policy instead of being only an implicit default.

### 2. Environment-driven bridge enable/disable

`ApplicationAssemblyEnvironment` now reads:

- `VITALAI_RUNTIME_SIGNALS_ENABLED`

And `to_config()` now decides whether to inject:

- a fresh `RuntimeSignalBridge`
- or `None`

So when runtime signals are disabled, workflows still run, but they do not emit runtime-signal records.

### 3. Policy observability updated

Updated:

- `VitalAI/platform/observability/service.py`
- `VitalAI/interfaces/typed_flow_support.py`

Policy observations now include:

- `runtime_signals_enabled`

This keeps runtime-signal policy aligned with the existing assembly observability path.

## Why this shape

This keeps the architecture consistent:

- assembly owns runtime-role and environment-sensitive behavior
- runtime bridge remains optional
- observability can describe the active policy set explicitly

The implementation also stayed minimal:

- default behavior is unchanged
- the new policy is only one more assembly-boundary toggle
- no new business flow or heavy infra was introduced

## Verification

Verified with:

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.platform.test_observability_contracts tests.platform.test_security_contracts tests.application.test_runtime_signal_views tests.application.test_health_alert_flow tests.application.test_mental_care_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

Result:

- `Ran 58 tests ... OK`

## Outcome

After this step:

- runtime-signal emission is now an explicit assembly policy
- policy snapshots and policy observations expose that status
- runtime signals can be disabled without changing workflow logic

## Best next step

The next natural step is to decide whether there should be a role-default policy for runtime-signal emission, or whether the current environment-driven toggle is the right stable stop point.
