# -*- coding: utf-8 -*-
"""
AI 工具统一路由入口
==================
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_db, get_current_user
from database.models.user import User
from services.ai.comment_generator import CommentRequest, generate_comment
from services.ai.discipline_coach import DisciplineRequest, generate_discipline_script
from services.ai.notice_polisher import NoticeRequest, polish_notice
from services.ai.rule_bot import RuleQARequest, answer_rule_question
from services.ai.score_diagnosis import ScoreDiagnosisRequest, diagnose_score
from services.ai.meeting_planner import MeetingRequest, plan_meeting
from services.ai.mock_interview import InterviewRequest, mock_interview
from services.ai.group_helper import (
    GroupConfirmRequest,
    GroupRequest,
    confirm_admin_grouping,
    smart_grouping,
)

router = APIRouter(prefix="/api/ai", tags=["AI工具"])


@router.post("/comment")
async def api_generate_comment(
    request: CommentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await generate_comment(db, current_user, request)


@router.post("/discipline")
async def api_generate_discipline(
    request: DisciplineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await generate_discipline_script(db, current_user, request)


@router.post("/notice")
async def api_polish_notice(
    request: NoticeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await polish_notice(db, current_user, request)


@router.post("/rule-qa")
async def api_rule_qa(
    request: RuleQARequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await answer_rule_question(db, current_user, request)


@router.post("/score-diagnosis")
async def api_diagnose_score(
    request: ScoreDiagnosisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await diagnose_score(db, current_user, request)


@router.post("/meeting")
async def api_plan_meeting(
    request: MeetingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await plan_meeting(db, current_user, request)


@router.post("/interview")
async def api_mock_interview(
    request: InterviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await mock_interview(db, current_user, request)


@router.post("/group")
async def api_smart_grouping(
    request: GroupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await smart_grouping(db, current_user, request)


@router.post("/group/confirm")
def api_confirm_grouping(
    request: GroupConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return confirm_admin_grouping(db, current_user, request)
