# Student Care Graph Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为学生关怀系统新增“图数据库关系增强层”，让系统能识别社交关系、风险共现、群体聚集和干预后复发等关系型线索，并把图分析结果回流到现有画像、贝叶斯辅助层与多智能体研判。

**Architecture:** 保留当前关系型主库和学生关怀主链路，新增 Neo4j 图谱层作为“关系增强侧脑”。业务表数据通过同步服务写入图数据库，图查询生成 `graph signals`，再回写到现有 `student_care_signal`、贝叶斯 evidence 和 Agent prompt 中。这样不会推翻现有系统，但能补强 `social` 和 `safety` 两个最需要关系分析的维度。

**Tech Stack:** FastAPI, SQLAlchemy, Neo4j Python Driver, Cypher, pytest

---

### Task 1: 接入图数据库依赖与配置

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/core/graph_config.py`
- Modify: `backend/core/config.py`
- Test: `backend/tests/test_student_care_graph_config.py`

**Step 1: Write the failing test**

```python
def test_graph_settings_defaults():
    settings = GraphSettings()
    assert settings.neo4j_enabled is False
    assert settings.neo4j_uri == "bolt://127.0.0.1:7687"
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_student_care_graph_config.py -v`
Expected: FAIL with `GraphSettings` not defined

**Step 3: Write minimal implementation**

```python
from pydantic_settings import BaseSettings


class GraphSettings(BaseSettings):
    neo4j_enabled: bool = False
    neo4j_uri: str = "bolt://127.0.0.1:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"
```

**Step 4: Expose config in main settings**

Add to `backend/core/config.py`:

```python
neo4j_enabled: bool = False
neo4j_uri: str = "bolt://127.0.0.1:7687"
neo4j_username: str = "neo4j"
neo4j_password: str = ""
neo4j_database: str = "neo4j"
```

**Step 5: Run test to verify it passes**

Run: `pytest backend/tests/test_student_care_graph_config.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/requirements.txt backend/core/config.py backend/core/graph_config.py backend/tests/test_student_care_graph_config.py
git commit -m "feat: add graph layer configuration"
```

### Task 2: 建立 Neo4j 客户端与健康检查

**Files:**
- Create: `backend/services/student_care_graph_service.py`
- Modify: `backend/main.py`
- Test: `backend/tests/test_student_care_graph_service.py`

**Step 1: Write the failing test**

```python
def test_graph_service_disabled_returns_empty_health():
    service = StudentCareGraphService(enabled=False)
    assert service.healthcheck() == {"enabled": False, "connected": False}
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_student_care_graph_service.py::test_graph_service_disabled_returns_empty_health -v`
Expected: FAIL with `StudentCareGraphService` not defined

**Step 3: Write minimal implementation**

```python
class StudentCareGraphService:
    def __init__(self, enabled: bool, driver=None):
        self.enabled = enabled
        self.driver = driver

    def healthcheck(self):
        if not self.enabled:
            return {"enabled": False, "connected": False}
        return {"enabled": True, "connected": self.driver is not None}
```

**Step 4: Add startup health log**

In `backend/main.py`, print graph health status during startup/lifespan when enabled.

**Step 5: Run test to verify it passes**

Run: `pytest backend/tests/test_student_care_graph_service.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/services/student_care_graph_service.py backend/main.py backend/tests/test_student_care_graph_service.py
git commit -m "feat: add graph service bootstrap"
```

### Task 3: 设计图谱节点与关系同步

**Files:**
- Modify: `backend/services/student_care_graph_service.py`
- Create: `backend/tests/test_student_care_graph_sync.py`
- Reference: `backend/database/models/student.py`
- Reference: `backend/database/models/student_behavior_event.py`
- Reference: `backend/database/models/student_care_observation.py`
- Reference: `backend/database/models/student_family_contact.py`
- Reference: `backend/database/models/student_assistant_summary.py`

**Step 1: Write the failing test**

```python
def test_build_student_graph_payload_contains_nodes_and_edges():
    payload = build_student_graph_payload(student, events, observations, contacts, summaries)
    assert "students" in payload
    assert "events" in payload
    assert "edges" in payload
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_student_care_graph_sync.py -v`
Expected: FAIL with `build_student_graph_payload` not defined

**Step 3: Write minimal implementation**

Implement graph payload builder that outputs:

```python
{
    "students": [...],
    "events": [...],
    "observations": [...],
    "contacts": [...],
    "assistant_disclosures": [...],
    "edges": [
        {"from": "student:1", "to": "event:10", "type": "INVOLVED_IN"},
    ],
}
```

**Step 4: Add sync method**

Add method:

```python
def sync_student_subgraph(self, student_id: int, payload: dict) -> None:
    ...
