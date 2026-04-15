# Step 40: Snapshot Policy Generalization For High-Urgency Daily Life

## Why this step

Runtime snapshot capture had already become real in one place:

- critical `HEALTH_ALERT`

But the capture rule still lived as a hard-coded branch inside shared runtime support.

That made the policy:

- implicit
- hard to extend
- hard to test independently

This step turns that into a small typed runtime policy and extends it to one adjacent real case:

- `DAILY_LIFE_CHECKIN` with `urgency="high"`

## What changed

### 1. Added a typed runtime snapshot policy

Updated:

- `VitalAI/platform/runtime/snapshots.py`
- `VitalAI/platform/runtime/__init__.py`

Added:

- `SnapshotCaptureRule`
- `SnapshotCaptureDecision`
- `SnapshotCapturePolicy`
- `DEFAULT_RUNTIME_SNAPSHOT_POLICY`

The default policy now explicitly covers:

- critical `HEALTH_ALERT`
- critical `DAILY_LIFE_CHECKIN` where payload urgency is `high`

### 2. Shared runtime support now consumes the typed policy

Updated:

- `VitalAI/application/use_cases/runtime_support.py`

Instead of using an inline boolean check, shared runtime support now asks the default snapshot policy for a capture decision.

When a rule matches, the snapshot payload now also records:

- `capture_policy`
- `capture_reason`

The failover-readiness interrupt reason is also derived from the capture decision, keeping the policy explicit instead of hard-coded to health wording.

### 3. High-urgency daily-life flow now emits a real snapshot chain

Updated verification targets:

- `tests/application/test_health_alert_flow.py`
- `tests/interfaces/test_typed_flow_routes.py`
- `tests/platform/test_runtime_contract_wiring.py`

For `DAILY_LIFE_CHECKIN` with `urgency="high"`, runtime signals now include:

- `EVENT_SUMMARY`
- `SECURITY_REVIEW`
- `RUNTIME_SNAPSHOT`
- `SECURITY_REVIEW`
- `INTERRUPT_SIGNAL`
- `SECURITY_REVIEW`

This keeps the change adjacent and real without opening the same policy to every flow at once.

## Why this shape

This stays intentionally narrow:

- policy is now typed and testable
- only one neighboring real flow was added
- no new interface-only formatting layer was introduced
- `runtime_signals` result shaping itself was not redesigned

## Verification

Verified with:

```bash
python -m unittest tests.application.test_application_assembly tests.application.test_health_alert_flow tests.platform.test_runtime_contract_wiring tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

Result:

- `Ran 54 tests`
- `OK`

## Outcome

After this step:

- runtime snapshot capture policy is explicit instead of hidden in one branch
- critical health remains covered
- high-urgency daily-life is now also covered
- the next nearby slice can shift to security review detail refinement
