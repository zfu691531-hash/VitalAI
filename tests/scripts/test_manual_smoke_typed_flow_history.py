"""Tests for the local typed-flow history smoke script."""

from __future__ import annotations

import subprocess
from pathlib import Path
import shutil
import sys
import unittest
from uuid import uuid4

from scripts.manual_smoke_typed_flow_history import ROOT_DIR, _resolve_runtime_dir, format_text_report, run_manual_smoke


class ManualSmokeTypedFlowHistoryTests(unittest.TestCase):
    def test_relative_runtime_dir_resolves_under_project_root(self) -> None:
        runtime_dir = _resolve_runtime_dir(Path(".runtime") / "manual-smoke-local")

        self.assertEqual((ROOT_DIR / ".runtime" / "manual-smoke-local").resolve(), runtime_dir)

    def test_smoke_uses_temporary_databases_and_checks_all_flows(self) -> None:
        runtime_root = Path(".runtime")
        runtime_root.mkdir(exist_ok=True)
        runtime_dir = runtime_root / f"manual-smoke-test-{uuid4().hex}"
        default_database_paths = [
            runtime_root / "profile_memory.sqlite3",
            runtime_root / "health.sqlite3",
            runtime_root / "daily_life.sqlite3",
            runtime_root / "mental_care.sqlite3",
        ]
        before_stats = {
            path: None if not path.exists() else (path.stat().st_size, path.stat().st_mtime_ns)
            for path in default_database_paths
        }

        try:
            report = run_manual_smoke(runtime_dir)

            self.assertTrue(report["ok"])
            self.assertEqual(str(runtime_dir.resolve()), report["runtime_dir"])
            database_paths = report["database_paths"]
            for name in ("profile_memory", "health", "daily_life", "mental_care"):
                self.assertTrue(Path(database_paths[name]).exists())
                self.assertEqual(runtime_dir.resolve(), Path(database_paths[name]).parent)

            flows = report["flows"]
            self.assertEqual(["favorite_drink"], flows["profile_memory"]["memory_keys"])
            self.assertEqual(["high"], flows["health"]["recent_risk_levels"])
            self.assertEqual(["meal_support"], flows["daily_life"]["recent_needs"])
            self.assertEqual(["calm"], flows["mental_care"]["recent_mood_signals"])
        finally:
            shutil.rmtree(runtime_dir, ignore_errors=True)

        for path, before in before_stats.items():
            after = None if not path.exists() else (path.stat().st_size, path.stat().st_mtime_ns)
            self.assertEqual(before, after)

    def test_text_report_summarizes_all_flow_results(self) -> None:
        report = {
            "ok": True,
            "runtime_dir": "runtime-smoke",
            "flows": {
                "profile_memory": {
                    "ok": True,
                    "memory_count": 1,
                    "memory_keys": ["favorite_drink"],
                    "readable_summary": "1 profile memory entry: favorite_drink",
                },
                "health": {
                    "ok": True,
                    "alert_count": 1,
                    "recent_risk_levels": ["high"],
                    "readable_summary": "1 health alert: high",
                },
                "daily_life": {
                    "ok": True,
                    "checkin_count": 1,
                    "recent_needs": ["meal_support"],
                    "readable_summary": "1 daily-life check-in: meal_support",
                },
                "mental_care": {
                    "ok": True,
                    "checkin_count": 1,
                    "recent_mood_signals": ["calm"],
                    "recent_support_needs": ["companionship"],
                    "readable_summary": "1 mental-care check-in: calm",
                },
            },
        }

        text = format_text_report(report)

        self.assertIn("VitalAI typed-flow history smoke: OK", text)
        self.assertIn("profile_memory: OK memory_count=1 memory_keys=favorite_drink", text)
        self.assertIn("health: OK alert_count=1 recent_risk_levels=high", text)
        self.assertIn("daily_life: OK checkin_count=1 recent_needs=meal_support", text)
        self.assertIn(
            "mental_care: OK checkin_count=1 recent_mood_signals=calm recent_support_needs=companionship",
            text,
        )

    def test_cli_text_output_is_quiet_by_default(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/manual_smoke_typed_flow_history.py", "--output", "text"],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("VitalAI typed-flow history smoke: OK", completed.stdout)
        self.assertNotIn("日志系统初始化完成", completed.stdout)
        self.assertNotIn("表 profile_memory_records 不存在", completed.stdout)


if __name__ == "__main__":
    unittest.main()