```

Use Cypher `MERGE` instead of `CREATE`.

**Step 5: Run test to verify it passes**

Run: `pytest backend/tests/test_student_care_graph_sync.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/services/student_care_graph_service.py backend/tests/test_student_care_graph_sync.py
git commit -m "feat: add graph sync payload builder"
```

### Task 4: 先实现 2 个高价值图信号

**Files:**
- Modify: `backend/services/student_care_graph_service.py`
- Create: `backend/tests/test_student_care_graph_signals.py`

**Step 1: Write the failing test**

```python
def test_conflict_cooccurrence_signal_detected():
    result = build_graph_signals(query_result)
    assert any(item["signal_type"] == "graph_conflict_cooccurrence" for item in result)


def test_social_isolation_signal_detected():
    result = build_graph_signals(query_result)
    assert any(item["signal_type"] == "graph_social_isolation" for item in result)
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_student_care_graph_signals.py -v`
Expected: FAIL with `build_graph_signals` not defined

**Step 3: Write minimal implementation**

Generate these signals:

- `graph_conflict_cooccurrence`
- `graph_social_isolation`

Signal schema should match existing `student_care_signal` conventions:

```python
{
    "signal_type": "graph_conflict_cooccurrence",
    "dimension": "safety",
    "signal_text": "学生与同一批同学在多起冲突事件中反复共现",
    "signal_weight": 0.25,
    "source": "graph"
}
```

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_student_care_graph_signals.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/services/student_care_graph_service.py backend/tests/test_student_care_graph_signals.py
git commit -m "feat: add initial graph-derived care signals"
```

### Task 5: 将 graph signals 接入学生关怀画像

**Files:**
- Modify: `backend/services/student_care_service.py`
- Modify: `backend/schemas/student_care.py`
- Test: `backend/tests/test_student_care.py`

**Step 1: Write the failing test**

```python
def test_profile_includes_graph_signals():
    result = get_student_care_profile(...)
    assert any(item["source"] == "graph" for item in result["signals"])
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_student_care.py::test_profile_includes_graph_signals -v`
Expected: FAIL because graph source is missing

**Step 3: Write minimal implementation**

Inside `get_student_care_profile(...)`:
- call graph service when `neo4j_enabled=True`
- merge graph signals into existing signals list
- preserve fallback when graph unavailable

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_student_care.py::test_profile_includes_graph_signals -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/services/student_care_service.py backend/schemas/student_care.py backend/tests/test_student_care.py
git commit -m "feat: include graph signals in student care profile"
```

### Task 6: 将 graph evidence 接入贝叶斯辅助层

**Files:**
- Modify: `backend/core/student_care_bayes_config.py`
- Modify: `backend/services/student_care_bayes_service.py`
- Test: `backend/tests/test_student_care_bayes_service.py`

**Step 1: Write the failing test**

```python
def test_graph_conflict_signal_updates_safety_posterior():
    result = build_bayes_result(...)
    assert "graph_conflict_cooccurrence" in result["evidence_keys"]
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_student_care_bayes_service.py::test_graph_conflict_signal_updates_safety_posterior -v`
Expected: FAIL because graph evidence key is unknown

**Step 3: Write minimal implementation**

Add graph evidence rules:
- `graph_conflict_cooccurrence`
- `graph_social_isolation`

Update evidence extraction so graph signals can map into LR keys.

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_student_care_bayes_service.py::test_graph_conflict_signal_updates_safety_posterior -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/core/student_care_bayes_config.py backend/services/student_care_bayes_service.py backend/tests/test_student_care_bayes_service.py
git commit -m "feat: add graph evidence to bayes layer"
```

### Task 7: 将图分析结果接入多智能体研判

**Files:**
- Modify: `backend/services/student_care_agent_service.py`
- Modify: `backend/schemas/student_care_agent.py`
- Test: `backend/tests/test_student_care_agent_service.py`

**Step 1: Write the failing test**

```python
def test_agent_payload_contains_graph_context():
    payload = build_prompt_payload(...)
    assert "graph_context" in payload
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_student_care_agent_service.py::test_agent_payload_contains_graph_context -v`
Expected: FAIL because graph context is absent

**Step 3: Write minimal implementation**

Add `graph_context` to prompt payload, including:
- graph-derived signals
- relationship summary
- co-occurrence findings

