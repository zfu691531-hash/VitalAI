# Step 35: Controlled Health Failover Drill

## Why this step

By Step 34, the critical health flow already emitted:

- a runtime snapshot
- a takeover-ready interrupt
- interface-visible proof that `snapshot_refs` were attached

The next smallest real step was not to let the normal business flow perform failover.

It was to let assembly diagnostics reuse that real health-flow signal path and then hand the resulting interrupt to `FailoverCoordinator` in a controlled drill.

## What changed

### 1. Added a health-critical failover drill in assembly

Updated:

- `VitalAI/application/assembly.py`

Added:

- `ApplicationAssembly.run_health_critical_failover_drill()`

This drill:

1. runs a real critical `HEALTH_ALERT` through the existing typed flow wiring
2. lets the flow emit:
   - `EVENT_SUMMARY`
   - `RUNTIME_SNAPSHOT`
   - takeover-ready `INTERRUPT_SIGNAL`
3. reconstructs the minimum typed runtime objects needed for failover coordination
4. feeds the interrupt into `FailoverCoordinator`
5. records the resulting `FAILOVER_TRANSITION`

### 2. Exposed the drill through interface helpers and API route

Updated:

- `VitalAI/interfaces/typed_flow_support.py`
- `VitalAI/interfaces/api/routers/typed_flows.py`

Added:

- `get_application_health_failover_drill()`
- `get_health_failover_drill()`
- `/flows/runtime-diagnostics/{role}/health-failover`

This keeps the path observable without replacing the older generic runtime diagnostics route.

### 3. Policy behavior remains consistent

The drill still obeys:

- `runtime_signals_enabled`

So:

- `api` can run the full controlled drill
- `scheduler` remains quiet by default and does not trigger failover in the drill result

## Why this shape

This is the right middle step between:

- signal production in real business flow
- and true runtime failover orchestration

It keeps actual failover:

- explicit
- controlled
- assembly-owned

while still proving that the signal chain is end-to-end coherent.

## Verification

Verified with:

```bash
python -m pytest tests/application/test_application_assembly.py -q
python -m pytest tests/interfaces/test_typed_flow_routes.py tests/interfaces/test_scheduler_and_consumer_adapters.py -q
```

Results:

- `19 passed`
- `19 passed`

Pytest emitted cache warnings because `.pytest_cache` could not be created in the current environment, but all tests passed.

## Outcome

After this step:

- a controlled assembly drill can run `health critical flow -> snapshot -> interrupt -> failover transition`
- normal business execution still does not directly perform failover
- the architecture now has a real bridge from flow-produced runtime signals into controlled failover coordination

## Best next step

The next natural step is to decide whether this controlled drill needs:

- a slightly richer failover diagnostics result
- or small security/observability exposure refinement around the new drill path
