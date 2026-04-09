# Student Care Minimum Data Capability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the minimum data capabilities (attendance, behavior events, family contacts, assistant summaries) and wire them into the student care profile so class teachers can maintain evidence and the radar view has real signals.

**Architecture:** Add four new database models + schemas, expose CRUD APIs with class-teacher scoping, add a front-end “student detail tabs” entry to maintain data, and pipe these signals into `student_care_service` scoring.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Vue 3 + Element Plus, Axios

---

### Task 1: Add SQLAlchemy models (new tables)

**Files:**
- Create: `backend/database/models/student_attendance.py`
- Create: `backend/database/models/student_behavior_event.py`
- Create: `backend/database/models/student_family_contact.py`
- Create: `backend/database/models/student_assistant_summary.py`
- Modify: `backend/database/models/__init__.py`

**Step 1: Write the failing test**

Create a basic test to verify table existence via ORM (this will fail until models are imported).

```python
def test_student_care_data_models_registered():
    from database.models import StudentAttendance, StudentBehaviorEvent
    from database.models import StudentFamilyContact, StudentAssistantSummary
    assert StudentAttendance.__tablename__ == "student_attendance"
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_student_care_data.py::test_student_care_data_models_registered -v`  
Expected: FAIL (ImportError or table missing)

**Step 3: Implement models**

Implement minimal columns:

- `student_attendance`:
  - `id`, `student_id`, `date`, `status`, `remark`, `created_at`
- `student_behavior_event`:
  - `id`, `student_id`, `event_type`, `event_level`, `event_desc`, `occurred_at`, `created_at`
- `student_family_contact`:
  - `id`, `student_id`, `contact_type`, `summary`, `created_at`
- `student_assistant_summary`:
  - `id`, `student_id`, `summary_text`, `signals_json`, `created_at`

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_student_care_data.py::test_student_care_data_models_registered -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add backend/database/models backend/tests/test_student_care_data.py
git commit -m "feat: add student care data models"
```

---

### Task 2: Add Pydantic schemas

**Files:**
- Create: `backend/schemas/student_care_data.py`

**Step 1: Write the failing test**

```python
def test_student_care_data_schemas_import():
    from schemas.student_care_data import AttendanceCreate, BehaviorEventCreate
    assert AttendanceCreate is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_student_care_data.py::test_student_care_data_schemas_import -v`  
Expected: FAIL

**Step 3: Write minimal schemas**

Include:
- `AttendanceCreate`, `AttendanceUpdate`, `AttendanceOut`
- `BehaviorEventCreate`, `BehaviorEventUpdate`, `BehaviorEventOut`
- `FamilyContactCreate`, `FamilyContactOut`
- `AssistantSummaryCreate`, `AssistantSummaryOut`

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_student_care_data.py::test_student_care_data_schemas_import -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add backend/schemas/student_care_data.py backend/tests/test_student_care_data.py
git commit -m "feat: add student care data schemas"
```

---

### Task 3: Add service layer CRUD

**Files:**
- Create: `backend/services/student_care_data_service.py`

**Step 1: Write the failing test**

```python
def test_attendance_crud_service(db_session):
    from services.student_care_data_service import create_attendance
    result = create_attendance(db_session, student_id=1, date="2026-04-06", status="normal", remark="")
    assert result.id is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_student_care_data.py::test_attendance_crud_service -v`  
Expected: FAIL

**Step 3: Implement CRUD functions**

Minimum:
- Attendance: list/create/update/delete
- BehaviorEvent: list/create/update/delete
- FamilyContact: list/create/delete
- AssistantSummary: list/create

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_student_care_data.py::test_attendance_crud_service -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add backend/services/student_care_data_service.py backend/tests/test_student_care_data.py
git commit -m "feat: add student care data service"
```

---

### Task 4: Add API routes with role scoping

**Files:**
- Create: `backend/api/student_care_data.py`
- Modify: `backend/main.py`

**Step 1: Write the failing test**

```python
def test_teacher_can_list_attendance(client_teacher):
    resp = client_teacher.get("/api/attendance?student_id=1")
    assert resp.status_code in (200, 404)
```

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_student_care_data.py::test_teacher_can_list_attendance -v`  
Expected: FAIL

**Step 3: Implement API**

Endpoints:
- `/api/attendance` GET/POST/PUT/DELETE
- `/api/behavior-events` GET/POST/PUT/DELETE
- `/api/family-contacts` GET/POST/DELETE
- `/api/assistant-summary` GET/POST

Rules:
- Teacher can only operate students in own class
- Admin can operate all

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_student_care_data.py::test_teacher_can_list_attendance -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add backend/api/student_care_data.py backend/main.py backend/tests/test_student_care_data.py
git commit -m "feat: add student care data api"
```

---

### Task 5: Add frontend API client

**Files:**
- Create: `frontend/src/api/studentCareData.js`

**Step 1: Write the failing test**

This repo doesn’t use unit tests for frontend; verify by build.

**Step 2: Implement API client**

Add functions for:
- Attendance CRUD
- Behavior events CRUD
- Family contacts CRUD
- Assistant summaries list/create

**Step 3: Build**

Run: `npm run build`  
Expected: PASS

**Step 4: Commit**

```bash
git add frontend/src/api/studentCareData.js
git commit -m "feat: add student care data api client"
```

---

### Task 6: Add student detail tabs (attendance, behavior, family)

**Files:**
- Create: `frontend/src/views/student/StudentDetailTabs.vue`
- Modify: `frontend/src/views/student/StudentList.vue`

**Step 1: Create component layout**

Tabs:
- 出勤记录
- 行为事件
- 家校沟通

Each tab:
- List table
- Add / Edit / Delete

**Step 2: Wire API calls**

Use `studentCareData.js` to load and mutate records.

**Step 3: Build**

Run: `npm run build`  
Expected: PASS

**Step 4: Commit**

```bash
git add frontend/src/views/student/StudentDetailTabs.vue frontend/src/views/student/StudentList.vue
git commit -m "feat: add student detail care tabs"
```

---

### Task 7: Connect care signals to profile scoring

**Files:**
- Modify: `backend/services/student_care_service.py`

**Step 1: Write the failing test**

```python
def test_attendance_signal_affects_behavior(db_session):
    # create attendance late record
    # recalc profile and assert behavior_score > 0
    assert True
```

**Step 2: Implement signal mapping**

Suggested mapping:
- late/absent -> behavior +0.2~0.4
- behavior_event(level high) -> safety or behavior +0.5
- family_contact(summary contains conflict) -> family +0.2
- assistant_summary signals -> map to dimension

**Step 3: Run tests**

Run: `pytest backend/tests/test_student_care_data.py::test_attendance_signal_affects_behavior -v`  
Expected: PASS

**Step 4: Commit**

```bash
git add backend/services/student_care_service.py backend/tests/test_student_care_data.py
git commit -m "feat: integrate care data into scoring"
```

---

### Task 8: End-to-end smoke test

**Files:**
- None (manual)

**Step 1: Run backend tests**

Run: `pytest backend/tests/test_student_care_data.py -v`  
Expected: PASS

**Step 2: Run frontend build**

Run: `npm run build`  
Expected: PASS

**Step 3: Manual check**

- Teacher opens student detail
- Adds attendance record
- Opens care profile and sees updated behavior dimension

**Step 4: Commit**

If needed for docs:

```bash
git add docs
git commit -m "docs: add student care data implementation notes"
```

