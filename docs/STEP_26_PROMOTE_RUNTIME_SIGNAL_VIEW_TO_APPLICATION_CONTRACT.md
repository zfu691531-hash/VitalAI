# Step 26: Promote Runtime Signal View To Application Contract

## Why this step

Step 25 already shrank the interface-facing runtime signal output into a smaller `runtime_signals` view.

The remaining question was whether that view should stay as interface-only formatting logic or become an explicit contract.

This round decided to promote it into `application` because:

- API, scheduler, and consumer all reuse it
- tests now depend on the same stable shape
- keeping the shaping rules only in `interfaces` would make a shared result look accidental instead of intentional

## Boundary decision

The new contract lives in:

- `VitalAI/application/use_cases/runtime_signal_views.py`

It was intentionally **not** moved to `Base` because `Base` still does not provide a suitable abstraction for this runtime-specific response shape.

It was also intentionally **not** moved to `shared` because this view is still most closely tied to application/use-case output, not a cross-project primitive.

## What was added

### 1. Explicit typed contract

Added:

- `RuntimeSignalView`

This dataclass defines the stable small runtime-signal shape:

- `kind`
- `severity`
- `source`
- `summary`
- `details`

### 2. Application-level mapping helpers

Added:

- `runtime_signal_view_from_observation()`
- `build_runtime_signal_views()`

These helpers convert raw `ObservationRecord` values into the application-facing contract.

### 3. Interface layer simplified

Updated:

- `VitalAI/interfaces/typed_flow_support.py`

The interface layer no longer owns the runtime-signal shaping rules directly.
It now consumes the application contract and only serializes it with `asdict`.

## Why this shape

This keeps the layers cleaner:

- `platform` still emits raw `ObservationRecord`
- `application` now owns the stable use-case-facing signal view
- `interfaces` remain thin and mostly serialize existing application contracts

That is more consistent with the project’s existing layering direction than keeping shared output-shaping logic inside adapters.

## Verification

Verified with:

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.platform.test_observability_contracts tests.platform.test_security_contracts tests.application.test_runtime_signal_views tests.application.test_health_alert_flow tests.application.test_mental_care_flow tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes tests.interfaces.test_scheduler_and_consumer_adapters
```

Result:

- `Ran 56 tests ... OK`

## Outcome

After this step:

- `runtime_signals` is now an explicit application contract
- interface adapters are thinner than before
- the boundary decision is now clear and documented

## Best next step

The next natural step is to check whether the existing application result objects should also expose `runtime_signals` directly, so interfaces no longer need to know about raw `runtime_observations` at all.
