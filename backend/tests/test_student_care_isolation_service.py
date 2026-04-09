# -*- coding: utf-8 -*-
"""Tests for the standalone isolation Bayesian-network plugin."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from services import student_care_isolation_service as service


def test_build_student_isolation_analysis_payload_returns_standardized_fields(monkeypatch):
    profile = SimpleNamespace(
        emotion_score=0.58,
        social_score=0.44,
        safety_score=0.21,
        family_score=0.48,
        study_score=0.32,
        behavior_score=0.27,
    )
    signals = [
        SimpleNamespace(
            id=1,
            signal_type="graph_social_isolation",
            dimension="social",
            signal_text="关系图谱中暂未形成稳定同伴连接",
            signal_weight=0.18,
            source="graph",
        ),
        SimpleNamespace(
            id=2,
            signal_type="care_observation_social_observation",
            dimension="social",
            signal_text="社交观察：课间多次独处，缺少稳定同伴互动",
            signal_weight=0.35,
            source="care_observation",
        ),
        SimpleNamespace(
            id=3,
            signal_type="care_observation_care_talk",
            dimension="emotion",
            signal_text="关怀谈话中表示最近不想主动和同学交流",
            signal_weight=0.35,
            source="care_observation",
        ),
        SimpleNamespace(
            id=4,
            signal_type="family_contact_summary",
            dimension="family",
            signal_text="家校沟通显示家庭支持不足",
            signal_weight=0.28,
            source="family_contact",
        ),
    ]
    student = SimpleNamespace(id=7)

    monkeypatch.setattr(service, "_ensure_profile_and_signals", lambda db, current_student: (profile, signals))

    payload = service.build_student_isolation_analysis_payload(db=None, student=student)

    assert payload["student_id"] == 7
    assert payload["scene"] == "social_isolation"
    assert 0 <= payload["risk_probability"] <= 1
    assert 0 <= payload["confidence"] <= 1
    assert payload["root_causes"]
    assert payload["propagation_paths"]
    assert payload["evidence_summary"]["matched_signal_count"] >= 3
    assert payload["network_snapshot"]["inference_version"] == "isolation_bn_v1"


def test_build_student_isolation_analysis_payload_applies_protective_factor(monkeypatch):
    profile = SimpleNamespace(
        emotion_score=0.25,
        social_score=0.12,
        safety_score=0.1,
        family_score=0.14,
        study_score=0.2,
        behavior_score=0.1,
    )
    signals = [
        SimpleNamespace(
            id=1,
            signal_type="graph_social_isolation",
            dimension="social",
            signal_text="关系图谱中暂未形成稳定同伴连接",
            signal_weight=0.18,
            source="graph",
        ),
        SimpleNamespace(
            id=2,
            signal_type="graph_manual_student_peer_support",
            dimension="social",
            signal_text="手工图谱关系：与同伴存在同伴支持线索",
            signal_weight=-0.12,
            source="graph",
        ),
    ]
    student = SimpleNamespace(id=8)

    monkeypatch.setattr(service, "_ensure_profile_and_signals", lambda db, current_student: (profile, signals))

    payload = service.build_student_isolation_analysis_payload(db=None, student=student)

    assert payload["evidence_summary"]["protective_factor_count"] >= 1
    assert payload["evidence_summary"]["protective_factors"][0]["id"] == "peer_support"
    assert payload["risk_probability"] < 0.7


def test_build_student_isolation_analysis_payload_uses_agent_social_summary_and_review_status(monkeypatch):
    profile = SimpleNamespace(
        emotion_score=0.22,
        social_score=0.34,
        safety_score=0.1,
        family_score=0.16,
        study_score=0.2,
        behavior_score=0.1,
    )
    signals = [
        SimpleNamespace(
            id=1,
            signal_type="graph_social_isolation",
            dimension="social",
            signal_text="关系图谱中暂未形成稳定同伴连接",
            signal_weight=0.18,
            source="graph",
        ),
    ]
    student = SimpleNamespace(id=9)
    agent_context = {
        "has_agent_record": True,
        "social_summary": "智能研判提示该生近期在班级互动中较被动，课间多独处。",
        "social_evidence": ["课间多独处", "与同学互动偏少"],
        "social_risk_level": "medium",
        "resolution_status": "resolved",
        "teacher_notes": "班主任已完成安抚并安排同伴结对观察。",
        "review_status": "confirmed",
    }

    monkeypatch.setattr(service, "_ensure_profile_and_signals", lambda db, current_student: (profile, signals))
    monkeypatch.setattr(service, "_get_recent_agent_context", lambda db, student_id: agent_context)

    payload = service.build_student_isolation_analysis_payload(db=None, student=student)

    social_cause = next(item for item in payload["root_causes"] if item["node"] == "peer_disconnect")
    evidence_ids = [item["rule_id"] for item in social_cause["evidence"]]

    assert "agent_social_summary" in evidence_ids
    assert "teacher_confirmed_social_evidence" in evidence_ids
    assert payload["evidence_summary"]["protective_factor_count"] >= 1
    assert any(item["id"] == "teacher_review_resolved" for item in payload["evidence_summary"]["protective_factors"])
    assert payload["network_snapshot"]["agent_linked"] is True


def test_build_student_isolation_analysis_payload_recognizes_positive_observation_as_protective(monkeypatch):
    profile = SimpleNamespace(
        emotion_score=0.2,
        social_score=0.22,
        safety_score=0.08,
        family_score=0.1,
        study_score=0.2,
        behavior_score=0.1,
    )
    signals = [
        SimpleNamespace(
            id=1,
            signal_type="graph_social_isolation",
            dimension="social",
            signal_text="图谱提示近期同伴连接偏弱",
            signal_weight=0.18,
            source="graph",
        ),
        SimpleNamespace(
            id=2,
            signal_type="care_observation_positive_social_observation",
            dimension="social",
            signal_text="近期愿意主动参与班级活动，与同学互动明显好转",
            signal_weight=-0.18,
            source="care_observation",
        ),
    ]
    student = SimpleNamespace(id=10)

    monkeypatch.setattr(service, "_ensure_profile_and_signals", lambda db, current_student: (profile, signals))

    payload = service.build_student_isolation_analysis_payload(db=None, student=student)

    protective_ids = [item["id"] for item in payload["evidence_summary"]["protective_factors"]]
    assert "positive_social_observation" in protective_ids


def test_build_student_isolation_analysis_payload_returns_social_coverage_and_missing_items(monkeypatch):
    profile = SimpleNamespace(
        emotion_score=0.22,
        social_score=0.34,
        safety_score=0.1,
        family_score=0.16,
        study_score=0.2,
        behavior_score=0.1,
    )
    signals = [
        SimpleNamespace(
            id=1,
            signal_type="graph_social_isolation",
            dimension="social",
            signal_text="关系图谱显示近期同伴连接偏弱",
            signal_weight=0.18,
            source="graph",
        ),
        SimpleNamespace(
            id=2,
            signal_type="care_observation_social_observation",
            dimension="social",
            signal_text="课间互动偏少，活动参与被动",
            signal_weight=0.3,
            source="care_observation",
        ),
    ]
    student = SimpleNamespace(id=11)
    agent_context = {
        "has_agent_record": True,
        "social_summary": "老师确认近期班级互动偏被动",
        "social_evidence": [],
        "social_risk_level": "attention",
        "resolution_status": "",
        "teacher_notes": "",
        "review_status": "confirmed",
    }

    monkeypatch.setattr(service, "_ensure_profile_and_signals", lambda db, current_student: (profile, signals))
    monkeypatch.setattr(service, "_get_recent_agent_context", lambda db, student_id: agent_context)

    payload = service.build_student_isolation_analysis_payload(db=None, student=student)

    coverage = payload["evidence_summary"]["social_data_coverage"]
    missing_ids = [item["id"] for item in coverage["missing_items"]]

    assert coverage["covered_count"] == 3
    assert coverage["required_count"] == 5
    assert coverage["evidence_sufficient"] is True
    assert "teacher_confirmed_social_evidence" in missing_ids
    assert "assistant_social_signal" in missing_ids
    missing_item = next(item for item in coverage["missing_items"] if item["id"] == "teacher_confirmed_social_evidence")
    assert "复核弹窗" in missing_item["action_hint"]


def test_build_student_isolation_analysis_payload_uses_assistant_social_signal(monkeypatch):
    profile = SimpleNamespace(
        emotion_score=0.24,
        social_score=0.31,
        safety_score=0.1,
        family_score=0.12,
        study_score=0.2,
        behavior_score=0.1,
    )
    signals = [
        SimpleNamespace(
            id=1,
            signal_type="assistant_signal",
            dimension="social",
            signal_text="AI 摘要提示近期经常回避同伴互动",
            signal_weight=0.28,
            source="assistant_summary",
        ),
    ]
    student = SimpleNamespace(id=12)

    monkeypatch.setattr(service, "_ensure_profile_and_signals", lambda db, current_student: (profile, signals))
    monkeypatch.setattr(service, "_get_recent_agent_context", lambda db, student_id: {
        "has_agent_record": False,
        "social_summary": "",
        "social_evidence": [],
        "social_risk_level": "",
        "resolution_status": "",
        "teacher_notes": "",
    })

    payload = service.build_student_isolation_analysis_payload(db=None, student=student)
    social_cause = next(item for item in payload["root_causes"] if item["node"] == "peer_disconnect")
    evidence_ids = [item["rule_id"] for item in social_cause["evidence"]]

    assert "assistant_social_signal" in evidence_ids


def test_build_student_isolation_analysis_payload_returns_worsening_social_trend(monkeypatch):
    profile = SimpleNamespace(
        emotion_score=0.3,
        social_score=0.42,
        safety_score=0.1,
        family_score=0.12,
        study_score=0.2,
        behavior_score=0.1,
    )
    now = datetime.now(timezone.utc)
    signals = [
        SimpleNamespace(
            id=1,
            signal_type="care_observation_social_observation",
            dimension="social",
            signal_text="近期与同学互动明显减少",
            signal_weight=0.26,
            source="care_observation",
            created_at=now - timedelta(days=3),
        ),
        SimpleNamespace(
            id=2,
            signal_type="graph_social_isolation",
            dimension="social",
            signal_text="早前仅提示同伴连接偏弱",
            signal_weight=0.08,
            source="graph",
            created_at=now - timedelta(days=30),
        ),
    ]
    student = SimpleNamespace(id=13)

    monkeypatch.setattr(service, "_ensure_profile_and_signals", lambda db, current_student: (profile, signals))
    monkeypatch.setattr(service, "_get_recent_agent_context", lambda db, student_id: {
        "has_agent_record": False,
        "social_summary": "",
        "social_evidence": [],
        "social_risk_level": "",
        "resolution_status": "",
        "teacher_notes": "",
    })

    payload = service.build_student_isolation_analysis_payload(db=None, student=student)

    assert payload["evidence_summary"]["social_trend"]["direction"] == "worsening"


def test_build_student_isolation_analysis_payload_returns_improving_social_trend(monkeypatch):
    profile = SimpleNamespace(
        emotion_score=0.18,
        social_score=0.22,
        safety_score=0.08,
        family_score=0.1,
        study_score=0.2,
        behavior_score=0.1,
    )
    now = datetime.now(timezone.utc)
    signals = [
        SimpleNamespace(
            id=1,
            signal_type="care_observation_positive_social_observation",
            dimension="social",
            signal_text="近期愿意主动参与活动，与同学互动改善",
            signal_weight=-0.18,
            source="care_observation",
            created_at=now - timedelta(days=2),
        ),
        SimpleNamespace(
            id=2,
            signal_type="graph_social_isolation",
            dimension="social",
            signal_text="早前图谱提示同伴连接偏弱",
            signal_weight=0.1,
            source="graph",
            created_at=now - timedelta(days=35),
        ),
    ]
    student = SimpleNamespace(id=14)

    monkeypatch.setattr(service, "_ensure_profile_and_signals", lambda db, current_student: (profile, signals))
    monkeypatch.setattr(service, "_get_recent_agent_context", lambda db, student_id: {
        "has_agent_record": False,
        "social_summary": "",
        "social_evidence": [],
        "social_risk_level": "",
        "resolution_status": "",
        "teacher_notes": "",
    })

    payload = service.build_student_isolation_analysis_payload(db=None, student=student)

    assert payload["evidence_summary"]["social_trend"]["direction"] == "improving"


def test_build_student_isolation_analysis_payload_returns_evidence_source_groups(monkeypatch):
    profile = SimpleNamespace(
        emotion_score=0.22,
        social_score=0.34,
        safety_score=0.1,
        family_score=0.16,
        study_score=0.2,
        behavior_score=0.1,
    )
    signals = [
        SimpleNamespace(
            id=1,
            signal_type="graph_social_isolation",
            dimension="social",
            signal_text="图谱显示近期同伴连接偏弱",
            signal_weight=0.18,
            source="graph",
        ),
        SimpleNamespace(
            id=2,
            signal_type="assistant_signal",
            dimension="social",
            signal_text="AI 摘要提示近期回避同伴互动",
            signal_weight=0.22,
            source="assistant_summary",
        ),
    ]
    student = SimpleNamespace(id=15)
    agent_context = {
        "has_agent_record": True,
        "social_summary": "老师确认近期班级互动偏被动。",
        "social_evidence": ["课间多独处"],
        "social_risk_level": "medium",
        "resolution_status": "",
        "teacher_notes": "",
        "review_status": "confirmed",
    }

    monkeypatch.setattr(service, "_ensure_profile_and_signals", lambda db, current_student: (profile, signals))
    monkeypatch.setattr(service, "_get_recent_agent_context", lambda db, student_id: agent_context)

    payload = service.build_student_isolation_analysis_payload(db=None, student=student)

    groups = {item["id"]: item for item in payload["evidence_summary"]["evidence_source_groups"]}
    assert "fact" in groups
    assert "teacher_feedback" in groups
    assert "ai_signal" in groups
