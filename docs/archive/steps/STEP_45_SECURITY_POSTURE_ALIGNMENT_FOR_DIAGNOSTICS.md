# Step 45: Security Posture Alignment For Diagnostics

## Why this step

Diagnostics already exposed a lightweight security posture through:

- `latest_security_action`
- `latest_security_finding_count`

But after security review detail refinement introduced `highest_severity`, diagnostics still lagged behind the underlying security signal shape.

That meant callers could read:

- whether security allowed or redacted
- how many findings existed

But they still could not read the strongest review severity directly from the diagnostics result.

## What changed

### 1. Diagnostics now expose highest security severity directly

Updated:

- `VitalAI/application/assembly.py`

`ApplicationRuntimeDiagnostics` now also exposes:

- `latest_security_highest_severity`

This is derived from the latest `SECURITY_REVIEW` observation, alongside the existing action and finding-count fields.

### 2. Interface serialization now stays aligned with that posture

Updated:

- `VitalAI/interfaces/typed_flow_support.py`

Runtime diagnostics responses now include:

- `latest_security_highest_severity`

This keeps the diagnostics surface aligned with the already-exposed security review signal detail.

### 3. Both diagnostics paths benefit without changing signal shape

Updated verification targets:

- `tests/application/test_application_assembly.py`
- `tests/interfaces/test_typed_flow_routes.py`

Both existing diagnostics paths now surface:

- `runtime_diagnostics`
- `health_failover_drill`

For the current clean-path tests, the value is:

- `latest_security_highest_severity="INFO"`

## Why this shape

This stays intentionally small:

- no new runtime signal type
- no new review logic
- no new result family

It only aligns diagnostics with security posture that already exists elsewhere in the runtime signal chain.

## Verification

Verified with:

```bash
python -m unittest tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.platform.test_observability_contracts
```

Result:

- `Ran 33 tests`
- `OK`

## Outcome

After this step:

- diagnostics now expose security action, finding count, and highest severity together
- diagnostics posture is better aligned with `SECURITY_REVIEW` signal detail
- the nearby diagnostics/security alignment seam has reached another stable stop point
