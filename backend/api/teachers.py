# -*- coding: utf-8 -*-
"""
教师管理路由模块
================
- GET    /api/teachers:          分页查询教师列表（支持关键词搜索、学科筛选，按角色过滤）
- POST   /api/teachers:          新增教师
- PUT    /api/teachers/{id}:     编辑教师信息
- DELETE /api/teachers/{id}:     删除教师（校验班主任绑定）
- POST   /api/teachers/bind-classes:    绑定班级
- POST   /api/teachers/unbind-classes:  解绑班级
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_db, get_current_user, require_role
from database.models.user import User
from schemas.teacher import TeacherCreate, TeacherUpdate, TeacherBindClasses
from services import teacher_service

router = APIRouter(prefix="/api/teachers", tags=["教师管理"])


@router.get("")
def get_teacher_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="关键词（姓名）"),
    subject: Optional[str] = Query(None, description="学科"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    分页查询教师列表
    
    权限过滤：
    - teacher: 仅查看自己
    - admin: 查看全部
    """
    return teacher_service.get_list(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        keyword=keyword,
        subject=subject,
    )


@router.post("")
def create_teacher(
    data: TeacherCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    新增教师
    
    仅admin可操作
    """
    return teacher_service.create(
        db=db,
        name=data.name,
        subject=data.subject,
        title=data.title,
        class_ids=data.class_ids,
    )


@router.put("/{teacher_id}")
def update_teacher(
    teacher_id: int,
    data: TeacherUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    编辑教师信息
    
    仅admin可操作
    """
    return teacher_service.update(
        db=db,
        teacher_id=teacher_id,
        name=data.name,
        subject=data.subject,
        title=data.title,
        class_ids=data.class_ids,
    )


@router.delete("/{teacher_id}")
def delete_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    删除教师
    
    仅admin可操作，班主任需先更换班主任才能删除
    """
    return teacher_service.delete(db=db, teacher_id=teacher_id)


@router.post("/bind-classes")
def bind_teacher_classes(
    data: TeacherBindClasses,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    绑定班级
    
    仅admin可操作
    """
    return teacher_service.bind_classes(
        db=db,
        teacher_id=data.teacher_id,
        class_ids=data.class_ids,
    )


@router.post("/unbind-classes")
def unbind_teacher_classes(
    data: TeacherBindClasses,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    解绑班级
    
    仅admin可操作
    """
    return teacher_service.unbind_classes(
        db=db,
        teacher_id=data.teacher_id,
        class_ids=data.class_ids,
    )
