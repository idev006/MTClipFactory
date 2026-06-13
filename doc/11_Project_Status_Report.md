# Project Status Report

## Project Manager Snapshot

- Report date: 2026-06-13
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
- Recipe Builder now explains its recipe-to-final purpose more directly, clarifies that the attach list shows only `ready` assets, keeps the asset panel tall enough for practical scanning, and offers composition-aware attach-role suggestions that combine asset type, current recipe segment order, auto-selection, and on-screen guidance instead of relying on free-typed role names alone
- Recipe Builder now uses a resizable three-column workspace so setup/actions, asset attachment, and output review can each claim more space without forcing the operator to fight one fixed grid
- Recipe Builder tables now declare vertical-scroll behavior explicitly so overflow rows stay usable without adding pagination
- Auto Factory batch planning now exists as a first automation slice, including production-order DTOs, batch-only uniqueness planning, voice-with-bounds duration resolution, planner-capacity truth, and internal recipe generation through the existing factory service seam
- assets can now be safely renamed or deleted from the `Assets` screen, with repository checks that block deletion when recipe-item or artifact-job references still exist
- the `Assets` screen now supports `Show References`, `Retire Selected`, and `Purge Media` so referenced assets can leave active use and disk without destroying audit truth
- the `Assets` screen now also supports `Replace In Recipes...` with recipe-safe validation, recipe reset-to-candidate behavior, and approval guards that prevent stale pre-replacement outputs from being reused as evidence for changed recipes
- Recipe Builder now surfaces replacement aftercare directly in the outputs area, including workflow guidance, per-output aftercare state, and historical-only visibility for outputs created before replacement
- preview and final render now normalize mixed visual source ratios into the recipe `Target Ratio` frame so output dimensions stay bounded and operator intent is respected
- preview and final render now support a layered visual compositing baseline for stacked `background_video` plus keyed `foreground_video`, with manifest-visible visual composite evidence and green-screen detection for clear presenter-over-background cases
- settings now expose a `Visual Composite` policy seam so operators can choose `auto`, `green`, `blue`, `magenta`, `custom`, or `disabled` key-color behavior for non-green studio backgrounds
- operators can now set exact preview and final output resolutions through the `Settings` UI, with `.toml` persistence and renderer enforcement for frames such as `1080x1920`
- widget-level settings UI verification coverage, including hybrid control mapping, high-value config preservation, and exact-entry synchronization
- scripted full-system release audit coverage for product-to-final workflow, recovery/escalation behavior, and runtime path hot reload
- operator-facing user manual now exists as SSOT guidance for controlled rollout and UAT
- controlled operator rollout kickoff guidance now exists as an execution-ready entry point for first real use on the current baseline
- the first controlled operator/UAT execution run has now completed a real recipe-to-final workflow and produced a verified final output at `720x1280`
- the second controlled operator/UAT run has now validated the richer-media path with voiceover, background music, two distinct foreground visuals, manifest-backed ducking evidence, and a no-review-gate final result
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

- `python -m pytest` via `.venv`: `156 passed`
- UI smoke via `QT_QPA_PLATFORM=offscreen`: `6` windows instantiated successfully

## Current Focus

- keep richer review signals and approval history truthful through append-only persistence
- monitor whether runtime path reload stays truthful and easy for operators to understand
- monitor whether the new recipe scoring baseline stays operationally useful for operators
- monitor whether hybrid settings controls remain operator-friendly in real manual use
- validate whether the new asset-maintenance controls are clear enough for operators without additional UI restructuring
- validate whether the new referenced-asset lifecycle controls are clear enough for operators during controlled use
- validate broader controlled operator use on real campaign media before claiming broad release readiness
- monitor whether operators understand the distinction between recipe `Target Ratio` and settings-level exact output resolution
- validate whether the new green-screen compositing baseline is robust enough across real foreground media and not only the current controlled sample
- validate whether the new non-green key policy is clear enough for operators and whether per-asset overrides are needed after broader use
- validate whether the new resizable Recipe Builder workspace reduces operator confusion during attach-versus-review work
- validate folder-driven batch intake and preview/final automation only after the new auto-factory planner baseline proves stable
- keep project documents truthful through per-milestone revision checkpoints

## Next Steps

1. Run broader controlled operator use on real campaign media without service-side assistance and record operator findings on both the asset-replacement and layered-compositing workflows.
2. Extend the auto-factory baseline from internal recipe generation into controlled preview/final automation only after planner-capacity truth is accepted.
3. Decide whether per-asset compositing overrides are justified beyond the new settings-level key policy.
4. Recalibrate recipe scoring only if operator feedback shows the current metadata, asset-diversity, and runtime-evidence baseline is not useful enough.
5. Clean the Alembic `path_separator=os` warning in a maintenance pass.

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
