"""Failover runtime shell."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from VitalAI.platform.interrupt import InterruptAction, InterruptSignal
from VitalAI.platform.runtime.decision_core import DecisionCore
from VitalAI.platform.runtime.shadow_decision_core import ShadowDecisionCore

if TYPE_CHECKING:
    from VitalAI.platform.runtime.signal_wiring import RuntimeSignalBridge


@dataclass
class FailoverCoordinator:
    """Minimal failover coordinator aligned with interrupt signals."""

    primary: DecisionCore
    shadow: ShadowDecisionCore
    active_node: str = "primary"
    last_signal: InterruptSignal | None = None

    def should_failover(self, signal: InterruptSignal | None = None) -> bool:
        """Return whether failover should occur for the given interrupt."""
        if signal is not None:
            self.last_signal = signal
            if signal.action is not InterruptAction.TAKEOVER:
                return False
            if signal.needs_interrupt_snapshot() and not signal.has_snapshot_refs():
                return False
        return self.shadow.takeover_ready()

    def failover(
        self,
        signal: InterruptSignal | None = None,
        signal_bridge: "RuntimeSignalBridge | None" = None,
    ) -> bool:
        """Switch to the shadow node when interrupt and snapshot conditions pass."""
        if not self.should_failover(signal):
            return False
        previous_node = self.active_node
        self.active_node = "shadow"
        if signal_bridge is not None:
            signal_bridge.observe_failover_transition(
                previous_node=previous_node,
                current_node=self.active_node,
                signal=signal,
            )
        return True

    def failback(
        self,
        signal: InterruptSignal | None = None,
        signal_bridge: "RuntimeSignalBridge | None" = None,
    ) -> None:
        """Switch the active node back to primary."""
        previous_node = self.active_node
        if signal is not None:
            self.last_signal = signal
        self.active_node = "primary"
        if signal_bridge is not None and previous_node != self.active_node:
            signal_bridge.observe_failover_transition(
                previous_node=previous_node,
                current_node=self.active_node,
                signal=signal,
            )
