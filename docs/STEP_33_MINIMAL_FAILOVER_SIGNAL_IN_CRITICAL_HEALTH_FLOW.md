# Step 33: Minimal Failover Signal In Critical Health Flow

## Why this step

Step 32 let the normal critical health flow emit a real `RUNTIME_SNAPSHOT`.

The next adjacent question was:

- can one real typed business flow emit a failover-related signal

But the step still needed to stay small.

So this step does not perform an actual failover.

Instead, it adds the minimum typed signal that says:

- this critical flow has captured recovery material
- takeover readiness can now be expressed through the existing interrupt contract

## What changed

### 1. Critical health flow now emits a takeover-ready interrupt

Updated:

- `VitalAI/application/use_cases/runtime_support.py`

After a critical `HEALTH_ALERT` snapshot is captured, shared runtime support now builds a typed `InterruptSignal` with:

- `action=TAKEOVER`
- `priority=P1`
- the current flow `trace_id`
- `snapshot_refs` pointing at the freshly created runtime snapshot

The signal is then sent through the existing `RuntimeSignalBridge`.

### 2. This is failover-related, but not an actual failover transition

The new normal-flow emission now adds:

- `INTERRUPT_SIGNAL`
- `SECURITY_REVIEW` for the interrupt payload

So a critical health flow now emits:

- `EVENT_SUMMARY`
- `SECURITY_REVIEW`
- `RUNTIME_SNAPSHOT`
- `SECURITY_REVIEW`
- `INTERRUPT_SIGNAL`
- `SECURITY_REVIEW`

This is intentionally smaller than calling `FailoverCoordinator` inside the business flow.

### 3. Scope remains narrow and explicit

This signal only appears when:

- the event is `HEALTH_ALERT`
- the priority is `CRITICAL`
- runtime signals are enabled

It does not affect:

- high-but-not-critical health alerts
- daily-life flow
- mental-care flow

## Why this shape

This keeps the architecture honest:

- business flow can now expose takeover readiness
- runtime contracts remain typed and reusable
- actual failover execution still stays outside the normal business path

That makes this a safe intermediate step between:

- snapshot-only runtime value
- and true failover orchestration

## Verification

Verified with:

```bash
python -m pytest tests/application/test_application_assembly.py -q
python -m pytest tests/application/test_health_alert_flow.py tests/interfaces/test_typed_flow_routes.py tests/interfaces/test_scheduler_and_consumer_adapters.py tests/application/test_mental_care_flow.py -q
```

Results:

- `17 passed`
- `23 passed`

Pytest emitted cache warnings because `.pytest_cache` could not be created in the current environment, but all tests passed.

## Outcome

After this step:

- the critical health flow emits the first real failover-related runtime signal
- the signal carries `snapshot_refs`, so it is aligned with later takeover semantics
- the code still avoids performing real failover during normal business execution

## Best next step

The next natural step is to choose one of two directions:

- let this interrupt feed a minimal failover coordinator path in a controlled non-business runtime drill
- or refine the exposed security/runtime details for the new interrupt signal