Prompt rule:
- graph context is supporting evidence
- final evidence must still be grounded in校内事实

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_student_care_agent_service.py::test_agent_payload_contains_graph_context -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/services/student_care_agent_service.py backend/schemas/student_care_agent.py backend/tests/test_student_care_agent_service.py
git commit -m "feat: add graph context to care agents"
```

### Task 8: 增加手动同步接口与管理端可见性

**Files:**
- Modify: `backend/api/student_care.py`
- Create: `backend/tests/test_student_care_graph_api.py`
- Modify: `frontend/src/api/studentCare.js`
- Modify: `frontend/src/views/student/StudentCareDrawer.vue`

**Step 1: Write the failing test**

```python
def test_sync_graph_endpoint_returns_ok(client):
    response = client.post("/api/student-care/graph-sync/1")
    assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_student_care_graph_api.py -v`
Expected: FAIL because endpoint does not exist

**Step 3: Write minimal implementation**

Add:
- `POST /api/student-care/graph-sync/{student_id}`
- optional `GET /api/student-care/graph-health`

Frontend:
- add “同步关系图谱” button for admin/teacher
- show latest graph findings in drawer

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_student_care_graph_api.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/api/student_care.py backend/tests/test_student_care_graph_api.py frontend/src/api/studentCare.js frontend/src/views/student/StudentCareDrawer.vue
git commit -m "feat: add graph sync management endpoints"
```

### Task 9: 编写部署与回退说明

**Files:**
- Modify: `学生关怀多智能体风险研判方案.md`
- Create: `docs/neo4j-local-setup.md`

**Step 1: Document local setup**

Include:
- Docker / Neo4j Desktop options
- `.env` settings
- healthcheck verification

**Step 2: Document fallback**

If graph layer unavailable:
- `neo4j_enabled=False`
- profile / bayes / agents continue running
- graph signals simply absent

**Step 3: Commit**

```bash
git add 学生关怀多智能体风险研判方案.md docs/neo4j-local-setup.md
git commit -m "docs: add graph layer setup and fallback guide"
```

### Task 10: 全链路验证

**Files:**
- Test: `backend/tests/test_student_care_graph_config.py`
- Test: `backend/tests/test_student_care_graph_service.py`
- Test: `backend/tests/test_student_care_graph_sync.py`
- Test: `backend/tests/test_student_care_graph_signals.py`
- Test: `backend/tests/test_student_care_bayes_service.py`
- Test: `backend/tests/test_student_care_agent_service.py`
- Test: `backend/tests/test_student_care.py`

**Step 1: Run targeted tests**

```bash
pytest backend/tests/test_student_care_graph_config.py -q
pytest backend/tests/test_student_care_graph_service.py -q
pytest backend/tests/test_student_care_graph_sync.py -q
pytest backend/tests/test_student_care_graph_signals.py -q
pytest backend/tests/test_student_care_bayes_service.py -q
pytest backend/tests/test_student_care_agent_service.py -q
pytest backend/tests/test_student_care.py -q
```

Expected: PASS

**Step 2: Run frontend build if management UI changes**

```bash
npm.cmd run build
```

Expected: build successfully

**Step 3: Manual verification checklist**

- Neo4j service reachable
- graph sync endpoint works
- graph signals appear in student care profile
- graph evidence enters bayes layer
- graph context enters agent prompt
- disabling graph layer does not break existing evaluation

**Step 4: Commit**

```bash
git add .
git commit -m "test: verify graph layer integration end to end"
```

---

## Local Setup Notes

### Minimal Dependencies

- Python package: `neo4j==5.28.1`
- Neo4j service: local Docker or Neo4j Desktop

### Suggested `.env`

```env
NEO4J_ENABLED=true
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
```

### First-Phase Scope

- Only `social` and `safety` graph signals
- Only relationship enhancement layer
- No graph neural network
- No frontend graph visualization
- No replacement of main relational database

## Expected Value

This plan should improve:
- 社交融入风险识别
- 校园安全共现识别
- 风险聚集发现
- 教师确认后复发链路识别

It should not change:
- existing fallback architecture
- existing rule profile calculations when graph is disabled
- current teacher confirmation loop

## Rollback Strategy

1. Set `NEO4J_ENABLED=false`
2. Skip graph sync jobs
3. Stop writing graph signals
4. Keep profile, bayes, and agent evaluation unchanged

Plan complete and saved to `docs/plans/2026-04-09-student-care-graph-layer-implementation.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
