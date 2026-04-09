# -*- coding: utf-8 -*-
"""Graph-enhanced signals and view data for student care."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from neo4j import GraphDatabase
from sqlalchemy import case
from sqlalchemy.orm import Session

from core.config import settings
from database.models.class_ import Class
from database.models.student import Student
from database.models.student_behavior_event import StudentBehaviorEvent
from database.models.student_care_graph_relation import StudentCareGraphRelation


SAFETY_EVENT_TYPES = {"conflict", "bullying", "threat", "dorm_conflict", "cyber_conflict"}
EVENT_TYPE_LABELS = {
    "conflict": "冲突事件",
    "bullying": "欺凌事件",
    "threat": "威胁事件",
    "dorm_conflict": "宿舍冲突",
    "cyber_conflict": "网络冲突",
    "discipline": "纪律事件",
}

MANUAL_RELATION_LABELS = {
    "peer_support": "同伴支持",
    "conflict": "冲突关系",
    "bullying_link": "欺凌关联",
    "shared_activity": "共同活动",
    "concern": "重点关注",
}


class StudentCareGraphService:
    """Syncs lightweight student-care graph data and derives graph signals."""

    def __init__(
        self,
        enabled: bool | None = None,
        uri: str | None = None,
        username: str | None = None,
        password: str | None = None,
        database: str | None = None,
        driver: Any | None = None,
    ) -> None:
        self.enabled = settings.NEO4J_ENABLED if enabled is None else enabled
        self.uri = settings.NEO4J_URI if uri is None else uri
        self.username = settings.NEO4J_USERNAME if username is None else username
        self.password = settings.NEO4J_PASSWORD if password is None else password
        self.database = settings.NEO4J_DATABASE if database is None else database
        self.driver = driver
        if self.enabled and self.driver is None and self.password:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))

    def healthcheck(self) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "connected": False}
        if not self.driver:
            return {"enabled": True, "connected": False, "reason": "driver_unavailable"}
        try:
            records = self._run_query("RETURN 1 AS ok")
            return {"enabled": True, "connected": bool(records and records[0].get("ok") == 1)}
        except Exception as exc:  # pragma: no cover - defensive
            return {"enabled": True, "connected": False, "reason": str(exc)}

    def build_graph_signals(self, db: Session, student: Student) -> list[dict[str, Any]]:
        if not self.enabled or not self.driver:
            return []
        try:
            self.sync_student_subgraph(db, student.id, include_classmates=True)
            return self._derive_signals(student)
        except Exception:
            return []

    def sync_student_graph(self, db: Session, student_id: int) -> dict[str, Any]:
        if not self.enabled or not self.driver:
            return {"enabled": False, "synced": False}
        self.sync_student_subgraph(db, student_id, include_classmates=True)
        return {"enabled": True, "synced": True, "student_id": student_id}

    def get_student_graph_view(self, db: Session, student_id: int) -> dict[str, Any]:
        payload = self.build_student_graph_payload(
            db,
            student_id,
            include_classmates=True,
            include_peer_events=False,
        )
        focus_student = next((item for item in payload["students"] if item["id"] == student_id), None)
        if not focus_student:
            return {
                "student_id": student_id,
                "window_days": 30,
                "nodes": [],
                "edges": [],
                "stats": {"student_count": 0, "peer_count": 0, "event_count": 0, "manual_relation_count": 0},
            }

        focus_node_id = f"student-{student_id}"
        class_id = focus_student.get("class_id")
        class_name = focus_student.get("class_name") or "未分班"
        nodes: list[dict[str, Any]] = [
            {
                "id": focus_node_id,
                "entity_id": focus_student["id"],
                "type": "student",
                "label": focus_student.get("name") or f"学生 {focus_student['id']}",
                "subtitle": focus_student.get("student_no") or "",
                "group": "focus",
                "focus": True,
            }
        ]
        edges: list[dict[str, Any]] = []

        if class_id:
            class_node_id = f"class-{class_id}"
            nodes.append(
                {
                    "id": class_node_id,
                    "entity_id": class_id,
                    "type": "class",
                    "label": class_name,
                    "subtitle": focus_student.get("grade") or "",
                    "group": "class",
                }
            )
            edges.append(
                {
                    "id": f"{focus_node_id}-{class_node_id}",
                    "source": focus_node_id,
                    "target": class_node_id,
                    "type": "in_class",
                    "label": "所在班级",
                }
            )

        classmates = [item for item in payload["students"] if item["id"] != student_id]
        for peer in classmates:
            peer_node_id = f"student-{peer['id']}"
            nodes.append(
                {
                    "id": peer_node_id,
                    "entity_id": peer["id"],
                    "type": "classmate",
                    "label": peer.get("name") or f"同学 {peer['id']}",
                    "subtitle": peer.get("student_no") or "",
                    "group": "peer",
                }
            )
            edges.append(
                {
                    "id": f"{focus_node_id}-{peer_node_id}",
                    "source": focus_node_id,
                    "target": peer_node_id,
                    "type": "same_class",
                    "label": "同班同学",
                }
            )
            if class_id:
                edges.append(
                    {
                        "id": f"{peer_node_id}-class-{class_id}",
                        "source": peer_node_id,
                        "target": f"class-{class_id}",
                        "type": "in_class",
                        "label": "同班",
                    }
                )

        for event in payload["events"]:
            event_node_id = f"event-{event['id']}"
            owner_node_id = f"student-{event['student_id']}"
            nodes.append(
                {
                    "id": event_node_id,
                    "entity_id": event["id"],
                    "type": "event",
                    "label": EVENT_TYPE_LABELS.get(event.get("event_type"), event.get("event_type") or "行为事件"),
                    "subtitle": event.get("event_level") or "",
                    "group": event.get("dimension") or "behavior",
                    "owner_student_id": event.get("student_id"),
                    "description": event.get("event_desc") or "",
                    "occurred_at": event.get("occurred_at"),
                }
            )
            edges.append(
                {
                    "id": f"{owner_node_id}-{event_node_id}",
                    "source": owner_node_id,
                    "target": event_node_id,
                    "type": "involved_in",
                    "label": "关联事件",
                }
            )

        manual_relation_count = 0
        for relation in payload.get("manual_relations", []):
            manual_relation_count += 1
            if relation["target_type"] == "student":
                target_student = relation.get("target_student")
                if not target_student:
                    continue
                target_node_id = f"student-{target_student['id']}"
                existing_node = next((item for item in nodes if item["id"] == target_node_id), None)
                if not existing_node:
                    nodes.append(
                        {
                            "id": target_node_id,
                            "entity_id": target_student["id"],
                            "manual_relation_id": relation["id"],
                            "type": "related_student",
                            "label": target_student.get("name") or f"关联同学 {target_student['id']}",
                            "subtitle": target_student.get("student_no") or "",
                            "group": "manual_student",
                            "description": relation.get("summary") or "",
                            "manual": True,
                        }
                    )
                else:
                    existing_node["description"] = relation.get("summary") or existing_node.get("description", "")
                    existing_node["manual"] = True
                    existing_node["manual_relation_id"] = existing_node.get("manual_relation_id") or relation["id"]

                edges.append(
                    {
                        "id": f"manual-relation-{relation['id']}",
                        "relation_id": relation["id"],
                        "source": focus_node_id,
                        "target": target_node_id,
                        "type": "manual_relation",
                        "label": MANUAL_RELATION_LABELS.get(relation.get("relation_type"), relation.get("relation_type") or "手工关系"),
                        "summary": relation.get("summary") or "",
                    }
                )
                continue

            event_node_id = f"manual-event-{relation['id']}"
            nodes.append(
                {
                    "id": event_node_id,
                    "entity_id": relation["id"],
                    "manual_relation_id": relation["id"],
                    "type": "manual_event",
                    "label": relation.get("event_title") or MANUAL_RELATION_LABELS.get(relation.get("relation_type"), "手工事件"),
                    "subtitle": relation.get("relation_level") or "",
                    "group": relation.get("dimension") or "behavior",
                    "description": relation.get("summary") or "",
                    "occurred_at": relation.get("occurred_at"),
                    "manual": True,
                }
            )
            edges.append(
                {
                    "id": f"manual-event-edge-{relation['id']}",
                    "relation_id": relation["id"],
                    "source": focus_node_id,
                    "target": event_node_id,
                    "type": "manual_relation",
                    "label": "手工补录关系",
                    "summary": relation.get("summary") or "",
                }
            )

        return {
            "student_id": student_id,
            "window_days": 30,
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "student_count": len(payload["students"]),
                "peer_count": len(classmates),
                "event_count": len(payload["events"]),
                "manual_relation_count": manual_relation_count,
            },
        }

    def sync_student_subgraph(
        self,
        db: Session,
        student_id: int,
        include_classmates: bool = True,
        include_peer_events: bool = True,
    ) -> None:
        if not self.enabled or not self.driver:
            return
        payload = self.build_student_graph_payload(
            db,
            student_id,
            include_classmates=include_classmates,
            include_peer_events=include_peer_events,
        )
        if not payload:
            return
        self._cleanup_student_subgraph(payload, student_id)

        for node in payload["students"]:
            self._run_query(
                """
                MERGE (s:Student {id: $id})
                SET s.student_no = $student_no,
                    s.name = $name,
                    s.grade = $grade,
                    s.class_id = $class_id
                """,
                node,
            )
            if node.get("class_id"):
                self._run_query(
                    """
                    MERGE (c:Class {id: $class_id})
                    SET c.name = $class_name,
                        c.grade = $grade
                    WITH c
                    MATCH (s:Student {id: $student_id})
                    MERGE (s)-[:IN_CLASS]->(c)
                    """,
                    {
                        "class_id": node["class_id"],
                        "class_name": node.get("class_name"),
                        "grade": node.get("grade"),
                        "student_id": node["id"],
                    },
                )

        for event in payload["events"]:
            self._run_query(
                """
                MERGE (e:BehaviorEvent {id: $id})
                SET e.event_type = $event_type,
                    e.event_level = $event_level,
                    e.event_desc = $event_desc,
                    e.occurred_at = $occurred_at,
                    e.dimension = $dimension
                WITH e
                MATCH (s:Student {id: $student_id})
                MERGE (s)-[:INVOLVED_IN]->(e)
                """,
                event,
            )

        for relation in payload.get("manual_relations", []):
            if relation["target_type"] == "student" and relation.get("target_student_id"):
                self._run_query(
                    """
                    MATCH (s:Student {id: $student_id})
                    MATCH (t:Student {id: $target_student_id})
                    MERGE (s)-[r:MANUAL_RELATION {relation_id: $relation_id}]->(t)
                    SET r.relation_type = $relation_type,
                        r.dimension = $dimension,
                        r.relation_level = $relation_level,
                        r.summary = $summary,
                        r.occurred_at = $occurred_at
                    """,
                    relation,
                )
            else:
                self._run_query(
                    """
                    MERGE (e:ManualGraphEvent {id: $relation_id})
                    SET e.title = $event_title,
                        e.relation_type = $relation_type,
                        e.dimension = $dimension,
                        e.relation_level = $relation_level,
                        e.summary = $summary,
                        e.occurred_at = $occurred_at
                    WITH e
                    MATCH (s:Student {id: $student_id})
                    MERGE (s)-[:MANUAL_RELATION {relation_id: $relation_id}]->(e)
                    """,
                    relation,
                )

    def _cleanup_student_subgraph(self, payload: dict[str, list[dict[str, Any]]], student_id: int) -> None:
        student_ids = [int(item["id"]) for item in payload.get("students", []) if item.get("id") is not None]
        current_event_ids = [int(item["id"]) for item in payload.get("events", []) if item.get("id") is not None]
        current_relation_ids = [
            int(item["relation_id"])
            for item in payload.get("manual_relations", [])
            if item.get("relation_id") is not None
        ]

        existing_event_rows = self._run_query(
            """
            MATCH (s:Student)-[:INVOLVED_IN]->(e:BehaviorEvent)
            WHERE s.id IN $student_ids
            RETURN DISTINCT e.id AS id
            """,
            {"student_ids": student_ids},
        ) if student_ids else []
        existing_event_ids = {
            int(item["id"])
            for item in existing_event_rows
            if item.get("id") is not None
        }
        stale_event_ids = sorted(existing_event_ids - set(current_event_ids))
        if stale_event_ids:
            self._run_query(
                """
                MATCH (s:Student)-[r:INVOLVED_IN]->(e:BehaviorEvent)
                WHERE s.id IN $student_ids AND e.id IN $event_ids
                DELETE r
                """,
                {"student_ids": student_ids, "event_ids": stale_event_ids},
            )
            self._run_query(
                """
                MATCH (e:BehaviorEvent)
                WHERE e.id IN $event_ids
                DETACH DELETE e
                """,
                {"event_ids": stale_event_ids},
            )

        existing_relation_rows = self._run_query(
            """
            MATCH (:Student {id: $student_id})-[r:MANUAL_RELATION]->()
            RETURN DISTINCT r.relation_id AS relation_id
            """,
            {"student_id": student_id},
        )
        existing_relation_ids = {
            int(item["relation_id"])
            for item in existing_relation_rows
            if item.get("relation_id") is not None
        }
        stale_relation_ids = sorted(existing_relation_ids - set(current_relation_ids))
        if stale_relation_ids:
            self._run_query(
                """
                MATCH (:Student {id: $student_id})-[r:MANUAL_RELATION]->()
                WHERE r.relation_id IN $relation_ids
                DELETE r
                """,
                {"student_id": student_id, "relation_ids": stale_relation_ids},
            )
            self._run_query(
                """
                MATCH (e:ManualGraphEvent)
                WHERE e.id IN $relation_ids
                DETACH DELETE e
                """,
                {"relation_ids": stale_relation_ids},
            )

    def build_student_graph_payload(
        self,
        db: Session,
        student_id: int,
        include_classmates: bool = True,
        include_peer_events: bool = True,
    ) -> dict[str, list[dict[str, Any]]]:
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return {"students": [], "events": [], "manual_relations": []}

        students = [student]
        if include_classmates and student.class_id:
            students = (
                db.query(Student)
                .filter(Student.class_id == student.class_id)
                .order_by(Student.id.asc())
                .all()
            )

        class_row = db.query(Class).filter(Class.id == student.class_id).first() if student.class_id else None
        student_nodes = [
            {
                "id": item.id,
                "student_no": item.student_no,
                "name": item.name,
                "grade": item.grade,
                "class_id": item.class_id,
                "class_name": class_row.name if class_row and item.class_id == class_row.id else None,
            }
            for item in students
        ]

        student_ids = [item.id for item in students] if include_peer_events else [student.id]
        cutoff = datetime.now() - timedelta(days=30)
        event_rows = (
            db.query(StudentBehaviorEvent)
            .filter(
                StudentBehaviorEvent.student_id.in_(student_ids),
                StudentBehaviorEvent.occurred_at >= cutoff,
            )
            .order_by(StudentBehaviorEvent.occurred_at.desc(), StudentBehaviorEvent.id.desc())
            .all()
        )
        events = [
            {
                "id": item.id,
                "student_id": item.student_id,
                "event_type": item.event_type,
                "event_level": item.event_level,
                "event_desc": item.event_desc,
                "occurred_at": item.occurred_at.isoformat() if item.occurred_at else None,
                "dimension": "safety" if item.event_type in SAFETY_EVENT_TYPES else "behavior",
            }
            for item in event_rows
        ]
        manual_relation_rows = (
            db.query(StudentCareGraphRelation)
            .filter(StudentCareGraphRelation.student_id == student_id)
            .order_by(
                case((StudentCareGraphRelation.occurred_at.is_(None), 1), else_=0).asc(),
                StudentCareGraphRelation.occurred_at.desc(),
                StudentCareGraphRelation.id.desc(),
            )
            .all()
        )
        manual_relations = []
        for item in manual_relation_rows:
            target_student = None
            if item.target_student_id:
                target_student_row = db.query(Student).filter(Student.id == item.target_student_id).first()
                if target_student_row:
                    target_student = {
                        "id": target_student_row.id,
                        "name": target_student_row.name,
                        "student_no": target_student_row.student_no,
                        "grade": target_student_row.grade,
                        "class_id": target_student_row.class_id,
                    }
            manual_relations.append(
                {
                    "id": item.id,
                    "relation_id": item.id,
                    "student_id": item.student_id,
                    "target_type": item.target_type,
                    "target_student_id": item.target_student_id,
                    "target_student": target_student,
                    "relation_type": item.relation_type,
                    "dimension": item.dimension,
                    "relation_level": item.relation_level,
                    "summary": item.summary,
                    "event_title": item.event_title,
                    "occurred_at": item.occurred_at.isoformat() if item.occurred_at else None,
                }
            )
        return {"students": student_nodes, "events": events, "manual_relations": manual_relations}

    def _derive_signals(self, student: Student) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []
        social_rows = self._run_query(
            """
            MATCH (s:Student {id: $student_id})
            OPTIONAL MATCH (s)-[:IN_CLASS]->(c:Class)<-[:IN_CLASS]-(peer:Student)
            RETURN count(DISTINCT peer) - 1 AS peer_count
            """,
            {"student_id": student.id},
        )
        peer_count = int((social_rows[0] or {}).get("peer_count", 0)) if social_rows else 0
        if student.class_id is None or peer_count <= 0:
            signals.append(
                {
                    "signal_type": "graph_social_isolation",
                    "dimension": "social",
                    "signal_text": "关系图谱中暂未形成稳定同伴连接，建议继续关注学生的社交融入情况。",
                    "signal_weight": 0.18,
                    "source": "graph",
                }
            )

        if student.class_id:
            safety_rows = self._run_query(
                """
                MATCH (s:Student {id: $student_id})-[:IN_CLASS]->(c:Class)<-[:IN_CLASS]-(peer:Student)-[:INVOLVED_IN]->(e:BehaviorEvent)
                WHERE e.dimension = 'safety'
                RETURN count(DISTINCT e) AS event_count, count(DISTINCT peer) AS peer_count
                """,
                {"student_id": student.id},
            )
            row = safety_rows[0] if safety_rows else {}
            event_count = int(row.get("event_count", 0) or 0)
            safety_peer_count = int(row.get("peer_count", 0) or 0)
            if event_count >= 2 and safety_peer_count >= 2:
                signals.append(
                    {
                        "signal_type": "graph_conflict_cooccurrence",
                        "dimension": "safety",
                        "signal_text": "关系图谱显示该生所在班级近期存在多名学生卷入冲突或欺凌事件，需要关注安全共现风险。",
                        "signal_weight": 0.22,
                        "source": "graph",
                    }
                )
        return signals

    def _run_query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if not self.driver:
            return []
        with self.driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]


student_care_graph_service = StudentCareGraphService()
