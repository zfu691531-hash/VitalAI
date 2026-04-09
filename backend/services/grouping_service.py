# -*- coding: utf-8 -*-
"""教师分组方案服务。"""

from sqlalchemy.orm import Session

from core.response import error_response, success_response
from database.models.class_ import Class
from database.models.group_scheme import GroupScheme
from database.models.student import Student
from database.models.teacher import Teacher
from database.models.user import User


def list_schemes(
    db: Session,
    current_user: User,
    page: int = 1,
    page_size: int = 10,
    class_id: int | None = None,
) -> dict:
    query = db.query(GroupScheme)

    if current_user.role == "teacher":
        query = query.filter(GroupScheme.created_by == current_user.id)

    if class_id:
        query = query.filter(GroupScheme.class_id == class_id)

    total = query.count()
    schemes = (
        query.order_by(GroupScheme.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return success_response(
        data={
            "list": [_serialize_scheme(item) for item in schemes],
            "total": total,
        }
    )


def get_scheme(db: Session, current_user: User, scheme_id: int) -> dict:
    scheme = db.query(GroupScheme).filter(GroupScheme.id == scheme_id).first()
    if not scheme:
        return error_response(msg="分组方案不存在")
    if current_user.role == "teacher" and scheme.created_by != current_user.id:
        return error_response(code=403, msg="无权查看该分组方案")

    return success_response(data=_serialize_scheme(scheme, include_students=True, db=db))


def create_scheme(
    db: Session,
    current_user: User,
    class_id: int,
    scheme_name: str,
    group_count: int,
    balance_factors: list[str],
    source_type: str,
    remark: str | None,
    assignments: list[dict],
) -> dict:
    access_error = _ensure_class_access(db, current_user, class_id)
    if access_error:
        return access_error

    validation_error = _validate_group_assignments(db, class_id, group_count, assignments)
    if validation_error:
        return validation_error

    scheme = GroupScheme(
        class_id=class_id,
        created_by=current_user.id,
        scheme_name=scheme_name,
        group_count=group_count,
        balance_factors=balance_factors,
        group_result_json=assignments,
        source_type=source_type,
        remark=remark,
    )
    db.add(scheme)
    db.commit()
    db.refresh(scheme)

    return success_response(msg="分组方案已保存", data={"id": scheme.id})


def update_scheme(
    db: Session,
    current_user: User,
    scheme_id: int,
    payload: dict,
) -> dict:
    scheme = db.query(GroupScheme).filter(GroupScheme.id == scheme_id).first()
    if not scheme:
        return error_response(msg="分组方案不存在")
    if current_user.role == "teacher" and scheme.created_by != current_user.id:
        return error_response(code=403, msg="无权修改该分组方案")

    next_group_count = payload.get("group_count", scheme.group_count)
    next_assignments = payload.get("assignments", scheme.group_result_json)

    validation_error = _validate_group_assignments(db, scheme.class_id, next_group_count, next_assignments)
    if validation_error:
        return validation_error

    for field, value in payload.items():
        if value is not None:
            if field == "assignments":
                scheme.group_result_json = value
            else:
                setattr(scheme, field, value)

    db.commit()
    db.refresh(scheme)
    return success_response(msg="分组方案已更新", data={"id": scheme.id})


def delete_scheme(db: Session, current_user: User, scheme_id: int) -> dict:
    scheme = db.query(GroupScheme).filter(GroupScheme.id == scheme_id).first()
    if not scheme:
        return error_response(msg="分组方案不存在")
    if current_user.role == "teacher" and scheme.created_by != current_user.id:
        return error_response(code=403, msg="无权删除该分组方案")

    db.delete(scheme)
    db.commit()
    return success_response(msg="分组方案已删除")


def _serialize_scheme(
    scheme: GroupScheme,
    include_students: bool = False,
    db: Session | None = None,
) -> dict:
    data = {
        "id": scheme.id,
        "class_id": scheme.class_id,
        "created_by": scheme.created_by,
        "scheme_name": scheme.scheme_name,
        "group_count": scheme.group_count,
        "balance_factors": scheme.balance_factors or [],
        "group_result_json": scheme.group_result_json or [],
        "source_type": scheme.source_type,
        "remark": scheme.remark,
        "created_at": scheme.created_at,
        "updated_at": scheme.updated_at,
    }

    if include_students and db is not None:
        student_ids = []
        for group in data["group_result_json"]:
            student_ids.extend(group.get("student_ids", []))
        student_map = {
            item.id: item
            for item in db.query(Student).filter(Student.id.in_(student_ids)).all()
        }
        data["group_result_json"] = [
            {
                **group,
                "students": [
                    {
                        "id": student.id,
                        "name": student.name,
                        "gender": student.gender,
                        "tags": student.tags or "",
                    }
                    for student_id in group.get("student_ids", [])
                    if (student := student_map.get(student_id))
                ],
            }
            for group in data["group_result_json"]
        ]

    return data


def _ensure_class_access(db: Session, current_user: User, class_id: int) -> dict | None:
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        return error_response(msg="班级不存在")

    if current_user.role == "admin":
        return None

    if current_user.role != "teacher":
        return error_response(code=403, msg="当前角色无权操作教师分组")

    teacher = db.query(Teacher).filter(Teacher.name == current_user.name).first()
    if not teacher or not teacher.class_ids:
        return error_response(code=403, msg="当前教师没有可操作班级")

    class_ids = [int(item.strip()) for item in teacher.class_ids.split(",") if item.strip()]
    if class_id not in class_ids:
        return error_response(code=403, msg="当前教师无权操作该班级")
    return None


def _validate_group_assignments(
    db: Session,
    class_id: int,
    group_count: int,
    assignments: list[dict],
) -> dict | None:
    students = db.query(Student).filter(Student.class_id == class_id).all()
    student_ids = {item.id for item in students}
    if not student_ids:
        return error_response(msg="当前班级暂无学生")

    if len(assignments) != group_count:
        return error_response(msg="分组数量与方案内容不一致")

    assigned_ids: list[int] = []
    for index, group in enumerate(assignments, start=1):
        if group.get("group_no") != index:
            return error_response(msg="分组序号必须从 1 开始连续排列")
        assigned_ids.extend(group.get("student_ids", []))

    if len(assigned_ids) != len(set(assigned_ids)):
        return error_response(msg="同一学生不能被分配到多个小组")

    if set(assigned_ids) != student_ids:
        return error_response(msg="分组结果必须完整覆盖班级全部学生")

    return None
