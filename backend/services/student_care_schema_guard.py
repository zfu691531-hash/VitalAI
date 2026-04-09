# -*- coding: utf-8 -*-
"""Schema guard for student care tables."""

from __future__ import annotations

from threading import Lock

from database.connection import engine
from sqlalchemy import inspect, text
from database.models.student_assistant_summary import StudentAssistantSummary
from database.models.student_attendance import StudentAttendance
from database.models.student_care_agent_record import StudentCareAgentRecord
from database.models.student_care_bayes_rule import StudentCareBayesRule
from database.models.student_care_graph_relation import StudentCareGraphRelation
from database.models.student_behavior_event import StudentBehaviorEvent
from database.models.student_care_observation import StudentCareObservation
from database.models.student_care_profile import StudentCareProfile
from database.models.student_care_signal import StudentCareSignal
from database.models.student_family_contact import StudentFamilyContact


_schema_ready = False
_schema_lock = Lock()


def ensure_student_care_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return

    with _schema_lock:
        if _schema_ready:
            return

        for table in (
            StudentCareProfile.__table__,
            StudentCareSignal.__table__,
            StudentAttendance.__table__,
            StudentBehaviorEvent.__table__,
            StudentCareObservation.__table__,
            StudentFamilyContact.__table__,
            StudentAssistantSummary.__table__,
            StudentCareAgentRecord.__table__,
            StudentCareBayesRule.__table__,
            StudentCareGraphRelation.__table__,
        ):
            table.create(bind=engine, checkfirst=True)
        _ensure_agent_record_review_columns()
        _schema_ready = True


def _ensure_agent_record_review_columns() -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if StudentCareAgentRecord.__tablename__ not in table_names:
        return
    column_names = {column["name"] for column in inspector.get_columns(StudentCareAgentRecord.__tablename__)}
    columns = [
        ("review_status", "VARCHAR(20) DEFAULT 'pending'"),
        ("reviewed_result_json", "JSON NULL"),
        ("review_labels_json", "JSON NULL"),
        ("teacher_notes", "TEXT NULL"),
        ("resolution_status", "VARCHAR(30) NULL"),
        ("confirmed_by", "BIGINT NULL"),
        ("confirmed_at", "DATETIME NULL"),
    ]
    with engine.begin() as connection:
        for name, ddl in columns:
            if name in column_names:
                continue
            if engine.dialect.name == "mysql":
                connection.execute(text(f"ALTER TABLE {StudentCareAgentRecord.__tablename__} ADD COLUMN {name} {ddl}"))
            else:
                sqlite_type = "TEXT"
                if name in {"reviewed_result_json"}:
                    sqlite_type = "JSON"
                elif name in {"confirmed_by"}:
                    sqlite_type = "INTEGER"
                connection.execute(text(f"ALTER TABLE {StudentCareAgentRecord.__tablename__} ADD COLUMN {name} {sqlite_type}"))
