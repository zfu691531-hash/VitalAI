"""Application use case for the typed mental-care check-in flow."""

from __future__ import annotations

from dataclasses import dataclass, field

from VitalAI.application.use_cases.runtime_support import ingest_and_get_latest_summary
from VitalAI.application.use_cases.runtime_signal_views import RuntimeSignalView, build_runtime_signal_views
from VitalAI.domains.mental_care.services import MentalCareCheckInSupportService, MentalCareSupportOutcome
from VitalAI.platform.messaging import MessageEnvelope
from VitalAI.platform.observability import ObservationRecord
from VitalAI.platform.runtime import DecisionCore, EventAggregator, EventSummary, SnapshotStore
from VitalAI.platform.runtime.signal_wiring import RuntimeSignalBridge


@dataclass(slots=True)
class MentalCareCheckInFlowResult:
    """Runtime result for the typed mental-care check-in flow."""

    accepted: bool
    summary: EventSummary | None
    outcome: MentalCareSupportOutcome | None
    runtime_observations: list[ObservationRecord] = field(default_factory=list)

    @property
    def runtime_signals(self) -> list[RuntimeSignalView]:
        """Expose runtime observations through the application signal-view contract."""
        return build_runtime_signal_views(self.runtime_observations)


@dataclass
class RunMentalCareCheckInFlowUseCase:
    """Minimal end-to-end use case for mental-care check-in messages."""

    aggregator: EventAggregator
    decision_core: DecisionCore
    support_service: MentalCareCheckInSupportService
    signal_bridge: RuntimeSignalBridge | None = None
    snapshot_store: SnapshotStore | None = None
    _pending_outcomes: dict[str, MentalCareSupportOutcome] = field(default_factory=dict, init=False, repr=False)

    def configure_handlers(self) -> None:
        """Register the mental-care handler on the decision core."""
        self.decision_core.register_handler(
            "MENTAL_CARE_CHECKIN",
            self._resolve_pending_decision_message,
        )

    def run(self, event: MessageEnvelope) -> MentalCareCheckInFlowResult:
        """Route a typed message through runtime and domain orchestration."""
        accepted, summary, runtime_observations = ingest_and_get_latest_summary(
            self.aggregator,
            event,
            signal_bridge=self.signal_bridge,
            snapshot_store=self.snapshot_store,
        )
        if not accepted or summary is None:
            return MentalCareCheckInFlowResult(
                accepted=False,
                summary=None,
                outcome=None,
                runtime_observations=runtime_observations,
            )

        outcome = self.support_service.support(summary)
        self._pending_outcomes[summary.message_id] = outcome
        try:
            decision_message = self.decision_core.process_summary(summary)
        finally:
            self._pending_outcomes.pop(summary.message_id, None)
        if decision_message is None:
            return MentalCareCheckInFlowResult(
                accepted=True,
                summary=summary,
                outcome=None,
                runtime_observations=runtime_observations,
            )

        return MentalCareCheckInFlowResult(
            accepted=True,
            summary=summary,
            outcome=outcome,
            runtime_observations=runtime_observations,
        )

    def _resolve_pending_decision_message(self, summary: EventSummary) -> MessageEnvelope | None:
        """Return the already-computed decision message for one summarized event."""
        outcome = self._pending_outcomes.get(summary.message_id)
        if outcome is None:
            return None
        return outcome.decision_message
