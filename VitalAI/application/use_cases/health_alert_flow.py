"""Application use case for the typed health alert flow."""

from __future__ import annotations

from dataclasses import dataclass, field

from VitalAI.application.use_cases.runtime_support import ingest_and_get_latest_summary
from VitalAI.application.use_cases.runtime_signal_views import RuntimeSignalView, build_runtime_signal_views
from VitalAI.domains.health.services import HealthAlertTriageService, HealthTriageOutcome
from VitalAI.platform.messaging import MessageEnvelope
from VitalAI.platform.observability import ObservationRecord
from VitalAI.platform.runtime import DecisionCore, EventAggregator, EventSummary
from VitalAI.platform.runtime.signal_wiring import RuntimeSignalBridge


@dataclass(slots=True)
class HealthAlertFlowResult:
    """Runtime result for the typed health alert application flow."""

    accepted: bool
    summary: EventSummary | None
    outcome: HealthTriageOutcome | None
    runtime_observations: list[ObservationRecord] = field(default_factory=list)

    @property
    def runtime_signals(self) -> list[RuntimeSignalView]:
        """Expose runtime observations through the application signal-view contract."""
        return build_runtime_signal_views(self.runtime_observations)


@dataclass
class RunHealthAlertFlowUseCase:
    """Minimal end-to-end use case for health alert messages."""

    aggregator: EventAggregator
    decision_core: DecisionCore
    triage_service: HealthAlertTriageService
    signal_bridge: RuntimeSignalBridge | None = None

    def configure_handlers(self) -> None:
        """Register the health alert handler on the decision core."""
        self.decision_core.register_handler(
            "HEALTH_ALERT",
            lambda summary: self.triage_service.triage(summary).decision_message,
        )

    def run(self, event: MessageEnvelope) -> HealthAlertFlowResult:
        """Route a typed message through runtime and domain orchestration."""
        accepted, summary, runtime_observations = ingest_and_get_latest_summary(
            self.aggregator,
            event,
            signal_bridge=self.signal_bridge,
        )
        if not accepted or summary is None:
            return HealthAlertFlowResult(
                accepted=False,
                summary=None,
                outcome=None,
                runtime_observations=runtime_observations,
            )

        outcome = self.triage_service.triage(summary)
        decision_message = self.decision_core.process_summary(summary)
        if decision_message is None:
            return HealthAlertFlowResult(
                accepted=True,
                summary=summary,
                outcome=None,
                runtime_observations=runtime_observations,
            )

        return HealthAlertFlowResult(
            accepted=True,
            summary=summary,
            outcome=outcome,
            runtime_observations=runtime_observations,
        )
