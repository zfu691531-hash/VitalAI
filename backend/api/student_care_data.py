# -*- coding: utf-8 -*-
"""Student care data endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_db
from core.response import error_response, success_response
from database.models.class_ import Class
from database.models.student import Student
from database.models.student_attendance import StudentAttendance
from database.models.student_behavior_event import StudentBehaviorEvent
from database.models.student_care_graph_relation import StudentCareGraphRelation
from database.models.student_care_observation import StudentCareObservation
from database.models.student_family_contact import StudentFamilyContact
from database.models.teacher import Teacher
from database.models.user import User
from schemas.student_care_data import (
    AttendanceCreate,
    AttendanceOut,
    AttendanceUpdate,
    BehaviorEventCreate,
    BehaviorEventOut,
    BehaviorEventUpdate,
    CareObservationCreate,
    CareObservationOut,
    CareObservationUpdate,
    FamilyContactCreate,
    FamilyContactOut,
    GraphRelationCreate,
    GraphRelationOut,
    GraphRelationUpdate,
    AssistantSummaryOut,
    AssistantSummaryCreate,
)
from services.student_care_data_service import (
    create_assistant_summary,
    create_attendance,
    create_behavior_event,
    create_care_observation,
    create_family_contact,
    create_graph_relation,
    delete_attendance,
    delete_behavior_event,
    delete_care_observation,
    delete_family_contact,
    delete_graph_relation,
    list_assistant_summaries,
    list_attendance,
    list_behavior_events,
    list_care_observations,
    list_family_contacts,
    list_graph_relations,
    update_attendance,
    update_behavior_event,
    update_care_observation,
    update_graph_relation,
)
from services.student_care_graph_service import student_care_graph_service
from services.student_care_service import recalculate_student_care_profile


router = APIRouter(prefix="/api", tags=["Student Care Data"])


def _recalc_student_profile(db: Session, student_id: int) -> None:
    student = db.query(Student).filter(Student.id == student_id).first()
    if student:
        recalculate_student_care_profile(db, student)
        try:
            student_care_graph_service.sync_student_graph(db, student_id)
        except Exception:
            # Graph sync is best-effort here so data maintenance still succeeds even
            # if Neo4j is unavailable or temporarily unhealthy.
            pass


def _ensure_teacher_scope(db: Session, current_user: User, student_id: int) -> dict | None:
    if current_user.role == "admin":
        return None
    if current_user.role != "teacher":
        return error_response(code=403, msg="当前仅班主任或管理员可操作")

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return error_response(code=404, msg="学生不存在")
    if not student.class_id:
        return error_response(code=403, msg="学生未分班")

    teacher = db.query(Teacher).filter(Teacher.name == current_user.name).first()
    if not teacher:
        return error_response(code=403, msg="未找到教师档案")

    class_row = db.query(Class).filter(Class.id == student.class_id).first()
    if not class_row or class_row.head_teacher_id != teacher.id:
        return error_response(code=403, msg="仅可操作本班学生数据")
    return None


def _dump_attendance(record: StudentAttendance) -> dict:
    return AttendanceOut.model_validate(record).model_dump()


def _dump_behavior_event(record: StudentBehaviorEvent) -> dict:
    return BehaviorEventOut.model_validate(record).model_dump()


def _dump_care_observation(record: StudentCareObservation) -> dict:
    return CareObservationOut.model_validate(record).model_dump()


def _dump_family_contact(record: StudentFamilyContact) -> dict:
    return FamilyContactOut.model_validate(record).model_dump()


def _dump_assistant_summary(record) -> dict:
    return AssistantSummaryOut.model_validate(record).model_dump()


def _dump_graph_relation(db: Session, record: StudentCareGraphRelation) -> dict:
    target_student = None
    if record.target_student_id:
        target_student = db.query(Student).filter(Student.id == record.target_student_id).first()
    payload = {
        "id": record.id,
        "student_id": record.student_id,
        "target_type": record.target_type,
        "target_student_id": record.target_student_id,
        "target_student_name": target_student.name if target_student else None,
        "target_student_no": target_student.student_no if target_student else None,
        "relation_type": record.relation_type,
        "dimension": record.dimension,
        "relation_level": record.relation_level,
        "summary": record.summary,
        "event_title": record.event_title,
        "occurred_at": record.occurred_at,
        "created_at": record.created_at,
    }
    return GraphRelationOut.model_validate(payload).model_dump()


def _validate_graph_relation_payload(payload: GraphRelationCreate | GraphRelationUpdate) -> dict | None:
    target_type = getattr(payload, "target_type", None)
    target_student_id = getattr(payload, "target_student_id", None)
    event_title = (getattr(payload, "event_title", None) or "").strip()
    if target_type == "student" and not target_student_id:
        return error_response(code=400, msg="关联同学类型必须选择目标学生")
    if target_type == "event" and not event_title:
        return error_response(code=400, msg="关联事件类型必须填写事件标题")
    return None


def _validate_graph_relation_target_student(
    db: Session,
    source_student: Student,
    target_student_id: int | None,
) -> dict | None:
    if not target_student_id:
        return None
    target_student = db.query(Student).filter(Student.id == target_student_id).first()
    if not target_student:
        return error_response(code=404, msg="Target student not found")
    if not source_student.class_id or target_student.class_id != source_student.class_id:
        return error_response(code=403, msg="Only same-class students can be linked")
    return None


@router.get("/attendance")
def get_attendance(
    student_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin" and not student_id:
        return error_response(code=403, msg="仅管理员可查看全部记录")
    if student_id:
        scope_error = _ensure_teacher_scope(db, current_user, student_id)
        if scope_error:
            return scope_error
    records = list_attendance(db, student_id)
    return success_response(data={"list": [_dump_attendance(item) for item in records]})


@router.post("/attendance")
def add_attendance(
    payload: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scope_error = _ensure_teacher_scope(db, current_user, payload.student_id)
    if scope_error:
        return scope_error
    record = create_attendance(db, payload.student_id, payload.date, payload.status, payload.remark)
    _recalc_student_profile(db, payload.student_id)
    return success_response(data=_dump_attendance(record))


@router.put("/attendance/{record_id}")
def edit_attendance(
    record_id: int,
    payload: AttendanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(StudentAttendance).filter(StudentAttendance.id == record_id).first()
    if not record:
        return error_response(code=404, msg="记录不存在")
    scope_error = _ensure_teacher_scope(db, current_user, record.student_id)
    if scope_error:
        return scope_error
    updated = update_attendance(db, record, payload.status, payload.remark)
    _recalc_student_profile(db, record.student_id)
    return success_response(data=_dump_attendance(updated))


@router.delete("/attendance/{record_id}")
def remove_attendance(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(StudentAttendance).filter(StudentAttendance.id == record_id).first()
    if not record:
        return error_response(code=404, msg="记录不存在")
    scope_error = _ensure_teacher_scope(db, current_user, record.student_id)
    if scope_error:
        return scope_error
    delete_attendance(db, record)
    _recalc_student_profile(db, record.student_id)
    return success_response(msg="删除成功")


@router.get("/behavior-events")
def get_behavior_events(
    student_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin" and not student_id:
        return error_response(code=403, msg="仅管理员可查看全部记录")
    if student_id:
        scope_error = _ensure_teacher_scope(db, current_user, student_id)
        if scope_error:
            return scope_error
    records = list_behavior_events(db, student_id)
    return success_response(data={"list": [_dump_behavior_event(item) for item in records]})


@router.post("/behavior-events")
def add_behavior_event(
    payload: BehaviorEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scope_error = _ensure_teacher_scope(db, current_user, payload.student_id)
    if scope_error:
        return scope_error
    record = create_behavior_event(
        db,
        payload.student_id,
        payload.event_type,
        payload.event_level,
        payload.event_desc,
        payload.occurred_at,
    )
    _recalc_student_profile(db, payload.student_id)
    return success_response(data=_dump_behavior_event(record))


@router.put("/behavior-events/{record_id}")
def edit_behavior_event(
    record_id: int,
    payload: BehaviorEventUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(StudentBehaviorEvent).filter(StudentBehaviorEvent.id == record_id).first()
    if not record:
        return error_response(code=404, msg="记录不存在")
    scope_error = _ensure_teacher_scope(db, current_user, record.student_id)
    if scope_error:
        return scope_error
    updated = update_behavior_event(
        db,
        record,
        payload.event_type,
        payload.event_level,
        payload.event_desc,
        payload.occurred_at,
    )
    _recalc_student_profile(db, record.student_id)
    return success_response(data=_dump_behavior_event(updated))


@router.delete("/behavior-events/{record_id}")
def remove_behavior_event(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(StudentBehaviorEvent).filter(StudentBehaviorEvent.id == record_id).first()
    if not record:
        return error_response(code=404, msg="记录不存在")
    scope_error = _ensure_teacher_scope(db, current_user, record.student_id)
    if scope_error:
        return scope_error
    delete_behavior_event(db, record)
    _recalc_student_profile(db, record.student_id)
    return success_response(msg="删除成功")


@router.get("/care-observations")
def get_care_observations(
    student_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin" and not student_id:
        return error_response(code=403, msg="仅管理员可查看全部记录")
    if student_id:
        scope_error = _ensure_teacher_scope(db, current_user, student_id)
        if scope_error:
            return scope_error
    records = list_care_observations(db, student_id)
    return success_response(data={"list": [_dump_care_observation(item) for item in records]})


@router.post("/care-observations")
def add_care_observation(
    payload: CareObservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scope_error = _ensure_teacher_scope(db, current_user, payload.student_id)
    if scope_error:
        return scope_error
    record = create_care_observation(
        db,
        payload.student_id,
        payload.dimension,
        payload.observation_type,
        payload.observation_level,
        payload.observed_at,
        payload.summary,
    )
    _recalc_student_profile(db, payload.student_id)
    return success_response(data=_dump_care_observation(record))


@router.put("/care-observations/{record_id}")
def edit_care_observation(
    record_id: int,
    payload: CareObservationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(StudentCareObservation).filter(StudentCareObservation.id == record_id).first()
    if not record:
        return error_response(code=404, msg="记录不存在")
    scope_error = _ensure_teacher_scope(db, current_user, record.student_id)
    if scope_error:
        return scope_error
    updated = update_care_observation(
        db,
        record,
        payload.dimension,
        payload.observation_type,
        payload.observation_level,
        payload.observed_at,
        payload.summary,
    )
    _recalc_student_profile(db, record.student_id)
    return success_response(data=_dump_care_observation(updated))


@router.delete("/care-observations/{record_id}")
def remove_care_observation(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(StudentCareObservation).filter(StudentCareObservation.id == record_id).first()
    if not record:
        return error_response(code=404, msg="记录不存在")
    scope_error = _ensure_teacher_scope(db, current_user, record.student_id)
    if scope_error:
        return scope_error
    delete_care_observation(db, record)
    _recalc_student_profile(db, record.student_id)
    return success_response(msg="删除成功")


@router.get("/family-contacts")
def get_family_contacts(
    student_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin" and not student_id:
        return error_response(code=403, msg="仅管理员可查看全部记录")
    if student_id:
        scope_error = _ensure_teacher_scope(db, current_user, student_id)
        if scope_error:
            return scope_error
    records = list_family_contacts(db, student_id)
    return success_response(data={"list": [_dump_family_contact(item) for item in records]})


@router.post("/family-contacts")
def add_family_contact(
    payload: FamilyContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scope_error = _ensure_teacher_scope(db, current_user, payload.student_id)
    if scope_error:
        return scope_error
    record = create_family_contact(db, payload.student_id, payload.contact_type, payload.summary)
    _recalc_student_profile(db, payload.student_id)
    return success_response(data=_dump_family_contact(record))


@router.delete("/family-contacts/{record_id}")
def remove_family_contact(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(StudentFamilyContact).filter(StudentFamilyContact.id == record_id).first()
    if not record:
        return error_response(code=404, msg="记录不存在")
    scope_error = _ensure_teacher_scope(db, current_user, record.student_id)
    if scope_error:
        return scope_error
    delete_family_contact(db, record)
    _recalc_student_profile(db, record.student_id)
    return success_response(msg="删除成功")


@router.get("/assistant-summary")
def get_assistant_summary(
    student_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin" and not student_id:
        return error_response(code=403, msg="仅管理员可查看全部记录")
    if student_id:
        scope_error = _ensure_teacher_scope(db, current_user, student_id)
        if scope_error:
            return scope_error
    records = list_assistant_summaries(db, student_id)
    return success_response(data={"list": [_dump_assistant_summary(item) for item in records]})


@router.post("/assistant-summary")
def add_assistant_summary(
    payload: AssistantSummaryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scope_error = _ensure_teacher_scope(db, current_user, payload.student_id)
    if scope_error:
        return scope_error
    record = create_assistant_summary(db, payload.student_id, payload.summary_text, payload.signals_json)
    _recalc_student_profile(db, payload.student_id)
    return success_response(data=_dump_assistant_summary(record))


@router.get("/graph-relations")
def get_graph_relations(
    student_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin" and not student_id:
        return error_response(code=403, msg="仅管理员可查看全部图谱关系记录")
    if student_id:
        scope_error = _ensure_teacher_scope(db, current_user, student_id)
        if scope_error:
            return scope_error
    records = list_graph_relations(db, student_id)
    return success_response(data={"list": [_dump_graph_relation(db, item) for item in records]})


@router.post("/graph-relations")
def add_graph_relation(
    payload: GraphRelationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scope_error = _ensure_teacher_scope(db, current_user, payload.student_id)
    if scope_error:
        return scope_error
    source_student = db.query(Student).filter(Student.id == payload.student_id).first()
    if not source_student:
        return error_response(code=404, msg="Student not found")
    validate_error = _validate_graph_relation_payload(payload)
    if validate_error:
        return validate_error
    if payload.target_type == "student" and payload.target_student_id == payload.student_id:
        return error_response(code=400, msg="Cannot relate the student to themself")
    target_scope_error = _validate_graph_relation_target_student(
        db,
        source_student,
        payload.target_student_id if payload.target_type == "student" else None,
    )
    if target_scope_error:
        return target_scope_error
    record = create_graph_relation(
        db=db,
        student_id=payload.student_id,
        target_type=payload.target_type,
        target_student_id=payload.target_student_id if payload.target_type == "student" else None,
        relation_type=payload.relation_type,
        dimension=payload.dimension,
        relation_level=payload.relation_level,
        summary=payload.summary,
        event_title=payload.event_title if payload.target_type == "event" else None,
        occurred_at=payload.occurred_at,
        created_by=current_user.id,
    )
    _recalc_student_profile(db, payload.student_id)
    return success_response(data=_dump_graph_relation(db, record))


@router.put("/graph-relations/{record_id}")
def edit_graph_relation(
    record_id: int,
    payload: GraphRelationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(StudentCareGraphRelation).filter(StudentCareGraphRelation.id == record_id).first()
    if not record:
        return error_response(code=404, msg="Record not found")
    scope_error = _ensure_teacher_scope(db, current_user, record.student_id)
    if scope_error:
        return scope_error
    source_student = db.query(Student).filter(Student.id == record.student_id).first()
    if not source_student:
        return error_response(code=404, msg="Student not found")
    validate_error = _validate_graph_relation_payload(payload)
    if payload.target_type and validate_error:
        return validate_error
    effective_target_type = payload.target_type or record.target_type
    target_student_id = record.target_student_id
    if effective_target_type == "student":
        target_student_id = payload.target_student_id
        if target_student_id == record.student_id:
            return error_response(code=400, msg="Cannot relate the student to themself")
    if effective_target_type == "event":
        target_student_id = None
    target_scope_error = _validate_graph_relation_target_student(
        db,
        source_student,
        target_student_id if effective_target_type == "student" else None,
    )
    if target_scope_error:
        return target_scope_error
    updated = update_graph_relation(
        db=db,
        record=record,
        target_type=payload.target_type,
        target_student_id=target_student_id,
        relation_type=payload.relation_type,
        dimension=payload.dimension,
        relation_level=payload.relation_level,
        summary=payload.summary,
        event_title=payload.event_title if payload.target_type != "student" else None,
        occurred_at=payload.occurred_at,
    )
    _recalc_student_profile(db, record.student_id)
    return success_response(data=_dump_graph_relation(db, updated))


@router.delete("/graph-relations/{record_id}")
def remove_graph_relation(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(StudentCareGraphRelation).filter(StudentCareGraphRelation.id == record_id).first()
    if not record:
        return error_response(code=404, msg="记录不存在")
    scope_error = _ensure_teacher_scope(db, current_user, record.student_id)
    if scope_error:
        return scope_error
    student_id = record.student_id
    delete_graph_relation(db, record)
    _recalc_student_profile(db, student_id)
    return success_response(msg="删除成功")
