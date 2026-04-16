"""Lightweight application assembly for the current typed flows."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
import os
from typing import Callable

from VitalAI.application.commands import HealthAlertCommand
from VitalAI.application.use_cases.daily_life_checkin_flow import RunDailyLifeCheckInFlowUseCase
from VitalAI.application.use_cases.daily_life_checkin_query import RunDailyLifeCheckInHistoryQueryUseCase
from VitalAI.application.use_cases.health_alert_flow import RunHealthAlertFlowUseCase
from VitalAI.application.use_cases.health_alert_query import RunHealthAlertHistoryQueryUseCase
from VitalAI.application.use_cases.mental_care_checkin_flow import RunMentalCareCheckInFlowUseCase
from VitalAI.application.use_cases.mental_care_checkin_query import RunMentalCareCheckInHistoryQueryUseCase
from VitalAI.application.use_cases.profile_memory_flow import RunProfileMemoryFlowUseCase
from VitalAI.application.use_cases.profile_memory_query import RunProfileMemoryQueryUseCase
from VitalAI.application.use_cases.intent_recognition import (
    RunUserIntentRecognitionUseCase,
    build_intent_recognition_use_case,
    parse_bert_intent_label_map,
)
from VitalAI.application.use_cases.intent_decomposition import (
    RunIntentDecompositionUseCase,
    build_intent_decomposition_use_case,
)
from VitalAI.application.use_cases.runtime_signal_views import RuntimeSignalView, build_runtime_signal_views
from VitalAI.application.workflows.daily_life_checkin_workflow import DailyLifeCheckInWorkflow
from VitalAI.application.workflows.daily_life_checkin_query_workflow import DailyLifeCheckInHistoryQueryWorkflow
from VitalAI.application.workflows.health_alert_workflow import HealthAlertWorkflow
from VitalAI.application.workflows.health_alert_query_workflow import HealthAlertHistoryQueryWorkflow
from VitalAI.application.workflows.mental_care_checkin_workflow import MentalCareCheckInWorkflow
from VitalAI.application.workflows.mental_care_checkin_query_workflow import (
    MentalCareCheckInHistoryQueryWorkflow,
)
from VitalAI.application.workflows.profile_memory_workflow import ProfileMemoryWorkflow
from VitalAI.application.workflows.profile_memory_query_workflow import ProfileMemoryQueryWorkflow
from VitalAI.application.workflows.user_interaction_workflow import UserInteractionWorkflow
from VitalAI.domains.daily_life import DailyLifeCheckInRepository, DailyLifeCheckInSupportService
from VitalAI.domains.health import HealthAlertRepository, HealthAlertTriageService
from VitalAI.domains.mental_care import MentalCareCheckInRepository, MentalCareCheckInSupportService
from VitalAI.domains.profile_memory import ProfileMemoryRepository, ProfileMemoryUpdateService
from VitalAI.domains.reporting import FeedbackReportService, NoOpFeedbackReportService
from VitalAI.platform.interrupt import InterruptAction, InterruptPriority, InterruptSignal, SnapshotReference
from VitalAI.platform.messaging import MessageEnvelope
from VitalAI.platform.observability import ObservationKind, ObservationRecord, ObservabilityCollector
from VitalAI.platform.runtime import (
    DecisionCore,
    EventAggregator,
    FailoverCoordinator,
    FileSnapshotStore,
    RuntimeSnapshot,
    ShadowDecisionCore,
    SnapshotStore,
)
from VitalAI.platform.runtime.signal_wiring import RuntimeSignalBridge
from VitalAI.platform.security import SensitiveDataGuard


def _build_runtime_signal_bridge() -> RuntimeSignalBridge:
    """Build a fresh runtime signal bridge for one workflow/use-case graph."""
    return RuntimeSignalBridge(
        observability=ObservabilityCollector(),
        security_guard=SensitiveDataGuard(),
    )


@dataclass(slots=True)
class ApplicationAssemblyConfig:
    """Lightweight dependency hooks used by the current assembly layer."""

    event_aggregator_factory: Callable[[], EventAggregator] = EventAggregator
    decision_core_factory: Callable[[], DecisionCore] = DecisionCore
    snapshot_store_factory: Callable[[], SnapshotStore] = SnapshotStore
    health_triage_service_factory: Callable[[], HealthAlertTriageService] = HealthAlertTriageService
    health_repository_factory: Callable[[], HealthAlertRepository] = HealthAlertRepository
    daily_life_support_service_factory: Callable[[], DailyLifeCheckInSupportService] = (
        DailyLifeCheckInSupportService
    )
    daily_life_repository_factory: Callable[[], DailyLifeCheckInRepository] = DailyLifeCheckInRepository
    mental_care_support_service_factory: Callable[[], MentalCareCheckInSupportService] = (
        MentalCareCheckInSupportService
    )
    mental_care_repository_factory: Callable[[], MentalCareCheckInRepository] = MentalCareCheckInRepository
    profile_memory_repository_factory: Callable[[], ProfileMemoryRepository] = ProfileMemoryRepository
    profile_memory_service_factory: Callable[[ProfileMemoryRepository], ProfileMemoryUpdateService] = (
        ProfileMemoryUpdateService
    )
    feedback_report_service_factory: Callable[[], FeedbackReportService] = FeedbackReportService
    runtime_signal_bridge_factory: Callable[[], RuntimeSignalBridge | None] = _build_runtime_signal_bridge
    intent_recognition_use_case_factory: Callable[[], RunUserIntentRecognitionUseCase] = (
        RunUserIntentRecognitionUseCase
    )
    intent_decomposition_use_case_factory: Callable[[], RunIntentDecompositionUseCase] = (
        RunIntentDecompositionUseCase
    )


@dataclass(slots=True)
class ApplicationIngressPolicy:
    """Lightweight ingress-message policy applied at the application boundary."""

    require_ack_override: bool | None = None
    ttl_override: int | None = None

    def apply(self, envelope: MessageEnvelope) -> MessageEnvelope:
        """Return an ingress envelope adjusted for the current runtime role."""
        if self.require_ack_override is None and self.ttl_override is None:
            return envelope
        return replace(
            envelope,
            require_ack=envelope.require_ack if self.require_ack_override is None else self.require_ack_override,
            ttl=envelope.ttl if self.ttl_override is None else self.ttl_override,
        )


@dataclass(slots=True)
class ApplicationAssemblyPolicySnapshot:
    """Typed snapshot of the current assembly policy for one runtime role."""

    runtime_role: str
    reporting_enabled: bool
    reporting_policy_source: str
    runtime_signals_enabled: bool
    runtime_signals_policy_source: str
    require_ack_override: bool | None
    ttl_override: int | None
    ingress_policy_source: str


@dataclass(slots=True)
class ApplicationRuntimeDiagnostics:
    """Typed result for an assembly-driven runtime diagnostics drill."""

    runtime_role: str
    snapshot_id: str | None
    failover_triggered: bool
    active_node: str
    interrupt_action: str | None = None
    interrupt_has_snapshot_refs: bool | None = None
    latest_security_action: str | None = None
    latest_security_finding_count: int | None = None
    latest_security_highest_severity: str | None = None
    latest_failover_signal_id: str | None = None
    runtime_observations: list[ObservationRecord] = field(default_factory=list)

    @property
    def runtime_signals(self) -> list[RuntimeSignalView]:
        """Expose diagnostics observations through the runtime-signal contract."""
        return build_runtime_signal_views(self.runtime_observations)


@dataclass(slots=True)
class ApplicationAssemblyEnvironment:
    """Minimal environment configuration kept local to the application layer."""

    app_env: str = "development"
    runtime_role: str = "default"
    reporting_enabled: bool = True
    runtime_signals_enabled: bool = True
    runtime_control_enabled: bool = True
    runtime_snapshot_store_path: str | None = None
    intent_recognizer: str = "rule_based"
    bert_intent_model_path: str | None = None
    bert_intent_confidence_threshold: float = 0.65
    bert_intent_label_map: str | None = None
    intent_decomposer: str = "placeholder"

    @classmethod
    def from_environment(
        cls,
        runtime_role: str | None = None,
    ) -> "ApplicationAssemblyEnvironment":
        """Load assembly-relevant settings from process environment."""
        resolved_runtime_role = runtime_role or os.getenv("VITALAI_RUNTIME_ROLE", "default")
        resolved_app_env = os.getenv("APP_ENV", "development")
        return cls(
            app_env=resolved_app_env,
            runtime_role=resolved_runtime_role,
            reporting_enabled=_env_to_bool(
                os.getenv("VITALAI_REPORTING_ENABLED"),
                default=_default_reporting_enabled_for_role(resolved_runtime_role),
            ),
            runtime_signals_enabled=_env_to_bool(
                os.getenv("VITALAI_RUNTIME_SIGNALS_ENABLED"),
                default=_default_runtime_signals_enabled_for_role(resolved_runtime_role),
            ),
            runtime_control_enabled=_env_to_bool(
                os.getenv("VITALAI_RUNTIME_CONTROL_ENABLED"),
                default=_default_runtime_control_enabled_for_env(resolved_app_env),
            ),
            runtime_snapshot_store_path=_env_to_optional_str(
                os.getenv("VITALAI_RUNTIME_SNAPSHOT_STORE_PATH")
            ),
            intent_recognizer=os.getenv("VITALAI_INTENT_RECOGNIZER", "rule_based"),
            bert_intent_model_path=_env_to_optional_str(
                os.getenv("VITALAI_BERT_INTENT_MODEL_PATH")
            ),
            bert_intent_confidence_threshold=_env_to_float(
                os.getenv("VITALAI_BERT_INTENT_CONFIDENCE_THRESHOLD"),
                default=0.65,
            ),
            bert_intent_label_map=_env_to_optional_str(
                os.getenv("VITALAI_BERT_INTENT_LABELS")
            ),
            intent_decomposer=os.getenv("VITALAI_INTENT_DECOMPOSER", "placeholder"),
        )

    def to_config(self) -> ApplicationAssemblyConfig:
        """Convert environment choices into the existing assembly hooks."""
        report_factory: Callable[[], FeedbackReportService] = FeedbackReportService
        if not self.reporting_enabled:
            report_factory = NoOpFeedbackReportService

        return ApplicationAssemblyConfig(
            feedback_report_service_factory=report_factory,
            snapshot_store_factory=_snapshot_store_factory_for_path(self.runtime_snapshot_store_path),
            intent_recognition_use_case_factory=_intent_recognition_use_case_factory(
                mode=self.intent_recognizer,
                bert_model_path=self.bert_intent_model_path,
                bert_confidence_threshold=self.bert_intent_confidence_threshold,
                bert_label_map=parse_bert_intent_label_map(self.bert_intent_label_map),
            ),
            intent_decomposition_use_case_factory=_intent_decomposition_use_case_factory(
                mode=self.intent_decomposer,
            ),
            runtime_signal_bridge_factory=(
                _build_runtime_signal_bridge if self.runtime_signals_enabled else _build_disabled_runtime_signal_bridge
            ),
        )

    def to_ingress_policy(self) -> ApplicationIngressPolicy:
        """Convert runtime-role defaults into ingress-message policy."""
        if self.runtime_role == "scheduler":
            return ApplicationIngressPolicy(require_ack_override=False, ttl_override=300)
        if self.runtime_role == "consumer":
            return ApplicationIngressPolicy(require_ack_override=True, ttl_override=60)
        return ApplicationIngressPolicy()


@dataclass(slots=True)
class ApplicationAssembly:
    """Small assembly object used by interfaces and tests."""

    config: ApplicationAssemblyConfig
    environment: ApplicationAssemblyEnvironment | None = None
    _snapshot_store: SnapshotStore | None = field(default=None, init=False, repr=False)
    _health_repository: HealthAlertRepository | None = field(default=None, init=False, repr=False)
    _daily_life_repository: DailyLifeCheckInRepository | None = field(default=None, init=False, repr=False)
    _mental_care_repository: MentalCareCheckInRepository | None = field(default=None, init=False, repr=False)
    _profile_memory_repository: ProfileMemoryRepository | None = field(default=None, init=False, repr=False)

    @classmethod
    def from_environment(
        cls,
        runtime_role: str | None = None,
    ) -> "ApplicationAssembly":
        """Build an assembly object from environment settings."""
        environment = ApplicationAssemblyEnvironment.from_environment(runtime_role=runtime_role)
        return cls(config=environment.to_config(), environment=environment)

    @property
    def runtime_role(self) -> str:
        """Expose the resolved runtime role for lightweight branching."""
        if self.environment is None:
            return "default"
        return self.environment.runtime_role

    @property
    def ingress_policy(self) -> ApplicationIngressPolicy:
        """Expose the active ingress policy for the assembly."""
        if self.environment is None:
            return ApplicationIngressPolicy()
        return self.environment.to_ingress_policy()

    @property
    def runtime_control_enabled(self) -> bool:
        """Return whether side-effecting runtime control endpoints are enabled."""
        if self.environment is None:
            return True
        return self.environment.runtime_control_enabled

    @property
    def snapshot_store(self) -> SnapshotStore:
        """Return the shared snapshot store for this assembled runtime graph."""
        if self._snapshot_store is None:
            self._snapshot_store = self.config.snapshot_store_factory()
        return self._snapshot_store

    @property
    def daily_life_repository(self) -> DailyLifeCheckInRepository:
        """Return the shared daily-life history repository for this assembly."""
        if self._daily_life_repository is None:
            self._daily_life_repository = self.config.daily_life_repository_factory()
        return self._daily_life_repository

    @property
    def health_repository(self) -> HealthAlertRepository:
        """Return the shared health alert history repository for this assembly."""
        if self._health_repository is None:
            self._health_repository = self.config.health_repository_factory()
        return self._health_repository

    @property
    def mental_care_repository(self) -> MentalCareCheckInRepository:
        """Return the shared mental-care history repository for this assembly."""
        if self._mental_care_repository is None:
            self._mental_care_repository = self.config.mental_care_repository_factory()
        return self._mental_care_repository

    @property
    def profile_memory_repository(self) -> ProfileMemoryRepository:
        """Return the shared profile-memory repository for this assembly."""
        if self._profile_memory_repository is None:
            self._profile_memory_repository = self.config.profile_memory_repository_factory()
        return self._profile_memory_repository

    def apply_ingress_policy(self, envelope: MessageEnvelope) -> MessageEnvelope:
        """Apply assembly ingress policy to a typed message envelope."""
        return self.ingress_policy.apply(envelope)

    def describe_policies(self) -> ApplicationAssemblyPolicySnapshot:
        """Return the active assembly policy as a typed snapshot."""
        ingress_policy = self.ingress_policy
        return ApplicationAssemblyPolicySnapshot(
            runtime_role=self.runtime_role,
            reporting_enabled=True if self.environment is None else self.environment.reporting_enabled,
            reporting_policy_source=self._reporting_policy_source(),
            runtime_signals_enabled=True
            if self.environment is None
            else self.environment.runtime_signals_enabled,
            runtime_signals_policy_source=self._runtime_signals_policy_source(),
            require_ack_override=ingress_policy.require_ack_override,
            ttl_override=ingress_policy.ttl_override,
            ingress_policy_source=self._ingress_policy_source(),
        )

    def run_runtime_diagnostics(self) -> ApplicationRuntimeDiagnostics:
        """Run a minimal assembly-driven snapshot/failover diagnostics path."""
        signal_bridge = self.config.runtime_signal_bridge_factory()
        snapshot = self.snapshot_store.save(
            snapshot_id=f"{self.runtime_role}-runtime-snapshot",
            source="application-assembly",
            payload={
                "runtime_role": self.runtime_role,
                "reporting_enabled": True if self.environment is None else self.environment.reporting_enabled,
                "runtime_signals_enabled": True
                if self.environment is None
                else self.environment.runtime_signals_enabled,
            },
            trace_id=f"assembly-runtime-diagnostics-{self.runtime_role}",
            signal_bridge=signal_bridge,
        )
        coordinator = FailoverCoordinator(
            primary=self.config.decision_core_factory(),
            shadow=ShadowDecisionCore(latest_snapshot=snapshot),
        )
        failover_triggered = coordinator.failover(
            InterruptSignal(
                trace_id=f"assembly-runtime-diagnostics-{self.runtime_role}",
                source="application-assembly",
                priority=InterruptPriority.P1,
                action=InterruptAction.TAKEOVER,
                reason="assembly runtime diagnostics failover drill",
                target="decision-core",
                snapshot_refs=[snapshot.to_reference()],
                payload={"runtime_role": self.runtime_role},
            ),
            signal_bridge=signal_bridge,
        )
        runtime_observations: list[ObservationRecord] = []
        if signal_bridge is not None:
            runtime_observations = list(signal_bridge.observability.records)
        interrupt_observation = _latest_observation_by_kind(runtime_observations, ObservationKind.INTERRUPT_SIGNAL)
        security_observation = _latest_observation_by_kind(runtime_observations, ObservationKind.SECURITY_REVIEW)
        failover_observation = _latest_observation_by_kind(runtime_observations, ObservationKind.FAILOVER_TRANSITION)
        return ApplicationRuntimeDiagnostics(
            runtime_role=self.runtime_role,
            snapshot_id=snapshot.snapshot_id,
            failover_triggered=failover_triggered,
            active_node=coordinator.active_node,
            interrupt_action=_observation_attribute_as_str(interrupt_observation, "action"),
            interrupt_has_snapshot_refs=_observation_attribute_as_bool(interrupt_observation, "has_snapshot_refs"),
            latest_security_action=_observation_attribute_as_str(security_observation, "action"),
            latest_security_finding_count=_observation_attribute_as_int(security_observation, "finding_count"),
            latest_security_highest_severity=_observation_attribute_as_str(security_observation, "highest_severity"),
            latest_failover_signal_id=_observation_attribute_as_str(failover_observation, "signal_id"),
            runtime_observations=runtime_observations,
        )

    def run_health_critical_failover_drill(self) -> ApplicationRuntimeDiagnostics:
        """Run a controlled failover drill driven by a real critical health flow."""
        signal_bridge = self.config.runtime_signal_bridge_factory()
        use_case = RunHealthAlertFlowUseCase(
            aggregator=self.config.event_aggregator_factory(),
            decision_core=self.config.decision_core_factory(),
            triage_service=self.config.health_triage_service_factory(),
            signal_bridge=signal_bridge,
            snapshot_store=self.snapshot_store,
        )
        use_case.configure_handlers()
        use_case.run(
            HealthAlertCommand(
                source_agent="assembly-health-failover-drill",
                trace_id=f"assembly-health-failover-drill-{self.runtime_role}",
                user_id="drill-elder",
                risk_level="critical",
            ).to_message_envelope()
        )
        if signal_bridge is None:
            return ApplicationRuntimeDiagnostics(
                runtime_role=self.runtime_role,
                snapshot_id=None,
                failover_triggered=False,
                active_node="primary",
                interrupt_action=None,
                interrupt_has_snapshot_refs=None,
                latest_security_action=None,
                latest_security_finding_count=None,
                latest_security_highest_severity=None,
                latest_failover_signal_id=None,
                runtime_observations=[],
            )

        snapshot_observation = _latest_observation_by_kind(
            signal_bridge.observability.records,
            ObservationKind.RUNTIME_SNAPSHOT,
        )
        interrupt_observation = _latest_observation_by_kind(
            signal_bridge.observability.records,
            ObservationKind.INTERRUPT_SIGNAL,
        )
        if snapshot_observation is None or interrupt_observation is None:
            return ApplicationRuntimeDiagnostics(
                runtime_role=self.runtime_role,
                snapshot_id=None if snapshot_observation is None else snapshot_observation.attributes.get("snapshot_id"),
                failover_triggered=False,
                active_node="primary",
                interrupt_action=_observation_attribute_as_str(interrupt_observation, "action"),
                interrupt_has_snapshot_refs=_observation_attribute_as_bool(interrupt_observation, "has_snapshot_refs"),
                latest_security_action=_observation_attribute_as_str(
                    _latest_observation_by_kind(signal_bridge.observability.records, ObservationKind.SECURITY_REVIEW),
                    "action",
                ),
                latest_security_finding_count=_observation_attribute_as_int(
                    _latest_observation_by_kind(signal_bridge.observability.records, ObservationKind.SECURITY_REVIEW),
                    "finding_count",
                ),
                latest_security_highest_severity=_observation_attribute_as_str(
                    _latest_observation_by_kind(signal_bridge.observability.records, ObservationKind.SECURITY_REVIEW),
                    "highest_severity",
                ),
                latest_failover_signal_id=_observation_attribute_as_str(
                    _latest_observation_by_kind(signal_bridge.observability.records, ObservationKind.FAILOVER_TRANSITION),
                    "signal_id",
                ),
                runtime_observations=list(signal_bridge.observability.records),
            )

        snapshot = RuntimeSnapshot(
            snapshot_id=str(snapshot_observation.attributes["snapshot_id"]),
            created_at=datetime.now(UTC),
            source="typed-flow-runtime",
            payload={"drill": "health-critical-failover"},
            trace_id=snapshot_observation.trace_id,
            version=int(snapshot_observation.attributes.get("version", 1)),
        )
        interrupt_signal = InterruptSignal(
            trace_id=str(interrupt_observation.trace_id or f"health-failover-drill-{self.runtime_role}"),
            source=str(interrupt_observation.source),
            priority=InterruptPriority(str(interrupt_observation.attributes["priority"])),
            action=InterruptAction(str(interrupt_observation.attributes["action"])),
            reason="controlled failover drill from critical health flow",
            target=None
            if interrupt_observation.attributes.get("target") is None
            else str(interrupt_observation.attributes["target"]),
            snapshot_refs=[
                SnapshotReference(
                    snapshot_id=snapshot.snapshot_id,
                    source=snapshot.source,
                    version=snapshot.version,
                )
            ],
            payload={"drill_source": "critical_health_flow"},
        )
        coordinator = FailoverCoordinator(
            primary=self.config.decision_core_factory(),
            shadow=ShadowDecisionCore(latest_snapshot=snapshot),
        )
        failover_triggered = coordinator.failover(interrupt_signal, signal_bridge=signal_bridge)
        security_observation = _latest_observation_by_kind(signal_bridge.observability.records, ObservationKind.SECURITY_REVIEW)
        failover_observation = _latest_observation_by_kind(signal_bridge.observability.records, ObservationKind.FAILOVER_TRANSITION)
        return ApplicationRuntimeDiagnostics(
            runtime_role=self.runtime_role,
            snapshot_id=snapshot.snapshot_id,
            failover_triggered=failover_triggered,
            active_node=coordinator.active_node,
            interrupt_action=_observation_attribute_as_str(interrupt_observation, "action"),
            interrupt_has_snapshot_refs=_observation_attribute_as_bool(interrupt_observation, "has_snapshot_refs"),
            latest_security_action=_observation_attribute_as_str(security_observation, "action"),
            latest_security_finding_count=_observation_attribute_as_int(security_observation, "finding_count"),
            latest_security_highest_severity=_observation_attribute_as_str(security_observation, "highest_severity"),
            latest_failover_signal_id=_observation_attribute_as_str(failover_observation, "signal_id"),
            runtime_observations=list(signal_bridge.observability.records),
        )

    def build_health_workflow(self) -> HealthAlertWorkflow:
        """Build the health typed workflow from the current assembly config."""
        cfg = self.config
        triage_service = cfg.health_triage_service_factory()
        if triage_service.history_repository is None:
            triage_service.history_repository = self.health_repository
        use_case = RunHealthAlertFlowUseCase(
            aggregator=cfg.event_aggregator_factory(),
            decision_core=cfg.decision_core_factory(),
            triage_service=triage_service,
            signal_bridge=cfg.runtime_signal_bridge_factory(),
            snapshot_store=self.snapshot_store,
        )
        use_case.configure_handlers()
        return HealthAlertWorkflow(
            use_case=use_case,
            report_service=cfg.feedback_report_service_factory(),
            message_transformer=self.apply_ingress_policy,
        )

    def build_health_alert_history_query_workflow(self) -> HealthAlertHistoryQueryWorkflow:
        """Build the read-only health alert history query workflow."""
        cfg = self.config
        triage_service = cfg.health_triage_service_factory()
        if triage_service.history_repository is None:
            triage_service.history_repository = self.health_repository
        use_case = RunHealthAlertHistoryQueryUseCase(
            triage_service=triage_service,
        )
        return HealthAlertHistoryQueryWorkflow(use_case=use_case)

    def build_daily_life_workflow(self) -> DailyLifeCheckInWorkflow:
        """Build the daily-life typed workflow from the current assembly config."""
        cfg = self.config
        support_service = cfg.daily_life_support_service_factory()
        if support_service.history_repository is None:
            support_service.history_repository = self.daily_life_repository
        use_case = RunDailyLifeCheckInFlowUseCase(
            aggregator=cfg.event_aggregator_factory(),
            decision_core=cfg.decision_core_factory(),
            support_service=support_service,
            signal_bridge=cfg.runtime_signal_bridge_factory(),
            snapshot_store=self.snapshot_store,
        )
        use_case.configure_handlers()
        return DailyLifeCheckInWorkflow(
            use_case=use_case,
            report_service=cfg.feedback_report_service_factory(),
            message_transformer=self.apply_ingress_policy,
        )

    def build_daily_life_checkin_history_query_workflow(self) -> DailyLifeCheckInHistoryQueryWorkflow:
        """Build the read-only daily-life history query workflow."""
        cfg = self.config
        support_service = cfg.daily_life_support_service_factory()
        if support_service.history_repository is None:
            support_service.history_repository = self.daily_life_repository
        use_case = RunDailyLifeCheckInHistoryQueryUseCase(
            support_service=support_service,
        )
        return DailyLifeCheckInHistoryQueryWorkflow(use_case=use_case)

    def build_mental_care_workflow(self) -> MentalCareCheckInWorkflow:
        """Build the mental-care typed workflow from the current assembly config."""
        cfg = self.config
        support_service = cfg.mental_care_support_service_factory()
        if support_service.history_repository is None:
            support_service.history_repository = self.mental_care_repository
        use_case = RunMentalCareCheckInFlowUseCase(
            aggregator=cfg.event_aggregator_factory(),
            decision_core=cfg.decision_core_factory(),
            support_service=support_service,
            signal_bridge=cfg.runtime_signal_bridge_factory(),
            snapshot_store=self.snapshot_store,
        )
        use_case.configure_handlers()
        return MentalCareCheckInWorkflow(
            use_case=use_case,
            report_service=cfg.feedback_report_service_factory(),
            message_transformer=self.apply_ingress_policy,
        )

    def build_mental_care_checkin_history_query_workflow(self) -> MentalCareCheckInHistoryQueryWorkflow:
        """Build the read-only mental-care history query workflow."""
        cfg = self.config
        support_service = cfg.mental_care_support_service_factory()
        if support_service.history_repository is None:
            support_service.history_repository = self.mental_care_repository
        use_case = RunMentalCareCheckInHistoryQueryUseCase(
            support_service=support_service,
        )
        return MentalCareCheckInHistoryQueryWorkflow(use_case=use_case)

    def build_profile_memory_workflow(self) -> ProfileMemoryWorkflow:
        """Build the profile-memory typed workflow from the current assembly config."""
        cfg = self.config
        use_case = RunProfileMemoryFlowUseCase(
            aggregator=cfg.event_aggregator_factory(),
            decision_core=cfg.decision_core_factory(),
            memory_service=cfg.profile_memory_service_factory(self.profile_memory_repository),
            signal_bridge=cfg.runtime_signal_bridge_factory(),
            snapshot_store=self.snapshot_store,
        )
        use_case.configure_handlers()
        return ProfileMemoryWorkflow(
            use_case=use_case,
            report_service=cfg.feedback_report_service_factory(),
            message_transformer=self.apply_ingress_policy,
        )

    def build_profile_memory_query_workflow(self) -> ProfileMemoryQueryWorkflow:
        """Build the read-only profile-memory query workflow."""
        cfg = self.config
        use_case = RunProfileMemoryQueryUseCase(
            memory_service=cfg.profile_memory_service_factory(self.profile_memory_repository),
        )
        return ProfileMemoryQueryWorkflow(use_case=use_case)

    def build_user_interaction_workflow(self) -> UserInteractionWorkflow:
        """Build the minimal backend-only user interaction workflow."""
        return UserInteractionWorkflow(
            health_workflow=self.build_health_workflow(),
            daily_life_workflow=self.build_daily_life_workflow(),
            mental_care_workflow=self.build_mental_care_workflow(),
            profile_memory_workflow=self.build_profile_memory_workflow(),
            profile_memory_query_workflow=self.build_profile_memory_query_workflow(),
            intent_recognition_use_case=self.config.intent_recognition_use_case_factory(),
            intent_decomposition_use_case=self.config.intent_decomposition_use_case_factory(),
        )

    def _reporting_policy_source(self) -> str:
        """Describe where the active reporting policy came from."""
        return _boolean_policy_source(
            env_var_name="VITALAI_REPORTING_ENABLED",
            role_default_applies=self.runtime_role == "scheduler",
        )

    def _runtime_signals_policy_source(self) -> str:
        """Describe where the active runtime-signal policy came from."""
        return _boolean_policy_source(
            env_var_name="VITALAI_RUNTIME_SIGNALS_ENABLED",
            role_default_applies=self.runtime_role == "scheduler",
        )

    def _ingress_policy_source(self) -> str:
        """Describe where the active ingress policy came from."""
        if self.runtime_role in {"scheduler", "consumer"}:
            return "role_default"
        return "assembly_default"


def _env_to_bool(value: str | None, default: bool) -> bool:
    """Convert common environment-value strings to booleans."""
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized == "":
        return default
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _env_to_optional_str(value: str | None) -> str | None:
    """Return a stripped environment string when it is present."""
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _env_to_float(value: str | None, default: float) -> float:
    """Convert an environment string to float with a safe default."""
    if value is None:
        return default
    normalized = value.strip()
    if normalized == "":
        return default
    try:
        return float(normalized)
    except ValueError:
        return default


def _snapshot_store_factory_for_path(
    storage_path: str | None,
) -> Callable[[], SnapshotStore]:
    """Build the configured snapshot store factory."""
    if storage_path is None:
        return SnapshotStore
    return lambda: FileSnapshotStore(storage_path=storage_path)


def _intent_recognition_use_case_factory(
    *,
    mode: str,
    bert_model_path: str | None,
    bert_confidence_threshold: float,
    bert_label_map: dict[str, str] | str | None = None,
) -> Callable[[], RunUserIntentRecognitionUseCase]:
    """Build the configured intent-recognition use-case factory."""
    return lambda: build_intent_recognition_use_case(
        mode=mode,
        bert_model_path=bert_model_path,
        bert_confidence_threshold=bert_confidence_threshold,
        bert_label_map=bert_label_map,
    )


def _intent_decomposition_use_case_factory(
    *,
    mode: str,
) -> Callable[[], RunIntentDecompositionUseCase]:
    """Build the configured intent-decomposition use-case factory."""
    return lambda: build_intent_decomposition_use_case(mode=mode)


def _default_reporting_enabled_for_role(runtime_role: str) -> bool:
    """Return the default reporting policy for one runtime role."""
    return runtime_role != "scheduler"


def _default_runtime_signals_enabled_for_role(runtime_role: str) -> bool:
    """Return the default runtime-signal policy for one runtime role."""
    return runtime_role != "scheduler"


def _default_runtime_control_enabled_for_env(app_env: str) -> bool:
    """Return whether runtime control endpoints should be enabled by default."""
    return app_env.strip().lower() in {"development", "testing", "test"}


def _build_disabled_runtime_signal_bridge() -> RuntimeSignalBridge | None:
    """Return no bridge when runtime signal emission is disabled."""
    return None


def _boolean_policy_source(*, env_var_name: str, role_default_applies: bool) -> str:
    """Describe whether a boolean policy comes from assembly default, role default, or env."""
    value = os.getenv(env_var_name)
    if value is not None and value.strip() != "":
        return "environment_override"
    if role_default_applies:
        return "role_default"
    return "assembly_default"


def _latest_observation_by_kind(
    records: list[ObservationRecord],
    kind: ObservationKind,
) -> ObservationRecord | None:
    """Return the latest observation of one kind from a record list."""
    for record in reversed(records):
        if record.kind is kind:
            return record
    return None


def _observation_attribute_as_str(record: ObservationRecord | None, key: str) -> str | None:
    """Return one observation attribute as a string when available."""
    if record is None:
        return None
    value = record.attributes.get(key)
    return None if value is None else str(value)


def _observation_attribute_as_bool(record: ObservationRecord | None, key: str) -> bool | None:
    """Return one observation attribute as a bool when available."""
    if record is None:
        return None
    value = record.attributes.get(key)
    return value if isinstance(value, bool) else None


def _observation_attribute_as_int(record: ObservationRecord | None, key: str) -> int | None:
    """Return one observation attribute as an int when available."""
    if record is None:
        return None
    value = record.attributes.get(key)
    return value if isinstance(value, int) else None


def build_application_assembly(
    config: ApplicationAssemblyConfig | None = None,
) -> ApplicationAssembly:
    """Build an assembly object from lightweight configuration hooks."""
    return ApplicationAssembly(config=config or ApplicationAssemblyConfig())


def build_application_assembly_from_environment() -> ApplicationAssembly:
    """Build an assembly object from environment settings."""
    return ApplicationAssembly.from_environment()


def build_application_assembly_for_role(
    runtime_role: str,
    config: ApplicationAssemblyConfig | None = None,
) -> ApplicationAssembly:
    """Build an assembly object for one runtime role."""
    environment = ApplicationAssemblyEnvironment.from_environment(runtime_role=runtime_role)
    return ApplicationAssembly(
        config=config or environment.to_config(),
        environment=environment,
    )


def build_application_assembly_from_environment_for_role(
    runtime_role: str,
) -> ApplicationAssembly:
    """Build an assembly object for one runtime role from environment settings."""
    return ApplicationAssembly.from_environment(runtime_role=runtime_role)


def build_health_workflow(
    config: ApplicationAssemblyConfig | None = None,
) -> HealthAlertWorkflow:
    """Build the current health typed workflow from configurable dependencies."""
    return build_application_assembly(config=config).build_health_workflow()


def build_health_alert_history_query_workflow(
    config: ApplicationAssemblyConfig | None = None,
) -> HealthAlertHistoryQueryWorkflow:
    """Build the current health alert history query workflow."""
    return build_application_assembly(config=config).build_health_alert_history_query_workflow()


def build_daily_life_workflow(
    config: ApplicationAssemblyConfig | None = None,
) -> DailyLifeCheckInWorkflow:
    """Build the current daily-life typed workflow from configurable dependencies."""
    return build_application_assembly(config=config).build_daily_life_workflow()


def build_daily_life_checkin_history_query_workflow(
    config: ApplicationAssemblyConfig | None = None,
) -> DailyLifeCheckInHistoryQueryWorkflow:
    """Build the current daily-life history query workflow."""
    return build_application_assembly(config=config).build_daily_life_checkin_history_query_workflow()


def build_mental_care_workflow(
    config: ApplicationAssemblyConfig | None = None,
) -> MentalCareCheckInWorkflow:
    """Build the current mental-care typed workflow from configurable dependencies."""
    return build_application_assembly(config=config).build_mental_care_workflow()


def build_mental_care_checkin_history_query_workflow(
    config: ApplicationAssemblyConfig | None = None,
) -> MentalCareCheckInHistoryQueryWorkflow:
    """Build the current mental-care history query workflow."""
    return build_application_assembly(config=config).build_mental_care_checkin_history_query_workflow()


def build_profile_memory_workflow(
    config: ApplicationAssemblyConfig | None = None,
) -> ProfileMemoryWorkflow:
    """Build the current profile-memory typed workflow from configurable dependencies."""
    return build_application_assembly(config=config).build_profile_memory_workflow()


def build_profile_memory_query_workflow(
    config: ApplicationAssemblyConfig | None = None,
) -> ProfileMemoryQueryWorkflow:
    """Build the current profile-memory query workflow from configurable dependencies."""
    return build_application_assembly(config=config).build_profile_memory_query_workflow()


def build_user_interaction_workflow(
    config: ApplicationAssemblyConfig | None = None,
) -> UserInteractionWorkflow:
    """Build the current backend-only user interaction workflow."""
    return build_application_assembly(config=config).build_user_interaction_workflow()
