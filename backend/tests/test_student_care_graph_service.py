# -*- coding: utf-8 -*-
"""Tests for graph service."""

from services.student_care_graph_service import StudentCareGraphService


def test_graph_service_disabled_returns_empty_health():
    service = StudentCareGraphService(enabled=False)
    assert service.healthcheck() == {"enabled": False, "connected": False}


def test_graph_service_builds_signals_from_query_results(monkeypatch):
    service = StudentCareGraphService(enabled=True, driver=object())

    def fake_run_query(query, parameters=None):
        if "peer_count" in query and "e.dimension = 'safety'" not in query:
            return [{"peer_count": 0}]
        if "e.dimension = 'safety'" in query:
            return [{"event_count": 3, "peer_count": 2}]
        return [{"ok": 1}]

    monkeypatch.setattr(service, "_run_query", fake_run_query)

    student = type("Student", (), {"id": 1, "class_id": 1})()
    signals = service._derive_signals(student)

    signal_types = {item["signal_type"] for item in signals}
    assert "graph_social_isolation" in signal_types
    assert "graph_conflict_cooccurrence" in signal_types


def test_graph_service_builds_graph_view_from_payload(monkeypatch):
    service = StudentCareGraphService(enabled=True, driver=object())

    monkeypatch.setattr(
        service,
        "build_student_graph_payload",
        lambda db, student_id, include_classmates=True, include_peer_events=True: {
            "students": [
                {
                    "id": 17,
                    "student_no": "20240017",
                    "name": "唐子墨",
                    "grade": "高一",
                    "class_id": 1,
                    "class_name": "高一1班",
                },
                {
                    "id": 2,
                    "student_no": "20240002",
                    "name": "王小红",
                    "grade": "高一",
                    "class_id": 1,
                    "class_name": "高一1班",
                },
            ],
            "events": [
                {
                    "id": 5,
                    "student_id": 17,
                    "event_type": "conflict",
                    "event_level": "medium",
                    "event_desc": "测试冲突事件",
                    "occurred_at": "2026-04-09T10:00:00",
                    "dimension": "safety",
                }
            ],
        },
    )

    view = service.get_student_graph_view(object(), 17)

    assert view["student_id"] == 17
    assert view["stats"]["student_count"] == 2
    assert view["stats"]["peer_count"] == 1
    assert view["stats"]["event_count"] == 1
    node_types = {item["type"] for item in view["nodes"]}
    edge_types = {item["type"] for item in view["edges"]}
    assert {"student", "class", "classmate", "event"}.issubset(node_types)
    assert {"same_class", "in_class", "involved_in"}.issubset(edge_types)


def test_graph_service_sync_cleans_stale_events_and_manual_relations(monkeypatch):
    service = StudentCareGraphService(enabled=True, driver=object())
    queries = []

    monkeypatch.setattr(
        service,
        "build_student_graph_payload",
        lambda db, student_id, include_classmates=True, include_peer_events=True: {
            "students": [
                {"id": 17, "student_no": "20240017", "name": "唐子墨", "grade": "高一", "class_id": 1, "class_name": "高一1班"},
                {"id": 2, "student_no": "20240002", "name": "王小红", "grade": "高一", "class_id": 1, "class_name": "高一1班"},
            ],
            "events": [],
            "manual_relations": [],
        },
    )

    def fake_run_query(query, parameters=None):
        queries.append((query, parameters or {}))
        if "RETURN DISTINCT e.id AS id" in query:
            return [{"id": 5}, {"id": 6}]
        if "RETURN DISTINCT r.relation_id AS relation_id" in query:
            return [{"relation_id": 11}, {"relation_id": 12}]
        return []

    monkeypatch.setattr(service, "_run_query", fake_run_query)

    service.sync_student_subgraph(object(), 17, include_classmates=True)

    assert any(
        "DELETE r" in query and params.get("event_ids") == [5, 6]
        for query, params in queries
    )
    assert any(
        "DETACH DELETE e" in query and params.get("event_ids") == [5, 6]
        for query, params in queries
    )
    assert any(
        "DELETE r" in query and params.get("relation_ids") == [11, 12]
        for query, params in queries
    )
    assert any(
        "DETACH DELETE e" in query and params.get("relation_ids") == [11, 12]
        for query, params in queries
    )
