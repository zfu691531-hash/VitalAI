# Step 30: Role Default Runtime Signal Policy

## Why this step

Step 29 made `runtime_signals_enabled` an explicit assembly policy, but it was still only an environment-driven toggle.

The next question was whether it deserved a real role default, the same way the assembly layer already has role-aware behavior for:

- reporting
- ingress ack
- ingress ttl

This step answers yes, in one small and justified place:

- `scheduler` now defaults to `runtime_signals_enabled=False`

## Why `scheduler`

This fits the current shape of the architecture:

- scheduler already defaults to no reporting
- scheduler already uses a distinct ingress policy
- scheduled internal jobs are the least compelling place to emit runtime-signal noise by default

At the same time:

- API keeps runtime signals on by default
- consumer keeps runtime signals on by default
- the environment can still explicitly override the role default

## What changed

### 1. Role default policy

Updated:

- `VitalAI/application/assembly.py`

`_default_runtime_signals_enabled_for_role()` now returns:

- `False` for `scheduler`
- `True` for other current roles

### 2. Tests updated

Updated:

- `tests/application/test_application_assembly.py`
- `tests/interfaces/test_scheduler_and_consumer_adapters.py`
- `tests/interfaces/test_typed_flow_routes.py`

Coverage now verifies:

- scheduler defaults to no runtime signals
- scheduler can still explicitly enable runtime signals through environment override
- policy matrix / policy observation stay aligned with the new role default

## Why this shape

This keeps the change small and meaningful:

- only one role gets a special default
- the policy stays explicit and observable
- no runtime bridge internals were changed

## Verification

Verified with:

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.platform.test_observability_contracts tests.platform.test_security_contracts tests.application.test_runtime_signal_views tests.application.test_health_alert_flow tests.application.test_mental_care_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

Result:

- `Ran 60 tests ... OK`

## Outcome

After this step:

- `runtime_signals_enabled` is a real role-default assembly policy
- scheduler is quieter by default
- policy snapshot and policy observation remain aligned
- environment override still works when scheduler runtime signals are needed

## Best next step

The next natural step is to pause boundary work and choose one adjacent runtime/observability/security slice that produces new signal value, instead of continuing to refine assembly defaults.
