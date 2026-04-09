from __future__ import annotations

from sqlalchemy.orm import Session

from core.response import error_response, success_response
from database.models.student_tag_definition import StudentTagDefinition
from database.models.user import User


VALID_SCOPE = {"school", "grade", "class"}
VALID_POLARITY = {"positive", "neutral", "negative"}


def list_definitions(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    scope_type: str | None = None,
    scope_value: str | None = None,
    keyword: str | None = None,
):
    query = db.query(StudentTagDefinition)
    if scope_type:
        query = query.filter(StudentTagDefinition.scope_type == scope_type)
    if scope_value:
        query = query.filter(StudentTagDefinition.scope_value == scope_value)
    if keyword:
        query = query.filter(StudentTagDefinition.tag_text.like(f"%{keyword}%"))

    total = query.count()
    rows = (
        query.order_by(StudentTagDefinition.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return success_response(data={"list": [serialize(item) for item in rows], "total": total})


def create_definition(db: Session, current_user: User, data: dict):
    scope_type = data.get("scope_type")
    polarity = data.get("polarity")
    if scope_type not in VALID_SCOPE:
        return error_response(code=400, msg="scope_type 不合法")
    if polarity not in VALID_POLARITY:
        return error_response(code=400, msg="polarity 不合法")
    tag_text = (data.get("tag_text") or "").strip()
    if not tag_text:
        return error_response(code=400, msg="标签内容不能为空")

    record = StudentTagDefinition(
        scope_type=scope_type,
        scope_value=data.get("scope_value"),
        tag_text=tag_text,
        polarity=polarity,
        dimension=data.get("dimension"),
        weight=data.get("weight"),
        description=data.get("description"),
        created_by=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return success_response(data=serialize(record))


def update_definition(db: Session, record_id: int, data: dict):
    record = db.query(StudentTagDefinition).filter(StudentTagDefinition.id == record_id).first()
    if not record:
        return error_response(code=404, msg="标签不存在")

    if "scope_type" in data and data["scope_type"] is not None:
        if data["scope_type"] not in VALID_SCOPE:
            return error_response(code=400, msg="scope_type 不合法")
        record.scope_type = data["scope_type"]
    if "polarity" in data and data["polarity"] is not None:
        if data["polarity"] not in VALID_POLARITY:
            return error_response(code=400, msg="polarity 不合法")
        record.polarity = data["polarity"]
    if "scope_value" in data and data["scope_value"] is not None:
        record.scope_value = data["scope_value"]
    if "tag_text" in data and data["tag_text"] is not None:
        record.tag_text = data["tag_text"].strip()
    if "dimension" in data and data["dimension"] is not None:
        record.dimension = data["dimension"]
    if "weight" in data and data["weight"] is not None:
        record.weight = data["weight"]
    if "description" in data and data["description"] is not None:
        record.description = data["description"]

    db.add(record)
    db.commit()
    db.refresh(record)
    return success_response(data=serialize(record))


def delete_definition(db: Session, record_id: int):
    record = db.query(StudentTagDefinition).filter(StudentTagDefinition.id == record_id).first()
    if not record:
        return error_response(code=404, msg="标签不存在")
    db.delete(record)
    db.commit()
    return success_response(msg="删除成功")


def get_available_definitions(
    db: Session,
    class_id: int | None = None,
    grade: str | None = None,
) -> dict:
    query = db.query(StudentTagDefinition)
    records = query.all()
    filtered = []
    for item in records:
        if item.scope_type == "school":
            filtered.append(item)
        elif item.scope_type == "grade" and grade and item.scope_value == grade:
            filtered.append(item)
        elif item.scope_type == "class" and class_id and item.scope_value == str(class_id):
            filtered.append(item)

    priority = {"class": 3, "grade": 2, "school": 1}
    resolved = {}
    for item in filtered:
        key = item.tag_text
        current = resolved.get(key)
        if not current or priority[item.scope_type] > priority[current.scope_type]:
            resolved[key] = item

    return success_response(data={"list": [serialize(item) for item in resolved.values()]})


def serialize(item: StudentTagDefinition) -> dict:
    return {
        "id": item.id,
        "scope_type": item.scope_type,
        "scope_value": item.scope_value,
        "tag_text": item.tag_text,
        "polarity": item.polarity,
        "dimension": item.dimension,
        "weight": item.weight,
        "description": item.description,
    }
