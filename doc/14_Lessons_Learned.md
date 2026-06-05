# Lessons Learned

## LL-001 | 2026-06-05 | Document-First Helped

- locking `.venv`, `.md`, `.toml`, SSOT, UML, Kanban, and issue logging early reduced project ambiguity
- documentation quality directly improved implementation speed because the repo now has stable decision memory

## LL-002 | 2026-06-05 | Split By Business Capability

- separating `Resource Library Management` from `Video Assembly Factory` is more useful than splitting by screens alone
- shared core plus separate workflows kept the codebase cohesive without needing multiple repositories yet

## LL-003 | 2026-06-05 | Testability Paid Off

- keeping service seams around metadata analysis, asset generation, and preview generation made it easy to add new pytest coverage quickly
- the project now benefits from fast in-memory repository tests and focused view model tests

## LL-004 | 2026-06-05 | Persisted Jobs Improve Truthfulness

- once artifact and preview work are represented as persisted jobs, dashboard reporting becomes much more honest
- queued and failed counts are more useful than silent background actions

## LL-005 | 2026-06-05 | Preview Build Is Not Approval

- generating a preview artifact is a processing milestone, not a business approval decision
- workflow states must reflect reality or the dashboard will mislead operators

## LL-006 | 2026-06-05 | Circular Imports Are Architectural Signals

- the circular import found between control-center and artifact code exposed an unhealthy runtime dependency shape
- solving it with type-only imports kept the design cleaner and improved test collection stability

## LL-007 | 2026-06-05 | No-Hardcode Needs Constant Enforcement

- moving operational thresholds into `app_config.toml` was a good step, but path configuration is still not complete
- the team should treat remaining implicit defaults as active debt, not “good enough”
