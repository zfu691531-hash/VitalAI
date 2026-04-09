# -*- coding: utf-8 -*-
"""Schema guard for newly added RAG tables."""

from __future__ import annotations

from threading import Lock

from database.connection import engine
from database.models.knowledge_sync_task import KnowledgeSyncTask
from database.models.rule_qa_feedback import RuleQaFeedback
from database.models.rule_qa_record import RuleQaRecord
from database.models.school_rule_chunk import SchoolRuleChunk


_schema_ready = False
_schema_lock = Lock()


def ensure_rule_rag_schema() -> None:
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        tables = [
            RuleQaRecord.__table__,
            RuleQaFeedback.__table__,
            SchoolRuleChunk.__table__,
            KnowledgeSyncTask.__table__,
        ]
        for table in tables:
            table.create(bind=engine, checkfirst=True)
        _schema_ready = True
