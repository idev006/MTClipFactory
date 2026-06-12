# Project Status Report

## Project Manager Snapshot

- Report date: 2026-06-12
- Overall status: In Progress
- Current phase: Phase 5, automation baseline plus full-system release audit complete; controlled operator rollout recommended before broader release
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
- review-gate reliability controls for low-diversity, loop-heavy, mismatch-heavy, audio-masking-risk, or emergency-fill preview/final compositions
- settings-backed review thresholds in `app_config.toml`, settings UI, and dashboard summary
- dashboard visibility for `needs_review` recipe count
- Recipe Builder output-detail visibility for manifest-backed review-gate evidence plus quality/duplicate-risk signals
- Recipe Builder recipe-summary visibility for persisted `recipe_score` and recipe-level `duplicate_risk`
- approval guard that requires an explicit human reason before approving a flagged recipe
- configurable duck engine with `sidechain_compressor` default plus `windowed_volume_duck` fallback
- settings-backed duck mode, threshold, and ratio controls surfaced through `.toml`, dashboard, and settings UI
- manifest-visible runtime evidence for the applied duck mode and compressor tuning
- settings-backed voice/music gain-stage controls surfaced through `.toml`, dashboard, and settings UI
- manifest-visible runtime evidence for applied voice/music balance during audio mixing
- persisted failed-job recovery-attempt metadata with configurable escalation threshold
- dashboard-visible operator playbook guidance plus deferred bulk-retry handling for escalated failed jobs
- payload-backed recovery metadata retained as the current audit seam by explicit architecture decision
- desktop-app runtime hot reload for path-root dependent services with runtime-vs-configured dashboard truthfulness
- redesigned grouped settings surface with two-column panel layout and hybrid slider-plus-exact-entry numeric controls
- settings numeric controls now use uniform slider/editor widths for more consistent operator scanning
- package-backed QSS theme loading seam now exists for Qt windows, with a shared app-window theme baseline across dashboard, library, and factory windows plus a settings-specific override
- shared app-window buttons now use balanced gradient, border-depth, focus, and pressed-state affordance so primary actions read clearly as clickable controls without feeling oversized
- Recipe Builder now explains its recipe-to-final purpose more directly, clarifies that the attach list shows only `ready` assets, keeps the asset panel tall enough for practical scanning, and offers a suggested attach-role pick list instead of relying on free-typed role names alone
- widget-level settings UI verification coverage, including hybrid control mapping, high-value config preservation, and exact-entry synchronization
- scripted full-system release audit coverage for product-to-final workflow, recovery/escalation behavior, and runtime path hot reload
- operator-facing user manual now exists as SSOT guidance for controlled rollout and UAT
- controlled operator rollout kickoff guidance now exists as an execution-ready entry point for first real use on the current baseline
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

- `python -m pytest` via `.venv`: `111 passed`
- UI smoke via `QT_QPA_PLATFORM=offscreen`: `6` windows instantiated successfully

## Current Focus

- keep richer review signals and approval history truthful through append-only persistence
- monitor whether runtime path reload stays truthful and easy for operators to understand
- monitor whether the new recipe scoring baseline stays operationally useful for operators
- monitor whether hybrid settings controls remain operator-friendly in real manual use
- validate real operator workflows in a controlled rollout before claiming broad release readiness
- keep project documents truthful through per-milestone revision checkpoints

## Next Steps

1. Run controlled operator/UAT rollout on a normal desktop workflow before broadening release scope.
2. Recalibrate recipe scoring only if operator feedback shows the current metadata, asset-diversity, and runtime-evidence baseline is not useful enough.
3. Clean the Alembic `path_separator=os` warning in a maintenance pass.

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
- `IR-10` now adds runtime-backed audio masking review signals plus duration-unknown emergency-fill detection in manifest-backed review evidence
- `IR-11` now adds settings-backed voice/music gain staging with runtime manifest evidence and operator-visible balance controls
- `IR-12` now locks recovery audit shape to the current payload-backed seam until stronger cross-job audit requirements justify schema promotion
- `IR-13` now persists recipe-level score/risk summaries derived from metadata, asset composition, and runtime review evidence, and exposes them in Recipe Builder recipe surfaces
- `IR-14` now hot-reloads path-root dependent desktop services by rebuilding the runtime module and swapping live service proxies instead of requiring an app restart

## Ownership

- Engineering owner: implementation and automated verification
- Project management owner: SSOT status, Kanban, issue log, lesson log
