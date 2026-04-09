# -*- coding: utf-8 -*-
"""Bayesian helper service for student care."""

from __future__ import annotations

from core.student_care_bayes_config import STUDENT_CARE_BAYES_CONFIG


BRUISE_HINTS = ("淤青", "伤", "受伤", "流血", "打了", "被打")
WORRY_HINTS = ("担忧", "害怕", "恐惧", "不安", "紧张")
FAMILY_VIOLENCE_HINTS = ("家暴", "殴打", "打骂", "被打", "暴力")
DISTRESS_HINTS = ("难受", "害怕", "低落", "崩溃", "想哭", "不想上学", "焦虑", "压抑")
FAMILY_ISSUE_HINTS = ("家庭", "家里", "父母", "监护", "照顾", "支持不足", "困难", "不耐烦", "打牌")


def _clamp_probability(value: float) -> float:
    return round(min(max(value, 0.0), 1.0), 4)


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _has_any_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    normalized = _normalize_text(text)
    return any(keyword in normalized for keyword in keywords)


def _match_safety_evidence(signals: list[dict], teacher_reviews: list[dict]) -> list[dict]:
    matched: dict[str, dict] = {}

    for item in signals:
        source = item.get("source")
        signal_type = item.get("signal_type")
        text = item.get("signal_text") or ""

        if source == "assistant_summary" and (
            signal_type == "assistant_safety_disclosure" or _has_any_keyword(text, BRUISE_HINTS)
        ):
            matched["assistant_self_report_assault"] = {"key": "assistant_self_report_assault", "text": text}

        if source == "attendance" and _has_any_keyword(text, BRUISE_HINTS):
            matched["attendance_bruise_remark"] = {"key": "attendance_bruise_remark", "text": text}

        if source == "attendance" and _has_any_keyword(text, WORRY_HINTS):
            matched["attendance_worried_remark"] = {"key": "attendance_worried_remark", "text": text}

        if source == "behavior_event" and signal_type == "behavior_conflict":
            matched["behavior_conflict"] = {"key": "behavior_conflict", "text": text}

        if source == "behavior_event" and signal_type == "behavior_bullying":
            matched["behavior_bullying"] = {"key": "behavior_bullying", "text": text}

        if source == "family_contact" and _has_any_keyword(text, FAMILY_VIOLENCE_HINTS):
            matched["family_violence_hint"] = {"key": "family_violence_hint", "text": text}

        if source == "graph" and signal_type == "graph_conflict_cooccurrence":
            matched["graph_conflict_cooccurrence"] = {"key": "graph_conflict_cooccurrence", "text": text}

    for review in teacher_reviews or []:
        resolution_status = review.get("resolution_status")
        if resolution_status == "resolved":
            matched["teacher_review_resolved"] = {
                "key": "teacher_review_resolved",
                "text": review.get("teacher_notes") or "老师确认已处理完成",
            }
        elif resolution_status == "false_alarm":
            matched["teacher_review_false_alarm"] = {
                "key": "teacher_review_false_alarm",
                "text": review.get("teacher_notes") or "老师确认本次为误报",
            }

    return list(matched.values())


def _match_emotion_evidence(signals: list[dict], teacher_reviews: list[dict]) -> list[dict]:
    matched: dict[str, dict] = {}

    for item in signals:
        source = item.get("source")
        signal_type = item.get("signal_type")
        text = item.get("signal_text") or ""

        if source == "score" and signal_type == "score_drop_emotion":
            matched["score_drop_emotion"] = {"key": "score_drop_emotion", "text": text}

        if source == "attendance" and _has_any_keyword(text, WORRY_HINTS):
            matched["attendance_worried_remark"] = {"key": "attendance_worried_remark", "text": text}

        if source == "assistant_summary" and (
            signal_type == "assistant_safety_disclosure" or _has_any_keyword(text, DISTRESS_HINTS)
        ):
            matched["assistant_self_report_distress"] = {"key": "assistant_self_report_distress", "text": text}

        if source == "care_observation" and item.get("dimension") == "emotion":
            matched["care_observation_emotion"] = {"key": "care_observation_emotion", "text": text}
            if signal_type == "care_observation_care_talk":
                matched["care_talk_low_mood"] = {"key": "care_talk_low_mood", "text": text}

        if source == "family_contact" and _has_any_keyword(text, ("不耐烦", "冲突", "压力", "打骂")):
            matched["family_negative_contact"] = {"key": "family_negative_contact", "text": text}

    for review in teacher_reviews or []:
        resolution_status = review.get("resolution_status")
        if resolution_status == "resolved":
            matched["teacher_review_resolved"] = {
                "key": "teacher_review_resolved",
                "text": review.get("teacher_notes") or "老师确认情绪问题已缓解",
            }
        elif resolution_status == "false_alarm":
            matched["teacher_review_false_alarm"] = {
                "key": "teacher_review_false_alarm",
                "text": review.get("teacher_notes") or "老师确认当前并无持续情绪风险",
            }

    return list(matched.values())


