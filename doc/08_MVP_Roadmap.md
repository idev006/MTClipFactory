# MVP Roadmap

This is the strategic roadmap.

For execution sequencing and acceptance criteria, use [19_Implementation_Roadmap.md](/F:/programming/python/MTClipFactory/doc/19_Implementation_Roadmap.md).

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
- migration-backed approval audit persistence
- immutable approval history ledger

## Status Snapshot On 2026-06-06

- Phase 1: complete
- Phase 2: functionally complete for MVP baseline
- Phase 3: functionally complete for MVP baseline
- Phase 4: functionally complete for current baseline
- Phase 5: in progress

## Current Phase 5 Remaining

1. Deepen review confidence beyond the current duration and visual-repetition heuristics.
2. Deepen orchestration beyond current queued-startup and failed-manual retry baselines.
3. Decide whether path-root changes remain restart-driven or move to hot-reload semantics.
4. Deepen runtime audio depth beyond the new configurable duck-engine baseline toward richer multi-layer polish.

## Composition Milestone Direction

The next composition-oriented milestones should be approached in this order:

1. finalize SSOT policy for master timeline, segment semantics, and audio priority
2. design timeline and render-decision data model
3. implement segment-based preview composition
4. implement final-render composition parity
5. apply runtime music ducking and operator-visible render decisions

## Roadmap Structure

- `08_MVP_Roadmap.md` is the phase-level strategic roadmap
- `19_Implementation_Roadmap.md` is the implementation-level execution roadmap
- when the two appear to disagree, the execution roadmap may refine sequencing but must not violate the strategic scope without a documented revision
