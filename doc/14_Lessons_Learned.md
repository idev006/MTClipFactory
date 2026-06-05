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

## LL-008 | 2026-06-06 | Path Config Must Be Explicit

- once path roots became first-class config, the dashboard and settings language also had to change from “runtime” to “configured” to stay truthful
- admin-facing controls are only useful when the system explains whether a change applies immediately or after restart

## LL-009 | 2026-06-06 | Output Records Matter

- writing a preview file alone is not enough; registering an output record makes reporting and product-level counts much more useful
- if work produces value, that value should usually enter the SSOT instead of living only on disk

## LL-010 | 2026-06-06 | Review Needs Explicit State

- “preview exists” and “content is approved” are different truths and should never be collapsed into one status
- separating output approval from recipe approval made the workflow much easier to explain and test

## LL-011 | 2026-06-06 | Final Render Can Start As Promotion Foundation

- a first final-render slice does not need full composition logic if it creates traceable value and preserves a clean seam for deeper rendering later
- promoting from an approved preview output gave us a safe bridge toward richer render orchestration without inventing hidden state

## LL-012 | 2026-06-06 | One Job Surface Improves Honesty

- once library and factory jobs share one dashboard surface, operators stop guessing where work is stuck
- a unified job vocabulary also makes retry behavior easier to explain, test, and document

## LL-013 | 2026-06-06 | Recovery Should Start Narrow And Truthful

- automatic recovery is safer when it begins with queued work only and leaves failed work under explicit human control
- putting recovery policy behind settings keeps the system durable without hiding side effects from operators

## LL-014 | 2026-06-06 | Reporting Can Get Better Before Schema Changes

- output reporting gained real value by correlating persisted output records with job payloads instead of waiting for a full audit-schema redesign
- deriving lineage from existing SSOT is safer than pretending approval history exists when it does not

## LL-015 | 2026-06-06 | Failed Recovery Should Stay Explicit

- allowing dashboard-driven failed-job retry improves operator control without silently re-running risky work at startup
- separating queued auto-recovery from failed manual retry keeps reliability policy easier to explain and trust

## LL-016 | 2026-06-06 | Schema Features Need Runtime Migration, Not Just Models

- once approval audit moved into persisted fields, Alembic had to become part of the real startup path instead of a document-only promise
- shipping schema changes without runtime upgrade support would have created a false sense of completeness
