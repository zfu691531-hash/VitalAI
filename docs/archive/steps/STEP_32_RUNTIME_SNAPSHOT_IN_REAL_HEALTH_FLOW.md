# Step 32: Runtime Snapshot In Real Health Flow

## Why this step

Step 31 proved that snapshot and failover signals could move through a real assembly-owned diagnostics path.

The next question was whether one normal typed business flow could start preserving similar runtime value during ordinary execution.

The smallest safe slice was:

- do not add failover to normal business flow yet
- do not expand all flows at once
- let one already critical flow emit a real `RUNTIME_SNAPSHOT`

That made `HEALTH_ALERT` the best first target.

## What changed

### 1. Shared runtime support can now capture a real flow snapshot

Updated:

- `VitalAI/application/use_cases/runtime_support.py`

`ingest_and_get_latest_summary()` now performs one extra runtime step when all of these are true:

- a `RuntimeSignalBridge` is present
- the latest summary is `HEALTH_ALERT`
- the summary priority is `CRITICAL`

In that case it saves a `RuntimeSnapshot` through `SnapshotStore`.

The snapshot payload is intentionally small and typed:

- `trace_id`
- `event_type`
- `priority`
- `source_agent`
- `target_agent`
- `event_payload`

### 2. The snapshot now enters the normal flow signal chain

Because the save happens through the existing runtime signal bridge, the normal health flow now emits:

- `EVENT_SUMMARY`
- `SECURITY_REVIEW` for the summary payload
- `RUNTIME_SNAPSHOT`
- `SECURITY_REVIEW` for the snapshot payload

This means `RUNTIME_SNAPSHOT` is no longer limited to:

- platform-only tests
- assembly diagnostics

It now also appears in a real typed business flow.

### 3. Scope stayed intentionally narrow

This step does not yet:

- trigger failover during normal flow execution
- broaden snapshot capture to daily-life or mental-care flows
- change the public `runtime_signals` contract

That keeps the change small while still moving the runtime architecture forward.

## Why this shape

This is the smallest realistic move from diagnostics into production-shaped flow:

- it reuses existing snapshot and signal-wiring contracts
- it keeps snapshot capture policy explicit in one shared helper
- it avoids pretending that every high-priority flow is already ready for failover semantics

## Verification

Verified with:

```bash
python -m pytest tests/application/test_health_alert_flow.py -q
python -m pytest tests/application/test_application_assembly.py -q
python -m pytest tests/interfaces/test_typed_flow_routes.py tests/interfaces/test_scheduler_and_consumer_adapters.py -q
```

Results:

- `4 passed`
- `17 passed`
- `17 passed`

Pytest emitted cache warnings because `.pytest_cache` could not be created in the current environment, but all tests passed.

## Outcome

After this step:

- the normal critical health flow emits a typed runtime snapshot
- snapshot capture now exists in both assembly diagnostics and a real typed business path
- the architecture has taken one real step from “signal-ready” to “signal-producing”

## Best next step

The next natural step is to decide whether normal flow execution should:

- add a minimal failover-related signal path for one critical scenario
- or generalize snapshot capture policy beyond `HEALTH_ALERT`
