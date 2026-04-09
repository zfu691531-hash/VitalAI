# -*- coding: utf-8 -*-
"""
成绩管理路由模块
================
- GET    /api/scores:          分页查询成绩列表（支持学生、班级、批次、科目筛选）
- POST   /api/scores:          新增成绩
- PUT    /api/scores/{id}:     编辑成绩
- DELETE /api/scores/{id}:     删除成绩
- DELETE /api/scores/batch:    批量删除成绩
- POST   /api/scores/import:   批量导入成绩（Excel）
- GET    /api/scores/export:   批量导出成绩（Excel）
- GET    /api/scores/stats:    成绩统计
- GET    /api/scores/template: 下载导入模板
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.deps import get_db, get_current_user, require_role
from database.models.user import User
from schemas.score import ScoreCreate, ScoreUpdate
from schemas.common import BatchDeleteRequest
from services import score_service

router = APIRouter(prefix="/api/scores", tags=["成绩管理"])


@router.get("")
def get_score_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    student_id: Optional[int] = Query(None, description="学生ID"),
    class_id: Optional[int] = Query(None, description="班级ID"),
    exam_batch: Optional[str] = Query(None, description="考试批次"),
    subject: Optional[str] = Query(None, description="科目"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    分页查询成绩列表
    
    三级权限过滤：
    - student: 仅查看自己
    - teacher: 仅查看本班
    - admin: 查看全部
    """
    return score_service.get_list(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        student_id=student_id,
        class_id=class_id,
        exam_batch=exam_batch,
        subject=subject,
    )


@router.get("/stats")
def get_score_stats(
    class_id: Optional[int] = Query(None, description="班级ID"),
    exam_batch: Optional[str] = Query(None, description="考试批次"),
    subject: Optional[str] = Query(None, description="科目"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    成绩统计（平均分、最高分、最低分）
    
    按科目分组统计
    """
    return score_service.get_stats(
        db=db,
        current_user=current_user,
        class_id=class_id,
        exam_batch=exam_batch,
        subject=subject,
    )


@router.post("")
def create_score(
    data: ScoreCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
):
    """
    新增成绩
    
    admin和teacher可操作，分数范围0-100
    """
    return score_service.create(
        db=db,
        student_id=data.student_id,
        class_id=data.class_id,
        exam_batch=data.exam_batch,
        subject=data.subject,
        score=data.score,
    )


@router.put("/{score_id}")
def update_score(
    score_id: int,
    data: ScoreUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
):
    """
    编辑成绩
    
    admin和teacher可操作
    """
    return score_service.update(
        db=db,
        score_id=score_id,
        student_id=data.student_id,
        class_id=data.class_id,
        exam_batch=data.exam_batch,
        subject=data.subject,
        score=data.score,
    )


@router.delete("/{score_id}")
def delete_score(
    score_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
):
    """
    删除成绩
    
    仅admin可操作
    """
    return score_service.delete(db=db, current_user=current_user, score_id=score_id)


@router.delete("/batch")
def batch_delete_scores(
    data: BatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
):
    """
    批量删除成绩
    
    仅admin可操作
    """
    return score_service.batch_delete(db=db, current_user=current_user, score_ids=data.ids)


@router.post("/import")
def import_scores(
    file: UploadFile = File(..., description="Excel文件"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
):
    """
    批量导入成绩
    
    admin和teacher可操作
    """
    return score_service.import_excel(db=db, file=file)


@router.get("/export")
def export_scores(
    student_id: Optional[int] = Query(None, description="学生ID"),
    class_id: Optional[int] = Query(None, description="班级ID"),
    exam_batch: Optional[str] = Query(None, description="考试批次"),
    subject: Optional[str] = Query(None, description="科目"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    批量导出成绩
    
    按筛选条件导出Excel
    """
    return score_service.export_excel(
        db=db,
        current_user=current_user,
        student_id=student_id,
        class_id=class_id,
        exam_batch=exam_batch,
        subject=subject,
    )


@router.get("/template")
def download_score_template():
    """
    下载批量导入Excel模板
    """
    return score_service.get_template()
