from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from core.response import error_response, success_response
from database.models.class_ import Class
from database.models.student import Student
from database.models.student_tag_definition import StudentTagDefinition
from database.models.student_tag_review import StudentTagReview
from database.models.teacher import Teacher
from database.models.user import User


VALID_STATUS = {"pending", "approved", "rejected"}
VALID_SCOPE = {"school", "grade", "class"}
VALID_POLARITY = {"positive", "neutral", "negative"}


def list_reviews(
    db: Session,
    current_user: User,
    page: int = 1,
    page_size: int = 10,
    status: str | None = None,
    keyword: str | None = None,
    class_id: int | None = None,
    grade: str | None = None,
):
    query = db.query(StudentTagReview)
    if status:
        query = query.filter(StudentTagReview.status == status)
    if keyword:
        query = query.filter(StudentTagReview.tag_text.like(f"%{keyword}%"))
    if class_id:
        query = query.filter(StudentTagReview.class_id == class_id)
    if grade:
        query = query.filter(StudentTagReview.grade == grade)

    if current_user.role == "teacher":
        class_ids = _get_teacher_class_ids(db, current_user)
        query = query.filter(StudentTagReview.class_id.in_(class_ids or [-1]))

    total = query.count()
    rows = (
        query.order_by(StudentTagReview.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return success_response(data={"list": [serialize(item) for item in rows], "total": total})


def approve_review(
    db: Session,
    current_user: User,
    review_id: int,
    data: dict,
):
    record = db.query(StudentTagReview).filter(StudentTagReview.id == review_id).first()
    if not record:
        return error_response(code=404, msg="审核记录不存在")
    if record.status != "pending":
        return error_response(code=400, msg="该记录已处理")
    if _ensure_teacher_review_scope(db, current_user, record):
        return error_response(code=403, msg="仅可审核本班标签")

    scope_type = data.get("scope_type")
    polarity = data.get("polarity")
    if scope_type not in VALID_SCOPE:
        return error_response(code=400, msg="scope_type 不合法")
    if polarity not in VALID_POLARITY:
        return error_response(code=400, msg="polarity 不合法")

    scope_value = data.get("scope_value")
    dimension = data.get("dimension")
    weight = data.get("weight")
    description = data.get("description")
    review_note = data.get("review_note")

    record.status = "approved"
    record.reviewed_by = current_user.id
    record.reviewed_at = datetime.now()
    record.review_note = review_note

    definition = (
        db.query(StudentTagDefinition)
        .filter(
            StudentTagDefinition.scope_type == scope_type,
            StudentTagDefinition.scope_value == scope_value,
            StudentTagDefinition.tag_text == record.tag_text,
        )
        .first()
    )
    if not definition:
        definition = StudentTagDefinition(
            scope_type=scope_type,
            scope_value=scope_value,
            tag_text=record.tag_text,
            polarity=polarity,
            dimension=dimension,
            weight=weight,
            description=description,
            created_by=current_user.id,
        )
        db.add(definition)
    else:
        definition.polarity = polarity
        definition.dimension = dimension
        definition.weight = weight
        definition.description = description

    db.add(record)
    db.commit()
    db.refresh(record)
    return success_response(data=serialize(record))


def reject_review(db: Session, current_user: User, review_id: int, data: dict):
    record = db.query(StudentTagReview).filter(StudentTagReview.id == review_id).first()
    if not record:
        return error_response(code=404, msg="审核记录不存在")
    if record.status != "pending":
        return error_response(code=400, msg="该记录已处理")
    if _ensure_teacher_review_scope(db, current_user, record):
        return error_response(code=403, msg="仅可审核本班标签")

    record.status = "rejected"
    record.reviewed_by = current_user.id
    record.reviewed_at = datetime.now()
    record.review_note = data.get("review_note")
    db.add(record)
    db.commit()
    db.refresh(record)
    return success_response(data=serialize(record))


def create_pending_reviews(
    db: Session,
    current_user: User,
    student: Student,
    tags: list[str],
    source: str = "teacher_input",
) -> None:
    if not tags:
        return

    existing_definitions = (
        db.query(StudentTagDefinition.tag_text)
        .filter(StudentTagDefinition.tag_text.in_(tags))
        .all()
    )
    defined_tags = {row[0] for row in existing_definitions}

    for tag in tags:
        if tag in defined_tags:
            continue
        exists = (
            db.query(StudentTagReview)
            .filter(
                StudentTagReview.tag_text == tag,
                StudentTagReview.student_id == student.id,
                StudentTagReview.status == "pending",
            )
            .first()
        )
        if exists:
            continue

        scope_type, scope_value = _suggest_scope(student)
        record = StudentTagReview(
            tag_text=tag,
            status="pending",
            student_id=student.id,
            class_id=student.class_id,
            grade=student.grade,
            source=source,
            suggested_scope_type=scope_type,
            suggested_scope_value=scope_value,
            created_by=current_user.id,
        )
        db.add(record)
    db.commit()


def _suggest_scope(student: Student) -> tuple[str, str | None]:
    if student.class_id:
        return "class", str(student.class_id)
    if student.grade:
        return "grade", student.grade
    return "school", None


def _get_teacher_class_ids(db: Session, current_user: User) -> list[int]:
    teacher = db.query(Teacher).filter(Teacher.name == current_user.name).first()
    if not teacher:
        return []
    class_rows = db.query(Class).filter(Class.head_teacher_id == teacher.id).all()
    return [row.id for row in class_rows]


def _ensure_teacher_review_scope(db: Session, current_user: User, record: StudentTagReview) -> bool:
    if current_user.role != "teacher":
        return False
    class_ids = _get_teacher_class_ids(db, current_user)
    return not record.class_id or record.class_id not in class_ids


def serialize(item: StudentTagReview) -> dict:
    return {
        "id": item.id,
        "tag_text": item.tag_text,
        "status": item.status,
        "student_id": item.student_id,
        "class_id": item.class_id,
        "grade": item.grade,
        "source": item.source,
        "suggested_scope_type": item.suggested_scope_type,
        "suggested_scope_value": item.suggested_scope_value,
        "suggested_polarity": item.suggested_polarity,
        "suggested_dimension": item.suggested_dimension,
        "suggested_weight": item.suggested_weight,
        "suggested_description": item.suggested_description,
        "suggestion_note": item.suggestion_note,
        "created_by": item.created_by,
        "reviewed_by": item.reviewed_by,
        "reviewed_at": str(item.reviewed_at) if item.reviewed_at else None,
        "review_note": item.review_note,
        "created_at": str(item.created_at) if item.created_at else None,
    }
