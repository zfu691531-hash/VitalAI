# Step 34: Interrupt Exposure For Snapshot Refs

## Why this step

Step 33 added the first real failover-related signal in a normal critical health flow:

- a takeover-ready `INTERRUPT_SIGNAL`

But the interface-facing runtime signal view still hid one important distinction:

- whether the interrupt actually carried recovery material through `snapshot_refs`

This step fixes that without changing runtime execution behavior.

## What changed

### 1. Interrupt runtime signal view now exposes snapshot readiness

Updated:

- `VitalAI/application/use_cases/runtime_signal_views.py`

`INTERRUPT_SIGNAL` details now include:

- `has_snapshot_refs`

This value comes from the existing observability record, so no runtime contract changed.

### 2. Critical health flow is now easier to interpret from interfaces

For the critical health path, interface consumers can now tell that the emitted takeover-ready interrupt is not just:

- high priority
- takeover-shaped

It is also:

- backed by snapshot references

That makes the signal more useful for future failover coordination and diagnostics.

## Why this shape

This is a very small but meaningful refinement:

- no business flow behavior changed
- no new signal type was added
- no result boundary was reopened

It simply lets the existing interrupt signal communicate whether failover recovery material is attached.

## Verification

Verified with:

```bash
python -m pytest tests/application/test_health_alert_flow.py -q
python -m pytest tests/interfaces/test_typed_flow_routes.py -q
```

Results:

- `4 passed`
- `7 passed`

Pytest emitted cache warnings because `.pytest_cache` could not be created in the current environment, but all tests passed.

## Outcome

After this step:

- `INTERRUPT_SIGNAL` exposure is more informative
- interfaces can distinguish takeover-ready interrupts that actually carry snapshot refs
- the codebase is better prepared for a later controlled failover-coordinator path

## Best next step

The next natural step is to decide whether the takeover-ready interrupt should enter one controlled `FailoverCoordinator` path outside normal business execution.
