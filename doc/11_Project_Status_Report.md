# Project Status Report

## Project Manager Snapshot

- Report date: 2026-06-06
- Overall status: In Progress
- Current phase: Phase 5, Automation and Quality
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
- settings-backed audio policy controls for narration looping, music looping, and duck timing
- dashboard and Recipe Builder visibility for composition-plan segments and render-decision summaries
- runtime voice/music mix path for preview and final render flows
- manifest-visible runtime audio-mix evidence for operator inspection
- review-gate reliability controls for low-diversity, loop-heavy, or mismatch-heavy preview/final compositions
- settings-backed review thresholds in `app_config.toml`, settings UI, and dashboard summary
- dashboard visibility for `needs_review` recipe count
- Recipe Builder output-detail visibility for manifest-backed review-gate evidence plus quality/duplicate-risk signals
- approval guard that requires an explicit human reason before approving a flagged recipe
- configurable duck engine with `sidechain_compressor` default plus `windowed_volume_duck` fallback
- settings-backed duck mode, threshold, and ratio controls surfaced through `.toml`, dashboard, and settings UI
- manifest-visible runtime evidence for the applied duck mode and compressor tuning
- persisted failed-job recovery-attempt metadata with configurable escalation threshold
- dashboard-visible operator playbook guidance plus deferred bulk-retry handling for escalated failed jobs
- restart-driven path-root policy with runtime-vs-configured dashboard truthfulness and restart-pending visibility
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

- `python -m pytest` via `.venv`: `86 passed`
- UI smoke via `QT_QPA_PLATFORM=offscreen`: `6` windows instantiated successfully

## Current Focus

- deepen review signals beyond the current duration and visual-repetition heuristics
- deepen runtime audio beyond the new configurable duck-engine baseline where needed
- keep review and approval history truthful through append-only persistence
- keep project documents truthful through per-milestone revision checkpoints

## Next Steps

1. Deepen review-gate signals with audio masking and emergency-fill detection when the supporting data is ready.
2. Extend audio work from configurable ducking into richer multi-layer polish if operator feedback demands it.
3. Revisit whether recovery history needs a dedicated audit schema beyond the current persisted job-payload seam.
4. Consider optional path-root hot-reload only if the restart-driven policy becomes operationally too costly.

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
- `IR-05a` now covers operator-controlled audio policy settings plus visible composition/render summaries, while runtime audio mixing remains a separate follow-up
- `IR-05b` now adds runtime voice/music mixing plus manifest-visible applied-audio evidence
- `IR-06` now adds review gates, configurable thresholds, dashboard visibility, and manifest-backed operator evidence for risky compositions
- `IR-07` now adds configurable duck modes, sidechain-compressor tuning, and higher-quality runtime audio evidence
- `IR-08` now adds persisted failed-job recovery history, escalation thresholds, deferred bulk retry, and operator playbook visibility
- `IR-09` now locks path-root reload semantics to restart-driven behavior and makes runtime-vs-configured path truth explicit to operators

## Ownership

- Engineering owner: implementation and automated verification
- Project management owner: SSOT status, Kanban, issue log, lesson log
