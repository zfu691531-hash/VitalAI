# -*- coding: utf-8 -*-
"""Manual utility to rebuild the new rule RAG knowledge base."""

from __future__ import annotations

import os
import sys


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from database.connection import SessionLocal  # noqa: E402
from services.rag.rule_kb_service import rebuild_all_indexes  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        result = rebuild_all_indexes(db)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
