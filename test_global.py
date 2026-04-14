"""
VitalAI 全局测试脚本 - 全面测试所有模块
"""

import sys
import time
import traceback
from datetime import datetime, UTC, timedelta
from dataclasses import asdict
import json

# 测试统计
stats = {"total": 0, "passed": 0, "failed": 0, "errors": 0, "details": []}

def test(name):
    def decorator(func):
        def wrapper():
            stats["total"] += 1
            start = time.time()
            try:
                func()
                elapsed = time.time() - start
                stats["passed"] += 1
                stats["details"].append({"name": name, "status": "PASS", "time": elapsed})
                print(f"[PASS] {name} - {elapsed:.4f}s")
            except AssertionError as e:
                elapsed = time.time() - start
                stats["failed"] += 1
                stats["details"].append({"name": name, "status": "FAIL", "error": str(e)})
                print(f"[FAIL] {name}: {e}")
            except Exception as e:
                elapsed = time.time() - start
                stats["errors"] += 1
                stats["details"].append({"name": name, "status": "ERROR", "error": str(e)})
                print(f"[ERROR] {name}: {type(e).__name__}: {e}")
        return wrapper
    return decorator

# 导入模块
print("=" * 80)
print("导入模块...")
print("=" * 80)

try:
    from VitalAI.platform.messaging.message_envelope import MessageEnvelope, MessagePriority
    from VitalAI.platform.feedback.events import FeedbackEvent, FeedbackLayer, FailureDetails
    from VitalAI.platform.arbitration.intents import IntentDeclaration, GoalType, Flexibility, ResourceRequirement
    from VitalAI.platform.interrupt.signals import InterruptSignal, InterruptPriority, InterruptAction, SnapshotReference
    from VitalAI.platform.runtime.event_aggregator import EventAggregator, EventSummary
    from VitalAI.platform.runtime.decision_core import DecisionCore
    from VitalAI.platform.runtime.snapshots import SnapshotStore, RuntimeSnapshot
    from VitalAI.platform.runtime.health_monitor import HealthMonitor
    from VitalAI.platform.runtime.shadow_decision_core import ShadowDecisionCore
    from VitalAI.platform.runtime.failover import FailoverCoordinator
    from VitalAI.platform.runtime.degradation import DegradationPolicy, DegradationLevel
    from VitalAI.application.commands.health_alert_command import HealthAlertCommand
    from VitalAI.application.commands.daily_life_checkin_command import DailyLifeCheckInCommand
    from VitalAI.application.use_cases.health_alert_flow import RunHealthAlertFlowUseCase
    from VitalAI.application.use_cases.daily_life_checkin_flow import RunDailyLifeCheckInFlowUseCase
    from VitalAI.domains.health.services.alert_triage import HealthAlertTriageService
    from VitalAI.domains.daily_life.services.checkin_support import DailyLifeCheckInSupportService
    from VitalAI.domains.reporting.services.feedback_report import FeedbackReportService
    print("[OK] 所有模块导入成功\n")
except Exception as e:
    print(f"[ERROR] 导入失败: {e}")
    sys.exit(1)

# ============================================================================
# 契约层测试
# ============================================================================

print("=" * 80)
print("第一部分：契约层测试")
print("=" * 80)

@test("MessageEnvelope创建")
def test1():
    e = MessageEnvelope(from_agent="a", to_agent="b", payload={}, priority=MessagePriority.HIGH, trace_id="t1")
    assert e.from_agent == "a"
    assert e.priority == MessagePriority.HIGH

@test("MessageEnvelope.TTL过期")
def test2():
    e = MessageEnvelope(from_agent="a", to_agent="b", payload={}, priority=MessagePriority.NORMAL, ttl=1)
    assert not e.is_expired()
    time.sleep(1.1)
    assert e.is_expired()

@test("FeedbackEvent创建")
def test3():
    f = FeedbackEvent(trace_id="t1", agent_id="a1", task_id="k1", event_type="DONE", feedback_layer=FeedbackLayer.L1, summary="test")
    assert not f.is_failure()

@test("FeedbackEvent失败")
def test4():
    f = FeedbackEvent(trace_id="t1", agent_id="a1", task_id="k1", event_type="FAIL", feedback_layer=FeedbackLayer.L2, summary="fail", failure=FailureDetails(error_code="E1", message="err"))
    assert f.is_failure()

@test("IntentDeclaration创建")
def test5():
    i = IntentDeclaration(agent_id="a1", action="act", content_preview="test", goal_type=GoalType.HEALTH, goal_weight=0.8, flexibility=Flexibility.PREFERRED)
    assert i.intent_id is not None

