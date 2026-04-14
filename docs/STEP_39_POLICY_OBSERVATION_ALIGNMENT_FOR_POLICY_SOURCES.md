# Step 39: Policy Observation Alignment For Policy Sources

## Why this step

The assembly policy snapshot already exposed the active policy values for:

- reporting
- runtime signal emission
- ingress ack/ttl behavior

But as runtime-related policy fields accumulated, one observability gap remained:

- callers could see the current values
- callers could not see whether those values came from assembly defaults, role defaults, or environment overrides

This step closes that gap without reopening the existing runtime-signal result boundary.

## What changed

### 1. Added typed policy-source fields to the assembly snapshot

Updated:

- `VitalAI/application/assembly.py`

`ApplicationAssemblyPolicySnapshot` now also exposes:

- `reporting_policy_source`
- `runtime_signals_policy_source`
- `ingress_policy_source`

Current source values stay intentionally small:

- `assembly_default`
- `role_default`
- `environment_override`

### 2. Aligned policy observations with the richer snapshot

Updated:

- `VitalAI/platform/observability/service.py`
- `VitalAI/interfaces/typed_flow_support.py`

`POLICY_SNAPSHOT` observations now carry the same source metadata in their attributes, so observability stays aligned with the application-facing policy snapshot.

### 3. Preserved the existing result boundaries

This step does not:

- extend the drill diagnostics result
- reopen `runtime_signals` shaping
- change runtime behavior

It only makes policy introspection and policy observation explain where the active settings came from.

## Why this shape

This is the smallest useful `policy observation alignment` slice:

- typed
- real
- local to assembly/observability/interfaces
- adjacent to the current stable stop point

## Verification

Verified with:

```bash
python -m unittest tests.application.test_application_assembly tests.platform.test_observability_contracts tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

Result:

- `Ran 44 tests`
- `OK`

## Outcome

After this step:

- policy snapshots expose active values and their sources
- policy observations carry the same source metadata
- role defaults and environment overrides are easier to distinguish directly
