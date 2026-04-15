# VitalAI Project Issue Report

Date: 2026-04-14

## Status Note

This report is a point-in-time review document, not the current source of truth.

For current project stage and next-step guidance, read:

- `docs/DOCS_INDEX.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/CURRENT_STATUS.md`
- `docs/NEXT_TASK.md`

Progress status after the first remediation wave:

- P1 `Security review accuracy`: partially addressed
- P2 `Snapshot persistence and versioning`: partially addressed
- P3 `Duplicate domain execution in use cases`: addressed
- P4 `Test and packaging baseline`: addressed
- P5 `Side-effect API semantics`: addressed at route semantics level
- P6 `Domain landing depth and Base reuse`: partially addressed
- P7 `Dependency and delivery hygiene`: still open

Important clarification:

- `profile_memory` is no longer an empty skeleton.
- runtime diagnostics and health failover drill are no longer exposed as side-effecting `GET` routes.
- default `pytest tests -q` baseline has already been restored.

## 1. Review Summary

This review covered the current repository structure, core runtime chain, interface adapters, domain modules, test baseline, and deployment-related files under:

- `VitalAI/`
- `Base/`
- `tests/`
- `docs/`

Overall judgment:

- The architecture direction is reasonable.
- The current codebase is still in a prototype/scaffolding stage rather than a production-ready backend stage.
- The main gap is that design documentation and target architecture are moving faster than real business implementation, persistence, and delivery infrastructure.

Current maturity assessment:

- Architecture design maturity: medium
- Runtime prototype maturity: medium
- Real domain landing maturity: low
- Engineering delivery maturity: low
- Production readiness: low

## 2. Core Conclusions

The current project has three structural strengths:

- The layering direction of `application / platform / domains / interfaces / shared` is clear.
- The project already has a typed contract mindset, which is good for later large-scale evolution.
- The runtime observability, security, and failover direction already has a coherent prototype shape.

The current project also has three structural gaps:

- Several key capabilities exist only as in-memory or demo-level implementations and are not yet real backend infrastructure.
- Some runtime paths already look complete at the API level, but their internal state and persistence model are not yet trustworthy.
- The repository is still missing a stable engineering baseline for test execution, delivery, and real domain implementation.

## 3. Priority Matrix

| ID | Priority | Topic | Short Conclusion |
| --- | --- | --- | --- |
| P1 | High | Security review accuracy | There are both false positives and missed detections. |
| P2 | High | Snapshot persistence and versioning | Version/history exists in shape only, not in actual cross-request behavior. |
| P3 | High | Duplicate domain execution in use cases | Domain services are invoked twice in the same flow. |
| P4 | Medium | Test and packaging baseline | Default test command fails without manual environment patching. |
| P5 | Medium | Side-effect API semantics | Read-like GET endpoints are performing snapshot/failover actions. |
| P6 | Medium | Domain landing depth and Base reuse | Most domains are still skeletons; real business/backend integration is missing. |
| P7 | Low | Dependency and delivery hygiene | Dependency surface is much larger than current app usage. |

## 4. Detailed Issues

### P1. Security review has both false positives and missed detections

#### Problem

The current `SensitiveDataGuard` can incorrectly classify runtime identifiers as phone numbers, and it only sanitizes the top level of mappings.

This creates two risks:

- False positives: normal runtime fields are marked as sensitive and produce unstable security outcomes.
- False negatives: nested business payloads can bypass review entirely.

#### Evidence

- `VitalAI/platform/security/service.py`
- `VitalAI/application/use_cases/runtime_support.py`
- `VitalAI/application/assembly.py`
- `tests/interfaces/test_typed_flow_routes.py`

Observed behavior during validation:

- `message_id` values in interrupt payloads can be misclassified as phone-like content.
- `review_runtime_snapshot()` only checks the top-level snapshot payload.
- Nested fields such as `event_payload.phone` are not recursively sanitized.
- `health failover drill` can fail intermittently because `latest_security_action` flips from `ALLOW` to `REDACT`.

#### Impact

- Runtime diagnostics become non-deterministic.
- Security observation quality is not reliable enough for real operational use.
- Sensitive information in nested payloads may leak into reports or observability records.

#### Suggested Optimization Direction

- Add recursive sanitization for nested `dict`, `list`, and string fields.
- Introduce an allowlist for technical identifiers such as:
  - `message_id`
  - `trace_id`
  - `signal_id`
  - `snapshot_id`
- Tighten the phone-detection rule so it does not match generic hex-like or identifier-like values.
- Separate "business PII detection" from "system identifier fields".
- Add deterministic security tests for repeated failover drill execution.

#### Delivery Standard

