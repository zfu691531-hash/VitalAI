"""Snapshot runtime primitives.

负责保存和读取运行时快照，为影子接管和中断恢复提供最小基础能力。
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class RuntimeSnapshot:
    """运行时快照对象。

    当前只保留最小结构，后续可扩展版本号、任务上下文和组件状态。
    """

    snapshot_id: str
    created_at: datetime
    source: str
    payload: dict[str, Any]
    version: int = 1


@dataclass
class SnapshotStore:
    """最小快照存储。

    当前使用内存保存，后续可切换到数据库、对象存储或缓存层。
    """

    snapshots: dict[str, RuntimeSnapshot] = field(default_factory=dict)

    def save(self, snapshot_id: str, source: str, payload: dict[str, Any]) -> RuntimeSnapshot:
        """保存快照并返回快照对象。"""
        snapshot = RuntimeSnapshot(
            snapshot_id=snapshot_id,
            created_at=datetime.now(UTC),
            source=source,
            payload=payload,
        )
        self.snapshots[snapshot_id] = snapshot
        return snapshot

    def get(self, snapshot_id: str) -> RuntimeSnapshot | None:
        """按 ID 获取快照。"""
        return self.snapshots.get(snapshot_id)

    def latest(self) -> RuntimeSnapshot | None:
        """获取最近一次保存的快照。"""
        if not self.snapshots:
            return None
        return max(self.snapshots.values(), key=lambda item: item.created_at)

