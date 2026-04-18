"""Run a local smoke check for the current typed-flow history loops."""

from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext, redirect_stderr, redirect_stdout
from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import shutil
import sys
from typing import TYPE_CHECKING, Any, Callable, Iterator
from uuid import uuid4

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if TYPE_CHECKING:
    from VitalAI.application import ApplicationAssembly


@dataclass(frozen=True)
class _ApplicationApi:
    build_application_assembly_from_environment_for_role: Callable[[str], Any]
    DailyLifeCheckInCommand: type[Any]
    DailyLifeCheckInHistoryQuery: type[Any]
    HealthAlertCommand: type[Any]
    HealthAlertHistoryQuery: type[Any]
    MentalCareCheckInCommand: type[Any]
    MentalCareCheckInHistoryQuery: type[Any]
    ProfileMemorySnapshotQuery: type[Any]
    ProfileMemoryUpdateCommand: type[Any]


_APPLICATION_API: _ApplicationApi | None = None
_NULL_STREAM = open(os.devnull, "w", encoding="utf-8")


def run_manual_smoke(
    runtime_dir: Path,
    *,
    suppress_console_logs: bool = True,
) -> dict[str, object]:
    """Run four write-then-read loops against temporary SQLite paths."""
    resolved_runtime_dir = _resolve_runtime_dir(runtime_dir)
    resolved_runtime_dir.mkdir(parents=True, exist_ok=True)

    database_paths = {
        "profile_memory": resolved_runtime_dir / "profile_memory.sqlite3",
        "health": resolved_runtime_dir / "health.sqlite3",
        "daily_life": resolved_runtime_dir / "daily_life.sqlite3",
        "mental_care": resolved_runtime_dir / "mental_care.sqlite3",
        "runtime_snapshots": resolved_runtime_dir / "runtime_snapshots.json",
    }
    env_overrides = {
        "VITALAI_PROFILE_MEMORY_DB_PATH": str(database_paths["profile_memory"]),
        "VITALAI_HEALTH_DB_PATH": str(database_paths["health"]),
        "VITALAI_DAILY_LIFE_DB_PATH": str(database_paths["daily_life"]),
        "VITALAI_MENTAL_CARE_DB_PATH": str(database_paths["mental_care"]),
        "VITALAI_RUNTIME_SNAPSHOT_STORE_PATH": str(database_paths["runtime_snapshots"]),
    }

    with _temporary_environment(env_overrides):
        api = _load_application_api(suppress_console_logs=suppress_console_logs)
        assembly = api.build_application_assembly_from_environment_for_role("api")

        profile_report = _smoke_profile_memory(assembly, api)
        health_report = _smoke_health(assembly, api)
        daily_life_report = _smoke_daily_life(assembly, api)
        mental_care_report = _smoke_mental_care(assembly, api)

    flows = {
        "profile_memory": profile_report,
        "health": health_report,
        "daily_life": daily_life_report,
        "mental_care": mental_care_report,
    }
    return {
        "ok": all(bool(report["ok"]) for report in flows.values()),
        "runtime_dir": str(resolved_runtime_dir),
        "database_paths": {name: str(path) for name, path in database_paths.items()},
        "flows": flows,
    }


def _load_application_api(*, suppress_console_logs: bool) -> _ApplicationApi:
    global _APPLICATION_API

    if _APPLICATION_API is None:
        import_context = _suppressed_console_streams() if suppress_console_logs else nullcontext()
        with import_context:
            from VitalAI.application import (
                DailyLifeCheckInCommand,
                DailyLifeCheckInHistoryQuery,
                HealthAlertCommand,
                HealthAlertHistoryQuery,
                MentalCareCheckInCommand,
                MentalCareCheckInHistoryQuery,
                ProfileMemorySnapshotQuery,
                ProfileMemoryUpdateCommand,
                build_application_assembly_from_environment_for_role,
            )

        _APPLICATION_API = _ApplicationApi(
            build_application_assembly_from_environment_for_role=build_application_assembly_from_environment_for_role,
            DailyLifeCheckInCommand=DailyLifeCheckInCommand,
            DailyLifeCheckInHistoryQuery=DailyLifeCheckInHistoryQuery,
            HealthAlertCommand=HealthAlertCommand,
            HealthAlertHistoryQuery=HealthAlertHistoryQuery,
            MentalCareCheckInCommand=MentalCareCheckInCommand,
            MentalCareCheckInHistoryQuery=MentalCareCheckInHistoryQuery,
            ProfileMemorySnapshotQuery=ProfileMemorySnapshotQuery,
            ProfileMemoryUpdateCommand=ProfileMemoryUpdateCommand,
        )

    _set_console_logging_enabled(enabled=not suppress_console_logs)
    return _APPLICATION_API


@contextmanager
def _suppressed_console_streams() -> Iterator[None]:
    """Hide startup noise while the application logging stack is initialized."""
    with redirect_stdout(_NULL_STREAM), redirect_stderr(_NULL_STREAM):
        yield