- A repeated run of the health failover drill is stable and does not intermittently change from `ALLOW` to `REDACT`.
- Nested snapshot payload fields are recursively reviewed and sanitized.
- Technical identifiers are not redacted unless they actually contain sensitive data.
- Add test cases that prove:
  - interrupt payload with `message_id` is not treated as phone data
  - nested payloads containing phone/email are detected
  - repeated drill execution produces deterministic security results

### P2. Snapshot versioning/history is not a real runtime capability yet

#### Problem

The project already exposes snapshot versioning and historical lookup concepts, but the actual runtime path creates a fresh `SnapshotStore()` in multiple places.

This means:

- snapshot history is not shared across requests
- version increments are not meaningful across workflow executions
- failover recovery cannot rely on a stable snapshot store

#### Evidence

- `VitalAI/platform/runtime/snapshots.py`
- `VitalAI/application/use_cases/runtime_support.py`
- `VitalAI/application/assembly.py`

Current behavior:

- `SnapshotStore` is in-memory only.
- `SnapshotStore` is constructed inline in the runtime path.
- The runtime path does not use dependency-injected shared snapshot storage.

#### Impact

- Snapshot history is effectively request-local.
- The current versioning model cannot support real failover, recovery, or replay.
- Diagnostic output gives the appearance of persistence without actual persistence guarantees.

#### Suggested Optimization Direction

- Promote snapshot storage into an injected runtime dependency from `ApplicationAssemblyConfig`.
- Provide one shared implementation path first:
  - in-memory singleton for prototype, or
  - Redis, or
  - database-backed storage
- Define snapshot lifecycle explicitly:
  - write
  - version increment
  - latest lookup
  - historical lookup
  - retention policy
- Make failover and drill paths consume the same store instance.

#### Delivery Standard

- Snapshot store is no longer instantiated ad hoc in use-case/runtime drill code.
- Two separate executions that write the same `snapshot_id` can observe incremented versions through the same store.
- `get_version(snapshot_id, version)` works across independent workflow invocations.
- At least one integration test proves cross-call snapshot history is available.

### P3. Domain services are executed twice in one flow

#### Problem

In each current typed flow, the domain service is used once inside the registered decision handler and once again directly in the use-case `run()` method.

This is not visible yet because the services are still lightweight and side-effect free, but it will become a real bug once services touch persistence, LLM, notifications, or billing-like side effects.

#### Evidence

- `VitalAI/application/use_cases/health_alert_flow.py`
- `VitalAI/application/use_cases/daily_life_checkin_flow.py`
- `VitalAI/application/use_cases/mental_care_checkin_flow.py`

#### Impact

- Duplicate writes
- Duplicate cost
- Possible mismatch between returned `outcome` and decision-core handler result
- Hard-to-debug behavior once side effects are introduced

#### Suggested Optimization Direction

- Make the use case own the domain execution exactly once.
- Refactor handler registration so the decision core consumes either:
  - the already computed outcome, or
  - a pure decision adapter derived from the outcome
- Separate "domain execution" from "message emission" more clearly.
- Add call-count-based tests using mocks/stubs.

#### Delivery Standard

- Each flow executes its domain service exactly once per accepted input.
- Unit tests assert single invocation for:
  - health
  - daily life
  - mental care
- The returned workflow result and decision-core output are derived from the same domain outcome instance.

### P4. Test execution baseline is incomplete

#### Problem

The repository currently does not provide a stable default way to run tests.

Observed validation result:

- `pytest tests -q` fails at collection time because `VitalAI` cannot be imported.
- Tests can run only after explicitly setting `PYTHONPATH=.`.

#### Evidence

- No `pyproject.toml`
- No `pytest.ini`
- No `setup.py`
- Absolute imports are used across tests and source code

#### Impact

- CI setup is fragile
- New contributors will fail on the first test command
- Local environment behavior is inconsistent

#### Suggested Optimization Direction

- Add one standard project entry for Python path and test discovery:
  - `pyproject.toml`, or
  - `pytest.ini`
- Standardize the official local test command in `README.md`.
- Add a minimal CI-friendly command that works without shell-specific environment patching.

#### Delivery Standard

- `pytest tests -q` runs successfully from the repository root without manually setting `PYTHONPATH`.
- The repository contains one clear Python project/test configuration file.
- `README.md` includes the canonical local test command.

### P5. Some GET endpoints have side effects and operational risk

#### Problem

The current interface exposes runtime diagnostics and health failover drill through GET endpoints even though these paths create snapshots and may trigger failover transitions.

#### Evidence

- `VitalAI/interfaces/api/routers/typed_flows.py`
- `VitalAI/application/assembly.py`

Current examples:

- `/flows/runtime-diagnostics/{role}`
- `/flows/runtime-diagnostics/{role}/health-failover`

#### Impact

- A monitoring system, crawler, or accidental browser visit may trigger stateful operations.
- API semantics do not clearly distinguish read-only behavior from control actions.
- Future production deployment risk increases significantly.

