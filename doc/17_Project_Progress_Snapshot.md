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
- Automatic unattended recovery is not done yet. Manual retry is done.

## Delivered In The Latest Loop

- dashboard now combines persisted jobs from library and factory workflows
- dashboard now shows recent jobs and operational attention text
- factory preview/final jobs now support manual retry from persisted state
- factory retry behavior is covered with restart-style service recreation tests
- documents, Kanban, issues, and lessons learned were updated with the same milestone

## Still Open

1. richer preview composition
2. richer final-render composition
3. output approval trail and reporting depth
4. automatic resume/orchestrator behavior after restart
5. optional hot-reload decision for path-root changes

## Verification Baseline

- `python -m pytest` in `.venv`: `64 passed`
- `QT_QPA_PLATFORM=offscreen` UI smoke: `6` main windows instantiated
