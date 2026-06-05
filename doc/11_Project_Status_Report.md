# Project Status Report

## Project Manager Snapshot

- Report date: 2026-06-05
- Overall status: In Progress
- Current phase: Phase 3, Video Assembly Factory MVP
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
- initial Video Assembly Factory:
  - recipe persistence
  - recipe item assignment
  - preview render job flow
  - recipe builder view model
  - recipe builder desktop window
  - output registration foundation
- configurable path roots in `app_config.toml` for database, media, docs, outputs, and preview roots

## Verification Baseline

- `python -m pytest` via `.venv`: `53 passed`
- UI smoke via `QT_QPA_PLATFORM=offscreen`: `6` windows instantiated successfully

## Current Focus

- deepen recovery policy across jobs
- add richer review/final-render workflow on top of the preview-output baseline
- decide whether runtime path changes should hot-reload or remain restart-driven

## Next Steps

1. Add review decision workflow after preview build.
2. Add richer preview composition and asset-role handling.
3. Add durable retry and resume policy for all job types.
4. Add final render orchestration and output reports.

## Ownership

- Engineering owner: implementation and automated verification
- Project management owner: SSOT status, Kanban, issue log, lesson log
