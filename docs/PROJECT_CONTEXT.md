# Project Context

## Project Name

VitalAI

## Project Nature

VitalAI is a server-side multi-agent project built on top of the existing `Base/` layer.

It is not an isolated greenfield project.

Its development strategy is:

- reuse shared capabilities from `Base`
- build business orchestration and domain logic in `VitalAI`
- keep large-scale project structure stable for long-term iteration

## Project Goal

Build a center-driven elder-care intelligence system covering:

- daily assistance
- health monitoring and risk detection
- mental care and companionship
- family-facing reporting
- long-term profile and memory evolution

## Source of Truth

The current architecture direction is derived from:

- the documents under `docs/`
- the supervisor design materials
- the four-layer architecture documents
- the current capabilities already present in `Base/`

## Architecture Direction

VitalAI uses this structure:

```text
VitalAI/
├─ application/
├─ platform/
├─ domains/
├─ interfaces/
├─ shared/
└─ main.py
```

## Layer Intent

### `platform/`

Cross-domain runtime kernel.

Maps to the four-layer architecture:

- messaging
- feedback
- arbitration
- interrupt
- observability
- security
- runtime

Important clarification:

`runtime/` should not become a single overloaded supervisor module.

It should evolve as a set of runtime components centered on decision-making:

- decision core
- event aggregator
- health monitor
- shadow decision core
- snapshots
- failover
- degradation

### `domains/`

Business domains:

- health
- daily_life
- mental_care
- reporting
- profile_memory

### `application/`

Use-case orchestration and workflow composition.

### `interfaces/`

API, scheduler, consumer, and web entrypoints.

### `shared/`

Lightweight stable shared definitions only.

## Relationship With `Base`

`Base` is the foundational capability layer for VitalAI.

VitalAI should read and reuse `Base` before creating new infrastructure.

## What `Base` Already Provides

### `Base/Config`

- settings loading
- logging setup
- application config base

### `Base/Ai`

- LLM base abstractions
- model wrappers
- prompt support
- AI service helpers

### `Base/Client`

- MySQL client
- Redis client
- MinIO client
- email client
- scheduler client
- ASR and related wrappers

### `Base/Repository`

- DB connection abstractions
- ORM-style base models
- connection manager
- multiple database backends

### `Base/Models`

- reusable shared models

### `Base/Service`

- reusable service wrappers already built on top of Base

### `Base/RicUtils`

- file, path, date, http, pdf, redis, reflection, and other general utilities

## Base Reuse Rule

Before implementing a new VitalAI module:

1. check whether `Base` already provides the capability
2. if yes, reuse it
3. if it is generic and missing, prefer adding it to `Base`
4. if it is VitalAI-specific, implement it in `VitalAI`

## Practical Boundary

### Put in `Base`

- generic clients
- generic DB abstractions
- generic model and LLM wrappers
- generic utilities
- reusable infra helpers

### Put in `VitalAI`

- decision core runtime
- event aggregation and failover runtime
- cross-agent collaboration logic
- four-layer platform mechanisms
- elder-care domain logic
- profile and memory evolution logic
- scenario-specific orchestration

## New Session Bootstrap

When starting a new session, read in this order:

1. `docs/PROJECT_CONTEXT.md`
2. `docs/CURRENT_STATUS.md`
3. `docs/NEXT_TASK.md`
4. `README.md`
5. related `Base/` directories for the current module

## Module-To-Base Reading Hints

- building messaging: read `Base/Config`, `Base/RicUtils`
- building persistence: read `Base/Repository`, `Base/Models`
- building LLM-based agents: read `Base/Ai`
- building integrations: read `Base/Client`, `Base/Service`
