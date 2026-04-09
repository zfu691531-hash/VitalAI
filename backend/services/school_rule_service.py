# -*- coding: utf-8 -*-
"""School rule CRUD service."""

from typing import Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from core.response import error_response, success_response
from database.models.school_rule import SchoolRule
from database.models.user import User
from services.rag.rule_kb_service import delete_rule_index, rebuild_rule_index
from utils.logger import logger


def get_list(db: Session, page: int = 1, page_size: int = 10, category: Optional[str] = None) -> dict:
    query = db.query(SchoolRule)
    if category:
        query = query.filter(SchoolRule.category == category)

    total = query.count()
    rules = (
        query.order_by(desc(SchoolRule.updated_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return success_response(
        data={
            "list": [
                {
                    "id": item.id,
                    "category": item.category,
                    "title": item.title,
                    "content": item.content,
                    "updated_by": item.updated_by,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                }
                for item in rules
            ],
            "total": total,
        }
    )


def get_categories(db: Session) -> dict:
    rows = db.query(SchoolRule.category, func.count(SchoolRule.id).label("count")).group_by(SchoolRule.category).all()
    return success_response(data=[{"name": item.category, "count": item.count} for item in rows])


def create(db: Session, current_user: User, category: str, title: str, content: str) -> dict:
    rule = SchoolRule(category=category, title=title, content=content, updated_by=current_user.id)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    rebuild_rule_index(db, rule.id)
    logger.info("create school rule: %s", title)
    return success_response(msg="创建成功", data={"id": rule.id})


def update(
    db: Session,
    current_user: User,
    rule_id: int,
    category: Optional[str] = None,
    title: Optional[str] = None,
    content: Optional[str] = None,
) -> dict:
    rule = db.query(SchoolRule).filter(SchoolRule.id == rule_id).first()
    if not rule:
        return error_response(msg="校规不存在")

    if category is not None:
        rule.category = category
    if title is not None:
        rule.title = title
    if content is not None:
        rule.content = content
    rule.updated_by = current_user.id

    db.commit()
    db.refresh(rule)
    rebuild_rule_index(db, rule.id)
    logger.info("update school rule: %s", rule_id)
    return success_response(msg="更新成功")


def delete(db: Session, rule_id: int) -> dict:
    rule = db.query(SchoolRule).filter(SchoolRule.id == rule_id).first()
    if not rule:
        return error_response(msg="校规不存在")

    db.delete(rule)
    db.commit()
    delete_rule_index(db, rule_id)
    logger.info("delete school rule: %s", rule_id)
    return success_response(msg="删除成功")
