# Project Status Report

## Project Manager Snapshot

- Report date: 2026-06-06
- Overall status: In Progress
- Current phase: Phase 4, Render Pipeline and Operational Recovery
- Delivery mode: document-led SSOT with code and tests kept in sync

## What Is Done

- architecture baseline for `Python 3.12 + SQLite + SQLAlchemy + Alembic + PySide6 + pytest + MVVM`
- product CRUD
- asset intake with local storage
- FFprobe-backed metadata analysis
- asset readiness classification
- tag dictionary and asset tagging
- asset list filters and tag visibility
- dashboard and settings control center
- FFmpeg-backed thumbnail/proxy generation jobs
- persisted job tracking with queued/failed visibility
- dashboard recent-job visibility across library and factory workflows
- queued-job recovery orchestrator with dashboard trigger and startup policy
- failed-job retry orchestration through dashboard control
- output lineage reporting in the Recipe Builder UI
- migration-backed approval actor/time/reason persistence
- append-only immutable decision-event history with Recipe Builder visibility
- persisted composition-plan and render-decision foundation for recipe-level duration and layer planning
- persisted timeline-segment foundation with contiguous semantic coverage validation
- segment-aware preview composition with manifest-visible visual clip planning
- segment-aware final-render composition parity with composition-based rerendering
- initial Video Assembly Factory:
  - recipe persistence
  - recipe item assignment
  - preview render job flow
  - output approval workflow
  - recipe approval / rejection workflow
  - recipe builder view model
  - recipe builder desktop window
  - final render composition parity
  - output browsing/reporting foundation
  - output lineage details from persisted job/output records
  - approval actor/time/reason capture for outputs and recipe decisions
  - manual retry for preview/final jobs
- configurable path roots in `app_config.toml` for database, media, docs, outputs, and preview roots
- configurable queued-job recovery policy in `app_config.toml`

## Verification Baseline

- `python -m pytest` via `.venv`: `78 passed`
- UI smoke via `QT_QPA_PLATFORM=offscreen`: `6` windows instantiated successfully

## Current Focus

- deepen render fidelity beyond the current visual parity baseline
- keep review and approval history truthful through append-only persistence
- keep project documents truthful through per-milestone revision checkpoints
- implement audio-priority behavior on top of the new preview/final visual parity baseline
- turn persisted render decisions into richer operator-visible preview/final behavior
- runtime migration path now exists, so future schema work can be delivered more safely
- decide whether runtime path changes should hot-reload or remain restart-driven
- deepen orchestration policy beyond the current queued-startup and failed-manual retry baselines

## Next Steps

1. Deliver `IR-05` audio-priority behavior and music ducking visibility.
2. Deliver `IR-06` review gates for low-confidence or mismatch-heavy composition cases.
3. Extend recovery orchestration beyond current sequential retry behavior and define escalation rules.
4. Decide whether path-root changes stay restart-driven or become hot-reload capable.

## Direction Locked In This Documentation Revision

- future composition is timeline-driven, not simple file stitching
- narration must not auto-loop
- background music may loop and must duck under narration
- loop/trim/freeze/duck decisions must become operator-visible and persistable
- the roadmap is now split into strategic and implementation layers
- `IR-01` composition-plan persistence is now implemented and becomes the baseline for `IR-02`
- `IR-02` timeline-segment persistence and validation are now implemented and become the baseline for `IR-03`
- `IR-03` preview composition now follows planned segments and becomes the baseline for `IR-04`
- `IR-04` final render now follows the planned composition path and becomes the baseline for `IR-05`

## Ownership

- Engineering owner: implementation and automated verification
- Project management owner: SSOT status, Kanban, issue log, lesson log
