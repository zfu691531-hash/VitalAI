# -*- coding: utf-8 -*-
"""AI grouping and placement suggestion service."""

from typing import List, Optional
import json

from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.response import error_response, success_response
from database.models.class_ import Class
from database.models.score import Score
from database.models.student import Student
from database.models.teacher import Teacher
from database.models.user import User
from services.ai.base import ai_client, save_history
from utils.logger import logger


class GroupRequest(BaseModel):
    mode: str = Field(..., description="teacher/admin")
    class_id: Optional[int] = Field(None, description="教师分组班级ID")
    grade: Optional[str] = Field(None, description="管理员正式分班年级")
    group_count: int = Field(..., description="分组数量")
    balance_factors: List[str] = Field(default=["score", "gender"], description="均衡因子")
    scenario: Optional[str] = Field(None, description="教师端应用场景")
    background: Optional[str] = Field(None, description="管理员端分班背景")


class GroupConfirmItem(BaseModel):
    class_id: int = Field(..., description="目标班级ID")
    student_ids: List[int] = Field(..., description="学生ID列表")


class GroupConfirmRequest(BaseModel):
    grade: str = Field(..., description="正式分班年级")
    assignments: List[GroupConfirmItem] = Field(..., description="确认后的结果")


async def smart_grouping(
    db: Session,
    current_user: User,
    request: GroupRequest,
) -> dict:
    students: List[Student] = []
    target_classes: List[Class] = []

    if request.mode == "teacher":
        if not request.class_id:
            return error_response(msg="教师分组模式必须选择班级")
        if current_user.role not in {"teacher", "admin"}:
            return error_response(msg="当前角色无权使用教师分组")

        if current_user.role == "teacher":
            teacher = db.query(Teacher).filter(Teacher.name == current_user.name).first()
            if not teacher or not teacher.class_ids:
                return error_response(msg="当前教师没有可操作的班级")
            class_ids = [int(item.strip()) for item in teacher.class_ids.split(",") if item.strip()]
            if request.class_id not in class_ids:
                return error_response(msg="当前教师无权操作该班级")

        students = db.query(Student).filter(Student.class_id == request.class_id).all()
        if not students:
            return error_response(msg="该班级下暂无可分组学生")

    elif request.mode == "admin":
        if current_user.role != "admin":
            return error_response(msg="只有管理员可以执行正式分班建议")
        if not request.grade:
            return error_response(msg="正式分班前必须先选择年级")

        target_classes = (
            db.query(Class)
            .filter(Class.grade == request.grade, Class.status == 1)
            .order_by(Class.name.asc())
            .all()
        )
        if not target_classes:
            return error_response(msg="该年级没有可用班级，无法执行正式分班")

        request.group_count = len(target_classes)
        target_class_ids = [item.id for item in target_classes]
        students = (
            db.query(Student)
            .filter(Student.grade == request.grade, Student.class_id.is_(None))
            .all()
        )
        if not students:
            students = (
                db.query(Student)
                .filter(Student.grade == request.grade, Student.class_id.in_(target_class_ids))
                .all()
            )
        if not students:
            return error_response(msg="该年级没有可用于正式分班的学生")

    else:
        return error_response(msg="无效的分组模式")

    if request.group_count < 1:
        return error_response(msg="分组数量必须大于 0")

    student_data = []
    for student in students:
        avg_score = 60.0
        if "score" in request.balance_factors:
            avg = db.query(func.avg(Score.score)).filter(Score.student_id == student.id).scalar()
            avg_score = float(avg) if avg is not None else 60.0
        student_data.append(
            {
                "id": student.id,
                "student_no": student.student_no,
                "name": student.name,
                "gender": student.gender,
                "grade": student.grade,
                "tags": student.tags or "",
                "avg_score": round(avg_score, 1),
            }
        )

    groups = _balance_group(student_data, request.group_count)

    if request.mode == "admin":
        for index, group in enumerate(groups):
            target_class = target_classes[index]
            group["target_class_id"] = target_class.id
            group["target_class_name"] = target_class.name
            group["target_grade"] = target_class.grade

    description = await _generate_description(request, groups, len(student_data))

    save_history(
        db=db,
        user_id=current_user.id,
        tool_type="group",
        input_params=request.model_dump(),
        content=description,
        class_id=request.class_id,
    )

    return success_response(
        data={
            "mode": request.mode,
            "grade": request.grade,
            "groups": groups,
            "description": description,
            "total_students": len(student_data),
        }
    )


