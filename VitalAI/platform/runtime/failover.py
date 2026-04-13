"""Failover runtime shell.

负责主决策核心与影子核心之间的最小切换流程定义。
"""

from dataclasses import dataclass

from VitalAI.platform.runtime.decision_core import DecisionCore
from VitalAI.platform.runtime.shadow_decision_core import ShadowDecisionCore


@dataclass
class FailoverCoordinator:
    """最小故障切换协调器。"""

    primary: DecisionCore
    shadow: ShadowDecisionCore
    active_node: str = "primary"

    def should_failover(self) -> bool:
        """判断是否具备基础切换条件。"""
        return self.shadow.takeover_ready()

    def failover(self) -> bool:
        """执行最小切换动作。"""
        if not self.should_failover():
            return False
        self.active_node = "shadow"
        return True

    def failback(self) -> None:
        """将活动节点切回主核心。"""
        self.active_node = "primary"

