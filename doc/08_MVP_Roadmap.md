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
- preview render job enqueue
- output approval workflow
- recipe approval / rejection workflow
- preview status tracking
- dashboard visibility for recipe/job counts
- output browsing/reporting in UI

## Phase 4: Render Pipeline

- preview render adapter
- compositor adapter
- audio mix adapter
- final render job
- output registration
- unified dashboard visibility for persisted jobs
- manual retry for persisted factory jobs
- output lineage reporting in factory UI

## Phase 5: Automation and Quality

- recipe scoring
- duplicate risk checks
- quality gate
- resumable orchestrator
- queued-job recovery orchestrator
- failed-job retry orchestration

## Status Snapshot On 2026-06-06

- Phase 1: complete
- Phase 2: functionally complete for MVP baseline
- Phase 3: functionally complete for MVP baseline
- Phase 4: started
- Phase 5: started

## Current Phase 4 Remaining

1. Deepen preview composition beyond the current simple renderable-video path.
2. Replace final-render foundation with richer composition and audio-aware rendering.
3. Deepen approval trail beyond the current output-lineage reporting foundation.
4. Deepen orchestration beyond current queued-startup and failed-manual retry baselines.