def _set_console_logging_enabled(*, enabled: bool) -> None:
    """Route the root console handler to stdout or to a null sink."""
    target_stream = sys.stdout if enabled else _NULL_STREAM
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if handler.__class__ is logging.StreamHandler:
            handler.setStream(target_stream)


def _smoke_profile_memory(assembly: "ApplicationAssembly", api: _ApplicationApi) -> dict[str, object]:
    write = assembly.build_profile_memory_workflow().run(
        api.ProfileMemoryUpdateCommand(
            source_agent="manual-smoke-profile",
            trace_id="trace-manual-smoke-profile-write",
            user_id="elder-smoke-profile-001",
            memory_key="favorite_drink",
            memory_value="ginger_tea",
        )
    )
    read = assembly.build_profile_memory_query_workflow().run(
        api.ProfileMemorySnapshotQuery(
            source_agent="manual-smoke-profile",
            trace_id="trace-manual-smoke-profile-read",
            user_id="elder-smoke-profile-001",
            memory_key="favorite_drink",
        )
    )
    snapshot = read.query_result.outcome.profile_snapshot
    ok = (
        write.flow_result.accepted
        and read.query_result.accepted
        and snapshot.memory_count == 1
        and snapshot.entries[0].memory_key == "favorite_drink"
        and snapshot.entries[0].memory_value == "ginger_tea"
    )
    return {
        "ok": ok,
        "write_accepted": write.flow_result.accepted,
        "read_accepted": read.query_result.accepted,
        "memory_count": snapshot.memory_count,
        "memory_keys": snapshot.memory_keys,
        "readable_summary": snapshot.readable_summary,
    }


def _smoke_health(assembly: "ApplicationAssembly", api: _ApplicationApi) -> dict[str, object]:
    write = assembly.build_health_workflow().run(
        api.HealthAlertCommand(
            source_agent="manual-smoke-health",
            trace_id="trace-manual-smoke-health-write",
            user_id="elder-smoke-health-001",
            risk_level="high",
        )
    )
    read = assembly.build_health_alert_history_query_workflow().run(
        api.HealthAlertHistoryQuery(
            source_agent="manual-smoke-health",
            trace_id="trace-manual-smoke-health-read",
            user_id="elder-smoke-health-001",
            limit=10,
        )
    )
    snapshot = read.query_result.snapshot
    ok = (
        write.flow_result.accepted
        and read.query_result.accepted
        and snapshot.alert_count == 1
        and snapshot.recent_risk_levels == ["high"]
    )
    return {
        "ok": ok,
        "write_accepted": write.flow_result.accepted,
        "read_accepted": read.query_result.accepted,
        "alert_count": snapshot.alert_count,
        "recent_risk_levels": snapshot.recent_risk_levels,
        "readable_summary": snapshot.readable_summary,
    }


def _smoke_daily_life(assembly: "ApplicationAssembly", api: _ApplicationApi) -> dict[str, object]:
    write = assembly.build_daily_life_workflow().run(
        api.DailyLifeCheckInCommand(
            source_agent="manual-smoke-daily-life",
            trace_id="trace-manual-smoke-daily-life-write",
            user_id="elder-smoke-daily-001",
            need="meal_support",
            urgency="normal",
        )
    )
    read = assembly.build_daily_life_checkin_history_query_workflow().run(
        api.DailyLifeCheckInHistoryQuery(
            source_agent="manual-smoke-daily-life",
            trace_id="trace-manual-smoke-daily-life-read",
            user_id="elder-smoke-daily-001",
            limit=10,
        )
    )
    snapshot = read.query_result.snapshot
    ok = (
        write.flow_result.accepted
        and read.query_result.accepted
        and snapshot.checkin_count == 1
        and snapshot.recent_needs == ["meal_support"]
    )
    return {
        "ok": ok,
        "write_accepted": write.flow_result.accepted,
        "read_accepted": read.query_result.accepted,
        "checkin_count": snapshot.checkin_count,
        "recent_needs": snapshot.recent_needs,
        "readable_summary": snapshot.readable_summary,
    }


def _smoke_mental_care(assembly: "ApplicationAssembly", api: _ApplicationApi) -> dict[str, object]:
    write = assembly.build_mental_care_workflow().run(
        api.MentalCareCheckInCommand(
            source_agent="manual-smoke-mental-care",
            trace_id="trace-manual-smoke-mental-care-write",
            user_id="elder-smoke-mental-001",
            mood_signal="calm",
            support_need="companionship",
        )
    )
    read = assembly.build_mental_care_checkin_history_query_workflow().run(
        api.MentalCareCheckInHistoryQuery(
            source_agent="manual-smoke-mental-care",
            trace_id="trace-manual-smoke-mental-care-read",
            user_id="elder-smoke-mental-001",
            limit=10,
        )
    )
    snapshot = read.query_result.snapshot
    ok = (
        write.flow_result.accepted
        and read.query_result.accepted
        and snapshot.checkin_count == 1
        and snapshot.recent_mood_signals == ["calm"]
        and snapshot.recent_support_needs == ["companionship"]
    )
    return {
        "ok": ok,
        "write_accepted": write.flow_result.accepted,
        "read_accepted": read.query_result.accepted,
        "checkin_count": snapshot.checkin_count,
        "recent_mood_signals": snapshot.recent_mood_signals,
        "recent_support_needs": snapshot.recent_support_needs,
        "readable_summary": snapshot.readable_summary,
    }