#### Suggested Optimization Direction

- Move drill and state-changing diagnostics to explicit admin/control endpoints.
- Use `POST` for operations that create snapshots or trigger transitions.
- Add environment and role guards so these endpoints are disabled or protected outside development/test environments.
- Keep true read-only policy/introspection endpoints as `GET`.

#### Delivery Standard

- All side-effecting runtime drill/control endpoints use `POST`.
- Read-only endpoints remain `GET`.
- Non-development environments require an explicit switch or authorization guard before drill endpoints are callable.
- Add interface tests proving side-effect endpoints are blocked or disabled when the guard is off.

### P6. Domain depth is still shallow and Base reuse is not yet meaningfully landed

#### Problem

The architecture intends to build real business domains on top of `Base/`, but most domain directories are still skeletons.

At the moment:

- `profile_memory` is still empty at implementation level.
- `health`, `daily_life`, and `mental_care` mostly translate `EventSummary` into typed output objects.
- Real repository/model/client integration is largely absent from `VitalAI`.

#### Evidence

- `docs/PROJECT_CONTEXT.md`
- `docs/MODULE_DOMAINS_GUIDE.md`
- `VitalAI/domains/`
- `VitalAI/main.py`

Observed status:

- The only concrete `Base` reuse inside `VitalAI` is mainly logging bootstrap.
- Real persistence, profile memory, and long-term data evolution have not been landed.
- Current domain services are still close to transport/result translation rather than full domain behavior.

#### Impact

- The project risks becoming a well-documented shell around a demo workflow.
- The most important business differentiators are not yet reflected in code.
- Future refactoring cost will rise if the prototype contracts harden before real business capabilities land.

#### Suggested Optimization Direction

- Prioritize one real domain landing next, preferably `profile_memory`.
- For that domain, implement a full vertical slice:
  - typed command
  - use case
  - domain service
  - repository
  - model
  - workflow
  - interface adapter
- Reuse `Base/Repository` or `Base/Client` instead of adding ad hoc storage logic in `VitalAI`.
- Define at least one persistent business scenario such as:
  - user profile read/write
  - preference update
  - memory snapshot lookup

#### Delivery Standard

- `profile_memory` or another selected priority domain has a real end-to-end business flow.
- The flow uses at least one real reusable capability from `Base`.
- Domain implementation includes more than service translation logic and contains actual persistence/business behavior.
- Add tests covering repository interaction and end-to-end workflow behavior.

### P7. Dependency and delivery surface is larger than current app usage

#### Problem

The current `requirements.txt` includes a very broad dependency set, while the active `VitalAI` application uses only a small subset of it.

Examples include heavyweight or unrelated stacks that are not obviously required by the current FastAPI runtime path.

#### Evidence

- `requirements.txt`
- `Dockerfile`

#### Impact

- Slower image build
- Larger attack surface
- Higher dependency conflict risk
- Harder upgrade and vulnerability management

#### Suggested Optimization Direction

- Split dependencies into layers if needed:
  - runtime
  - test
  - optional integrations
- Keep the main app runtime image as small as possible.
- Audit which packages are truly required by the current deployed service.

#### Delivery Standard

- The repository distinguishes core runtime dependencies from optional/test dependencies.
- Docker runtime image installs only the dependency set required by the deployed app path.
- A dependency review note or matrix exists for the retained packages.

## 5. Recommended Execution Order

Recommended implementation order:

1. Fix security review accuracy.
2. Fix snapshot store sharing and version persistence model.
3. Remove duplicate domain execution in use cases.
4. Establish test baseline and project packaging/test config.
5. Correct side-effect API semantics and add environment guards.
6. Land one real domain vertical slice with Base reuse.
7. Reduce dependency surface after the first functional vertical slice is stable.

Reason for this order:

- P1 to P3 are correctness and runtime trust issues.
- P4 and P5 are engineering safety and delivery issues.
- P6 is the most important product/backend maturity issue.
- P7 should follow after the real backend path is clearer.

## 6. Suggested Acceptance Milestone

The project can be considered to have moved from "architecture prototype" to "engineering-usable backend baseline" when the following conditions are all met:

- Default tests run successfully from the repository root.
- Security review output is deterministic and covers nested payloads.
- Snapshot version/history works across independent workflow executions.
- Each flow executes domain logic only once.
- Runtime drill/control APIs are clearly separated from read-only APIs.
- At least one real business domain uses Base-backed persistence or client capability end to end.

## 7. Final Assessment

VitalAI currently has a good architecture direction, but it still needs a round of "turn prototype into real backend baseline" work.

The most important next step is not adding more architecture documents. The most important next step is to improve runtime correctness, make persistence real, fix the engineering baseline, and land one true business domain slice.