@test("InterruptSignal创建")
def test6():
    s = InterruptSignal(trace_id="t1", source="src", priority=InterruptPriority.P1, action=InterruptAction.TAKEOVER, reason="test")
    assert s.needs_interrupt_snapshot()

# ============================================================================
# Runtime组件测试
# ============================================================================

print("\n" + "=" * 80)
print("第二部分：Runtime组件测试")
print("=" * 80)

@test("EventAggregator基本功能")
def test7():
    a = EventAggregator()
    e = MessageEnvelope(from_agent="a", to_agent="b", payload={}, priority=MessagePriority.NORMAL, trace_id="t1")
    assert a.ingest(e) is True
    assert len(a.summarize()) == 1

@test("EventAggregator拒绝过期消息")
def test8():
    a = EventAggregator()
    e = MessageEnvelope(from_agent="a", to_agent="b", payload={}, priority=MessagePriority.NORMAL, ttl=-1)
    assert a.ingest(e) is False

@test("DecisionCore基本功能")
def test9():
    d = DecisionCore()
    d.register_handler("TEST", lambda s: MessageEnvelope(from_agent="d", to_agent="o", payload={}, priority=MessagePriority.NORMAL))
    s = EventSummary(message_id="m1", trace_id="t1", event_type="TEST", source_agent="a", target_agent="d", priority=MessagePriority.NORMAL, timestamp=datetime.now(UTC), payload={})
    assert d.process_summary(s) is not None

@test("SnapshotStore基本功能")
def test10():
    s = SnapshotStore()
    snap = s.save("s1", "primary", {"state": 1})
    assert s.get("s1") is not None

@test("HealthMonitor基本功能")
def test11():
    h = HealthMonitor()
    h.heartbeat("c1")
    assert h.last_seen("c1") is not None

@test("HealthMonitor过期检测")
def test12():
    h = HealthMonitor()
    h.heartbeat("c1", datetime.now(UTC) - timedelta(seconds=100))
    assert h.is_stale("c1", timedelta(seconds=10)) is True

@test("ShadowDecisionCore基本功能")
def test13():
    sd = ShadowDecisionCore()
    assert not sd.takeover_ready()
    sd.sync_snapshot(RuntimeSnapshot(snapshot_id="s1", created_at=datetime.now(UTC), source="p", payload={}))
    assert sd.takeover_ready()

@test("FailoverCoordinator基本功能")
def test14():
    c = FailoverCoordinator(primary=DecisionCore(), shadow=ShadowDecisionCore())
    assert c.active_node == "primary"

@test("DegradationPolicy基本功能")
def test15():
    p = DegradationPolicy()
    assert p.level == DegradationLevel.NORMAL
    sig = InterruptSignal(trace_id="t1", source="s", priority=InterruptPriority.P1, action=InterruptAction.TAKEOVER, reason="test")
    assert p.apply_interrupt(sig) == DegradationLevel.DEGRADED

# ============================================================================
# Application层测试
# ============================================================================

print("\n" + "=" * 80)
print("第三部分：Application层测试")
print("=" * 80)

@test("HealthAlertCommand转换")
def test16():
    c = HealthAlertCommand(source_agent="h", trace_id="t1", user_id="u1", risk_level="critical")
    e = c.to_message_envelope()
    assert e.priority == MessagePriority.CRITICAL

@test("DailyLifeCheckInCommand转换")
def test17():
    c = DailyLifeCheckInCommand(source_agent="d", trace_id="t1", user_id="u1", need="check", urgency="high")
    e = c.to_message_envelope()
    assert e.priority == MessagePriority.CRITICAL

@test("RunHealthAlertFlowUseCase完整流程")
def test18():
    uc = RunHealthAlertFlowUseCase(aggregator=EventAggregator(), decision_core=DecisionCore(), triage_service=HealthAlertTriageService())
    uc.configure_handlers()
    cmd = HealthAlertCommand(source_agent="h", trace_id="t1", user_id="u1", risk_level="high")
    r = uc.run(cmd.to_message_envelope())
    assert r.accepted and r.outcome is not None

@test("RunDailyLifeCheckInFlowUseCase完整流程")
def test19():
    uc = RunDailyLifeCheckInFlowUseCase(aggregator=EventAggregator(), decision_core=DecisionCore(), support_service=DailyLifeCheckInSupportService())
    uc.configure_handlers()
    cmd = DailyLifeCheckInCommand(source_agent="d", trace_id="t1", user_id="u1", need="check", urgency="normal")
    r = uc.run(cmd.to_message_envelope())
    assert r.accepted and r.outcome is not None

# ============================================================================
# Domain层测试
# ============================================================================

