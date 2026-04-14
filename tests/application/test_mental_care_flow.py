"""精神关怀 typed application flow 测试。"""

from __future__ import annotations

import unittest

from VitalAI.application import (
    MentalCareCheckInCommand,
    MentalCareCheckInWorkflow,
    RunMentalCareCheckInFlowUseCase,
)
from VitalAI.domains.mental_care import MentalCareCheckInSupportService
from VitalAI.domains.reporting import FeedbackReportService
from VitalAI.platform.arbitration import GoalType
from VitalAI.platform.feedback import FeedbackEvent
from VitalAI.platform.runtime import DecisionCore, EventAggregator


class MentalCareTypedApplicationFlowTests(unittest.TestCase):
    def build_use_case(self) -> RunMentalCareCheckInFlowUseCase:
        use_case = RunMentalCareCheckInFlowUseCase(
            aggregator=EventAggregator(),
            decision_core=DecisionCore(),
            support_service=MentalCareCheckInSupportService(),
        )
        use_case.configure_handlers()
        return use_case

    def test_mental_care_flow_returns_typed_domain_outputs(self) -> None:
        use_case = self.build_use_case()
        command = MentalCareCheckInCommand(
            source_agent="mental-care-agent",
            trace_id="trace-mental-1",
            user_id="elder-301",
            mood_signal="distressed",
            support_need="emotional_checkin",
        )

        result = use_case.run(command.to_message_envelope())

        self.assertTrue(result.accepted)
        self.assertIsNotNone(result.summary)
        self.assertIsNotNone(result.outcome)
        self.assertEqual("MENTAL_CARE_CHECKIN", result.summary.event_type)
        self.assertEqual("MENTAL_CARE_DECISION", result.outcome.decision_message.msg_type)
        self.assertIsInstance(result.outcome.feedback_event, FeedbackEvent)
        self.assertEqual(GoalType.MENTAL_CARE, result.outcome.care_intent.goal_type)
        self.assertEqual("emotional_checkin", result.outcome.decision_message.payload["support_need"])

    def test_mental_care_workflow_builds_feedback_report(self) -> None:
        workflow = MentalCareCheckInWorkflow(
            use_case=self.build_use_case(),
            report_service=FeedbackReportService(),
        )
        command = MentalCareCheckInCommand(
            source_agent="mental-care-agent",
            trace_id="trace-mental-2",
            user_id="elder-302",
            mood_signal="calm",
            support_need="companionship",
        )

        result = workflow.run(command)

        self.assertTrue(result.flow_result.accepted)
        self.assertIsNotNone(result.feedback_report)
        self.assertIn("mental-care-domain-service", result.feedback_report.title)
        self.assertIn("elder-302", result.feedback_report.body)


if __name__ == "__main__":
    unittest.main()
