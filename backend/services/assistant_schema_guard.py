# -*- coding: utf-8 -*-
"""Schema guard for personal assistant tables."""

from __future__ import annotations

from threading import Lock

from database.connection import engine
from database.models.assistant_message import AssistantMessage
from database.models.assistant_session import AssistantSession


_schema_ready = False
_schema_lock = Lock()


def ensure_assistant_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return

    with _schema_lock:
        if _schema_ready:
            return

        for table in (AssistantSession.__table__, AssistantMessage.__table__):
            table.create(bind=engine, checkfirst=True)
        engine.dispose()
        _schema_ready = True
