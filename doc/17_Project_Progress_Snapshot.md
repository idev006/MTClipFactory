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
- `Video Assembly Factory` now has segment-aware preview/final visual composition, but not a full audio-aware composition engine yet.
- Dashboard and settings are now a stronger operational truth surface.
- Automatic queued-job recovery now exists when enabled. Failed jobs can now be retried from the dashboard, but they are still not auto-startup work.
- Output lineage is now visible from persisted output/job records.
- Approval actor/time/reason is persisted with migration support, and immutable decision-event history is now available in the Recipe Builder workflow.
- The composition direction is now documented: master timeline, semantic segments, `voice no-loop`, and `music ducking`.
- The first composition persistence seam now exists through `composition_plans` and `render_decisions`.
- Semantic segment persistence now exists through `timeline_segments` with baseline contiguous-coverage validation.
- Preview composition is now segment-aware and writes inspectable manifest data for chosen visual clips.
- Final render now rerenders from the planned composition path instead of depending on the approved preview file alone.
- The roadmap is now split into strategic and implementation layers so the next coding milestone is clearer.

## Delivered In The Latest Loop

- final rendering now follows the planned composition path instead of promoting the approved preview file
- final output lineage now includes manifest-visible composition information plus approved-preview traceability
- parity is covered by a test that corrupts the preview file and still expects a correct final rerender
- architecture, reliability, roadmap, Kanban, issues, and lessons learned were aligned to the delivered `IR-04` baseline

## Still Open

1. audio priority and music ducking implementation
2. operator-visible render decision reporting
3. failed-job escalation policy beyond manual retry
4. optional hot-reload decision for path-root changes

## Verification Baseline

- `python -m pytest` in `.venv`: `78 passed`
- `QT_QPA_PLATFORM=offscreen` UI smoke: `6` main windows instantiated
