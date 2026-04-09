# -*- coding: utf-8 -*-
"""Student care profile service."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from sqlalchemy import case
from sqlalchemy.orm import Session

from core.response import error_response, success_response
from database.models.class_ import Class
from database.models.score import Score
from database.models.student import Student
from database.models.student_assistant_summary import StudentAssistantSummary
from database.models.student_attendance import StudentAttendance
from database.models.student_behavior_event import StudentBehaviorEvent
from database.models.student_care_observation import StudentCareObservation
from database.models.student_care_profile import StudentCareProfile
from database.models.student_care_signal import StudentCareSignal
from database.models.student_care_agent_record import StudentCareAgentRecord
from database.models.student_care_graph_relation import StudentCareGraphRelation
from database.models.student_family_contact import StudentFamilyContact
from database.models.student_tag_definition import StudentTagDefinition
from database.models.teacher import Teacher
from database.models.user import User
from services.student_care_bayes_config_service import get_effective_bayes_config
from services.student_care_bayes_service import build_bayes_results
from services.student_care_graph_service import student_care_graph_service
from services.student_care_schema_guard import ensure_student_care_schema


DIMENSIONS = ("emotion", "social", "safety", "family", "study", "behavior")

OVERALL_WEIGHTS = {
    "emotion": 0.18,
    "social": 0.18,
    "safety": 0.18,
    "family": 0.18,
    "study": 0.16,
    "behavior": 0.12,
}

MANUAL_GRAPH_RELATION_POLARITY = {
    "peer_support": -1,
    "shared_activity": -1,
    "conflict": 1,
    "bullying_link": 1,
    "concern": 1,
}

ATTENDANCE_BEHAVIOR_WEIGHTS = {
    "late": 0.2,
    "absent": 0.35,
    "early_leave": 0.15,
}

BEHAVIOR_EVENT_WEIGHTS = {
    "low": 0.25,
    "medium": 0.4,
    "high": 0.6,
}

SAFETY_EVENT_TYPES = {"conflict", "bullying", "threat", "dorm_conflict", "cyber_conflict"}

CARE_OBSERVATION_WEIGHTS = {
    "low": 0.18,
    "medium": 0.35,
    "high": 0.55,
}

TIME_DECAY_WINDOWS = (
    (7, 1.0),
    (30, 0.75),
    (90, 0.45),
)

TEXT_NEGATIVE_HINTS = (
    "低落",
    "焦虑",
    "孤立",
    "冲突",
    "打骂",
    "欺凌",
    "受伤",
    "害怕",
    "不耐烦",
    "紧张",
    "回避",
    "独处",
    "迟到",
    "缺勤",
    "早退",
    "请假",
    "困难",
    "压力",
    "异常",
    "波动",
    "无助",
    "失控",
    "退缩",
)

TEXT_POSITIVE_HINTS = (
    "好转",
    "缓解",
    "稳定",
    "支持",
    "陪伴",
    "参与",
    "积极",
    "主动",
    "融入",
    "适应",
    "愿意",
    "恢复",
    "配合",
    "改善",
    "鼓励",
    "同伴支持",
    "共同活动",
    "家长支持",
    "情绪稳定",
)

TAG_SIGNAL_RULES = [
    {"keyword": "心理关爱", "dimension": "emotion", "weight": 0.38, "signal_type": "tag_emotion", "text": "学生标签包含“心理关爱”"},
    {"keyword": "学困生", "dimension": "study", "weight": 0.45, "signal_type": "tag_study", "text": "学生标签包含“学困生”"},
    {"keyword": "家庭困难", "dimension": "family", "weight": 0.52, "signal_type": "tag_family", "text": "学生标签包含“家庭困难”"},
    {"keyword": "待分班", "dimension": "social", "weight": 0.24, "signal_type": "tag_social", "text": "学生当前处于待分班状态"},
    {"keyword": "迟到", "dimension": "behavior", "weight": 0.42, "signal_type": "tag_behavior", "text": "学生标签包含“迟到”"},
    {"keyword": "违纪", "dimension": "behavior", "weight": 0.55, "signal_type": "tag_behavior", "text": "学生标签包含“违纪”"},
    {"keyword": "打架", "dimension": "safety", "weight": 0.62, "signal_type": "tag_safety", "text": "学生标签包含“打架”"},
]

TAG_NEGATIVE_DEFAULT_WEIGHT = 0.35

DIMENSION_LABELS = {
    "emotion": "情绪状态风险",
    "social": "社交融入风险",
    "safety": "校园安全风险",
    "family": "家庭支持风险",
    "study": "学习压力风险",
    "behavior": "行为稳定风险",
}


def get_student_care_profile(db: Session, current_user: User, student_id: int) -> dict:
    ensure_student_care_schema()
    db.rollback()
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return error_response(msg="学生不存在")

    permission_error = _ensure_head_teacher_access(db, current_user, student)
    if permission_error:
        return permission_error

    profile, signals, bayes_results = recalculate_student_care_profile(db, student)
    return success_response(
        data={
            "student": _serialize_student(student, db),
            "profile": _serialize_profile(profile, bayes_results),
            "signals": [_serialize_signal(item) for item in signals],
            "data_quality": _build_data_quality_summary(signals),
            "actions": _build_actions(profile),
        }
    )


def get_student_care_signals(db: Session, current_user: User, student_id: int) -> dict:
    ensure_student_care_schema()
    db.rollback()
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return error_response(msg="学生不存在")

    permission_error = _ensure_head_teacher_access(db, current_user, student)
    if permission_error:
        return permission_error

    _, signals, _ = recalculate_student_care_profile(db, student)
    return success_response(data={"list": [_serialize_signal(item) for item in signals]})


def recalculate_student_care_profile(
    db: Session,
    student: Student,
) -> tuple[StudentCareProfile, list[StudentCareSignal], dict]:
    ensure_student_care_schema()
    db.rollback()
    db.query(StudentCareSignal).filter(StudentCareSignal.student_id == student.id).delete(synchronize_session=False)

    signals_to_create: list[StudentCareSignal] = []
    dimension_scores: dict[str, float] = {key: 0.0 for key in DIMENSIONS}
    trend = "steady"

    tags = _parse_tags(student.tags)
    tag_def_map = _get_tag_definitions(db, student)
    handled_tags: set[str] = set()

    for tag in tags:
        definition = tag_def_map.get(tag)
        if not definition:
            continue
        handled_tags.add(tag)
        if definition.dimension not in DIMENSIONS:
            continue
        polarity = definition.polarity
        weight = definition.weight
        if polarity == "negative":
            weight = weight if weight is not None else TAG_NEGATIVE_DEFAULT_WEIGHT
        else:
            weight = 0.0

        signals_to_create.append(
            StudentCareSignal(
                student_id=student.id,
                class_id=student.class_id,
                signal_type=f"tag_{polarity}",
                dimension=definition.dimension,
                signal_text=f"标签“{tag}”被标注为{_polarity_label(polarity)}",
                signal_weight=weight,
                source="tag_definition",
            )
        )
        if weight:
            dimension_scores[definition.dimension] += weight

    for tag in tags:
        if tag in handled_tags:
            continue
        for rule in TAG_SIGNAL_RULES:
            if rule["keyword"] in tag:
                signal = StudentCareSignal(
                    student_id=student.id,
                    class_id=student.class_id,
                    signal_type=rule["signal_type"],
                    dimension=rule["dimension"],
                    signal_text=rule["text"],
                    signal_weight=rule["weight"],
                    source="student_tag",
                )
                signals_to_create.append(signal)
                dimension_scores[rule["dimension"]] += rule["weight"]

    score_rows = (
        db.query(Score)
        .filter(Score.student_id == student.id)
        .order_by(Score.id.asc())
        .all()
    )
    avg_score = 0.0
    if score_rows:
        numeric_scores = [float(item.score) for item in score_rows]
        avg_score = round(sum(numeric_scores) / len(numeric_scores), 2)
        if avg_score < 70:
            signals_to_create.append(
                StudentCareSignal(
                    student_id=student.id,
                    class_id=student.class_id,
                    signal_type="score_low_average",
                    dimension="study",
                    signal_text=f"学生当前平均分约为 {avg_score}，低于关注阈值",
                    signal_weight=0.4,
                    source="score",
                )
            )
            dimension_scores["study"] += 0.4
        elif avg_score < 80:
            signals_to_create.append(
                StudentCareSignal(
                    student_id=student.id,
                    class_id=student.class_id,
                    signal_type="score_medium_pressure",
                    dimension="study",
                    signal_text=f"学生当前平均分约为 {avg_score}，存在一定学习压力",
                    signal_weight=0.22,
                    source="score",
                )
            )
            dimension_scores["study"] += 0.22

        batch_map = defaultdict(list)
        for item in score_rows:
            batch_map[item.exam_batch].append(float(item.score))
        batch_avgs = [(batch, round(sum(values) / len(values), 2)) for batch, values in batch_map.items()]
        if len(batch_avgs) >= 2:
            prev_avg = batch_avgs[-2][1]
            latest_batch, latest_avg = batch_avgs[-1]
            if latest_avg <= prev_avg - 8:
                signals_to_create.append(
                    StudentCareSignal(
                        student_id=student.id,
                        class_id=student.class_id,
                        signal_type="score_drop",
                        dimension="study",
                        signal_text=f"{latest_batch}较上一阶段平均分下降明显（{prev_avg} -> {latest_avg}）",
                        signal_weight=0.18,
                        source="score",
                    )
                )
                signals_to_create.append(
                    StudentCareSignal(
                        student_id=student.id,
                        class_id=student.class_id,
                        signal_type="score_drop_emotion",
                        dimension="emotion",
                        signal_text=f"{latest_batch}成绩阶段性下滑，需关注情绪波动",
                        signal_weight=0.12,
                        source="score",
                    )
                )
                dimension_scores["study"] += 0.18
                dimension_scores["emotion"] += 0.12
                trend = "up"
    else:
        signals_to_create.append(
            StudentCareSignal(
                student_id=student.id,
                class_id=student.class_id,
                signal_type="score_missing",
                dimension="study",
                signal_text="当前缺少成绩记录，建议结合学习状态进一步观察",
                signal_weight=0.0,
                source="data_gap",
            )
        )
        dimension_scores["study"] += 0.0

    if student.class_id is None:
        signals_to_create.append(
            StudentCareSignal(
                student_id=student.id,
                class_id=student.class_id,
                signal_type="class_unassigned",
                dimension="social",
                signal_text="学生当前未分配班级，需关注融入状态",
                signal_weight=0.16,
                source="student_status",
            )
        )
        dimension_scores["social"] += 0.16

    _append_attendance_signals(db, student, signals_to_create, dimension_scores)
    _append_behavior_event_signals(db, student, signals_to_create, dimension_scores)
    _append_care_observation_signals(db, student, signals_to_create, dimension_scores)
    _append_family_contact_signals(db, student, signals_to_create, dimension_scores)
    _append_assistant_summary_signals(db, student, signals_to_create, dimension_scores)
    _append_manual_graph_relation_signals(db, student, signals_to_create, dimension_scores)
    _append_graph_signals(db, student, signals_to_create, dimension_scores)

    for key in DIMENSIONS:
        dimension_scores[key] = _clamp_score(dimension_scores[key])

    linear_scores = {key: value for key, value in dimension_scores.items()}
    signal_dicts = [_signal_to_dict(item) for item in signals_to_create]
    teacher_reviews = _list_recent_teacher_reviews(db, student.id)
    bayes_config = get_effective_bayes_config(db)
    bayes_results = build_bayes_results(
        dimension_scores=linear_scores,
        signals=signal_dicts,
        teacher_reviews=teacher_reviews,
        bayes_config=bayes_config,
    )
    emotion_bayes = bayes_results.get("emotion")
    if emotion_bayes and emotion_bayes.get("enabled"):
        dimension_scores["emotion"] = _clamp_score(emotion_bayes.get("final_score", dimension_scores["emotion"]))
    family_bayes = bayes_results.get("family")
    if family_bayes and family_bayes.get("enabled"):
        dimension_scores["family"] = _clamp_score(family_bayes.get("final_score", dimension_scores["family"]))
    safety_bayes = bayes_results.get("safety")
    if safety_bayes and safety_bayes.get("enabled"):
        dimension_scores["safety"] = _clamp_score(safety_bayes.get("final_score", dimension_scores["safety"]))
    social_bayes = bayes_results.get("social")
    if social_bayes and social_bayes.get("enabled"):
        dimension_scores["social"] = _clamp_score(social_bayes.get("final_score", dimension_scores["social"]))

    overall_risk = _clamp_score(
        dimension_scores["emotion"] * OVERALL_WEIGHTS["emotion"]
        + dimension_scores["social"] * OVERALL_WEIGHTS["social"]
        + dimension_scores["safety"] * OVERALL_WEIGHTS["safety"]
        + dimension_scores["family"] * OVERALL_WEIGHTS["family"]
        + dimension_scores["study"] * OVERALL_WEIGHTS["study"]
        + dimension_scores["behavior"] * OVERALL_WEIGHTS["behavior"]
    )
    risk_level = _risk_level(overall_risk)

    profile = db.query(StudentCareProfile).filter(StudentCareProfile.student_id == student.id).first()
    if not profile:
        profile = StudentCareProfile(student_id=student.id, class_id=student.class_id)
        db.add(profile)

    profile.class_id = student.class_id
    profile.emotion_score = dimension_scores["emotion"]
    profile.social_score = dimension_scores["social"]
    profile.safety_score = dimension_scores["safety"]
    profile.family_score = dimension_scores["family"]
    profile.study_score = dimension_scores["study"]
    profile.behavior_score = dimension_scores["behavior"]
    profile.overall_risk = overall_risk
    profile.risk_level = risk_level
    profile.trend = trend

    for signal in signals_to_create:
        db.add(signal)

    db.commit()
    db.refresh(profile)
    signals = (
        db.query(StudentCareSignal)
        .filter(StudentCareSignal.student_id == student.id)
        .order_by(StudentCareSignal.signal_weight.desc(), StudentCareSignal.id.desc())
        .all()
    )
    return profile, signals, bayes_results


def _ensure_head_teacher_access(db: Session, current_user: User, student: Student) -> dict | None:
    if current_user.role != "teacher":
        return error_response(code=403, msg="当前仅班主任可查看学生关怀画像")
    if not student.class_id:
        return error_response(code=403, msg="该学生当前未分班，无法查看关怀画像")

    teacher = db.query(Teacher).filter(Teacher.name == current_user.name).first()
    if not teacher:
        return error_response(code=403, msg="未找到当前教师档案")

    class_row = db.query(Class).filter(Class.id == student.class_id).first()
    if not class_row or class_row.head_teacher_id != teacher.id:
        return error_response(code=403, msg="当前仅该学生所属班级班主任可查看关怀画像")
    return None


def _serialize_student(student: Student, db: Session) -> dict:
    class_name = None
    if student.class_id:
        class_row = db.query(Class).filter(Class.id == student.class_id).first()
        class_name = class_row.name if class_row else None
    return {
        "id": student.id,
        "student_no": student.student_no,
        "name": student.name,
        "gender": student.gender,
        "age": student.age,
        "grade": student.grade,
        "class_id": student.class_id,
        "class_name": class_name,
        "tags": student.tags,
    }


def _serialize_profile(profile: StudentCareProfile, bayes_results: dict | None = None) -> dict:
    bayes_results = bayes_results or {}
    safety_bayes = bayes_results.get("safety", {})
    social_bayes = bayes_results.get("social", {})
    return {
        "student_id": profile.student_id,
        "class_id": profile.class_id,
        "emotion_score": round(profile.emotion_score or 0, 4),
        "emotion_linear_score": round(float(bayes_results.get("emotion", {}).get("linear_score", profile.emotion_score or 0)), 4),
        "emotion_bayes_posterior": round(float(bayes_results.get("emotion", {}).get("posterior", 0)), 4),
        "emotion_final_score": round(float(bayes_results.get("emotion", {}).get("final_score", profile.emotion_score or 0)), 4),
        "social_score": round(profile.social_score or 0, 4),
        "social_linear_score": round(float(social_bayes.get("linear_score", profile.social_score or 0)), 4),
        "social_bayes_posterior": round(float(social_bayes.get("posterior", 0)), 4),
        "social_final_score": round(float(social_bayes.get("final_score", profile.social_score or 0)), 4),
        "safety_score": round(profile.safety_score or 0, 4),
        "safety_linear_score": round(float(safety_bayes.get("linear_score", profile.safety_score or 0)), 4),
        "safety_bayes_posterior": round(float(safety_bayes.get("posterior", 0)), 4),
        "safety_final_score": round(float(safety_bayes.get("final_score", profile.safety_score or 0)), 4),
        "family_score": round(profile.family_score or 0, 4),
        "family_linear_score": round(float(bayes_results.get("family", {}).get("linear_score", profile.family_score or 0)), 4),
        "family_bayes_posterior": round(float(bayes_results.get("family", {}).get("posterior", 0)), 4),
        "family_final_score": round(float(bayes_results.get("family", {}).get("final_score", profile.family_score or 0)), 4),
        "study_score": round(profile.study_score or 0, 4),
        "behavior_score": round(profile.behavior_score or 0, 4),
        "overall_risk": round(profile.overall_risk or 0, 4),
        "risk_level": profile.risk_level,
        "trend": profile.trend,
        "bayes_results": bayes_results,
        "updated_at": str(profile.updated_at) if profile.updated_at else None,
    }


def _serialize_signal(signal: StudentCareSignal) -> dict:
    return {
        "id": signal.id,
        "signal_type": signal.signal_type,
        "dimension": signal.dimension,
        "dimension_label": DIMENSION_LABELS.get(signal.dimension, signal.dimension),
        "signal_text": signal.signal_text,
        "signal_weight": round(signal.signal_weight or 0, 4),
        "source": signal.source,
        "created_at": str(signal.created_at) if signal.created_at else None,
    }


def _signal_to_dict(signal: StudentCareSignal) -> dict:
    return {
        "signal_type": signal.signal_type,
        "dimension": signal.dimension,
        "signal_text": signal.signal_text,
        "signal_weight": round(signal.signal_weight or 0, 4),
        "source": signal.source,
    }


def _build_data_quality_summary(signals: list[StudentCareSignal]) -> dict:
    signal_rows = [_signal_to_dict(item) for item in signals]
    missing_sources = [
        item["signal_type"]
        for item in signal_rows
        if item["source"] == "data_gap"
    ]
    positive_sources = len([item for item in signal_rows if float(item.get("signal_weight") or 0) > 0])
    protective_sources = len([item for item in signal_rows if float(item.get("signal_weight") or 0) < 0])
    return {
        "missing_sources": missing_sources,
        "missing_count": len(missing_sources),
        "positive_signal_count": positive_sources,
        "protective_signal_count": protective_sources,
        "evidence_sufficient": len(missing_sources) <= 1 and positive_sources >= 2,
    }


def _list_recent_teacher_reviews(db: Session, student_id: int, limit: int = 3) -> list[dict]:
    records = (
        db.query(StudentCareAgentRecord)
        .filter(
            StudentCareAgentRecord.student_id == student_id,
            StudentCareAgentRecord.review_status == "confirmed",
        )
        .order_by(StudentCareAgentRecord.confirmed_at.desc(), StudentCareAgentRecord.id.desc())
        .limit(limit)
        .all()
    )
    reviews = []
    for item in records:
        reviews.append(
            {
                "record_id": item.id,
                "resolution_status": item.resolution_status,
                "teacher_notes": item.teacher_notes,
            }
        )
    return reviews


def _build_actions(profile: StudentCareProfile) -> list[str]:
    actions: list[str] = []
    dimension_pairs = [
        ("social", profile.social_score, "建议班主任近期安排一次非正式谈话，关注该生在班级中的同伴关系。"),
        ("safety", profile.safety_score, "建议尽快核实是否存在宿舍、课间或放学时段的安全风险。"),
        ("family", profile.family_score, "建议在合适时机了解学生家庭支持情况，必要时联系家长沟通。"),
        ("emotion", profile.emotion_score, "建议关注学生近期情绪变化，先以低压力方式建立信任沟通。"),
        ("study", profile.study_score, "建议结合最近成绩波动，帮助学生拆解当前学习压力来源。"),
        ("behavior", profile.behavior_score, "建议结合近期行为标签，观察是否存在明显节律或状态波动。"),
    ]
    for _, score, action in sorted(dimension_pairs, key=lambda item: item[1], reverse=True):
        if score >= 0.5:
            actions.append(action)
    if not actions:
        actions.append("当前整体风险较低，建议继续保持常规关注。")
    return actions[:3]


def _parse_tags(tags: str | None) -> list[str]:
    if not tags:
        return []
    return [item.strip() for item in tags.split(",") if item.strip()]


def _get_tag_definitions(db: Session, student: Student) -> dict[str, StudentTagDefinition]:
    query = db.query(StudentTagDefinition)
    records = query.all()
    filtered = []
    for item in records:
        if item.scope_type == "school":
            filtered.append(item)
        elif item.scope_type == "grade" and student.grade and item.scope_value == student.grade:
            filtered.append(item)
        elif item.scope_type == "class" and student.class_id and item.scope_value == str(student.class_id):
            filtered.append(item)

    priority = {"class": 3, "grade": 2, "school": 1}
    resolved: dict[str, StudentTagDefinition] = {}
    for item in filtered:
        key = item.tag_text
        current = resolved.get(key)
        if not current or priority[item.scope_type] > priority[current.scope_type]:
            resolved[key] = item
    return resolved


def _polarity_label(polarity: str) -> str:
    return {"positive": "正向", "neutral": "中性", "negative": "负向"}.get(polarity, "中性")


def _clamp_score(value: float) -> float:
    return round(min(max(value, 0.0), 1.0), 4)


def _days_since(value: date | datetime | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        target = value.date()
    else:
        target = value
    return max((date.today() - target).days, 0)


def _time_decay_multiplier(value: date | datetime | None) -> float:
    days = _days_since(value)
    if days is None:
        return 1.0
    for window, factor in TIME_DECAY_WINDOWS:
        if days <= window:
            return factor
    return 0.2


def _apply_time_decay(weight: float, value: date | datetime | None) -> float:
    return round(float(weight or 0) * _time_decay_multiplier(value), 4)


def _classify_text_polarity(text: str | None) -> str:
    content = str(text or "").strip()
    if not content:
        return "neutral"

    negative_hits = sum(1 for item in TEXT_NEGATIVE_HINTS if item in content)
    positive_hits = sum(1 for item in TEXT_POSITIVE_HINTS if item in content)
    if negative_hits > positive_hits and negative_hits > 0:
        return "negative"
    if positive_hits > negative_hits and positive_hits > 0:
        return "positive"
    return "neutral"


def _polarity_weight(base_weight: float, polarity: str, positive_factor: float = 0.6, neutral_factor: float = 0.0) -> float:
    if polarity == "negative":
        return round(float(base_weight or 0), 4)
    if polarity == "positive":
        return round(-abs(float(base_weight or 0)) * positive_factor, 4)
    return round(float(base_weight or 0) * neutral_factor, 4)


def _append_data_gap_signal(
    student: Student,
    signals_to_create: list[StudentCareSignal],
    dimension: str,
    signal_type: str,
    signal_text: str,
) -> None:
    signals_to_create.append(
        StudentCareSignal(
            student_id=student.id,
            class_id=student.class_id,
            signal_type=signal_type,
            dimension=dimension,
            signal_text=signal_text,
            signal_weight=0.0,
            source="data_gap",
        )
    )


def _risk_level(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.5:
        return "medium"
    if score >= 0.3:
        return "attention"
    return "low"


def _append_attendance_signals(
    db: Session,
    student: Student,
    signals_to_create: list[StudentCareSignal],
    dimension_scores: dict[str, float],
) -> None:
    records = (
        db.query(StudentAttendance)
        .filter(StudentAttendance.student_id == student.id)
        .order_by(StudentAttendance.date.desc(), StudentAttendance.id.desc())
        .all()
    )
    if not records:
        _append_data_gap_signal(
            student,
            signals_to_create,
            "behavior",
            "attendance_missing",
            "当前缺少出勤记录，暂不额外提升行为风险，建议补充近期出勤数据。",
        )
        return
    late_count = sum(1 for item in records if item.status == "late")
    absent_count = sum(1 for item in records if item.status == "absent")
    early_count = sum(1 for item in records if item.status == "early_leave")
    if late_count:
        relevant_records = [item for item in records if item.status == "late"]
        weight = min(
            0.4,
            sum(_apply_time_decay(ATTENDANCE_BEHAVIOR_WEIGHTS["late"], item.date) for item in relevant_records),
        )
        remark_summary = _attendance_remark_summary(records, "late")
        signals_to_create.append(
            StudentCareSignal(
                student_id=student.id,
                class_id=student.class_id,
                signal_type="attendance_late",
                dimension="behavior",
                signal_text=f"近阶段出现 {late_count} 次迟到记录{remark_summary}",
                signal_weight=weight,
                source="attendance",
            )
        )
        dimension_scores["behavior"] += weight
    if absent_count:
        relevant_records = [item for item in records if item.status == "absent"]
        weight = min(
            0.6,
            sum(_apply_time_decay(ATTENDANCE_BEHAVIOR_WEIGHTS["absent"], item.date) for item in relevant_records),
        )
        remark_summary = _attendance_remark_summary(records, "absent")
        signals_to_create.append(
            StudentCareSignal(
                student_id=student.id,
                class_id=student.class_id,
                signal_type="attendance_absent",
                dimension="behavior",
                signal_text=f"近阶段出现 {absent_count} 次缺勤记录{remark_summary}",
                signal_weight=weight,
                source="attendance",
            )
        )
        dimension_scores["behavior"] += weight
    if early_count:
        relevant_records = [item for item in records if item.status == "early_leave"]
        weight = min(
            0.3,
            sum(_apply_time_decay(ATTENDANCE_BEHAVIOR_WEIGHTS["early_leave"], item.date) for item in relevant_records),
        )
        remark_summary = _attendance_remark_summary(records, "early_leave")
        signals_to_create.append(
            StudentCareSignal(
                student_id=student.id,
                class_id=student.class_id,
                signal_type="attendance_early_leave",
                dimension="behavior",
                signal_text=f"近阶段出现 {early_count} 次早退记录{remark_summary}",
                signal_weight=weight,
                source="attendance",
            )
        )
        dimension_scores["behavior"] += weight


def _attendance_remark_summary(records: list[StudentAttendance], status: str) -> str:
    remarks = []
    for item in records:
        if item.status != status or not item.remark:
            continue
        remark = item.remark.strip()
        if not remark:
            continue
        remarks.append(f"{item.date}：{remark}")
        if len(remarks) >= 3:
            break
    if not remarks:
        return ""
    return "；备注：" + "；".join(remarks)


def _append_behavior_event_signals(
    db: Session,
    student: Student,
    signals_to_create: list[StudentCareSignal],
    dimension_scores: dict[str, float],
) -> None:
    records = (
        db.query(StudentBehaviorEvent)
        .filter(StudentBehaviorEvent.student_id == student.id)
        .order_by(StudentBehaviorEvent.occurred_at.desc(), StudentBehaviorEvent.id.desc())
        .all()
    )
    if not records:
        _append_data_gap_signal(
            student,
            signals_to_create,
            "behavior",
            "behavior_event_missing",
            "当前缺少行为事件记录，行为风险判断主要依赖其他来源。",
        )
        return

    for item in records[:5]:
        weight = _apply_time_decay(BEHAVIOR_EVENT_WEIGHTS.get(item.event_level, 0.2), item.occurred_at)
        dimension = "behavior"
        if item.event_type in SAFETY_EVENT_TYPES:
            dimension = "safety"
        signals_to_create.append(
            StudentCareSignal(
                student_id=student.id,
                class_id=student.class_id,
                signal_type=f"behavior_{item.event_type}",
                dimension=dimension,
                signal_text=f"行为事件：{item.event_desc}",
                signal_weight=weight,
                source="behavior_event",
            )
        )
        dimension_scores[dimension] += weight


def _append_care_observation_signals(
    db: Session,
    student: Student,
    signals_to_create: list[StudentCareSignal],
    dimension_scores: dict[str, float],
) -> None:
    records = (
        db.query(StudentCareObservation)
        .filter(StudentCareObservation.student_id == student.id)
        .order_by(StudentCareObservation.observed_at.desc(), StudentCareObservation.id.desc())
        .all()
    )
    if not records:
        _append_data_gap_signal(
            student,
            signals_to_create,
            "emotion",
            "care_observation_missing",
            "当前缺少关怀观察记录，情绪与社交判断的证据充分度有限。",
        )
        return

    for item in records[:6]:
        if item.dimension not in DIMENSIONS:
            continue
        base_weight = _apply_time_decay(CARE_OBSERVATION_WEIGHTS.get(item.observation_level, 0.25), item.observed_at)
        polarity = _classify_text_polarity(item.summary)
        weight = _polarity_weight(base_weight, polarity, positive_factor=0.65, neutral_factor=0.1)
        signals_to_create.append(
            StudentCareSignal(
                student_id=student.id,
                class_id=student.class_id,
                signal_type=(
                    f"care_observation_positive_{item.observation_type}"
                    if polarity == "positive"
                    else (
                        f"care_observation_neutral_{item.observation_type}"
                        if polarity == "neutral"
                        else f"care_observation_{item.observation_type}"
                    )
                ),
                dimension=item.dimension,
                signal_text=(
                    f"关怀观察（{_observation_type_label(item.observation_type)}，"
                    f"{_observation_level_label(item.observation_level)}）：{item.summary}"
                ),
                signal_weight=weight,
                source="care_observation",
            )
        )
        dimension_scores[item.dimension] += weight


def _observation_type_label(value: str) -> str:
    return {
        "care_talk": "关怀谈话",
        "emotion_observation": "情绪观察",
        "social_observation": "社交观察",
        "safety_observation": "安全线索",
        "study_observation": "学习状态",
        "behavior_observation": "行为观察",
        "follow_up": "后续跟进",
    }.get(value, value)


def _observation_level_label(value: str) -> str:
    return {
        "low": "轻度关注",
        "medium": "中度关注",
        "high": "高度关注",
    }.get(value, value)


def _append_family_contact_signals(
    db: Session,
    student: Student,
    signals_to_create: list[StudentCareSignal],
    dimension_scores: dict[str, float],
) -> None:
    records = (
        db.query(StudentFamilyContact)
        .filter(StudentFamilyContact.student_id == student.id)
        .order_by(StudentFamilyContact.id.desc())
        .all()
    )
    if not records:
        _append_data_gap_signal(
            student,
            signals_to_create,
            "family",
            "family_contact_missing",
            "当前缺少家校沟通记录，家庭支持判断的证据充分度有限。",
        )
        return

    latest = records[0]
    if latest.summary:
        base_weight = _apply_time_decay(0.25, latest.created_at)
        polarity = _classify_text_polarity(latest.summary)
        weight = _polarity_weight(base_weight, polarity, positive_factor=0.75, neutral_factor=0.05)
        signals_to_create.append(
            StudentCareSignal(
                student_id=student.id,
                class_id=student.class_id,
                signal_type=(
                    "family_contact_positive"
                    if polarity == "positive"
                    else ("family_contact_neutral" if polarity == "neutral" else "family_contact_summary")
                ),
                dimension="family",
                signal_text=f"家校沟通摘要：{latest.summary}",
                signal_weight=weight,
                source="family_contact",
            )
        )
        dimension_scores["family"] += weight


def _append_assistant_summary_signals(
    db: Session,
    student: Student,
    signals_to_create: list[StudentCareSignal],
    dimension_scores: dict[str, float],
) -> None:
    records = (
        db.query(StudentAssistantSummary)
        .filter(StudentAssistantSummary.student_id == student.id)
        .order_by(StudentAssistantSummary.id.desc())
        .all()
    )
    if not records:
        _append_data_gap_signal(
            student,
            signals_to_create,
            "emotion",
            "assistant_summary_missing",
            "当前缺少 AI 助手摘要，文本线索型证据暂不充分。",
        )
        return
    latest = records[0]
    if not latest.signals_json:
        _append_data_gap_signal(
            student,
            signals_to_create,
            "emotion",
            "assistant_signal_missing",
            "当前 AI 助手摘要未提取到结构化信号，文本线索型证据暂不充分。",
        )
        return
    signals = latest.signals_json.get("signals", [])
    for item in signals[:6]:
        dimension = item.get("dimension")
        base_weight = _apply_time_decay(float(item.get("weight", 0.2)), latest.created_at)
        if dimension not in DIMENSIONS:
            continue
        text = item.get("text", "鍔╂墜瀵硅瘽绾跨储")
        polarity = _classify_text_polarity(text)
        weight = _polarity_weight(base_weight, polarity, positive_factor=0.55, neutral_factor=0.15)
        signals_to_create.append(
            StudentCareSignal(
                student_id=student.id,
                class_id=student.class_id,
                signal_type=(
                    f"{item.get('type', 'assistant_signal')}_positive"
                    if polarity == "positive"
                    else (
                        f"{item.get('type', 'assistant_signal')}_neutral"
                        if polarity == "neutral"
                        else item.get("type", "assistant_signal")
                    )
                ),
                dimension=dimension,
                signal_text=item.get("text", "助手对话线索"),
                signal_weight=round(weight, 4),
                source="assistant_summary",
            )
        )
        dimension_scores[dimension] += weight


def _append_graph_signals(
    db: Session,
    student: Student,
    signals_to_create: list[StudentCareSignal],
    dimension_scores: dict[str, float],
) -> None:
    graph_signals = student_care_graph_service.build_graph_signals(db, student)
    for item in graph_signals:
        dimension = item.get("dimension")
        if dimension not in DIMENSIONS:
            continue
        weight = _clamp_score(float(item.get("signal_weight", 0)))
        signals_to_create.append(
            StudentCareSignal(
                student_id=student.id,
                class_id=student.class_id,
                signal_type=item.get("signal_type", "graph_signal"),
                dimension=dimension,
                signal_text=item.get("signal_text", "关系图谱发现新的辅助线索"),
                signal_weight=weight,
                source=item.get("source", "graph"),
            )
        )
        dimension_scores[dimension] += weight


def _append_manual_graph_relation_signals(
    db: Session,
    student: Student,
    signals_to_create: list[StudentCareSignal],
    dimension_scores: dict[str, float],
) -> None:
    records = (
        db.query(StudentCareGraphRelation)
        .filter(StudentCareGraphRelation.student_id == student.id)
        .order_by(
            case((StudentCareGraphRelation.occurred_at.is_(None), 1), else_=0).asc(),
            StudentCareGraphRelation.occurred_at.desc(),
            StudentCareGraphRelation.id.desc(),
        )
        .all()
    )
    if not records:
        return

    level_weights = {
        "low": 0.12,
        "medium": 0.2,
        "high": 0.3,
    }
    relation_labels = {
        "peer_support": "同伴支持",
        "conflict": "冲突关系",
        "bullying_link": "欺凌关联",
        "shared_activity": "共同活动",
        "concern": "重点关注",
    }

    for item in records[:8]:
        if item.dimension not in DIMENSIONS:
            continue
        weight = round(
            level_weights.get(item.relation_level, 0.16)
            * MANUAL_GRAPH_RELATION_POLARITY.get(item.relation_type, 1),
            4,
        )
        if item.target_type == "student" and item.target_student_id:
            target_student = db.query(Student).filter(Student.id == item.target_student_id).first()
            target_name = target_student.name if target_student else f"学生{item.target_student_id}"
            signal_text = (
                f"手工图谱关系：与 {target_name} 存在"
                f"{relation_labels.get(item.relation_type, item.relation_type)}线索，备注：{item.summary}"
            )
            signal_type = f"graph_manual_student_{item.relation_type}"
        else:
            title = item.event_title or relation_labels.get(item.relation_type, "手工事件")
            signal_text = f"手工图谱事件：{title}，备注：{item.summary}"
            signal_type = f"graph_manual_event_{item.relation_type}"

        signals_to_create.append(
            StudentCareSignal(
                student_id=student.id,
                class_id=student.class_id,
                signal_type=signal_type,
                dimension=item.dimension,
                signal_text=signal_text,
                signal_weight=weight,
                source="graph",
            )
        )
        dimension_scores[item.dimension] += weight
