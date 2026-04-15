# Step 41: Security Review Highest-Severity Detail

## Why this step

`SECURITY_REVIEW` runtime signals already exposed:

- `action`
- `finding_count`

That was enough to distinguish clean paths from redacted paths, but one useful typed detail was still missing:

- how severe the current review outcome actually was

Without that, callers could see that findings existed, but could not tell whether the posture was only warning-level or already critical-level without reconstructing it from internal finding records.

## What changed

### 1. Added highest-severity logic to the typed security review result

Updated:

- `VitalAI/platform/security/review.py`

`SecurityReviewResult` now exposes:

- `highest_severity()`

Current behavior is:

- no findings -> `INFO`
- any warning findings -> `WARNING`
- any critical findings -> `CRITICAL`

### 2. Observability now records the highest severity explicitly

Updated:

- `VitalAI/platform/observability/service.py`

`SECURITY_REVIEW` observations now include:

- `highest_severity`

This keeps the severity interpretation inside the typed security layer instead of forcing later consumers to rebuild it.

### 3. Runtime signal views now surface that detail directly

Updated:

- `VitalAI/application/use_cases/runtime_signal_views.py`

Interface-facing `SECURITY_REVIEW` details now expose:

- `signal_type`
- `action`
- `finding_count`
- `highest_severity`

This is a small refinement to an existing signal type, not a new result boundary.

## Why this shape

This stays minimal and general:

- no new top-level diagnostics fields
- no new signal types
- useful for normal flows, snapshot paths, and failover drills alike

## Verification

Verified with:

```bash
python -m unittest tests.platform.test_security_contracts tests.platform.test_observability_contracts tests.application.test_runtime_signal_views tests.application.test_health_alert_flow tests.interfaces.test_typed_flow_routes
```

Result:

- `Ran 28 tests`
- `OK`

## Outcome

After this step:

- security review output still stays compact
- callers can now read both review count and strongest severity directly
- the nearby security refinement slice has reached another reasonable stop point
