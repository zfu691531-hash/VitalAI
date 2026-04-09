# -*- coding: utf-8 -*-
"""Rule-level tests for student care scoring adjustments."""

from datetime import date, timedelta

from services import student_care_service as service


def test_time_decay_prefers_recent_records():
    recent = service._apply_time_decay(0.2, date.today() - timedelta(days=2))
    medium = service._apply_time_decay(0.2, date.today() - timedelta(days=20))
    old = service._apply_time_decay(0.2, date.today() - timedelta(days=120))

    assert recent == 0.2
    assert medium < recent
    assert old < medium


def test_text_polarity_distinguishes_positive_negative_and_neutral():
    assert service._classify_text_polarity("近期与同学互动积极，状态稳定，愿意参与活动") == "positive"
    assert service._classify_text_polarity("近期情绪低落，独处增多，存在明显压力") == "negative"
    assert service._classify_text_polarity("老师完成一次常规沟通记录") == "neutral"


def test_build_data_quality_summary_counts_missing_and_protective_signals():
    signals = [
        {
            "signal_type": "score_missing",
            "dimension": "study",
            "signal_text": "缺少成绩记录",
            "signal_weight": 0.0,
            "source": "data_gap",
        },
        {
            "signal_type": "family_contact_positive",
            "dimension": "family",
            "signal_text": "家长支持稳定",
            "signal_weight": -0.18,
            "source": "family_contact",
        },
        {
            "signal_type": "attendance_late",
            "dimension": "behavior",
            "signal_text": "近阶段出现 1 次迟到",
            "signal_weight": 0.2,
            "source": "attendance",
        },
    ]

    summary = service._build_data_quality_summary(
        [type("Signal", (), item)() for item in signals]
    )

    assert summary["missing_sources"] == ["score_missing"]
    assert summary["missing_count"] == 1
    assert summary["positive_signal_count"] == 1
    assert summary["protective_signal_count"] == 1
    assert summary["evidence_sufficient"] is False