print("\n" + "=" * 80)
print("第四部分：Domain层测试")
print("=" * 80)

@test("HealthAlertTriageService分诊")
def test20():
    s = HealthAlertTriageService()
    summary = EventSummary(message_id="m1", trace_id="t1", event_type="HEALTH", source_agent="a", target_agent="h", priority=MessagePriority.HIGH, timestamp=datetime.now(UTC), payload={"user_id": "u1", "risk_level": "high"})
    o = s.triage(summary)
    assert o.decision_message and o.feedback_event and o.escalation_intent

@test("DailyLifeCheckInSupportService支持")
def test21():
    s = DailyLifeCheckInSupportService()
    summary = EventSummary(message_id="m1", trace_id="t1", event_type="DAILY", source_agent="a", target_agent="d", priority=MessagePriority.HIGH, timestamp=datetime.now(UTC), payload={"user_id": "u1", "need": "check", "urgency": "normal"})
    o = s.support(summary)
    assert o.decision_message and o.feedback_event and o.support_intent

@test("FeedbackReportService报告")
def test22():
    s = FeedbackReportService()
    req = FeedbackReportService.Request(event_id="e1", trace_id="t1", agent_id="a1", task_id="k1", event_type="DONE", feedback_layer=FeedbackLayer.L1, summary="test")
    r = s.generate_report(req)
    assert r.trace_id == "t1"

# ============================================================================
# 集成测试
# ============================================================================

print("\n" + "=" * 80)
print("第五部分：集成测试")
print("=" * 80)

@test("健康告警端到端")
def test23():
    uc = RunHealthAlertFlowUseCase(aggregator=EventAggregator(), decision_core=DecisionCore(), triage_service=HealthAlertTriageService())
    uc.configure_handlers()
    cmd = HealthAlertCommand(source_agent="h", trace_id="t_e2e", user_id="u1", risk_level="critical")
    r = uc.run(cmd.to_message_envelope())
    assert r.accepted and r.outcome.feedback_event.trace_id == "t_e2e"

@test("多领域集成")
def test24():
    a = EventAggregator()
    a.ingest(HealthAlertCommand(source_agent="h", trace_id="t1", user_id="u1", risk_level="high").to_message_envelope())
    a.ingest(DailyLifeCheckInCommand(source_agent="d", trace_id="t2", user_id="u1", need="check", urgency="normal").to_message_envelope())
    assert len(a.summarize()) == 2

@test("快照故障转移集成")
def test25():
    store = SnapshotStore()
    shadow = ShadowDecisionCore()
    coord = FailoverCoordinator(primary=DecisionCore(), shadow=shadow)
    
    snap = store.save("s1", "primary", {"state": 1})
    shadow.sync_snapshot(snap)
    
    sig = InterruptSignal(trace_id="t1", source="sys", priority=InterruptPriority.P0, action=InterruptAction.TAKEOVER, reason="fail", snapshot_refs=[snap.to_reference()])
    assert coord.should_failover(sig) and coord.failover(sig)

# ============================================================================
# 性能测试
# ============================================================================

print("\n" + "=" * 80)
print("第六部分：性能测试")
print("=" * 80)

@test("EventAggregator吞吐量>5000msg/s")
def test26():
    a = EventAggregator()
    start = time.time()
    for i in range(1000):
        a.ingest(MessageEnvelope(from_agent=f"a{i}", to_agent="b", payload={}, priority=MessagePriority.NORMAL, trace_id=f"t{i}"))
    throughput = 1000 / (time.time() - start)
    print(f"  吞吐量: {throughput:.1f} msg/s")
    assert throughput > 5000

@test("DecisionCore吞吐量>5000ops/s")
def test27():
    d = DecisionCore()
    d.register_handler("T", lambda s: MessageEnvelope(from_agent="d", to_agent="o", payload={}, priority=MessagePriority.NORMAL))
    summaries = [EventSummary(message_id=f"m{i}", trace_id=f"t{i}", event_type="T", source_agent="a", target_agent="d", priority=MessagePriority.NORMAL, timestamp=datetime.now(UTC), payload={}) for i in range(500)]
    start = time.time()
    for s in summaries:
        d.process_summary(s)
    throughput = 500 / (time.time() - start)
    print(f"  吞吐量: {throughput:.1f} ops/s")
    assert throughput > 5000

@test("SnapshotStore吞吐量>5000ops/s")
def test28():
    s = SnapshotStore()
    start = time.time()
    for i in range(500):
        s.save(f"s{i}", "p", {"i": i})
    throughput = 500 / (time.time() - start)
    print(f"  吞吐量: {throughput:.1f} ops/s")
    assert throughput > 5000

