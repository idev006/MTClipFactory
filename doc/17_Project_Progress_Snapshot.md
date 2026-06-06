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
- `Video Assembly Factory` is at a working review-and-render foundation, not a full composition engine yet.
- Dashboard and settings are now a stronger operational truth surface.
- Automatic queued-job recovery now exists when enabled. Failed jobs can now be retried from the dashboard, but they are still not auto-startup work.
- Output lineage is now visible from persisted output/job records.
- Approval actor/time/reason is persisted with migration support, and immutable decision-event history is now available in the Recipe Builder workflow.
- The composition direction is now documented: master timeline, semantic segments, `voice no-loop`, and `music ducking`.

## Delivered In The Latest Loop

- composition and timeline policy was written as SSOT before deeper render coding
- architecture, domain, reliability, roadmap, UML, Kanban, issues, and lessons learned were aligned to the new composition direction
- the project now has an explicit rule that narration must not auto-loop
- the project now has an explicit rule that music may loop and must duck under narration
- the roadmap and issue log now show the next implementation slice as timeline/data-model work before deeper render automation

## Still Open

1. richer preview composition
2. richer final-render composition
3. timeline/composition data model
4. audio priority and music ducking implementation
5. failed-job escalation policy beyond manual retry
6. optional hot-reload decision for path-root changes

## Verification Baseline

- `python -m pytest` in `.venv`: `72 passed`
- `QT_QPA_PLATFORM=offscreen` UI smoke: `6` main windows instantiated
