# Step 47: Runtime Snapshot History Lookup

## Why this step

The previous snapshot versioning step made repeated saves with the same `snapshot_id` increment `version`.

But one small runtime primitive gap still remained:

- only the latest snapshot for a given id could be read back directly
- older versions were no longer addressable even though version numbers now existed

This step closes that gap by making version history readable inside the current in-memory store.

## What changed

### 1. SnapshotStore now keeps version-addressable snapshot history

Updated:

- `VitalAI/platform/runtime/snapshots.py`

`SnapshotStore` now keeps:

- `snapshots` for the latest snapshot by `snapshot_id`
- `snapshot_versions` for historical lookup by `(snapshot_id, version)`

### 2. Added explicit historical lookup

Updated:

- `VitalAI/platform/runtime/snapshots.py`

Added:

- `SnapshotStore.get_version(snapshot_id, version)`

This returns one concrete historical `RuntimeSnapshot` when that version exists.

### 3. Existing latest-snapshot behavior stays unchanged

The current store still behaves the same for callers that only need the latest value:

- `get(snapshot_id)` still returns the latest snapshot
- `get_reference(snapshot_id)` still reflects the latest version

The new history lookup only adds read access to earlier versions.

## Why this shape

This stays intentionally small:

- no persistence layer
- no cleanup policy
- no interface-level exposure

It only makes the current in-memory versioning rule actually queryable.

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

- repeated snapshot saves still advance version numbers
- older in-memory versions can now be read back explicitly
- the snapshot versioning seam is now more complete without opening a larger persistence design
