# -*- coding: utf-8 -*-
"""Append demo data for student care signals.

Safe to re-run: uses a simple guard to avoid duplicate entries on the same date.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from database.connection import SessionLocal
from database.models.student_attendance import StudentAttendance
from database.models.student_behavior_event import StudentBehaviorEvent
from database.models.student_family_contact import StudentFamilyContact
from database.models.student_assistant_summary import StudentAssistantSummary
from services.student_care_schema_guard import ensure_student_care_schema


def _exists_attendance(db, student_id: int, date_value: date) -> bool:
    return (
        db.query(StudentAttendance)
        .filter(StudentAttendance.student_id == student_id, StudentAttendance.date == date_value)
        .first()
        is not None
    )


def _append_attendance(db, student_id: int) -> None:
    today = date.today()
    samples = [
        (today - timedelta(days=2), "late", "demo late"),
        (today - timedelta(days=1), "absent", "demo absent"),
    ]
    for dt, status, remark in samples:
        if _exists_attendance(db, student_id, dt):
            continue
        db.add(
            StudentAttendance(
                student_id=student_id,
                date=dt,
                status=status,
                remark=remark,
            )
        )


def _append_behavior(db, student_id: int) -> None:
    now = datetime.now()
    db.add(
        StudentBehaviorEvent(
            student_id=student_id,
            event_type="conflict",
            event_level="medium",
            event_desc="demo conflict with peer",
            occurred_at=now - timedelta(days=3),
        )
    )


def _append_family_contact(db, student_id: int) -> None:
    db.add(
        StudentFamilyContact(
            student_id=student_id,
            contact_type="phone",
            summary="demo family contact note",
        )
    )


def _append_assistant_summary(db, student_id: int) -> None:
    db.add(
        StudentAssistantSummary(
            student_id=student_id,
            summary_text="demo assistant summary",
            signals_json={
                "signals": [
                    {"dimension": "social", "weight": 0.35, "text": "demo social signal", "type": "assistant_signal"},
                    {"dimension": "emotion", "weight": 0.25, "text": "demo emotion signal", "type": "assistant_signal"},
                ]
            },
        )
    )


def main() -> None:
    ensure_student_care_schema()
    db = SessionLocal()
    try:
        # Default demo targets: student_id 1 and 2.
        for student_id in (1, 2):
            _append_attendance(db, student_id)
            _append_behavior(db, student_id)
            _append_family_contact(db, student_id)
            _append_assistant_summary(db, student_id)
        db.commit()
        print("Demo data appended.")
    except Exception as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


if __name__ == "__main__":
    main()
