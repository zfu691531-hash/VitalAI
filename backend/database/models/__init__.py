# -*- coding: utf-8 -*-
"""
ORM 模型统一导出
=================
将所有数据表模型在此导出，便于 Alembic 自动检测模型变更。
导出：User, Student, Teacher, Class, Score, AiHistory, SchoolRule
"""

from .ai_history import AiHistory
from .assistant_message import AssistantMessage
from .assistant_session import AssistantSession
from .class_ import Class
from .group_scheme import GroupScheme
from .placement_batch import PlacementBatch
from .knowledge_sync_task import KnowledgeSyncTask
from .rule_qa_feedback import RuleQaFeedback
from .rule_qa_record import RuleQaRecord
from .school_rule import SchoolRule
from .school_rule_chunk import SchoolRuleChunk
from .score import Score
from .student import Student
from .student_assistant_summary import StudentAssistantSummary
from .student_attendance import StudentAttendance
from .student_care_agent_record import StudentCareAgentRecord
from .student_care_bayes_rule import StudentCareBayesRule
from .student_care_graph_relation import StudentCareGraphRelation
from .student_behavior_event import StudentBehaviorEvent
from .student_care_observation import StudentCareObservation
from .student_care_profile import StudentCareProfile
from .student_care_signal import StudentCareSignal
from .student_family_contact import StudentFamilyContact
from .student_tag_definition import StudentTagDefinition
from .student_tag_review import StudentTagReview
from .teacher import Teacher
from .user import User

__all__ = [
    "User",
    "Student",
    "StudentAttendance",
    "StudentCareAgentRecord",
    "StudentCareBayesRule",
    "StudentCareGraphRelation",
    "StudentBehaviorEvent",
    "StudentCareObservation",
    "StudentFamilyContact",
    "StudentTagDefinition",
    "StudentTagReview",
    "StudentAssistantSummary",
    "StudentCareProfile",
    "StudentCareSignal",
    "Teacher",
    "Class",
    "Score",
    "AiHistory",
    "AssistantSession",
    "AssistantMessage",
    "GroupScheme",
    "PlacementBatch",
    "SchoolRule",
    "RuleQaRecord",
    "RuleQaFeedback",
    "SchoolRuleChunk",
    "KnowledgeSyncTask",
]
