# -*- coding: utf-8 -*-
"""Tests for student care bayesian helper service."""

from services import student_care_bayes_service as service


def test_build_bayes_result_for_safety_raises_posterior_with_multiple_signals():
    result = service.build_bayes_result(
        dimension="safety",
        linear_score=0.2,
        signals=[
            {
                "source": "assistant_summary",
                "signal_type": "assistant_safety_disclosure",
                "signal_text": "学生自述我被人打了，受伤了",
            },
            {
                "source": "attendance",
                "signal_type": "attendance_late",
                "signal_text": "近阶段出现 1 次迟到记录；备注：脸上有淤青",
            },
            {
                "source": "behavior_event",
                "signal_type": "behavior_bullying",
                "signal_text": "行为事件：学生反映疑似被同学欺负",
            },
        ],
        teacher_reviews=[],
    )

    assert result["enabled"] is True
    assert result["posterior"] > result["prior"]
    assert result["final_score"] > result["linear_score"]
    assert "assistant_self_report_assault" in result["evidence_keys"]
    assert "attendance_bruise_remark" in result["evidence_keys"]


def test_build_bayes_result_for_safety_is_reduced_by_false_alarm_review():
    result = service.build_bayes_result(
        dimension="safety",
        linear_score=0.3,
        signals=[
            {
                "source": "behavior_event",
                "signal_type": "behavior_conflict",
                "signal_text": "行为事件：与同学发生冲突",
            }
        ],
        teacher_reviews=[
            {
                "resolution_status": "false_alarm",
                "teacher_notes": "班主任核实后确认为误报",
            }
        ],
    )

    assert result["enabled"] is True
    assert "teacher_review_false_alarm" in result["evidence_keys"]
    assert result["posterior"] < 0.2


def test_build_bayes_result_for_emotion_raises_posterior_with_distress_signals():
    result = service.build_bayes_result(
        dimension="emotion",
        linear_score=0.18,
        signals=[
            {
                "source": "score",
                "signal_type": "score_drop_emotion",
                "signal_text": "成绩阶段性下滑，需要关注情绪波动",
            },
            {
                "source": "attendance",
                "signal_type": "attendance_early_leave",
                "signal_text": "近阶段出现 1 次早退记录；备注：神情很担忧",
            },
            {
                "source": "care_observation",
                "dimension": "emotion",
                "signal_type": "care_observation_care_talk",
                "signal_text": "关怀谈话中学生提到近期情绪低落",
            },
        ],
        teacher_reviews=[],
    )

    assert result["enabled"] is True
    assert result["posterior"] > result["prior"]
    assert result["final_score"] > result["linear_score"]
    assert "score_drop_emotion" in result["evidence_keys"]
    assert "attendance_worried_remark" in result["evidence_keys"]
    assert "care_talk_low_mood" in result["evidence_keys"]


def test_build_bayes_result_for_family_raises_posterior_with_family_signals():
    result = service.build_bayes_result(
        dimension="family",
        linear_score=0.2,
        signals=[
            {
                "source": "student_tag",
                "signal_type": "tag_family",
                "signal_text": "学生标签包含“家庭困难”",
            },
            {
                "source": "family_contact",
                "signal_type": "family_contact_summary",
                "signal_text": "家校沟通摘要：父亲打牌，不出去工作，对学生表现不耐烦",
            },
            {
                "source": "attendance",
                "signal_type": "attendance_late",
                "signal_text": "近阶段出现 1 次迟到记录；备注：因家庭临时安排迟到",
            },
        ],
        teacher_reviews=[],
    )

    assert result["enabled"] is True
    assert result["posterior"] > result["prior"]
    assert result["final_score"] > result["linear_score"]
    assert "tag_family_hardship" in result["evidence_keys"]
    assert "family_contact_negative" in result["evidence_keys"]
    assert "attendance_family_issue" in result["evidence_keys"]


def test_build_bayes_result_uses_custom_override_config():
    result = service.build_bayes_result(
        dimension="safety",
        linear_score=0.2,
        signals=[
            {
                "source": "behavior_event",
                "signal_type": "behavior_conflict",
                "signal_text": "行为事件：与同学发生冲突",
            }
        ],
        teacher_reviews=[],
        bayes_config={
            "safety": {
                "enabled": True,
                "prior": 0.5,
                "blend_alpha": 0.2,
                "evidence_rules": {
                    "behavior_conflict": 5.0,
                },
            }
        },
    )

    assert result["prior"] == 0.5
    assert result["blend_alpha"] == 0.2
    assert result["posterior"] > 0.8
    assert result["final_score"] > 0.6


def test_graph_conflict_signal_updates_safety_posterior():
    result = service.build_bayes_result(
        dimension="safety",
        linear_score=0.12,
        signals=[
            {
                "source": "graph",
                "signal_type": "graph_conflict_cooccurrence",
                "signal_text": "关系图谱显示该生所在班级近期存在多名学生卷入冲突/欺凌事件",
            }
        ],
        teacher_reviews=[],
    )

    assert result["enabled"] is True
    assert "graph_conflict_cooccurrence" in result["evidence_keys"]
    assert result["posterior"] > result["prior"]
    assert result["final_score"] > result["linear_score"]


def test_graph_social_isolation_signal_updates_social_posterior():
    result = service.build_bayes_result(
        dimension="social",
        linear_score=0.08,
        signals=[
            {
                "source": "graph",
                "signal_type": "graph_social_isolation",
                "signal_text": "关系图谱中暂未形成稳定同伴连接，建议继续关注学生融入情况",
            }
        ],
        teacher_reviews=[],
    )

    assert result["enabled"] is True
    assert "graph_social_isolation" in result["evidence_keys"]
    assert result["posterior"] > result["prior"]
    assert result["final_score"] > result["linear_score"]
