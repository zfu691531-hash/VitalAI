# -*- coding: utf-8 -*-
"""
班级管理路由模块
================
- GET    /api/classes:          分页查询班级列表（支持年级、状态筛选）
- GET    /api/classes/all:      获取所有班级（下拉选择用）
- POST   /api/classes:          新增班级
- PUT    /api/classes/{id}:     编辑班级信息
- DELETE /api/classes/{id}:     删除班级（校验关联数据）
- POST   /api/classes/bind-students:    绑定学生
- POST   /api/classes/unbind-students:  解绑学生
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps import get_db, get_current_user, require_role
from database.models.user import User
from schemas.class_ import ClassCreate, ClassUpdate, ClassStudentBind
from services import class_service

router = APIRouter(prefix="/api/classes", tags=["班级管理"])


@router.get("")
def get_class_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    grade: Optional[str] = Query(None, description="年级"),
    status: Optional[int] = Query(1, description="状态：1-在读，0-毕业"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    分页查询班级列表
    
    默认过滤在读班级(status=1)
    """
    return class_service.get_list(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        grade=grade,
        status=status,
    )


@router.get("/all")
def get_all_classes(
    status: Optional[int] = Query(1, description="状态：1-在读，0-毕业"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取所有班级（下拉选择用）
    """
    return class_service.get_all(db=db, status=status)


@router.post("")
def create_class(
    data: ClassCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    新增班级
    
    仅admin可操作，需指定班主任
    """
    return class_service.create(
        db=db,
        grade=data.grade,
        name=data.name,
        head_teacher_id=data.head_teacher_id,
        max_count=data.max_count,
        status=data.status,
    )


@router.put("/{class_id}")
def update_class(
    class_id: int,
    data: ClassUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    编辑班级信息
    
    仅admin可操作
    """
    return class_service.update(
        db=db,
        class_id=class_id,
        grade=data.grade,
        name=data.name,
        head_teacher_id=data.head_teacher_id,
        max_count=data.max_count,
        status=data.status,
    )


@router.delete("/{class_id}")
def delete_class(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """
    删除班级
    
    仅admin可操作，有学生或成绩时拒绝删除
    """
    return class_service.delete(db=db, class_id=class_id)


@router.post("/bind-students")
def bind_class_students(
    data: ClassStudentBind,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
):
    """
    绑定学生到班级
    
    admin和teacher可操作
    """
    return class_service.bind_students(
        db=db,
        class_id=data.class_id,
        student_ids=data.student_ids,
    )


@router.post("/unbind-students")
def unbind_class_students(
    data: ClassStudentBind,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
):
    """
    从班级解绑学生
    
    admin和teacher可操作
    """
    return class_service.unbind_students(
        db=db,
        class_id=data.class_id,
        student_ids=data.student_ids,
    )
