"""Shadow Decision Core runtime shell.

负责接收主决策核心的状态快照，为热备接管预留能力。
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ShadowDecisionCore:
    """最小影子决策核心外壳。"""

    latest_snapshot: dict[str, Any] | None = None

    def sync_snapshot(self, snapshot: dict[str, Any]) -> None:
        """同步主核心快照。"""
        self.latest_snapshot = snapshot

    def takeover_ready(self) -> bool:
        """判断是否具备基础接管条件。"""
        return self.latest_snapshot is not None

