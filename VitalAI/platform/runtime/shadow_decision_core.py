"""Shadow Decision Core runtime shell."""

from __future__ import annotations

from dataclasses import dataclass

from VitalAI.platform.interrupt import SnapshotReference
from VitalAI.platform.runtime.snapshots import RuntimeSnapshot


@dataclass
class ShadowDecisionCore:
    """Minimal shadow decision core aligned with typed runtime snapshots."""

    latest_snapshot: RuntimeSnapshot | None = None

    def sync_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        """Sync a primary-core snapshot into the shadow node."""
        self.latest_snapshot = snapshot

    def latest_reference(self) -> SnapshotReference | None:
        """Return the latest snapshot as an interrupt-facing reference."""
        if self.latest_snapshot is None:
            return None
        return self.latest_snapshot.to_reference()

    def takeover_ready(self) -> bool:
        """Return whether the shadow has enough state for a basic takeover."""
        return self.latest_snapshot is not None
