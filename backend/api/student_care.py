# -*- coding: utf-8 -*-
"""Student care profile routes."""

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_db, require_role
from core.response import error_response, success_response
from database.models.student import Student
from database.models.user import User
from schemas.student_care_bayes import StudentCareBayesRuleUpdate
from schemas.student_care_agent import StudentCareAgentReviewUpdate
from services import student_care_agent_service
from services import student_care_bayes_config_service
from services import student_care_isolation_service
from services import student_care_service
from services.student_care_graph_service import student_care_graph_service

router = APIRouter(prefix="/api/student-care", tags=["student-care"])


@router.get("/profile/{student_id}")
def get_student_care_profile(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return student_care_service.get_student_care_profile(db, current_user, student_id)


@router.get("/signals/{student_id}")
def get_student_care_signals(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return student_care_service.get_student_care_signals(db, current_user, student_id)


@router.post("/recalculate", response_model=None)
def recalculate_student_care_bulk(
    class_id: int | None = None,
    grade: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        return error_response(code=403, msg="仅管理员可执行批量重算")
    query = db.query(Student)
    if class_id:
        query = query.filter(Student.class_id == class_id)
    if grade:
        query = query.filter(Student.grade == grade)
    students = query.all()
    for student in students:
        student_care_service.recalculate_student_care_profile(db, student)
    return success_response(data={"count": len(students)})


@router.get("/agent-eval/{student_id}")
async def get_student_care_agent_eval(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await student_care_agent_service.evaluate_student_care_agent(db, current_user, student_id)


@router.get("/isolation-bn/{student_id}")
def get_student_care_isolation_bn(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return student_care_isolation_service.get_student_isolation_analysis(db, current_user, student_id)


@router.get("/agent-eval-history/{student_id}")
def get_student_care_agent_history(
    student_id: int,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return student_care_agent_service.list_agent_eval_history(
        db=db,
        current_user=current_user,
        student_id=student_id,
        page=page,
        page_size=page_size,
    )


@router.post("/agent-eval-review/{record_id}")
def confirm_student_care_agent_review(
    record_id: int,
    payload: StudentCareAgentReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return student_care_agent_service.confirm_agent_eval_review(
        db=db,
        current_user=current_user,
        record_id=record_id,
        payload=payload,
    )


@router.get("/bayes-rules")
def list_student_care_bayes_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return student_care_bayes_config_service.list_bayes_rules(db=db)


@router.put("/bayes-rules/{dimension}/{evidence_key:path}")
def update_student_care_bayes_rule(
    dimension: str,
    evidence_key: str,
    payload: StudentCareBayesRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return student_care_bayes_config_service.update_bayes_rule(
        db=db,
        current_user=current_user,
        dimension=dimension,
        evidence_key=evidence_key,
        payload=payload.model_dump(),
    )


@router.get("/graph-health")
def get_student_care_graph_health(
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {"admin", "teacher"}:
        return error_response(code=403, msg="无权限查看关系图谱状态")
    return success_response(data=student_care_graph_service.healthcheck())


@router.post("/graph-sync/{student_id}")
def sync_student_care_graph(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return error_response(code=404, msg="学生不存在")
    if current_user.role != "admin":
        permission_error = student_care_service._ensure_head_teacher_access(db, current_user, student)
        if permission_error:
            return permission_error
    return success_response(data=student_care_graph_service.sync_student_graph(db, student_id))


@router.get("/graph-view/{student_id}")
def get_student_care_graph_view(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return error_response(code=404, msg="学生不存在")
    if current_user.role != "admin":
        permission_error = student_care_service._ensure_head_teacher_access(db, current_user, student)
        if permission_error:
            return permission_error
    return success_response(data=student_care_graph_service.get_student_graph_view(db, student_id))


@router.get("/agent-stats")
def get_student_care_agent_stats(
    start_date: str | None = None,
    end_date: str | None = None,
    class_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return student_care_agent_service.get_agent_stats(
        db=db,
        current_user=current_user,
        start_date=start_date,
        end_date=end_date,
        class_id=class_id,
    )


@router.get("/evaluation-summary")
def get_student_care_evaluation_summary(
    start_date: str | None = None,
    end_date: str | None = None,
    class_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return student_care_agent_service.get_agent_evaluation_summary(
        db=db,
        current_user=current_user,
        start_date=start_date,
        end_date=end_date,
        class_id=class_id,
    )


@router.get("/evaluation-detail")
def get_student_care_evaluation_detail(
    start_date: str | None = None,
    end_date: str | None = None,
    class_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return student_care_agent_service.get_agent_evaluation_detail(
        db=db,
        current_user=current_user,
        start_date=start_date,
        end_date=end_date,
        class_id=class_id,
    )


@router.get("/agent-stats-export")
def export_student_care_agent_stats(
    start_date: str | None = None,
    end_date: str | None = None,
    class_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    csv_text, filename = student_care_agent_service.export_agent_stats_csv(
        db=db,
        current_user=current_user,
        start_date=start_date,
        end_date=end_date,
        class_id=class_id,
    )
    if not csv_text:
        return error_response(code=400, msg=filename or "导出失败")
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/evaluation-summary-export")
def export_student_care_evaluation_summary(
    start_date: str | None = None,
    end_date: str | None = None,
    class_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    csv_text, filename = student_care_agent_service.export_agent_evaluation_summary_csv(
        db=db,
        current_user=current_user,
        start_date=start_date,
        end_date=end_date,
        class_id=class_id,
    )
    if not csv_text:
        return error_response(code=400, msg=filename or "瀵煎嚭澶辫触")
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
