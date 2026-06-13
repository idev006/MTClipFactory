# Issues Log

## Open Issues

| ID | Date | Severity | Topic | Description | Owner | Status | Next Action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ISS-001 | 2026-06-05 | Medium | UI Direction | The original blueprint referenced Streamlit ideas, but the implementation SSOT is now PySide6 + MVVM. Team members must ignore legacy UI assumptions. | Engineering | Open | Continue updating docs and screens only from current repo behavior. |
| ISS-002 | 2026-06-05 | Medium | Module Boundary | `Video Assembly Factory` must consume prepared assets without mutating core asset metadata ownership owned by `Resource Library Management`. | Engineering | Open | Keep ownership rule explicit in architecture and service contracts. |
| ISS-019 | 2026-06-06 | Medium | Execution Roadmap Discipline | The project now needs implementation milestones with acceptance criteria so composition work lands in a controlled sequence instead of broad feature waves. | Project Management | Open | Maintain the implementation roadmap and keep Kanban/issues aligned to the current milestone. |
| ISS-020 | 2026-06-06 | Medium | Segment Heuristic Depth | Timeline segments are now persisted and validated, but segment content is still inferred from duration bands and recipe metadata instead of operator-authored structure. | Engineering | Open | Expose stronger segment authoring or refinement controls and reduce heuristic planning over time. |
| ISS-032 | 2026-06-13 | High | Distributed Worker Orchestration | Scalable worker-node execution now depends on a documented lease, heartbeat, retry, and idempotency model that does not yet exist in the implementation SSOT. | Engineering | Open | Deliver the shared job-state and worker-lease baseline before distributed execution work begins. |

## Closed Issues

| ID | Date Closed | Topic | Resolution |
| --- | --- | --- | --- |
| ISS-035-CLOSED | 2026-06-13 | Asset-First Tagging UX | Closed by redesigning the `Tags` workflow around one selected asset, adding selected-asset state in the view model, available-tag filtering, current-tag visibility, and `Create And Attach` behavior while preserving the current tag service seam. |
| ISS-034-CLOSED | 2026-06-13 | Tag-Aware Automation Selection | Closed by delivering optional `pipeline.toml [selection_tags]` planner rules, deterministic required-tag filtering for auto-factory asset pools, truthful shortfall reporting when tag rules remove ready visuals, and `Tags` screen hardening with `Asset Type` filtering plus visible current asset tag labels. |
| ISS-033-CLOSED | 2026-06-13 | Auto Factory Operator Control Surface | Closed by delivering a dashboard-reachable `Auto Factory` desktop screen with guided root-folder selection, `scan_depth`, explicit run modes, truthful intake reporting, recent production-order visibility, and a composed flow that routes materialize/preview runs through persisted `ProductionOrderService` records. |
| ISS-028-CLOSED | 2026-06-06 | Path Hot Reload Implementation | Closed by delivering a desktop-app runtime coordinator that rebuilds path-root dependent services, swaps live service proxies, hot-reloads database/media/output roots without a full restart, refreshes bound view models, and keeps dashboard path truth aligned through pytest-backed coverage. |
| ISS-031-CLOSED | 2026-06-13 | Production-Order State Model | Closed by delivering persisted `production_orders`, `production_order_items`, and `production_order_stages`, plus a `ProductionOrderService` that records control-plane `materialize`, `preview`, and `review` orchestration truth independently from recipe rows. |
| ISS-030-CLOSED | 2026-06-13 | UAT Coverage Depth | Closed by running a second controlled UAT pass with voiceover, background music, a second distinct foreground visual, generated thumbnail/proxy coverage, manifest-backed audio-mix evidence, and a no-review-gate richer-media result. |
| ISS-029-CLOSED | 2026-06-12 | Theme Separation Debt | Closed by extracting the settings-window stylesheet into package-backed QSS assets, adding a reusable `ui.theme` loader/apply seam, extending the shared app-window theme baseline across dashboard/library/factory windows, updating packaging metadata for `.qss` assets, and adding pytest coverage for theme loading/application. |
| ISS-027-CLOSED | 2026-06-06 | Recipe Scoring Depth | Closed by delivering persisted recipe-level `recipe_score` and `duplicate_risk`, a metadata-plus-asset heuristic that also reuses runtime review evidence, Recipe Builder visibility for score/risk summaries, and pytest coverage for both scoring logic and service/view-model flow. |
| ISS-026-CLOSED | 2026-06-06 | Recovery Audit Shape | Closed by auditing current recovery metadata usage and explicitly keeping recovery history payload-backed inside `jobs.output_json` until cross-job analytics, governance retention, or independent query requirements justify a dedicated schema. |
| ISS-025-CLOSED | 2026-06-06 | Multi-Layer Audio Depth | Closed by delivering settings-backed voice/music gain staging, runtime FFmpeg gain application, manifest-visible balance evidence, dashboard/settings visibility, and pytest coverage for the richer audio-polish baseline. |
| ISS-023-CLOSED | 2026-06-06 | Review Gate Depth | Closed by delivering runtime-backed audio masking review signals from render audio evidence, duration-unknown emergency-fill detection across visual and audio layers, manifest metrics, and pytest coverage. |
| ISS-008-CLOSED | 2026-06-06 | Path Reload Semantics | Closed by explicitly locking path-root reload semantics to restart-driven behavior, exposing runtime-vs-configured path roots on the dashboard, and surfacing restart-required path changes in operator feedback. |
| ISS-014-CLOSED | 2026-06-06 | Recovery Scope | Closed by delivering persisted recovery-attempt metadata, configurable failed-job escalation thresholds, deferred bulk-retry ordering, dashboard-visible escalated-job counts, and operator playbook guidance. |
| ISS-022-CLOSED | 2026-06-06 | Audio Mix Sophistication | Closed by delivering configurable duck modes, `sidechain_compressor` tuning fields, dashboard/settings visibility, runtime manifest evidence, and pytest coverage for both the new primary mode and fallback windowed mode. |
| ISS-024-CLOSED | 2026-06-06 | Composition Review Visibility | Closed by delivering configurable review thresholds, automatic `needs_review` routing, dashboard visibility for flagged recipes, manifest-backed review evidence, and pytest coverage for the new workflow. |
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