def _match_family_evidence(signals: list[dict], teacher_reviews: list[dict]) -> list[dict]:
    matched: dict[str, dict] = {}

    for item in signals:
        source = item.get("source")
        signal_type = item.get("signal_type")
        text = item.get("signal_text") or ""

        if signal_type == "tag_family":
            matched["tag_family_hardship"] = {"key": "tag_family_hardship", "text": text}

        if source == "family_contact" and _has_any_keyword(text, FAMILY_ISSUE_HINTS):
            matched["family_contact_negative"] = {"key": "family_contact_negative", "text": text}

        if source == "family_contact" and _has_any_keyword(text, FAMILY_VIOLENCE_HINTS):
            matched["family_violence_hint"] = {"key": "family_violence_hint", "text": text}

        if source == "attendance" and _has_any_keyword(text, ("家庭", "家里", "家长", "父母")):
            matched["attendance_family_issue"] = {"key": "attendance_family_issue", "text": text}

        if source == "assistant_summary" and _has_any_keyword(text, ("家里", "父母", "家庭", "没人管", "不想回家")):
            matched["assistant_family_distress"] = {"key": "assistant_family_distress", "text": text}

    for review in teacher_reviews or []:
        resolution_status = review.get("resolution_status")
        if resolution_status == "resolved":
            matched["teacher_review_resolved"] = {
                "key": "teacher_review_resolved",
                "text": review.get("teacher_notes") or "老师确认家庭支持问题已缓解",
            }
        elif resolution_status == "false_alarm":
            matched["teacher_review_false_alarm"] = {
                "key": "teacher_review_false_alarm",
                "text": review.get("teacher_notes") or "老师确认当前并无持续家庭支持风险",
            }

    return list(matched.values())


def _match_social_evidence(signals: list[dict], teacher_reviews: list[dict]) -> list[dict]:
    matched: dict[str, dict] = {}

    for item in signals:
        source = item.get("source")
        signal_type = item.get("signal_type")
        text = item.get("signal_text") or ""

        if source == "graph" and signal_type == "graph_social_isolation":
            matched["graph_social_isolation"] = {"key": "graph_social_isolation", "text": text}

    for review in teacher_reviews or []:
        resolution_status = review.get("resolution_status")
        if resolution_status == "resolved":
            matched["teacher_review_resolved"] = {
                "key": "teacher_review_resolved",
                "text": review.get("teacher_notes") or "教师确认当前社交融入问题已缓解",
            }
        elif resolution_status == "false_alarm":
            matched["teacher_review_false_alarm"] = {
                "key": "teacher_review_false_alarm",
                "text": review.get("teacher_notes") or "教师确认当前并无持续社交风险",
            }

    return list(matched.values())


def _calculate_posterior(prior: float, likelihood_ratios: list[float]) -> float:
    prior = _clamp_probability(prior)
    if prior <= 0:
        return 0.0
    if prior >= 1:
        return 1.0
    odds = prior / (1 - prior)
    for lr in likelihood_ratios:
        odds *= max(lr, 0.01)
    posterior = odds / (1 + odds)
    return _clamp_probability(posterior)


def build_bayes_result(
    dimension: str,
    linear_score: float,
    signals: list[dict],
    teacher_reviews: list[dict] | None = None,
    bayes_config: dict | None = None,
) -> dict:
    config_source = bayes_config or STUDENT_CARE_BAYES_CONFIG
    config = config_source.get(dimension, {})
    if not config.get("enabled"):
        return {"enabled": False, "dimension": dimension}

    teacher_reviews = teacher_reviews or []
    evidence_rules = config.get("evidence_rules", {})
    if dimension == "safety":
        matches = _match_safety_evidence(signals, teacher_reviews)
    elif dimension == "emotion":
        matches = _match_emotion_evidence(signals, teacher_reviews)
    elif dimension == "family":
        matches = _match_family_evidence(signals, teacher_reviews)
    elif dimension == "social":
        matches = _match_social_evidence(signals, teacher_reviews)
    else:
        matches = []

    evidence_details = []
    likelihood_ratios = []
    for item in matches:
        lr = float(evidence_rules.get(item["key"], 1.0))
        likelihood_ratios.append(lr)
        evidence_details.append(
            {
                "key": item["key"],
                "matched": True,
                "lr": round(lr, 4),
                "text": item.get("text") or "",
            }
        )

    prior = float(config.get("prior", 0.0))
    posterior = _calculate_posterior(prior, likelihood_ratios)
    blend_alpha = float(config.get("blend_alpha", 0.7))
    final_score = _clamp_probability((blend_alpha * linear_score) + ((1 - blend_alpha) * posterior))

    return {
        "enabled": True,
        "dimension": dimension,
        "prior": _clamp_probability(prior),
        "linear_score": _clamp_probability(linear_score),
        "posterior": posterior,
        "blend_alpha": round(blend_alpha, 4),
        "final_score": final_score,
        "evidence_keys": [item["key"] for item in evidence_details],
        "evidence_details": evidence_details,
    }


def build_bayes_results(
    dimension_scores: dict[str, float],
    signals: list[dict],
    teacher_reviews: list[dict] | None = None,
    bayes_config: dict | None = None,
) -> dict:
    results = {}
    config_source = bayes_config or STUDENT_CARE_BAYES_CONFIG
    for dimension, linear_score in dimension_scores.items():
        config = config_source.get(dimension)
        if not config or not config.get("enabled"):
            continue
        results[dimension] = build_bayes_result(
            dimension=dimension,
            linear_score=float(linear_score or 0.0),
            signals=signals,
            teacher_reviews=teacher_reviews,
            bayes_config=config_source,
        )
    return results
