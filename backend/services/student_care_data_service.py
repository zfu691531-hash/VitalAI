# -*- coding: utf-8 -*-
"""CRUD services for student care data."""

from __future__ import annotations

from datetime import date

from sqlalchemy import case
from sqlalchemy.orm import Session

from database.models.student_assistant_summary import StudentAssistantSummary
from database.models.student_attendance import StudentAttendance
from database.models.student_behavior_event import StudentBehaviorEvent
from database.models.student_care_observation import StudentCareObservation
from database.models.student_care_graph_relation import StudentCareGraphRelation
from database.models.student_family_contact import StudentFamilyContact
from services.student_care_schema_guard import ensure_student_care_schema


def list_attendance(db: Session, student_id: int | None = None) -> list[StudentAttendance]:
    ensure_student_care_schema()
    db.rollback()
    query = db.query(StudentAttendance)
    if student_id:
        query = query.filter(StudentAttendance.student_id == student_id)
    return query.order_by(StudentAttendance.date.desc(), StudentAttendance.id.desc()).all()


def create_attendance(
    db: Session,
    student_id: int,
    date_value: date,
    status: str,
    remark: str | None,
) -> StudentAttendance:
    ensure_student_care_schema()
    db.rollback()
    record = StudentAttendance(
        student_id=student_id,
        date=date_value,
        status=status,
        remark=remark,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_attendance(
    db: Session,
    record: StudentAttendance,
    status: str | None,
    remark: str | None,
) -> StudentAttendance:
    ensure_student_care_schema()
    db.rollback()
    if status is not None:
        record.status = status
    if remark is not None:
        record.remark = remark
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_attendance(db: Session, record: StudentAttendance) -> None:
    ensure_student_care_schema()
    db.rollback()
    db.delete(record)
    db.commit()


def list_behavior_events(db: Session, student_id: int | None = None) -> list[StudentBehaviorEvent]:
    ensure_student_care_schema()
    db.rollback()
    query = db.query(StudentBehaviorEvent)
    if student_id:
        query = query.filter(StudentBehaviorEvent.student_id == student_id)
    return query.order_by(StudentBehaviorEvent.occurred_at.desc(), StudentBehaviorEvent.id.desc()).all()


def create_behavior_event(
    db: Session,
    student_id: int,
    event_type: str,
    event_level: str,
    event_desc: str,
    occurred_at,
) -> StudentBehaviorEvent:
    ensure_student_care_schema()
    db.rollback()
    record = StudentBehaviorEvent(
        student_id=student_id,
        event_type=event_type,
        event_level=event_level,
        event_desc=event_desc,
        occurred_at=occurred_at,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_behavior_event(
    db: Session,
    record: StudentBehaviorEvent,
    event_type: str | None,
    event_level: str | None,
    event_desc: str | None,
    occurred_at,
) -> StudentBehaviorEvent:
    ensure_student_care_schema()
    db.rollback()
    if event_type is not None:
        record.event_type = event_type
    if event_level is not None:
        record.event_level = event_level
    if event_desc is not None:
        record.event_desc = event_desc
    if occurred_at is not None:
        record.occurred_at = occurred_at
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_behavior_event(db: Session, record: StudentBehaviorEvent) -> None:
    ensure_student_care_schema()
    db.rollback()
    db.delete(record)
    db.commit()


def list_care_observations(db: Session, student_id: int | None = None) -> list[StudentCareObservation]:
    ensure_student_care_schema()
    db.rollback()
    query = db.query(StudentCareObservation)
    if student_id:
        query = query.filter(StudentCareObservation.student_id == student_id)
    return query.order_by(StudentCareObservation.observed_at.desc(), StudentCareObservation.id.desc()).all()


def create_care_observation(
    db: Session,
    student_id: int,
    dimension: str,
    observation_type: str,
    observation_level: str,
    observed_at,
    summary: str,
) -> StudentCareObservation:
    ensure_student_care_schema()
    db.rollback()
    record = StudentCareObservation(
        student_id=student_id,
        dimension=dimension,
        observation_type=observation_type,
        observation_level=observation_level,
        observed_at=observed_at,
        summary=summary,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_care_observation(
    db: Session,
    record: StudentCareObservation,
    dimension: str | None,
    observation_type: str | None,
    observation_level: str | None,
    observed_at,
    summary: str | None,
) -> StudentCareObservation:
    ensure_student_care_schema()
    db.rollback()
    if dimension is not None:
        record.dimension = dimension
    if observation_type is not None:
        record.observation_type = observation_type
    if observation_level is not None:
        record.observation_level = observation_level
    if observed_at is not None:
        record.observed_at = observed_at
    if summary is not None:
        record.summary = summary
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_care_observation(db: Session, record: StudentCareObservation) -> None:
    ensure_student_care_schema()
    db.rollback()
    db.delete(record)
    db.commit()


def list_family_contacts(db: Session, student_id: int | None = None) -> list[StudentFamilyContact]:
    ensure_student_care_schema()
    db.rollback()
    query = db.query(StudentFamilyContact)
    if student_id:
        query = query.filter(StudentFamilyContact.student_id == student_id)
    return query.order_by(StudentFamilyContact.id.desc()).all()


def create_family_contact(
    db: Session,
    student_id: int,
    contact_type: str,
    summary: str,
) -> StudentFamilyContact:
    ensure_student_care_schema()
    db.rollback()
    record = StudentFamilyContact(
        student_id=student_id,
        contact_type=contact_type,
        summary=summary,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_family_contact(db: Session, record: StudentFamilyContact) -> None:
    ensure_student_care_schema()
    db.rollback()
    db.delete(record)
    db.commit()


def list_assistant_summaries(db: Session, student_id: int | None = None) -> list[StudentAssistantSummary]:
    ensure_student_care_schema()
    db.rollback()
    query = db.query(StudentAssistantSummary)
    if student_id:
        query = query.filter(StudentAssistantSummary.student_id == student_id)
    return query.order_by(StudentAssistantSummary.id.desc()).all()


def create_assistant_summary(
    db: Session,
    student_id: int,
    summary_text: str,
    signals_json: dict | None,
) -> StudentAssistantSummary:
    ensure_student_care_schema()
    db.rollback()
    record = StudentAssistantSummary(
        student_id=student_id,
        summary_text=summary_text,
        signals_json=signals_json,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_graph_relations(db: Session, student_id: int | None = None) -> list[StudentCareGraphRelation]:
    ensure_student_care_schema()
    db.rollback()
    query = db.query(StudentCareGraphRelation)
    if student_id:
        query = query.filter(StudentCareGraphRelation.student_id == student_id)
    return query.order_by(
        case((StudentCareGraphRelation.occurred_at.is_(None), 1), else_=0).asc(),
        StudentCareGraphRelation.occurred_at.desc(),
        StudentCareGraphRelation.id.desc(),
    ).all()


def create_graph_relation(
    db: Session,
    student_id: int,
    target_type: str,
    target_student_id: int | None,
    relation_type: str,
    dimension: str,
    relation_level: str,
    summary: str,
    event_title: str | None,
    occurred_at,
    created_by: int | None,
) -> StudentCareGraphRelation:
    ensure_student_care_schema()
    db.rollback()
    record = StudentCareGraphRelation(
        student_id=student_id,
        target_type=target_type,
        target_student_id=target_student_id,
        relation_type=relation_type,
        dimension=dimension,
        relation_level=relation_level,
        summary=summary,
        event_title=event_title,
        occurred_at=occurred_at,
        created_by=created_by,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_graph_relation(
    db: Session,
    record: StudentCareGraphRelation,
    target_type: str | None,
    target_student_id: int | None,
    relation_type: str | None,
    dimension: str | None,
    relation_level: str | None,
    summary: str | None,
    event_title: str | None,
    occurred_at,
) -> StudentCareGraphRelation:
    ensure_student_care_schema()
    db.rollback()
    if target_type is not None:
        record.target_type = target_type
    if target_student_id is not None or (target_type == "event"):
        record.target_student_id = target_student_id
    if relation_type is not None:
        record.relation_type = relation_type
    if dimension is not None:
        record.dimension = dimension
    if relation_level is not None:
        record.relation_level = relation_level
    if summary is not None:
        record.summary = summary
    if event_title is not None or (target_type == "student"):
        record.event_title = event_title
    if occurred_at is not None:
        record.occurred_at = occurred_at
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_graph_relation(db: Session, record: StudentCareGraphRelation) -> None:
    ensure_student_care_schema()
    db.rollback()
    db.delete(record)
    db.commit()
