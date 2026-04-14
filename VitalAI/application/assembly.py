"""Lightweight application assembly for the current typed flows."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
import os
from typing import Callable

from VitalAI.application.commands import HealthAlertCommand
from VitalAI.application.use_cases.daily_life_checkin_flow import RunDailyLifeCheckInFlowUseCase
from VitalAI.application.use_cases.health_alert_flow import RunHealthAlertFlowUseCase
from VitalAI.application.use_cases.mental_care_checkin_flow import RunMentalCareCheckInFlowUseCase
from VitalAI.application.use_cases.runtime_signal_views import RuntimeSignalView, build_runtime_signal_views
from VitalAI.application.workflows.daily_life_checkin_workflow import DailyLifeCheckInWorkflow
from VitalAI.application.workflows.health_alert_workflow import HealthAlertWorkflow
from VitalAI.application.workflows.mental_care_checkin_workflow import MentalCareCheckInWorkflow
from VitalAI.domains.daily_life import DailyLifeCheckInSupportService
from VitalAI.domains.health import HealthAlertTriageService
from VitalAI.domains.mental_care import MentalCareCheckInSupportService
from VitalAI.domains.reporting import FeedbackReportService, NoOpFeedbackReportService
from VitalAI.platform.interrupt import InterruptAction, InterruptPriority, InterruptSignal, SnapshotReference
from VitalAI.platform.messaging import MessageEnvelope
from VitalAI.platform.observability import ObservationKind, ObservationRecord, ObservabilityCollector
from VitalAI.platform.runtime import (
    DecisionCore,
    EventAggregator,
    FailoverCoordinator,
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
    health_triage_service_factory: Callable[[], HealthAlertTriageService] = HealthAlertTriageService
    daily_life_support_service_factory: Callable[[], DailyLifeCheckInSupportService] = (
        DailyLifeCheckInSupportService
    )
    mental_care_support_service_factory: Callable[[], MentalCareCheckInSupportService] = (
        MentalCareCheckInSupportService
    )
    feedback_report_service_factory: Callable[[], FeedbackReportService] = FeedbackReportService
    runtime_signal_bridge_factory: Callable[[], RuntimeSignalBridge | None] = _build_runtime_signal_bridge


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

    @classmethod
    def from_environment(
        cls,
        runtime_role: str | None = None,
    ) -> "ApplicationAssemblyEnvironment":
        """Load assembly-relevant settings from process environment."""
        resolved_runtime_role = runtime_role or os.getenv("VITALAI_RUNTIME_ROLE", "default")
        return cls(
            app_env=os.getenv("APP_ENV", "development"),
            runtime_role=resolved_runtime_role,
            reporting_enabled=_env_to_bool(
                os.getenv("VITALAI_REPORTING_ENABLED"),
                default=_default_reporting_enabled_for_role(resolved_runtime_role),
            ),
            runtime_signals_enabled=_env_to_bool(
                os.getenv("VITALAI_RUNTIME_SIGNALS_ENABLED"),
                default=_default_runtime_signals_enabled_for_role(resolved_runtime_role),
            ),
        )

    def to_config(self) -> ApplicationAssemblyConfig:
        """Convert environment choices into the existing assembly hooks."""
        report_factory: Callable[[], FeedbackReportService] = FeedbackReportService
        if not self.reporting_enabled:
            report_factory = NoOpFeedbackReportService

        return ApplicationAssemblyConfig(
            feedback_report_service_factory=report_factory,
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
        snapshot = SnapshotStore().save(
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
        use_case = RunHealthAlertFlowUseCase(
            aggregator=cfg.event_aggregator_factory(),
            decision_core=cfg.decision_core_factory(),
            triage_service=cfg.health_triage_service_factory(),
            signal_bridge=cfg.runtime_signal_bridge_factory(),
        )
        use_case.configure_handlers()
        return HealthAlertWorkflow(
            use_case=use_case,
            report_service=cfg.feedback_report_service_factory(),
            message_transformer=self.apply_ingress_policy,
        )

    def build_daily_life_workflow(self) -> DailyLifeCheckInWorkflow:
        """Build the daily-life typed workflow from the current assembly config."""
        cfg = self.config
        use_case = RunDailyLifeCheckInFlowUseCase(
            aggregator=cfg.event_aggregator_factory(),
            decision_core=cfg.decision_core_factory(),
            support_service=cfg.daily_life_support_service_factory(),
            signal_bridge=cfg.runtime_signal_bridge_factory(),
        )
        use_case.configure_handlers()
        return DailyLifeCheckInWorkflow(
            use_case=use_case,
            report_service=cfg.feedback_report_service_factory(),
            message_transformer=self.apply_ingress_policy,
        )

    def build_mental_care_workflow(self) -> MentalCareCheckInWorkflow:
        """Build the mental-care typed workflow from the current assembly config."""
        cfg = self.config
        use_case = RunMentalCareCheckInFlowUseCase(
            aggregator=cfg.event_aggregator_factory(),
            decision_core=cfg.decision_core_factory(),
            support_service=cfg.mental_care_support_service_factory(),
            signal_bridge=cfg.runtime_signal_bridge_factory(),
        )
        use_case.configure_handlers()
        return MentalCareCheckInWorkflow(
            use_case=use_case,
            report_service=cfg.feedback_report_service_factory(),
            message_transformer=self.apply_ingress_policy,
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


def _default_reporting_enabled_for_role(runtime_role: str) -> bool:
    """Return the default reporting policy for one runtime role."""
    return runtime_role != "scheduler"


def _default_runtime_signals_enabled_for_role(runtime_role: str) -> bool:
    """Return the default runtime-signal policy for one runtime role."""
    return runtime_role != "scheduler"


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


def build_daily_life_workflow(
    config: ApplicationAssemblyConfig | None = None,
) -> DailyLifeCheckInWorkflow:
    """Build the current daily-life typed workflow from configurable dependencies."""
    return build_application_assembly(config=config).build_daily_life_workflow()


def build_mental_care_workflow(
    config: ApplicationAssemblyConfig | None = None,
) -> MentalCareCheckInWorkflow:
    """Build the current mental-care typed workflow from configurable dependencies."""
    return build_application_assembly(config=config).build_mental_care_workflow()
