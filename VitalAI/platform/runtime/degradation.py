"""Degradation runtime policies.

负责描述中心不可用时的最小降级状态与模块自治惯性规则。
"""

from dataclasses import dataclass, field
from enum import StrEnum


class DegradationLevel(StrEnum):
    """系统降级级别。"""

    NORMAL = "NORMAL"
    ALERT = "ALERT"
    DEGRADED = "DEGRADED"
    SURVIVAL = "SURVIVAL"


@dataclass
class AutonomyRule:
    """模块自治规则。"""

    module_name: str
    description: str
    max_duration_minutes: int | None = None


@dataclass
class DegradationPolicy:
    """最小降级策略集合。"""

    level: DegradationLevel = DegradationLevel.NORMAL
    autonomy_rules: list[AutonomyRule] = field(default_factory=list)

    def set_level(self, level: DegradationLevel) -> None:
        """更新当前降级级别。"""
        self.level = level

    def add_rule(self, rule: AutonomyRule) -> None:
        """增加模块自治规则。"""
        self.autonomy_rules.append(rule)

