# -*- coding: utf-8 -*-
"""Student routes."""

from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_db, require_role
from database.models.user import User
from schemas.common import BatchDeleteRequest
from schemas.student import StudentCreate, StudentUpdate
from services import student_service

router = APIRouter(prefix="/api/students", tags=["学生管理"])


@router.get("")
def get_student_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="关键词"),
    grade: Optional[str] = Query(None, description="年级"),
    class_id: Optional[int] = Query(None, description="班级ID"),
    tag: Optional[str] = Query(None, description="标签"),
    gender: Optional[str] = Query(None, description="性别"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return student_service.get_list(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        keyword=keyword,
        grade=grade,
        class_id=class_id,
        tag=tag,
        gender=gender,
    )


@router.post("")
def create_student(
    data: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
):
    return student_service.create(
        db=db,
        current_user=current_user,
        student_no=data.student_no,
        name=data.name,
        gender=data.gender,
        age=data.age,
        grade=data.grade,
        class_id=data.class_id,
        contact=data.contact,
        specialty=data.specialty,
        tags=data.tags,
    )


@router.put("/{student_id}")
def update_student(
    student_id: int,
    data: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
):
    payload = data.model_dump(exclude_unset=True)
    return student_service.update(
        db=db,
        current_user=current_user,
        student_id=student_id,
        student_no=payload.get("student_no", student_service._UNSET),
        name=payload.get("name", student_service._UNSET),
        gender=payload.get("gender", student_service._UNSET),
        age=payload.get("age", student_service._UNSET),
        grade=payload.get("grade", student_service._UNSET),
        class_id=payload.get("class_id", student_service._UNSET),
        contact=payload.get("contact", student_service._UNSET),
        specialty=payload.get("specialty", student_service._UNSET),
        tags=payload.get("tags", student_service._UNSET),
    )


@router.delete("/{student_id}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return student_service.delete(db=db, student_id=student_id)


@router.delete("/batch")
def batch_delete_students(
    data: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return student_service.batch_delete(db=db, student_ids=data.ids)


@router.post("/import")
def import_students(
    file: UploadFile = File(..., description="Excel文件"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
):
    return student_service.import_excel(db=db, current_user=current_user, file=file)


@router.get("/export")
def export_students(
    keyword: Optional[str] = Query(None, description="关键词"),
    grade: Optional[str] = Query(None, description="年级"),
    class_id: Optional[int] = Query(None, description="班级ID"),
    tag: Optional[str] = Query(None, description="标签"),
    gender: Optional[str] = Query(None, description="性别"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return student_service.export_excel(
        db=db,
        current_user=current_user,
        keyword=keyword,
        grade=grade,
        class_id=class_id,
        tag=tag,
        gender=gender,
    )


@router.get("/template")
def download_student_template():
    return student_service.get_template()
