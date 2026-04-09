# -*- coding: utf-8 -*-
"""Personal assistant APIs."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.deps import get_current_user, get_db
from database.models.user import User
from schemas.assistant import (
    AssistantMessageRequest,
    AssistantSessionClearRequest,
    AssistantSessionCreateRequest,
)
from services import assistant_service

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.get("/session")
def get_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return assistant_service.get_or_create_active_session(db, current_user)


@router.post("/session")
def create_session(
    payload: AssistantSessionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return assistant_service.get_or_create_active_session(db, current_user, payload.title)


@router.post("/session/clear")
def clear_session(
    payload: AssistantSessionClearRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return assistant_service.clear_session_messages(db, current_user, payload.session_id)


@router.post("/message")
async def send_message(
    payload: AssistantMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await assistant_service.send_message(db, current_user, payload.session_id, payload.content)


@router.post("/message/stream")
async def stream_message(
    payload: AssistantMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    generator = assistant_service.stream_message_events(db, current_user, payload.session_id, payload.content)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
