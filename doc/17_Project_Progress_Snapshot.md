# Project Progress Snapshot

## Snapshot Date

- 2026-06-06

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
- Path roots now follow an explicit restart-driven activation policy, with runtime-active and configured-next-start roots shown separately for operator truthfulness.
- The roadmap is now split into strategic and implementation layers so the next coding milestone is clearer.

## Delivered In The Latest Loop

- recovery audit shape is now explicitly locked to the current payload-backed `jobs.output_json` seam instead of being left ambiguous
- docs now record the concrete trigger conditions that would justify promoting recovery history into a dedicated schema later
- pytest remains aligned with the delivered `IR-12` baseline because no runtime code path changed in this decision milestone
- architecture, reliability, roadmap, Kanban, issues, and lessons learned were aligned to the delivered `IR-12` baseline

## Still Open

1. implement optional path-root hot-reload only if restart-driven semantics become too costly in practice
2. broaden composition-confidence scoring only if current review heuristics stop being operationally useful

## Verification Baseline

- `python -m pytest` in `.venv`: `91 passed`
- `QT_QPA_PLATFORM=offscreen` UI smoke: `6` main windows instantiated
