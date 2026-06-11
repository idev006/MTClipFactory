# Testing Strategy

## Purpose

MTClipFactory must stay easy to test with `pytest` from day one. The system is expected to evolve into a durable desktop workflow tool, so testability is a design requirement, not a cleanup task.

For execution-ready release and UAT planning, use [20_Master_Test_Plan.md](/F:/programming/python/MTClipFactory/doc/20_Master_Test_Plan.md).

## Current Baseline

- Python runtime: `F:\programming\python\MTClipFactory\.venv`
- Test command: `python -m pytest`
- Current automated baseline on 2026-06-11: `105 passed`
- audio-policy settings persistence, failed-job escalation coverage, and runtime hot-reload path visibility coverage are now part of that baseline
- settings-window widget coverage is now part of the baseline, including grouped-panel rendering, hybrid slider-plus-exact-entry mapping, preservation of pre-existing out-of-range config values, and precision-entry synchronization
- Current UI smoke baseline on 2026-06-11: `6` PySide windows instantiated with `QT_QPA_PLATFORM=offscreen`

## Test Pyramid

### Unit Tests

- domain rules
- service validation
- DTO mapping
- workflow state changes

### Integration Tests

- SQLAlchemy repository behavior with in-memory SQLite
- unit-of-work persistence flow
- local storage copy behavior
- `ffprobe` adapter contract
- artifact and preview job persistence

### ViewModel Tests

- signal-safe state transitions
- success and failure feedback
- command forwarding to services
- filtering and refresh behavior

### UI Smoke Tests

- import and instantiate all main windows offscreen
- verify wiring after navigation or constructor changes

### Widget-Level UI Tests

- settings-window grouped panel rendering
- settings-window control population from loaded settings
- settings-window slider and checkbox save mapping
- settings-window preservation of pre-existing high-value config settings without silent clamp

## Current Covered Areas

### Resource Library Management

- product CRUD
- asset intake
- tag dictionary
- asset readiness
- asset filters
- thumbnail/proxy job flow
- dashboard/settings aggregation

### Video Assembly Factory

- recipe creation
- recipe item assignment
- preview job enqueue
- preview render output generation
- output approval decisions
- recipe approval/rejection decisions
- final render composition parity
- preview/final factory job retry after restart-style service recreation
- queued-job recovery orchestration through the dashboard and startup policy
- output lineage reporting from persisted output and job records
- failed-job retry orchestration from the dashboard
- persisted recovery-attempt metadata with escalation thresholds and deferred bulk-retry ordering
- runtime-active versus configured path-root reporting with truthful reload-state visibility
- desktop-app runtime path-root hot reload with whole-module rebind coverage
- Alembic-backed approval audit persistence and runtime migration guard
- append-only decision-event history persistence and retrieval
- composition-plan and render-decision persistence plus duration/layer inference
- timeline-segment persistence plus contiguous coverage validation
- segment-aware preview composition manifest and no-visual failure handling
- final-render composition parity with composition-based rerendering and manifest lineage
- recipe builder view model flow
- dashboard/settings audio-policy controls
- Recipe Builder composition-plan visibility alongside output lineage
- runtime audio-mix command path and manifest audio evidence
- voice/music gain-stage settings persistence plus runtime balance-command coverage
- Recipe Builder output-detail helper for runtime audio-mix inspection
- review-gate status routing, manifest evidence, and approval-reason enforcement for flagged recipes
- sidechain duck-mode settings persistence plus fallback windowed-duck command coverage
- recipe scoring heuristic plus score/risk propagation through service and view-model seams

## Conventions

- always activate `.venv` before running tests or installing packages
- use in-memory SQLite for repository and application tests unless a filesystem contract is the subject of the test
- isolate filesystem work under `tmp_path`
- avoid depending on the production database file
- keep UI logic in view models so it can be tested without opening real windows

## Design Rules For Easy Testing

- keep business logic out of Qt widgets
- inject adapters for filesystem, FFmpeg, metadata analysis, and preview generation
- persist workflow state through repositories and jobs so retry and recovery can be tested
- prefer small service seams over hidden module globals
- treat circular imports as test failures in disguise and remove them immediately

## Next Testing Slice

1. Add integration coverage for the real FFmpeg preview and final renderers using controlled sample media.
2. Add widget-level interaction tests for the expanded Recipe Builder review-gate and audio-evidence surfaces.
3. Add a manual operator-focused usability pass for hybrid slider-plus-exact-entry ergonomics and keyboard accessibility.
4. Add deeper orchestration tests for score calibration and richer review/audio signals now that runtime path reload is part of the baseline.
