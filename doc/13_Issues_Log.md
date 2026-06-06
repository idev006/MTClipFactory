# Issues Log

## Open Issues

| ID | Date | Severity | Topic | Description | Owner | Status | Next Action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ISS-001 | 2026-06-05 | Medium | UI Direction | The original blueprint referenced Streamlit ideas, but the implementation SSOT is now PySide6 + MVVM. Team members must ignore legacy UI assumptions. | Engineering | Open | Continue updating docs and screens only from current repo behavior. |
| ISS-002 | 2026-06-05 | Medium | Module Boundary | `Video Assembly Factory` must consume prepared assets without mutating core asset metadata ownership owned by `Resource Library Management`. | Engineering | Open | Keep ownership rule explicit in architecture and service contracts. |
| ISS-008 | 2026-06-06 | Medium | Path Reload Semantics | Path roots are now configurable, but a full runtime switch still assumes application restart for complete consistency. | Engineering | Open | Decide whether to keep restart semantics explicit or implement hot-reload for path-dependent services. |
| ISS-014 | 2026-06-06 | Medium | Recovery Scope | Startup queued-job recovery and manual failed-job retry now exist, but failed-job escalation and richer orchestration policy are still limited. | Engineering | Open | Expand recovery semantics beyond current sequential retry flow and document escalation rules. |
| ISS-022 | 2026-06-06 | Medium | Audio Mix Sophistication | Runtime voice/music mixing now exists, but ducking currently uses a windowed-volume strategy rather than a smoother envelope or sidechain-style mix. Richer multi-layer audio support is also still limited. | Engineering | Open | Evaluate smoother ducking and broader multi-layer audio policy after `IR-06` lands. |
| ISS-019 | 2026-06-06 | Medium | Execution Roadmap Discipline | The project now needs implementation milestones with acceptance criteria so composition work lands in a controlled sequence instead of broad feature waves. | Project Management | Open | Maintain the implementation roadmap and keep Kanban/issues aligned to the current milestone. |
| ISS-020 | 2026-06-06 | Medium | Segment Heuristic Depth | Timeline segments are now persisted and validated, but segment content is still inferred from duration bands and recipe metadata instead of operator-authored structure. | Engineering | Open | Expose stronger segment authoring or refinement controls and reduce heuristic planning over time. |

## Closed Issues

| ID | Date Closed | Topic | Resolution |
| --- | --- | --- | --- |
| ISS-018-CLOSED | 2026-06-06 | Audio Priority Policy | Closed by delivering runtime voice/music mixing in preview/final renderers, settings-driven duck policy consumption, manifest-visible audio-mix evidence, and pytest coverage for the supported mix path. |
| ISS-010-CLOSED | 2026-06-06 | Final Render Depth | Closed by delivering composition-based final rerendering, manifest-visible final lineage, and proof that final render no longer depends on the approved preview file alone. |
| ISS-009-CLOSED | 2026-06-06 | Preview Composition Depth | Closed by delivering segment-aware preview composition, manifest-visible segment clip planning, and explicit no-visual failure handling. Audio layering remains tracked separately. |
| ISS-021-CLOSED | 2026-06-06 | Timeline Segment Model | Closed by delivering persisted `timeline_segments`, Alembic migration coverage, validation rules, and service-level composition-plan retrieval with semantic segment output. |
| ISS-017-CLOSED | 2026-06-06 | Timeline Composition Model | Closed by delivering persisted `composition_plans` and `render_decisions`, service-level composition-plan retrieval, migration coverage, and pytest-backed duration/layer inference. |
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
