# -*- coding: utf-8 -*-
"""Bayesian helper config for student care."""

STUDENT_CARE_BAYES_CONFIG = {
    "emotion": {
        "enabled": True,
        "prior": 0.15,
        "blend_alpha": 0.75,
        "evidence_rules": {
            "score_drop_emotion": 1.8,
            "attendance_worried_remark": 1.9,
            "assistant_self_report_distress": 2.8,
            "care_observation_emotion": 2.4,
            "care_talk_low_mood": 2.1,
            "family_negative_contact": 1.6,
            "teacher_review_resolved": 0.5,
            "teacher_review_false_alarm": 0.4,
        },
    },
    "family": {
        "enabled": True,
        "prior": 0.14,
        "blend_alpha": 0.75,
        "evidence_rules": {
            "tag_family_hardship": 1.8,
            "family_contact_negative": 2.3,
            "family_violence_hint": 2.8,
            "attendance_family_issue": 1.7,
            "assistant_family_distress": 2.0,
            "teacher_review_resolved": 0.45,
            "teacher_review_false_alarm": 0.35,
        },
    },
    "social": {
        "enabled": True,
        "prior": 0.1,
        "blend_alpha": 0.78,
        "evidence_rules": {
            "graph_social_isolation": 1.9,
            "teacher_review_resolved": 0.55,
            "teacher_review_false_alarm": 0.45,
        },
    },
    "safety": {
        "enabled": True,
        "prior": 0.12,
        "blend_alpha": 0.7,
        "evidence_rules": {
            "assistant_self_report_assault": 4.5,
            "attendance_bruise_remark": 3.0,
            "attendance_worried_remark": 1.6,
            "behavior_conflict": 2.2,
            "behavior_bullying": 3.8,
            "graph_conflict_cooccurrence": 1.9,
            "family_violence_hint": 2.4,
            "teacher_review_resolved": 0.35,
            "teacher_review_false_alarm": 0.15,
        },
    }
}
