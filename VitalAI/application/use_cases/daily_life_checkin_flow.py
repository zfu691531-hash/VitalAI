"""Application use case for the typed daily-life check-in flow."""

from __future__ import annotations

from dataclasses import dataclass, field

from VitalAI.application.use_cases.runtime_support import ingest_and_get_latest_summary
from VitalAI.application.use_cases.runtime_signal_views import RuntimeSignalView, build_runtime_signal_views
from VitalAI.domains.daily_life.services import DailyLifeCheckInSupportService, DailyLifeSupportOutcome
from VitalAI.platform.messaging import MessageEnvelope
from VitalAI.platform.observability import ObservationRecord
from VitalAI.platform.runtime import DecisionCore, EventAggregator, EventSummary
from VitalAI.platform.runtime.signal_wiring import RuntimeSignalBridge


@dataclass(slots=True)
class DailyLifeCheckInFlowResult:
    """Runtime result for the typed daily-life check-in flow."""

    accepted: bool
    summary: EventSummary | None
    outcome: DailyLifeSupportOutcome | None
    runtime_observations: list[ObservationRecord] = field(default_factory=list)

    @property
    def runtime_signals(self) -> list[RuntimeSignalView]:
        """Expose runtime observations through the application signal-view contract."""
        return build_runtime_signal_views(self.runtime_observations)


@dataclass
class RunDailyLifeCheckInFlowUseCase:
    """Minimal end-to-end use case for daily-life check-in messages."""

    aggregator: EventAggregator
    decision_core: DecisionCore
    support_service: DailyLifeCheckInSupportService
    signal_bridge: RuntimeSignalBridge | None = None

    def configure_handlers(self) -> None:
        """Register the daily-life handler on the decision core."""
        self.decision_core.register_handler(
            "DAILY_LIFE_CHECKIN",
            lambda summary: self.support_service.support(summary).decision_message,
        )

    def run(self, event: MessageEnvelope) -> DailyLifeCheckInFlowResult:
        """Route a typed message through runtime and domain orchestration."""
        accepted, summary, runtime_observations = ingest_and_get_latest_summary(
            self.aggregator,
            event,
            signal_bridge=self.signal_bridge,
        )
        if not accepted or summary is None:
            return DailyLifeCheckInFlowResult(
                accepted=False,
                summary=None,
                outcome=None,
                runtime_observations=runtime_observations,
            )

        outcome = self.support_service.support(summary)
        decision_message = self.decision_core.process_summary(summary)
        if decision_message is None:
            return DailyLifeCheckInFlowResult(
                accepted=True,
                summary=summary,
                outcome=None,
                runtime_observations=runtime_observations,
            )

        return DailyLifeCheckInFlowResult(
            accepted=True,
            summary=summary,
            outcome=outcome,
            runtime_observations=runtime_observations,
        )
