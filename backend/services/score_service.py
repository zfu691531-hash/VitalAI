# -*- coding: utf-8 -*-
"""Score service."""

from decimal import Decimal
from typing import List, Optional

from fastapi import UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.response import error_response, success_response
from database.models.class_ import Class
from database.models.score import Score
from database.models.student import Student
from database.models.teacher import Teacher
from database.models.user import User
from services.export_service import download_template, generate_score_excel, parse_import_excel
from services.user_service import get_student_by_user_id
from utils.logger import logger


def get_list(
    db: Session,
    current_user: User,
    page: int = 1,
    page_size: int = 10,
    student_id: Optional[int] = None,
    class_id: Optional[int] = None,
    exam_batch: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict:
    query = _scoped_score_query(db, current_user)

    if student_id:
        query = query.filter(Score.student_id == student_id)
    if class_id:
        query = query.filter(Score.class_id == class_id)
    if exam_batch:
        query = query.filter(Score.exam_batch == exam_batch)
    if subject:
        query = query.filter(Score.subject == subject)

    total = query.count()
    scores = (
        query.order_by(Score.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    student_ids = [item.student_id for item in scores]
    class_ids = [item.class_id for item in scores]
    student_map = {}
    class_map = {}

    if student_ids:
        students = db.query(Student).filter(Student.id.in_(student_ids)).all()
        student_map = {item.id: item for item in students}

    if class_ids:
        classes = db.query(Class).filter(Class.id.in_(class_ids)).all()
        class_map = {item.id: item for item in classes}

    rows = []
    for item in scores:
        student = student_map.get(item.student_id)
        class_obj = class_map.get(item.class_id)
        rows.append(
            {
                "id": item.id,
                "student_id": item.student_id,
                "student_name": student.name if student else "",
                "class_id": item.class_id,
                "class_name": class_obj.name if class_obj else "",
                "exam_batch": item.exam_batch,
                "subject": item.subject,
                "score": float(item.score),
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
        )

    return success_response(data={"list": rows, "total": total})


def create(
    db: Session,
    student_id: int,
    class_id: int,
    exam_batch: str,
    subject: str,
    score: float,
) -> dict:
    if not 0 <= score <= 100:
        return error_response(msg="分数必须在 0 到 100 之间")

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return error_response(msg=f"学生 ID {student_id} 不存在")

    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        return error_response(msg=f"班级 ID {class_id} 不存在")

    score_obj = Score(
        student_id=student_id,
        class_id=class_id,
        exam_batch=exam_batch,
        subject=subject,
        score=Decimal(str(score)),
    )
    db.add(score_obj)
    db.commit()
    db.refresh(score_obj)

    logger.info("create score success: student=%s subject=%s score=%s", student_id, subject, score)
    return success_response(msg="创建成功", data={"id": score_obj.id})


def update(
    db: Session,
    score_id: int,
    student_id: Optional[int] = None,
    class_id: Optional[int] = None,
    exam_batch: Optional[str] = None,
    subject: Optional[str] = None,
    score: Optional[float] = None,
) -> dict:
    score_obj = db.query(Score).filter(Score.id == score_id).first()
    if not score_obj:
        return error_response(msg="成绩不存在")

    if student_id is not None:
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return error_response(msg=f"学生 ID {student_id} 不存在")
        score_obj.student_id = student_id

    if class_id is not None:
        class_obj = db.query(Class).filter(Class.id == class_id).first()
        if not class_obj:
            return error_response(msg=f"班级 ID {class_id} 不存在")
        score_obj.class_id = class_id

    if score is not None:
        if not 0 <= score <= 100:
            return error_response(msg="分数必须在 0 到 100 之间")
        score_obj.score = Decimal(str(score))

    if exam_batch is not None:
        score_obj.exam_batch = exam_batch
    if subject is not None:
        score_obj.subject = subject

    db.commit()
    db.refresh(score_obj)

    logger.info("update score success: %s", score_id)
    return success_response(msg="更新成功")


def delete(db: Session, current_user: User, score_id: int) -> dict:
    score_obj = db.query(Score).filter(Score.id == score_id).first()
    if not score_obj:
        return error_response(msg="成绩不存在")

    access_error = _ensure_teacher_score_access(db, current_user, score_obj.class_id)
    if access_error:
        return access_error

    db.delete(score_obj)
    db.commit()

    logger.info("delete score success: %s", score_id)
    return success_response(msg="删除成功")


def batch_delete(db: Session, current_user: User, score_ids: List[int]) -> dict:
    query = db.query(Score).filter(Score.id.in_(score_ids))
    if current_user.role == "teacher":
        teacher_class_ids = _get_teacher_class_ids(db, current_user)
        if not teacher_class_ids:
            return error_response(code=403, msg="当前教师无权删除这些成绩")
        query = query.filter(Score.class_id.in_(teacher_class_ids))

    deleted = query.delete(synchronize_session=False)
    db.commit()

    logger.info("batch delete scores success: %s", deleted)
    return success_response(msg=f"成功删除 {deleted} 条")


def get_stats(
    db: Session,
    current_user: User,
    class_id: Optional[int] = None,
    exam_batch: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict:
    query = _scoped_score_query(db, current_user)

    if class_id:
        query = query.filter(Score.class_id == class_id)
    if exam_batch:
        query = query.filter(Score.exam_batch == exam_batch)
    if subject:
        query = query.filter(Score.subject == subject)

    stats_query = (
        query.with_entities(
            Score.subject,
            func.avg(Score.score).label("average"),
            func.max(Score.score).label("maximum"),
            func.min(Score.score).label("minimum"),
            func.count(Score.id).label("count"),
        )
        .group_by(Score.subject)
        .all()
    )

    data = []
    for item in stats_query:
        data.append(
            {
                "subject": item.subject,
                "average": round(float(item.average), 2),
                "maximum": float(item.maximum),
                "minimum": float(item.minimum),
                "count": item.count,
            }
        )

    return success_response(data=data)


def import_excel(db: Session, file: UploadFile) -> dict:
    valid_data, parse_errors = parse_import_excel(file, "score")
    if parse_errors and not valid_data:
        return error_response(msg="文件解析失败", data={"error_list": parse_errors})

    class_names = [row.get("班级名称", "") for row in valid_data if row.get("班级名称")]
    class_map = {}
    if class_names:
        classes = db.query(Class).filter(Class.name.in_(class_names)).all()
        class_map = {item.name: item for item in classes}

    student_nos = [row.get("学号", "") for row in valid_data if row.get("学号")]
    student_map = {}
    if student_nos:
        students = db.query(Student).filter(Student.student_no.in_(student_nos)).all()
        student_map = {item.student_no: item for item in students}

    success_count = 0
    error_list = list(parse_errors)

    for idx, row in enumerate(valid_data, start=2):
        student_no = str(row.get("学号", "")).strip()
        class_name = str(row.get("班级名称", "")).strip()
        exam_batch = str(row.get("考试批次", "")).strip()
        subject = str(row.get("科目", "")).strip()
        score_str = str(row.get("分数", "")).strip()

        student = student_map.get(student_no)
        if not student:
            error_list.append({"row": idx, "message": f"学号“{student_no}”不存在"})
            continue

        class_obj = class_map.get(class_name)
        if not class_obj:
            error_list.append({"row": idx, "message": f"班级“{class_name}”不存在"})
            continue

        try:
            score = float(score_str)
        except ValueError:
            error_list.append({"row": idx, "message": f"分数“{score_str}”不是有效数字"})
            continue

        if not 0 <= score <= 100:
            error_list.append({"row": idx, "message": f"分数“{score_str}”不在 0 到 100 范围内"})
            continue

        db.add(
            Score(
                student_id=student.id,
                class_id=class_obj.id,
                exam_batch=exam_batch,
                subject=subject,
                score=Decimal(str(score)),
            )
        )
        success_count += 1

    db.commit()
    logger.info("import scores success=%s failed=%s", success_count, len(error_list))

    return success_response(
        msg=f"成功导入 {success_count} 条",
        data={"success_count": success_count, "error_list": error_list},
    )


def export_excel(
    db: Session,
    current_user: User,
    student_id: Optional[int] = None,
    class_id: Optional[int] = None,
    exam_batch: Optional[str] = None,
    subject: Optional[str] = None,
) -> StreamingResponse:
    query = _scoped_score_query(db, current_user)

    if student_id:
        query = query.filter(Score.student_id == student_id)
    if class_id:
        query = query.filter(Score.class_id == class_id)
    if exam_batch:
        query = query.filter(Score.exam_batch == exam_batch)
    if subject:
        query = query.filter(Score.subject == subject)

    scores = query.order_by(Score.id.desc()).all()
    student_ids = [item.student_id for item in scores]
    class_ids = [item.class_id for item in scores]
    student_map = {}
    class_map = {}

    if student_ids:
        students = db.query(Student).filter(Student.id.in_(student_ids)).all()
        student_map = {item.id: item for item in students}

    if class_ids:
        classes = db.query(Class).filter(Class.id.in_(class_ids)).all()
        class_map = {item.id: item for item in classes}

    rows = []
    for item in scores:
        student = student_map.get(item.student_id)
        rows.append(
            {
                "学号": student.student_no if student else "",
                "姓名": student.name if student else "",
                "班级名称": class_map.get(item.class_id).name if class_map.get(item.class_id) else "",
                "考试批次": item.exam_batch,
                "科目": item.subject,
                "分数": float(item.score),
            }
        )

    logger.info("export scores success: %s", len(rows))
    return generate_score_excel(rows)


def get_template() -> StreamingResponse:
    return download_template("score")


def _scoped_score_query(db: Session, current_user: User):
    query = db.query(Score)
    if current_user.role == "student":
        student = get_student_by_user_id(db, current_user.id)
        if not student:
            return query.filter(Score.id == -1)
        return query.filter(Score.student_id == student.id)

    if current_user.role == "teacher":
        teacher_class_ids = _get_teacher_class_ids(db, current_user)
        if not teacher_class_ids:
            return query.filter(Score.id == -1)
        return query.filter(Score.class_id.in_(teacher_class_ids))

    return query


def _get_teacher_class_ids(db: Session, current_user: User) -> list[int]:
    teacher = db.query(Teacher).filter(Teacher.name == current_user.name).first()
    if not teacher or not teacher.class_ids:
        return []
    return [int(item.strip()) for item in teacher.class_ids.split(",") if item.strip()]


def _ensure_teacher_score_access(db: Session, current_user: User, class_id: Optional[int]) -> Optional[dict]:
    if current_user.role != "teacher":
        return None
    teacher_class_ids = _get_teacher_class_ids(db, current_user)
    if not class_id or class_id not in teacher_class_ids:
        return error_response(code=403, msg="当前教师无权操作该成绩")
    return None
