# Project Progress Snapshot

## Snapshot Date

- 2026-06-12

## Where To See Progress

1. In the desktop app dashboard:
   [src/mt_clip_factory/ui/control_center/dashboard_window.py](/F:/programming/python/MTClipFactory/src/mt_clip_factory/ui/control_center/dashboard_window.py)
2. Project manager status report:
   [11_Project_Status_Report.md](/F:/programming/python/MTClipFactory/doc/11_Project_Status_Report.md)
3. SSOT Kanban:
   [12_Kanban_Board.md](/F:/programming/python/MTClipFactory/doc/12_Kanban_Board.md)
4. Open issues and risks:
   [13_Issues_Log.md](/F:/programming/python/MTClipFactory/doc/13_Issues_Log.md)
5. Delivery learning log:
   [14_Lessons_Learned.md](/F:/programming/python/MTClipFactory/doc/14_Lessons_Learned.md)

## Honest Current State

- Foundation stack is established and testable on `Python 3.12 + SQLite + SQLAlchemy + PySide6 + pytest`.
- `Resource Library Management` is at a useful MVP baseline.
- `Video Assembly Factory` now has segment-aware preview/final visual composition plus a gain-staged runtime voice/music mix path, though it is still not a full audio-effects engine.
- Dashboard and settings are now a stronger operational truth surface.
- Dashboard now also exposes `needs_review` recipe count and the active review thresholds.
- Automatic queued-job recovery now exists when enabled. Failed jobs can now be retried from the dashboard, but they are still not auto-startup work.
- Output lineage is now visible from persisted output/job records.
- Approval actor/time/reason is persisted with migration support, and immutable decision-event history is now available in the Recipe Builder workflow.
- The composition direction is now documented: master timeline, semantic segments, `voice no-loop`, and `music ducking`.
- The first composition persistence seam now exists through `composition_plans` and `render_decisions`.
- Semantic segment persistence now exists through `timeline_segments` with baseline contiguous-coverage validation.
- Preview composition is now segment-aware and writes inspectable manifest data for chosen visual clips.
- Final render now rerenders from the planned composition path instead of depending on the approved preview file alone.
- Settings now expose `voice_loop_enabled`, `background_music_loop_enabled`, and music duck controls through `.toml` and the desktop settings screen.
- Dashboard and Recipe Builder now show more of the composition/render story instead of only output lineage.
- Preview and final renderers now emit manifest-visible runtime audio-mix evidence.
- Preview and final renderers now also emit manifest-visible review-gate evidence plus quality/duplicate-risk summaries.
- Review gates now also detect missing ducking protection during narration/music overlap and duration-unknown emergency fill across visual or audio layers.
- Preview and final renderers now support configurable duck modes with sidechain-compressor tuning evidence.
- Preview and final renderers now also support configurable voice/music gain staging with manifest-visible balance evidence.
- Failed jobs now retain persisted recovery-attempt history, escalate visibly after repeated failures, and surface operator playbook guidance on the dashboard.
- Recovery history now remains intentionally payload-backed on the `jobs` record until stronger cross-job audit needs appear.
- Path roots can now hot-reload inside the desktop app through a whole-module runtime rebind, and the dashboard still shows runtime-active versus configured paths truthfully.
- Recipe records now retain persisted score/risk summaries derived from metadata, asset composition, and runtime review evidence, and Recipe Builder now shows those summaries in the recipe list.
- The settings window now loads its styling from a package-backed QSS theme seam instead of embedding stylesheet text inline.
- Dashboard, resource-library, tag-dictionary, and recipe-builder windows now also consume a shared package-backed app-window theme baseline.
- Primary action buttons now have clearer but more restrained visual affordance through the shared theme, including balanced depth and pressed-state feedback.
- A controlled operator rollout kickoff guide now exists so the first real-use session can start from one practical SSOT entry point.
- Recipe Builder now explains its main workflow directly in the screen, makes the `ready`-asset-only attach list more explicit, gives the asset panel a more usable height, and provides a suggested attach-role pick list for faster operator input.
- The roadmap is now split into strategic and implementation layers, and the current mandatory implementation slice is complete.

## Delivered In The Latest Loop

- desktop app path-root changes now hot-reload by rebuilding the runtime service module and swapping live service proxies instead of waiting for a full restart
- settings save now emits runtime hot-reload feedback, and dashboard/path summaries stay aligned to the newly active roots
- pytest now covers pending hot-reload status, runtime module rebind, and settings-view-model hot-reload signaling
- architecture, reliability, roadmap, Kanban, issues, lessons learned, and UML were aligned to the delivered `IR-14` baseline
- settings UI now uses grouped panels and a two-column layout for clearer operator scanning
- hybrid slider-plus-exact-entry settings controls are now covered by widget-level pytest checks
- slider/editor width uniformity polish now keeps settings numeric controls visually aligned while preserving the hybrid control model
- a reusable `ui.theme` seam now loads packaged QSS assets, and the settings window theme was extracted out of Python code
- the broader desktop UI now shares one packaged app-window theme baseline, with focused window-level overrides reserved for justified differences
- packaged app-window buttons now read more clearly as clickable controls instead of flat color blocks, while staying proportionate to the rest of the UI
- a controlled operator rollout kickoff document now packages the go/no-go answer, first-run checklist, and first workflow for immediate use
- Recipe Builder layout hardening now improves asset-panel scanability and reduces confusion about why only `ready` assets appear in the attach list
- audit hardening now confirms pre-existing high-value config settings survive settings load/save without silent clamp
- audit hardening now also confirms exact numeric entry can push values beyond default slider spans without losing persistence truth
- full-system release audit now re-executes factory happy path, recovery/escalation flow, and runtime hot reload through a dedicated scripted audit runner
- operator-facing user manual is now published as SSOT document `27` for controlled rollout and UAT use

## Still Open

1. complete controlled operator/UAT rollout before broad release claims
2. recalibrate recipe scoring only if the current metadata, asset-diversity, and runtime-evidence baseline stops being operationally useful

## Verification Baseline

- `python -m pytest` in `.venv`: `111 passed`
- `QT_QPA_PLATFORM=offscreen` UI smoke: `6` main windows instantiated