# ============================================================================
# 序列化测试
# ============================================================================

print("\n" + "=" * 80)
print("第七部分：序列化测试")
print("=" * 80)

@test("MessageEnvelope序列化")
def test29():
    e = MessageEnvelope(from_agent="a", to_agent="b", payload={"k": "v"}, priority=MessagePriority.HIGH, trace_id="t1")
    j = json.dumps(asdict(e), default=str)
    assert "t1" in j

@test("FeedbackEvent序列化")
def test30():
    f = FeedbackEvent(trace_id="t1", agent_id="a1", task_id="k1", event_type="D", feedback_layer=FeedbackLayer.L1, summary="test")
    j = json.dumps(asdict(f), default=str)
    assert "t1" in j

@test("InterruptSignal序列化")
def test31():
    s = InterruptSignal(trace_id="t1", source="s", priority=InterruptPriority.P1, action=InterruptAction.TAKEOVER, reason="test", snapshot_refs=[SnapshotReference(snapshot_id="s1", source="p")])
    j = json.dumps(asdict(s), default=str)
    assert "t1" in j

# ============================================================================
# 边界测试
# ============================================================================

print("\n" + "=" * 80)
print("第八部分：边界测试")
print("=" * 80)

@test("TTL=0立即过期")
def test32():
    e = MessageEnvelope(from_agent="a", to_agent="b", payload={}, priority=MessagePriority.NORMAL, ttl=0)
    time.sleep(0.01)
    assert e.is_expired()

@test("TTL=-1立即过期")
def test33():
    e = MessageEnvelope(from_agent="a", to_agent="b", payload={}, priority=MessagePriority.NORMAL, ttl=-1)
    assert e.is_expired()

@test("无TTL不过期")
def test34():
    e = MessageEnvelope(from_agent="a", to_agent="b", payload={}, priority=MessagePriority.NORMAL)
    assert e.expire_at is None and not e.is_expired()

@test("空EventAggregator")
def test35():
    assert len(EventAggregator().summarize()) == 0

@test("SnapshotStore未找到")
def test36():
    assert SnapshotStore().get("none") is None

@test("降级所有级别")
def test37():
    p = DegradationPolicy()
    for pri, lvl in [(InterruptPriority.P3, DegradationLevel.NORMAL), (InterruptPriority.P2, DegradationLevel.ALERT), (InterruptPriority.P1, DegradationLevel.DEGRADED), (InterruptPriority.P0, DegradationLevel.SURVIVAL)]:
        s = InterruptSignal(trace_id="t", source="s", priority=pri, action=InterruptAction.PAUSE, reason="test")
        assert p.apply_interrupt(s) == lvl

# 执行测试
print("\n" + "=" * 80)
print("执行测试...")
print("=" * 80)

test1()
test2()
test3()
test4()
test5()
test6()
test7()
test8()
test9()
test10()
test11()
test12()
test13()
test14()
test15()
test16()
test17()
test18()
test19()
test20()
test21()
test22()
test23()
test24()
test25()
test26()
test27()
test28()
test29()
test30()
test31()
test32()
test33()
test34()
test35()
test36()
test37()

# 汇总结果
print("\n" + "=" * 80)
print("测试结果汇总")
print("=" * 80)

print(f"\n总测试数: {stats['total']}")
print(f"通过: {stats['passed']}")
print(f"失败: {stats['failed']}")
print(f"错误: {stats['errors']}")
print(f"通过率: {stats['passed'] / stats['total'] * 100:.1f}%")

total_time = sum(d['time'] for d in stats['details'])
print(f"总耗时: {total_time:.3f}s")

if stats['failed'] > 0 or stats['errors'] > 0:
    print("\n失败/错误的测试:")
    for d in stats['details']:
        if d['status'] in ['FAIL', 'ERROR']:
            print(f"  - {d['name']}: {d['status']}")
            if 'error' in d:
                print(f"    错误: {d['error']}")

# 导出结果
print("\n导出测试结果...")
with open("test_global_results.json", "w", encoding="utf-8") as f:
    json.dump({"summary": {"total": stats['total'], "passed": stats['passed'], "failed": stats['failed'], "errors": stats['errors'], "pass_rate": stats['passed'] / stats['total'] * 100, "total_time": total_time}, "details": stats['details']}, f, indent=2, ensure_ascii=False)

print("[OK] 结果已导出到 test_global_results.json")

if stats['failed'] > 0 or stats['errors'] > 0:
    sys.exit(1)
else:
    print("\n[SUCCESS] 所有测试通过！")
    sys.exit(0)