@contextmanager
def _temporary_environment(overrides: dict[str, str]) -> Iterator[None]:
    """Temporarily override environment variables used by the smoke check."""
    previous = {key: os.environ.get(key) for key in overrides}
    os.environ.update(overrides)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _resolve_runtime_dir(runtime_dir: Path) -> Path:
    """Resolve smoke runtime paths relative to the project root."""
    resolved_runtime_dir = runtime_dir.expanduser()
    if not resolved_runtime_dir.is_absolute():
        resolved_runtime_dir = (ROOT_DIR / resolved_runtime_dir).resolve()
    return resolved_runtime_dir


def format_text_report(report: dict[str, object]) -> str:
    """Build a compact human-readable report for manual smoke checks."""
    flows = report["flows"]
    assert isinstance(flows, dict)

    lines = [
        f"VitalAI typed-flow history smoke: {_status(bool(report['ok']))}",
        f"runtime_dir: {report['runtime_dir']}",
    ]
    lines.extend(
        [
            _format_profile_memory_line(flows["profile_memory"]),
            _format_health_line(flows["health"]),
            _format_daily_life_line(flows["daily_life"]),
            _format_mental_care_line(flows["mental_care"]),
        ]
    )
    return "\n".join(lines)


def _format_profile_memory_line(flow: object) -> str:
    report = _as_report(flow)
    return (
        f"profile_memory: {_status(bool(report['ok']))} "
        f"memory_count={report['memory_count']} "
        f"memory_keys={_join_values(report['memory_keys'])} "
        f"summary={report['readable_summary']}"
    )


def _format_health_line(flow: object) -> str:
    report = _as_report(flow)
    return (
        f"health: {_status(bool(report['ok']))} "
        f"alert_count={report['alert_count']} "
        f"recent_risk_levels={_join_values(report['recent_risk_levels'])} "
        f"summary={report['readable_summary']}"
    )


def _format_daily_life_line(flow: object) -> str:
    report = _as_report(flow)
    return (
        f"daily_life: {_status(bool(report['ok']))} "
        f"checkin_count={report['checkin_count']} "
        f"recent_needs={_join_values(report['recent_needs'])} "
        f"summary={report['readable_summary']}"
    )


def _format_mental_care_line(flow: object) -> str:
    report = _as_report(flow)
    return (
        f"mental_care: {_status(bool(report['ok']))} "
        f"checkin_count={report['checkin_count']} "
        f"recent_mood_signals={_join_values(report['recent_mood_signals'])} "
        f"recent_support_needs={_join_values(report['recent_support_needs'])} "
        f"summary={report['readable_summary']}"
    )


def _as_report(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"Expected smoke flow report dict, got {type(value).__name__}")
    return value


def _join_values(value: object) -> str:
    if not isinstance(value, list):
        return str(value)
    return ",".join(str(item) for item in value)


def _status(ok: bool) -> str:
    return "OK" if ok else "FAILED"


def main() -> int:
    """Run the smoke check from the command line."""
    parser = argparse.ArgumentParser(
        description="Smoke-check profile, health, daily-life, and mental-care history loops."
    )
    parser.add_argument(
        "--runtime-dir",
        default=None,
        help="Optional temporary runtime directory. Defaults to .runtime/manual-smoke-*.",
    )
    parser.add_argument(
        "--keep-runtime",
        action="store_true",
        help="Keep the generated runtime directory for manual inspection.",
    )
    parser.add_argument(
        "--output",
        choices=("json", "text"),
        default="json",
        help="Report format. Defaults to json for automation; text is easier for manual checks.",
    )
    parser.add_argument(
        "--verbose-logs",
        action="store_true",
        help="Show application initialization and repository logs during the smoke run.",
    )
    args = parser.parse_args()

    cleanup_path: Path | None = None
    if args.runtime_dir:
        runtime_dir = Path(args.runtime_dir)
    else:
        base_runtime_dir = ROOT_DIR / ".runtime"
        base_runtime_dir.mkdir(exist_ok=True)
        runtime_dir = base_runtime_dir / f"manual-smoke-{uuid4().hex}"
        runtime_dir.mkdir()
        if not args.keep_runtime:
            cleanup_path = runtime_dir

    try:
        report = run_manual_smoke(runtime_dir, suppress_console_logs=not args.verbose_logs)
        if args.output == "text":
            print(format_text_report(report))
        else:
            print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if bool(report["ok"]) else 1
    finally:
        if cleanup_path is not None:
            shutil.rmtree(cleanup_path, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
