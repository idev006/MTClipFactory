# Issues Log

## Open Issues

| ID | Date | Severity | Topic | Description | Owner | Status | Next Action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ISS-001 | 2026-06-05 | Medium | UI Direction | The original blueprint referenced Streamlit ideas, but the implementation SSOT is now PySide6 + MVVM. Team members must ignore legacy UI assumptions. | Engineering | Open | Continue updating docs and screens only from current repo behavior. |
| ISS-002 | 2026-06-05 | Medium | Module Boundary | `Video Assembly Factory` must consume prepared assets without mutating core asset metadata ownership owned by `Resource Library Management`. | Engineering | Open | Keep ownership rule explicit in architecture and service contracts. |
| ISS-008 | 2026-06-06 | Medium | Path Reload Semantics | Path roots are now configurable, but a full runtime switch still assumes application restart for complete consistency. | Engineering | Open | Decide whether to keep restart semantics explicit or implement hot-reload for path-dependent services. |
| ISS-009 | 2026-06-06 | Medium | Preview Composition Depth | Preview output currently supports a simple renderable-video path. It does not yet reflect layered composition, timing control, or audio mixing. | Engineering | Open | Add richer composition pipeline and explicit role-based render rules. |
| ISS-010 | 2026-06-06 | Medium | Final Render Depth | Current final-render flow promotes from an approved preview output as a foundation. It is traceable and useful, but not yet a full recomposition pipeline. | Engineering | Open | Add richer final renderer with composition/audio-aware pipeline and stronger reporting. |
| ISS-014 | 2026-06-06 | Medium | Recovery Scope | Startup queued-job recovery and manual failed-job retry now exist, but failed-job escalation and richer orchestration policy are still limited. | Engineering | Open | Expand recovery semantics beyond current sequential retry flow and document escalation rules. |
| ISS-017 | 2026-06-06 | Medium | Timeline Composition Model | The project now has direction for master timeline, semantic segments, and layered composition, but the actual data model and implementation are not built yet. | Engineering | Open | Design the composition-plan, segment, and render-decision model from the new SSOT policy. |
| ISS-018 | 2026-06-06 | Medium | Audio Priority Policy | The team has aligned on `voice no-loop` and `music ducking`, but those rules are not yet implemented in preview/final render flows. | Engineering | Open | Implement configurable narration/music policy with operator-visible render decisions. |
| ISS-019 | 2026-06-06 | Medium | Execution Roadmap Discipline | The project now needs implementation milestones with acceptance criteria so composition work lands in a controlled sequence instead of broad feature waves. | Project Management | Open | Maintain the implementation roadmap and keep Kanban/issues aligned to the current milestone. |

## Closed Issues

| ID | Date Closed | Topic | Resolution |
| --- | --- | --- | --- |
| ISS-016-CLOSED | 2026-06-06 | Approval History Depth | Closed by delivering an append-only `decision_events` ledger, migration coverage, service retrieval, and Recipe Builder visibility. |
| ISS-015-CLOSED | 2026-06-06 | Approval Audit Depth | Closed by delivering Alembic-backed approval actor/time/reason persistence plus runtime migration support. |
| ISS-013-CLOSED | 2026-06-06 | Auto Resume Depth | Closed by delivering configurable queued-job recovery orchestration through dashboard/manual trigger and startup policy for persisted jobs. |
| ISS-004-CLOSED | 2026-06-06 | Recovery Depth | Closed by delivering a uniform manual retry path across artifact, preview, and final persisted jobs, plus restart-style retry coverage for factory jobs. |
| ISS-011-CLOSED | 2026-06-06 | Review Workflow Gap | Closed by delivering output approval plus recipe approval/rejection workflow. |
| ISS-012-CLOSED | 2026-06-06 | Output Visibility Gap | Closed by delivering output browsing/reporting foundation in the Recipe Builder UI. |
| ISS-003-CLOSED | 2026-06-06 | Preview Depth | Closed by delivering preview output rendering plus output registration foundation. |
| ISS-005-CLOSED | 2026-06-06 | Path Configurability | Closed by adding `[paths]` support for database, media, docs, outputs, and preview roots. |
| ISS-006-CLOSED | 2026-06-05 | Artifact Generation Gap | Closed by delivering persisted thumbnail/proxy generation jobs and dashboard visibility. |
| ISS-007-CLOSED | 2026-06-05 | Empty Factory Package | Closed by delivering recipe persistence, preview jobs, and recipe builder UI scaffolding. |

## Rule

- anything affecting scope, architecture, reliability, or schedule goes here
- closing an issue requires a concrete resolution statement, not only code merged