def confirm_admin_grouping(
    db: Session,
    current_user: User,
    request: GroupConfirmRequest,
) -> dict:
    if current_user.role != "admin":
        return error_response(msg="只有管理员可以确认正式分班")

    target_classes = (
        db.query(Class)
        .filter(Class.grade == request.grade, Class.status == 1)
        .order_by(Class.name.asc())
        .all()
    )
    if not target_classes:
        return error_response(msg="该年级没有可用班级")

    target_class_map = {item.id: item for item in target_classes}
    target_class_ids = set(target_class_map.keys())
    if len(request.assignments) != len(target_class_ids):
        return error_response(msg="确认结果与目标班级数量不一致")

    assignment_class_ids = {item.class_id for item in request.assignments}
    if assignment_class_ids != target_class_ids:
        return error_response(msg="确认结果中的班级与目标年级班级不一致")

    eligible_students = db.query(Student).filter(Student.grade == request.grade, Student.class_id.is_(None)).all()
    if not eligible_students:
        eligible_students = db.query(Student).filter(Student.grade == request.grade, Student.class_id.in_(target_class_ids)).all()

    eligible_student_ids = {student.id for student in eligible_students}
    if not eligible_student_ids:
        return error_response(msg="当前没有可用于正式分班的学生")

    assigned_student_ids: List[int] = []
    for item in request.assignments:
        assigned_student_ids.extend(item.student_ids)

    if len(assigned_student_ids) != len(set(assigned_student_ids)):
        return error_response(msg="确认结果中存在重复分配的学生")
    if set(assigned_student_ids) != eligible_student_ids:
        return error_response(msg="确认结果没有完整覆盖本次应分班的学生")

    student_map = {
        student.id: student
        for student in db.query(Student).filter(Student.id.in_(eligible_student_ids)).all()
    }
    for item in request.assignments:
        target_class = target_class_map[item.class_id]
        for student_id in item.student_ids:
            student = student_map.get(student_id)
            if not student:
                return error_response(msg=f"学生 {student_id} 不存在")
            student.class_id = item.class_id
            student.grade = target_class.grade

    db.flush()
    for class_obj in target_classes:
        class_obj.current_count = db.query(Student).filter(Student.class_id == class_obj.id).count()
    db.commit()

    logger.info(
        "admin confirmed grouping, grade=%s, class_count=%s, student_count=%s",
        request.grade,
        len(target_classes),
        len(assigned_student_ids),
    )
    return success_response(
        msg="正式分班已生效",
        data={
            "grade": request.grade,
            "class_count": len(target_classes),
            "student_count": len(assigned_student_ids),
        },
    )


async def _generate_description(request: GroupRequest, groups: list[dict], total_students: int) -> str:
    system_prompt = (
        "你是一位教务管理专家。请根据给出的分组或分班结果，"
        "写一段120字以内的中文说明，概括均衡性、适用性与需要注意的地方。"
    )
    context_lines = [
        f"模式: {request.mode}",
        f"均衡因子: {', '.join(request.balance_factors)}",
        f"学生总数: {total_students}",
        f"分组数量: {request.group_count}",
    ]
    if request.mode == "teacher" and request.scenario:
        context_lines.append(f"应用场景: {request.scenario}")
    if request.mode == "admin" and request.background:
        context_lines.append(f"分班背景: {request.background}")
    user_prompt = "\n".join(context_lines) + f"\n结果:\n{json.dumps(groups, ensure_ascii=False, indent=2)}"
    return await ai_client.call(system_prompt, user_prompt)


def _balance_group(students: List[dict], group_count: int) -> List[dict]:
    sorted_students = sorted(students, key=lambda item: item["avg_score"], reverse=True)
    groups = [
        {"students": [], "avg_score": 0, "male_count": 0, "female_count": 0}
        for _ in range(group_count)
    ]

    if group_count == 1:
        groups[0]["students"] = sorted_students
        groups[0]["male_count"] = sum(1 for item in sorted_students if item["gender"] == "male")
        groups[0]["female_count"] = len(sorted_students) - groups[0]["male_count"]
    else:
        direction = 1
        group_index = 0
        for student in sorted_students:
            groups[group_index]["students"].append(student)
            if student["gender"] == "male":
                groups[group_index]["male_count"] += 1
            else:
                groups[group_index]["female_count"] += 1

            group_index += direction
            if group_index >= group_count:
                group_index = group_count - 2
                direction = -1
            elif group_index < 0:
                group_index = 1
                direction = 1

    for group in groups:
        if group["students"]:
            group["avg_score"] = round(
                sum(student["avg_score"] for student in group["students"]) / len(group["students"]),
                1,
            )

    return groups
