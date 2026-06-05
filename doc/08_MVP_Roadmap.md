# MVP Roadmap

## Phase 1: Foundation

- project skeleton
- architecture docs
- SQLAlchemy models
- Alembic baseline migration
- product creation use case
- initial MVVM view model
- pytest baseline

## Phase 2: Resource Library Management

- product CRUD
- library navigation
- asset registration flow
- metadata analyzer abstraction
- tag dictionary
- asset library queries
- asset readiness rules
- thumbnail/proxy artifact jobs

## Phase 3: Video Assembly Factory

- recipe persistence
- manual recipe builder
- recipe item assignment
- preview manifest job enqueue
- preview status tracking
- dashboard visibility for recipe/job counts

## Phase 4: Render Pipeline

- preview render adapter
- compositor adapter
- audio mix adapter
- final render job
- output registration

## Phase 5: Automation and Quality

- recipe scoring
- duplicate risk checks
- quality gate
- resumable orchestrator

## Status Snapshot On 2026-06-05

- Phase 1: complete
- Phase 2: functionally complete for MVP baseline
- Phase 3: in progress
- Phase 4: not started
- Phase 5: not started

## Current Phase 3 Remaining

1. Replace preview manifest scaffolding with a real preview render output.
2. Add explicit review decision workflow after preview generation.
3. Add final render orchestration and output registration.
