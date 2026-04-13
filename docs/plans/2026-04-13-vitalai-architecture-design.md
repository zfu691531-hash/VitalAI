# VitalAI Architecture Draft

## Inputs Reviewed

- `docs/` four-layer architecture documents
- `docs/` supervisor and XMind design material
- `Base/` shared capability package
- `Wolin/` business module layout and FastAPI entry pattern

## Chosen Structure

The first draft was further upgraded into a long-term structure based on `platform + domains + application + interfaces`.

- `VitalAI/platform`
  - Holds the cross-domain runtime kernel:
  - `messaging`, `feedback`, `arbitration`, `interrupt`, `observability`, `security`, `runtime`
- `VitalAI/domains`
  - Business capabilities are grouped by domain instead of technical layer:
  - `health`, `daily_life`, `mental_care`, `reporting`, `profile_memory`
- `VitalAI/application`
  - Owns orchestration use cases and cross-domain workflows.
- `VitalAI/interfaces`
  - Owns external delivery adapters such as API, scheduler, consumers, web.
- `VitalAI/shared`
  - Holds only lightweight shared constants, schemas, errors, and utilities.

## Why This Is Better Than The Earlier Skeleton

- The docs describe a platform-like agent operating system, not a small module tree.
- The four layers are cross-cutting platform concerns and belong in `platform/`.
- Large business codebases are easier to evolve when organized by domain ownership.
- `application/` prevents orchestration logic from leaking into controllers or agents.
- `interfaces/` makes future API, workers, schedulers, and event consumers easier to evolve independently.

## Recommended Next Step

Define the first three shared contracts in the new structure:

1. `platform/messaging`: `MessageEnvelope`
2. `platform/feedback`: `FeedbackEvent`
3. `platform/arbitration`: `IntentDeclaration`

Then create the first runtime coordinator in `platform/runtime/supervisor.py`.
