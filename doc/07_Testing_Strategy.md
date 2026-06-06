# Testing Strategy

## Purpose

MTClipFactory must stay easy to test with `pytest` from day one. The system is expected to evolve into a durable desktop workflow tool, so testability is a design requirement, not a cleanup task.

## Current Baseline

- Python runtime: `F:\programming\python\MTClipFactory\.venv`
- Test command: `python -m pytest`
- Current automated baseline on 2026-06-06: `78 passed`
- audio-policy settings persistence and Recipe Builder composition visibility are now part of that baseline
- Current UI smoke baseline on 2026-06-06: `6` PySide windows instantiated with `QT_QPA_PLATFORM=offscreen`

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
- Alembic-backed approval audit persistence and runtime migration guard
- append-only decision-event history persistence and retrieval
- composition-plan and render-decision persistence plus duration/layer inference
- timeline-segment persistence plus contiguous coverage validation
- segment-aware preview composition manifest and no-visual failure handling
- final-render composition parity with composition-based rerendering and manifest lineage
- recipe builder view model flow
- dashboard/settings audio-policy controls
- Recipe Builder composition-plan visibility alongside output lineage

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
2. Add widget-level interaction tests for the expanded Recipe Builder window.
3. Add deeper restart tests for broader orchestration policy, especially failed-job escalation and richer resume semantics.
