"""Health Monitor runtime shell."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from VitalAI.platform.interrupt import InterruptAction, InterruptPriority, InterruptSignal

if TYPE_CHECKING:
    from VitalAI.platform.runtime.signal_wiring import RuntimeSignalBridge


@dataclass(slots=True)
class HeartbeatRecord:
    """Minimal heartbeat record stored by the health monitor."""

    component_id: str
    observed_at: datetime


@dataclass
class HealthMonitor:
    """Minimal health monitor that can escalate stale components as interrupts."""

    heartbeat_registry: dict[str, HeartbeatRecord] = field(default_factory=dict)

    def heartbeat(self, component_id: str, observed_at: datetime | None = None) -> HeartbeatRecord:
        """Record a component heartbeat and return the stored record."""
        record = HeartbeatRecord(
            component_id=component_id,
            observed_at=observed_at or datetime.now(UTC),
        )
        self.heartbeat_registry[component_id] = record
        return record

    def last_seen(self, component_id: str) -> datetime | None:
        """Return when the component was last observed."""
        record = self.heartbeat_registry.get(component_id)
        return None if record is None else record.observed_at

    def is_stale(
        self,
        component_id: str,
        timeout: timedelta,
        now: datetime | None = None,
    ) -> bool:
        """Return whether the component has missed its heartbeat window."""
        last_seen = self.last_seen(component_id)
        if last_seen is None:
            return True
        current = now or datetime.now(UTC)
        return current - last_seen > timeout

    def build_interrupt(
        self,
        component_id: str,
        timeout: timedelta,
        now: datetime | None = None,
        signal_bridge: "RuntimeSignalBridge | None" = None,
    ) -> InterruptSignal | None:
        """Create an interrupt signal when a component becomes stale."""
        if not self.is_stale(component_id, timeout=timeout, now=now):
            return None
        signal = InterruptSignal(
            trace_id=f"health-monitor:{component_id}",
            source="health-monitor",
            priority=InterruptPriority.P1,
            action=InterruptAction.TAKEOVER,
            reason=f"{component_id} heartbeat timed out",
            target=component_id,
            payload={"timeout_seconds": int(timeout.total_seconds())},
        )
        if signal_bridge is not None:
            signal_bridge.observe_interrupt(signal)
        return signal
