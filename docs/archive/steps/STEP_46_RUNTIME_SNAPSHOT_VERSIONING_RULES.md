# Step 46: Runtime Snapshot Versioning Rules

## Why this step

Runtime snapshots already had a `version` field, but the in-memory store still behaved as if every save were a brand-new version `1`.

That left one small runtime primitive gap:

- repeated saves with the same `snapshot_id` had no explicit versioning rule

This step closes that gap with the smallest useful rule:

- saving the same `snapshot_id` again increments the stored version

## What changed

### 1. SnapshotStore now increments version for repeated snapshot ids

Updated:

- `VitalAI/platform/runtime/snapshots.py`

`SnapshotStore.save()` now checks whether the `snapshot_id` already exists.

Current behavior:

- first save for one id -> `version=1`
- repeated save for the same id -> previous version + 1

The store still keeps the latest snapshot instance for that id, so this remains a lightweight in-memory rule rather than a historical archive.

### 2. Snapshot references now reflect the updated stored version

Because `get_reference()` already reads from the latest stored snapshot, repeated saves now naturally propagate the incremented version into:

- `SnapshotReference`
- any later runtime usage that reads the current snapshot reference

### 3. Added direct runtime verification

Updated:

- `tests/platform/test_runtime_contract_wiring.py`

The new verification covers:

- first save returns version `1`
- second save with the same id returns version `2`
- latest stored snapshot keeps the newest trace id
- `get_reference()` reflects the incremented version

## Why this shape

This stays intentionally minimal:

- no persistence layer
- no archive history model
- no new result boundary

It only makes the existing `version` field real inside the current runtime store.

## Verification

Verified with:

```bash
python -m unittest tests.platform.test_runtime_contract_wiring tests.platform.test_observability_contracts tests.application.test_application_assembly tests.interfaces.test_typed_flow_routes
```

Result:

- `Ran 47 tests`
- `OK`

## Outcome

After this step:

- runtime snapshot versioning is no longer nominal only
- repeated snapshot saves have a stable incremental rule
- the current nearby runtime snapshot seam has reached a reasonable stop point
