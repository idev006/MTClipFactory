# Implementation Roadmap

This document is the execution-facing roadmap for turning the current composition policy into code.

It complements [08_MVP_Roadmap.md](/F:/programming/python/MTClipFactory/doc/08_MVP_Roadmap.md), which remains the strategic roadmap.

## Purpose

- translate the strategic roadmap into implementation-sized milestones
- define sequencing and acceptance criteria before deeper render work begins
- keep code, UML, tests, dashboard visibility, and settings work aligned in one delivery path

## Planning Model

The project now uses two roadmap layers:

- `Strategic roadmap`: phase-level direction and project scope
- `Implementation roadmap`: milestone-level execution order and acceptance criteria

## Delivery Status

- `IR-01` Composition data model: complete on 2026-06-06
- `IR-02` Timeline segment model: complete on 2026-06-06
- `IR-03` Segment-based preview composition: complete on 2026-06-06
- `IR-04` Final-render composition parity: complete on 2026-06-06
- `IR-05a` Audio policy settings and operator-visible render decisions: complete on 2026-06-06
- `IR-05b` Runtime audio ducking application: complete on 2026-06-06
- `IR-06` Review gates and composition reliability controls: complete on 2026-06-06
- `IR-07` Audio-mix quality refinement beyond windowed-duck baseline: complete on 2026-06-06
- `IR-08` Recovery escalation rules and operator playbook: complete on 2026-06-06
- `IR-09` Path-root reload decision and runtime truthfulness: complete on 2026-06-06
- `IR-10` Runtime-backed review signals for audio masking and emergency fill: complete on 2026-06-06
- `IR-11` Voice-priority gain staging and audio-balance visibility: complete on 2026-06-06
- `IR-12` Payload-backed recovery audit decision: complete on 2026-06-06
- `IR-13` Recipe scoring refinement and operator-visible score/risk summaries: complete on 2026-06-06
- `IR-14` Path-root runtime hot reload: complete on 2026-06-06
- `IR-15` Auto Factory batch planning baseline: complete on 2026-06-13
- `IR-16` Folder-driven batch intake baseline: complete on 2026-06-13
- `IR-17` Auto Factory preview production baseline: complete on 2026-06-13
- `IR-18` Enterprise factory pipeline review and architecture blueprint: complete on 2026-06-13
- `IR-19` Production-order and shared job-state orchestration baseline: complete on 2026-06-13
- `IR-21` Folder discovery depth and assisted tagging ergonomics: complete on 2026-06-13
- `IR-22` Auto Factory desktop control surface baseline: complete on 2026-06-13
- `IR-23` Tag-aware auto-factory selection baseline: complete on 2026-06-13
- `IR-24` Asset-first tagging workflow baseline: complete on 2026-06-13
- `IR-25` Bulk asset tagging workflow baseline: complete on 2026-06-14

## Current Execution Stream

The next mandatory implementation stream should build worker lease, heartbeat, and retry semantics on top of the new production-order control-plane baseline.

The newly delivered auto-factory desktop control surface is intentionally additive and does not change the mandatory priority of `IR-20`.

Backlog activation rules:

1. Further recipe-score calibration only activates if the delivered metadata, asset-diversity, and runtime-evidence baseline stops being operationally useful.
2. Distributed worker execution does not activate before lease, heartbeat, and retry semantics are implemented on the new control-plane baseline.

## IR-01 | Composition Data Model

### Goal

Create the first persistent planning model for timeline-driven composition.

### Scope

- introduce a `composition_plan` concept for one recipe/render
- define master duration source and resolved duration
- define layer assignment structure
- define a persisted render-decision structure direction

### Acceptance Criteria

- SSOT docs and UML describe the chosen model
- persistence direction is documented clearly enough for Alembic planning
- preview/final services have a clean seam for using a composition plan later
- open questions are logged in issues if not implemented yet

### Delivery Result

- delivered `composition_plans` and `render_decisions` persistence with Alembic migration `20260606_0004`
- added recipe-level composition-plan retrieval through `VideoAssemblyFactoryService`
- covered duration resolution and layer inference with pytest
- left timeline segments and deeper preview/final composition for the next milestones

## IR-02 | Timeline Segment Model

### Goal

Represent semantic segments such as `hook`, `problem`, `benefit`, `proof`, and `cta`.

### Scope

- define `timeline_segment`
- define segment timing fields
- define segment-to-layer expectations
- define minimal validation rules

### Acceptance Criteria

- UML shows segment flow inside the composition plan
- domain model and architecture docs are updated
- segment validation rules are testable and documented
- Kanban and issues reflect any remaining gaps

### Delivery Result

- delivered persisted `timeline_segments` with Alembic migration `20260606_0005`
- added contiguous-coverage validation for semantic segment timing
- extended composition-plan retrieval to return segment DTOs
- logged the remaining heuristic-planning gap for later preview and authoring work

## IR-03 | Segment-Based Preview Composition

### Goal

Replace the current simple preview render path with a segment-aware preview pipeline.

### Scope

- resolve one master timeline for preview
- apply background fill policy for preview visuals
- keep narration non-looping
- use policy-driven music fill behavior
- preserve existing job persistence and output registration

### Acceptance Criteria

- preview follows the composition plan instead of a simple renderable-video path
- pytest covers timeline resolution and preview composition behavior
- preview output/reporting exposes enough detail to inspect the chosen composition path
- docs, UML, and progress artifacts are updated in the same loop

### Delivery Result

- delivered segment-aware preview composition built from persisted composition plans and timeline segments
- added manifest-visible segment clip mapping and fill-mode reporting
- covered preview composition behavior and no-visual failure handling with pytest
- left final-render parity and audio ducking for the next milestones

## IR-04 | Final-Render Composition Parity

### Goal

Make final render follow the same composition semantics as preview.

### Scope

- final render uses the composition plan, not only preview promotion
- align preview/final behavior except for quality/runtime differences
- keep lineage reporting truthful

### Acceptance Criteria

- preview and final use the same business rules
- differences between preview and final are documented and intentional
- lineage and render-decision visibility remain truthful
- tests prove preview/final policy parity for core scenarios

### Delivery Result

- delivered composition-based final rerendering from persisted plans and timeline segments
- preserved approved-preview lineage while removing dependence on the preview file as the final render source
- added final manifest visibility and a corruption-proof parity test
- left audio ducking and richer operator-facing render decision surfaces for the next milestones

## IR-05a | Audio Policy Settings And Render Decision Visibility

### Goal

Expose the agreed audio policy and composition decisions to operators through settings, dashboard, and factory inspection surfaces.

### Scope

- add configurable narration/music policy settings in `.toml` and settings UI
- keep narration as the documented foreground message layer
- expose persisted composition/render summaries in factory UI and dashboard views
- cover the new visibility and settings seams with pytest

### Acceptance Criteria

- narration never auto-loops in supported composition paths
- music ducking is configurable through settings and `.toml`
- operator-facing surfaces show render decisions clearly
- tests cover ducking configuration and decision visibility

### Delivery Result

- delivered `[audio]` policy settings in `app_config.toml`
- exposed audio policy controls in the settings window and dashboard
- exposed composition-plan segment summaries and render-decision summaries in Recipe Builder output inspection
- covered audio policy persistence and operator visibility with pytest

## IR-05b | Runtime Audio Ducking Application

### Goal

Apply the configured narration/music policy inside preview and final rendering, not only in settings and UI visibility.

### Scope

- build a real runtime audio mix path for narration and music layers
- consume configured duck enable/gain/attack/release settings
- emit inspectable evidence that ducking was applied in the render output metadata or manifest
- keep preview/final parity truthful

### Acceptance Criteria

- preview and final both consume the configured duck policy
- runtime output contains inspectable evidence of applied audio behavior
- tests cover the supported audio-mix path
- issues and PM artifacts remain truthful about any remaining limits

### Delivery Result

- delivered runtime voice/music mixing in preview and final renderers
- consumed configured duck gain plus attack/release timing in the supported mix path
- wrote applied audio-mix evidence into preview/final manifests
- extended Recipe Builder output details so operators can inspect manifest-backed audio evidence
- covered runtime mix command generation, manifest evidence, and operator visibility with pytest

## IR-06 | Review Gates And Composition Reliability

### Goal

Prevent low-trust automatic renders from slipping through silently.

### Scope

- add review thresholds for duration mismatch
- add loop repetition warnings
- add emergency-fill or low-confidence review states
- align reliability reporting with dashboard visibility

### Acceptance Criteria

- risky composition cases trigger reviewable outcomes instead of silent completion
- dashboard or factory UI can show why review is required
- issues and lessons learned capture important reliability tradeoffs
- final roadmap/status docs reflect the new baseline honestly

### Delivery Result

- delivered configurable review thresholds through `app_config.toml`, `SystemSettingsService`, settings UI, and dashboard summary
- delivered automatic `needs_review` routing for risky preview compositions based on duration mismatch and visual repetition heuristics
- persisted manifest-backed `review_gate` evidence plus output `quality_score` and `duplicate_risk`
- exposed review evidence in Recipe Builder output details and dashboard recipe-review counts
- enforced explicit human reasoning when approving a recipe that was flagged for review
- covered review-gate routing and approval enforcement with pytest

## IR-07 | Audio-Mix Quality Refinement Beyond Windowed-Duck Baseline

### Goal

Improve runtime narration/music mixing quality without sacrificing testability, operator visibility, or configurability.

### Scope

- introduce configurable duck modes with a higher-quality default path
- keep `windowed_volume_duck` as a supported fallback for safe compatibility
- add sidechain-compressor tuning fields to settings, dashboard, and `.toml`
- expose the applied duck mode and tuning evidence in runtime manifest summaries

### Acceptance Criteria

- preview and final renderers can use a configurable higher-quality duck mode
- the chosen duck mode and tuning settings are visible in operator-facing evidence
- tests cover settings persistence plus runtime command generation for the new mode
- roadmap, architecture, UML, Kanban, issues, and lessons learned stay aligned to the delivered baseline

### Delivery Result

- delivered configurable duck modes with `sidechain_compressor` as the higher-quality default and `windowed_volume_duck` as a supported fallback
- delivered settings-backed duck mode, threshold, and ratio fields through `app_config.toml`, `SystemSettingsService`, dashboard summary, and settings UI
- wrote manifest-visible runtime evidence for the applied duck mode and its active tuning fields
- extended Recipe Builder audio detail rendering to expose threshold/ratio evidence when present
- covered new mode selection, fallback behavior, and settings persistence with pytest and re-verified the full suite plus UI smoke

## IR-08 | Recovery Escalation Rules And Operator Playbook

### Goal

Make failed-job recovery more truthful and more actionable without silently widening automation scope.

### Scope

- persist recovery-attempt and failure-streak metadata on jobs
- add a configurable failed-job escalation threshold in `.toml`, settings UI, and dashboard summary
- prioritize non-escalated failed jobs first during bulk retry and defer escalated jobs when the configured run cap is reached
- expose operator playbook guidance and escalated-job visibility through the dashboard

### Acceptance Criteria

- repeated failed retries become visible as escalated jobs instead of one flat failure bucket
- dashboard recovery summaries show deferred and escalated job codes when relevant
- failed-job bulk retry follows a documented prioritization rule instead of simple sequential order
- pytest covers the new recovery metadata, prioritization, and dashboard visibility seams
- roadmap, UML, reliability docs, Kanban, issues, and lessons learned stay aligned to the delivered baseline

### Delivery Result

- delivered persisted recovery metadata through shared job payload helpers used by artifact and factory job services
- delivered settings-backed `failed_job_escalation_threshold` through `app_config.toml`, `SystemSettingsService`, settings UI, and dashboard summary
- delivered deferred bulk-retry ordering that prioritizes lower-risk failed jobs ahead of escalated ones under `max_recovery_jobs_per_run`
- delivered dashboard-visible escalated job counts, recovery summary details, and operator playbook guidance for current failed jobs
- covered recovery metadata persistence, escalation ordering, and operator visibility with pytest

## IR-09 | Path-Root Reload Decision And Runtime Truthfulness

### Goal

Lock path-root reload semantics to a truthful, operator-visible baseline instead of implying unsupported hot reload.

### Scope

- declare path-root reload policy as restart-driven
- expose runtime-active and configured-next-start path roots separately in the dashboard
- surface restart-required path changes in operator attention and settings feedback
- cover the new path-status seams with pytest

### Acceptance Criteria

- operators can tell which path roots are active now versus only configured for next startup
- path-root changes no longer appear to hot-apply when runtime services are still using startup-wired roots
- settings feedback and dashboard attention both explain when restart is required
- roadmap, UML, Kanban, issues, lessons learned, and reliability docs reflect the locked decision honestly

### Delivery Result

- delivered shared path-root status reporting through `SystemSettingsService` and dashboard summaries
- delivered runtime-active versus configured-next-start path visibility across dashboard summary and path detail surfaces
- delivered restart-pending operator feedback when saved path roots diverge from the running app configuration
- covered fresh-start and save-before-restart path semantics with pytest

## IR-10 | Runtime-Backed Review Signals For Audio Masking And Emergency Fill

### Goal

Deepen review gating with runtime-backed evidence so risky audio overlap and emergency-fill outcomes become operator-visible instead of implicit.

### Scope

- move review assessment to the point where renderer audio evidence is available
- add `audio_masking_risk` when narration and music coexist without confirmed ducking
- add `emergency_fill_detected` for duration-unknown visual or audio layers
- persist supporting review metrics through manifest-backed review evidence
- cover the new unit and service seams with pytest

### Acceptance Criteria

- runtime audio evidence can change the preview/final review result when masking protection is missing
- duration-unknown emergency-fill outcomes are visible in review signals and metrics
- tests cover direct review evaluation and service-level manifest routing
- roadmap, UML, reliability docs, Kanban, issues, and lessons learned stay aligned to the delivered baseline

### Delivery Result

- delivered review assessment ordering that now consumes renderer audio evidence before finalizing review state
- delivered manifest-visible `audio_masking_risk` when narration and music overlap without confirmed ducking protection
- delivered manifest-visible `emergency_fill_detected` across duration-unknown visual clips and audio tracks
- covered unit-level review evaluation plus service-level manifest routing with pytest

## IR-11 | Voice-Priority Gain Staging And Audio-Balance Visibility

### Goal

Improve runtime audio polish with configurable layer balance so narration stays foregrounded without relying on ducking alone.

### Scope

- add settings-backed voice and music mix gains in `.toml`, dashboard summary, and settings UI
- apply runtime FFmpeg gain staging to voice and music layers before the final mix
- expose gain-stage balance evidence through manifest-backed audio summaries and Recipe Builder details
- keep preview/final parity truthful
- cover the new settings and runtime seams with pytest

### Acceptance Criteria

- preview and final renderers consume configurable voice/music gain settings during runtime mixing
- operator-facing surfaces can inspect the active voice/music balance policy and resulting manifest evidence
- tests cover settings persistence, runtime command generation, and manifest/UI audio-detail visibility
- roadmap, UML, architecture, issues, lessons learned, and status docs remain aligned to the delivered baseline

### Delivery Result

- delivered settings-backed `voice_mix_gain_db` and `music_mix_gain_db` through `app_config.toml`, `SystemSettingsService`, dashboard summary, and settings UI
- delivered runtime FFmpeg gain staging for voice and music layers before the final mix path
- delivered manifest-visible `mix_balance` evidence plus Recipe Builder audio-detail visibility for applied gain settings
- covered renderer, settings, dashboard, manifest, and service-level seams with pytest

## IR-12 | Payload-Backed Recovery Audit Decision

### Goal

Lock the recovery-audit architecture to a truthful baseline instead of leaving future schema work implied without evidence.

### Scope

- audit how recovery metadata is currently written, read, and surfaced across library, factory, and dashboard flows
- decide whether the existing payload-backed seam is sufficient for the current operational scope
- document the trigger conditions that would justify a dedicated recovery-audit schema later
- align roadmap, issues, architecture, and reliability docs to the chosen decision

### Acceptance Criteria

- the project states clearly whether recovery metadata is intentionally payload-backed or only temporarily so
- issue tracking and reliability docs explain when schema promotion would become justified
- UML and architecture docs remain truthful about where recovery metadata lives today
- no migration or table is introduced without a demonstrated operational need

### Delivery Result

- delivered an explicit architecture decision to keep recovery history payload-backed inside `jobs.output_json` for the current scope
- documented schema-promotion triggers around cross-job analytics, governance retention, and independent query/reporting needs
- closed the open recovery-audit-shape issue without inventing unused persistence
- aligned roadmap, status, Kanban, UML, and reliability docs to the locked decision

## IR-13 | Recipe Scoring Refinement And Operator-Visible Score/Risk Summaries

### Goal

Make recipe-level confidence scoring operationally useful instead of leaving persisted score/risk fields dormant.

### Scope

- derive `recipe_score` from recipe metadata completeness plus attached-asset composition
- derive recipe-level `duplicate_risk` from asset reuse and role/visual diversity
- let runtime review evidence refine the persisted recipe score/risk after preview/final rendering
- expose score/risk through service DTOs and Recipe Builder recipe summaries
- cover the scoring heuristic and propagation seams with pytest

### Acceptance Criteria

- recipe records retain non-dormant score/risk values after create, attach, and render workflows
- Recipe Builder recipe surfaces show score/risk summaries without requiring manifest inspection first
- runtime review evidence can influence the persisted recipe score/risk after render jobs complete
- roadmap, UML, architecture, issues, lessons learned, and PM status docs remain aligned to the delivered baseline

### Delivery Result

- delivered a reusable recipe-scoring helper that combines metadata completeness, asset mix, and runtime review evidence
- delivered persisted recipe-level `recipe_score` and `duplicate_risk` refresh during recipe create, asset attach, preview render, and final render flows
- delivered score/risk propagation through repository summaries, service DTOs, and Recipe Builder recipe-list visibility
- covered the scoring heuristic directly plus service/view-model propagation with pytest

## IR-14 | Path-Root Runtime Hot Reload

### Goal

Apply configured path-root changes inside the live desktop app without forcing a full restart, while keeping runtime truthfulness intact.

### Scope

- introduce a desktop-app runtime coordinator that can rebuild the path-root dependent service module
- keep view-model references stable by swapping live service proxies instead of reconstructing every window
- apply newly configured database, media, docs, outputs, and preview roots together as one runtime rebind
- surface hot-reload feedback through settings and dashboard path summaries
- cover pending-status, runtime-rebind, and settings-triggered hot-reload seams with pytest

### Acceptance Criteria

- saving changed path roots from the desktop app makes the new roots active without a full process restart
- dashboard path summaries stay truthful about runtime-active versus configured roots before and after reload
- view models can keep operating after a runtime path reload without being manually reconstructed
- roadmap, UML, architecture, issues, lessons learned, and PM status docs remain aligned to the delivered baseline

### Delivery Result

- delivered `ApplicationRuntime` plus reloadable service proxies so the desktop app can rebuild and swap the entire path-root dependent module at runtime
- delivered settings-driven runtime hot reload that refreshes bound view models after a successful path-root rebind
- delivered dashboard-path truth surfaces that now distinguish restart-required behavior from hot-reload-capable runtime behavior
- covered pending hot-reload status, database-root rebind behavior, and settings-view-model signaling with pytest

## IR-15 | Auto Factory Batch Planning Baseline

### Goal

Add a truthful first automation seam so operators can request output counts by product without hand-building every recipe.

### Scope

- define `Production Order` as the operator-facing batch request model
- lock first-slice policies to `uniqueness_scope = "batch"` and `duration_mode = "voice_with_bounds"`
- introduce an auto-factory batch service that uses existing product, asset, and factory services
- estimate planner-feasible unique capacity before creating internal recipes
- materialize internal recipes automatically when the order can be fulfilled
- cover planning and materialization seams with pytest

### Acceptance Criteria

- batch planning reports requested count versus planner-feasible unique count per product
- duplicate output fingerprints are prevented within the same batch under current planner policy
- duration planning follows `voice_with_bounds` with fixed fallback when no voiceover exists
- the service can create internal recipes and assign assets automatically through current factory APIs
- SSOT workflow, UML, status, and test-plan docs remain aligned to the delivered slice

### Delivery Result

- delivered `AutoFactoryBatchService` plus DTOs for production-order planning and batch materialization
- delivered deterministic constrained-variant planning with batch-only uniqueness fingerprints and truthful shortfall reporting
- delivered internal recipe generation through the existing `VideoAssemblyFactoryService` instead of bypassing business rules
- covered unique-capacity planning, shortfall blocking, duration fallback, and recipe materialization with pytest

## IR-16 | Folder-Driven Batch Intake Baseline

### Goal

Turn the new auto-factory planner into a practical ingestion seam by reading product folders plus `.toml` contracts instead of requiring all assets and requests to be supplied manually in code.

### Scope

- define `product.toml` and `pipeline.toml` as the folder-contract SSOT inputs
- discover product folders under one batch root
- create missing products automatically from `product.toml`
- register deterministic asset codes from `foreground/background/music/voice`
- skip already-ingested deterministic asset codes on rerun
- build one production order from the folder tree and materialize internal recipes

### Acceptance Criteria

- a batch root with one or more valid product folders can be processed end to end into internal recipes
- rerunning the same batch root does not duplicate asset records for already-ingested files
- invalid or incomplete folder contracts fail truthfully before silent partial production
- roadmap, UML, status, progress, and test-plan docs remain aligned to the delivered slice

### Delivery Result

- delivered `AutoFactoryFolderService` to parse folder contracts, bootstrap products, ingest deterministic asset codes, and invoke the existing batch planner
- delivered rerun-safe skip behavior for already-ingested deterministic asset codes instead of duplicating asset records
- delivered folder-contract pytest coverage for success, rerun idempotence, shortfall propagation, and invalid TOML structure
- kept preview/final auto-run, watcher loops, and automation UI explicitly deferred behind the new folder-intake baseline

## IR-17 | Auto Factory Preview Production Baseline

### Goal

Turn materialized auto-factory recipes into real preview outputs automatically, while preserving the normal human review and approval boundary.

### Scope

- enqueue one preview job per created recipe in materialized batch order
- run preview rendering automatically for those recipes
- return per-recipe batch result truth including job status, output path, output identity, and resulting recipe review state
- keep output approval, recipe approval, and final render explicitly outside this automation slice
- extend folder-driven runs so they can optionally build previews after materialization

### Acceptance Criteria

- a satisfiable materialized batch can automatically produce preview outputs without manual per-recipe clicking
- preview failures are reported per recipe without hiding partial success
- folder-driven batch intake can optionally continue into preview production in the same service-level flow
- approval and final-render boundaries remain explicit and human-controlled
- roadmap, UML, status, progress, and test-plan docs remain aligned to the delivered slice

### Delivery Result

- delivered batch-level preview orchestration through `AutoFactoryBatchService.build_previews_for_materialized_batch(...)` and `materialize_batch_and_build_previews(...)`
- delivered per-recipe preview production reporting with job status, output path, output identity, failure text, and resulting recipe status
- delivered optional folder-run preview automation through `AutoFactoryFolderService.run_batch_root(..., build_previews=True)`
- delivered pytest coverage for happy-path preview automation, partial preview failure continuity, folder-run preview production, and invalid preview-without-materialization requests
- kept approval automation, final-render automation, watcher loops, and automation UI explicitly deferred

## IR-18 | Enterprise Factory Pipeline Review And Architecture Blueprint

### Goal

Lock the enterprise operating model before scalable worker orchestration or deeper final-render automation begins.

### Scope

- review the current system as a full video-production pipeline instead of only milestone slices
- define the four-plane architecture vocabulary: `Control Plane`, `Execution Plane`, `State Plane`, and `Operator Plane`
- document the end-to-end stage model from production order through archive
- define the need for first-class `Production Order`, shared job-state, lease, heartbeat, retry, and idempotency rules
- align status, UML, reliability, Kanban, issues, and lessons-learned docs to that decision

### Acceptance Criteria

- the project has one SSOT pipeline review for the factory target
- the project has one SSOT architecture blueprint for scalable worker evolution
- UML reflects the future plane map, job-state model, and worker topology direction
- roadmap, status, Kanban, issues, and lessons learned all describe the same next implementation direction

### Delivery Result

- delivered a full enterprise pipeline review document for MTClipFactory as a hybrid manual-plus-automated Video Production Factory
- delivered an enterprise architecture blueprint covering planes, worker classes, job model, lease model, scaling rules, and observability direction
- aligned implementation architecture, UML, reliability, status, progress, Kanban, issues, and lessons-learned docs to the re-baselined factory direction
- locked the next implementation stream to `Production Order` persistence plus shared job-state orchestration before distributed execution

## IR-19 | Production-Order And Shared Job-State Orchestration Baseline

### Goal

Turn the documented factory architecture into a real control-plane baseline by making production orders and stage-aware job orchestration first-class persisted concepts.

### Scope

- persist `Production Order` as a first-class state-plane object
- define one shared job-state vocabulary across factory automation stages
- introduce orchestration records that map orders to materialization, preview, review, and final stages
- classify retryable versus terminal failures explicitly
- keep the baseline compatible with the current local runtime before multi-node worker rollout

### Acceptance Criteria

- production orders can be persisted, queried, and tracked independently of recipe rows
- automated factory stages report through one shared orchestration state model
- retry, failure, and review-needed states are explicit and inspectable
- docs, UML, issues, Kanban, and tests stay aligned to the new orchestration seam

### Delivery Result

- delivered persisted `production_orders`, `production_order_items`, and `production_order_stages` through Alembic migration `20260613_0006`
- delivered `ProductionOrderService` as the first control-plane seam for creating, running, listing, and inspecting automated factory orders
- delivered stage-level orchestration truth for `materialize`, `preview`, and `review` flows, including explicit `failed_retryable`, `failed_terminal`, and `review_required` outcomes
- kept the baseline compatible with the current local runtime by layering orchestration state above existing execution-plane jobs instead of rewriting every job-status path
- covered persistence, success, review-required, retryable preview failure, and terminal planning failure paths with pytest

## IR-20 | Worker Lease, Heartbeat, And Retry-Policy Baseline

### Goal

Make the new control-plane baseline safe for future multi-worker execution by introducing explicit worker-ownership and retry semantics.

### Planned Scope

- define lease ownership fields and expiration policy
- define worker heartbeat persistence and visibility
- distinguish claimed work from merely queued work
- formalize requeue rules after lease expiration
- keep the baseline compatible with the current local runtime before remote workers arrive

### Planned Acceptance Criteria

- queueable work can be claimed through explicit ownership semantics
- stale work can be identified without guessing from timestamps alone
- retry policy becomes more precise than one generic failed state
- docs, UML, issues, Kanban, and tests stay aligned to the new worker-control seam

## IR-21 | Folder Discovery Depth And Assisted Tagging Ergonomics

### Goal

Make folder-driven automation easier to aim at real operator media trees while also reducing manual typing and visual scanning during tag assignment.

### Scope

- add explicit `scan_depth` semantics to auto-factory root-folder discovery
- allow root-level or deeper nested product-folder contracts to be discovered deterministically
- keep valid product-folder matches terminal so product asset subfolders are not reinterpreted as deeper product candidates
- add guided tag-group reuse plus product/status/search asset filtering in the `Tags` screen
- keep the slice additive to current services and existing desktop workflows

### Acceptance Criteria

- folder-driven runs can discover valid product folders at depth `0..n` from a selected root
- invalid negative depth values fail truthfully
- reruns stay deterministic and do not break current direct-child folder behavior
- operators can narrow tag-assignment candidates without manually scanning the full asset table
- docs, UML, manual, and pytest stay aligned to the delivered ergonomics slice

### Delivery Result

- delivered `scan_depth` support to `AutoFactoryFolderService.run_batch_root(...)` while preserving the existing direct-child baseline as the default behavior
- delivered deterministic root-level and nested product-folder discovery coverage in pytest, plus truthful failure for invalid negative depth input
- delivered `TagDictionaryViewModel` asset filtering by product, status, and free-text search
- delivered `TagDictionaryWindow` guided controls through an editable group combo box, filter combos, and search-assisted asset narrowing

## IR-22 | Auto Factory Desktop Control Surface Baseline

### Goal

Give operators a real desktop control surface for folder-root automation without bypassing the new production-order control plane.

### Scope

- add a dedicated `Auto Factory` desktop window reachable from the dashboard
- provide guided controls for root-folder browse, optional batch-code override, `scan_depth`, and explicit run mode
- run folder discovery and deterministic intake first through `AutoFactoryFolderService`
- route materialize and preview modes through `ProductionOrderService` so stage truth is persisted
- surface recent production orders, selected order stages, and intake outcomes in-screen
- cover the new view-model and window seams with pytest

### Acceptance Criteria

- operators can run folder intake from the desktop app without hidden scripts
- materialize and preview modes create persisted production-order records instead of bypassing control-plane truth
- the screen shows discovered folders, asset-intake actions, and order-stage outcomes clearly enough for operator review
- roadmap, status, progress, UML, manual, and test-plan docs remain aligned to the delivered slice

### Delivery Result

- delivered `AutoFactoryControlViewModel` and `AutoFactoryControlWindow` as the first operator-facing automation control surface
- delivered dashboard navigation into the new screen plus guided browse, depth, and run-mode controls
- delivered a composed intake-then-order execution flow that keeps `Intake Only` available while routing materialize and preview runs through persisted `ProductionOrderService` records
- covered the new operator-control seam with pytest for both the view model and offscreen window wiring

## IR-23 | Tag-Aware Auto Factory Selection Baseline

### Goal

Make asset tags operational inside auto-factory planning while improving the tagging screen so operators can prepare automation-relevant labels confidently.

### Scope

- extend `pipeline.toml` with optional `[selection_tags]` rules for `foreground`, `background`, `music`, and `voice`
- filter ready asset pools by explicit required `group:name` labels before planner capacity is estimated
- keep the first matching mode deterministic through all-of tag matching per asset type
- surface the automation direction more clearly in the `Tags` screen through `Asset Type` filtering and visible current asset tag labels
- cover planner filtering, folder parsing, and tagging UI seams with pytest

### Acceptance Criteria

- configured tag rules can change which assets are eligible for automated recipe generation
- planner shortfalls caused by tag rules remain truthful and do not silently fall back to untagged assets
- operators can see and filter current asset tags in the `Tags` screen while preparing assets for automation
- roadmap, status, progress, UML, manual, and test-plan docs remain aligned to the delivered slice

### Delivery Result

- delivered optional `pipeline.toml [selection_tags]` parsing into auto-factory product requests
- delivered deterministic tag-aware planner filtering across foreground/background/music/voice pools using normalized `group:name` labels
- delivered truthful limiting-reason reporting when tag rules remove all renderable visual candidates
- delivered `Tags` window hardening with `Asset Type` filtering, visible asset tag labels, and operator guidance that automation consumes normalized labels

## IR-24 | Asset-First Tagging Workflow Baseline

### Goal

Make tag assignment feel natural for operators by centering the workflow on the selected asset instead of forcing two-table coordination first.

### Scope

- persist selected-asset state inside `TagDictionaryViewModel`
- allow tag search and group narrowing for the available-tag list
- add `Create And Attach` for the selected asset
- show selected asset details plus current tag labels in a dedicated panel
- keep the slice compatible with the existing tag service seam

### Acceptance Criteria

- operators can select one asset and complete most tagging work without mentally bouncing between unrelated tables
- existing tag assignment still works through the same service seam
- UI and pytest stay aligned to the asset-first interaction model
- roadmap, UML, user manual, and status docs remain truthful

### Delivery Result

- delivered selected-asset state, available-tag filtering, and create-and-attach behavior in `TagDictionaryViewModel`
- delivered an asset-first `Tag Dictionary` layout with asset list, selected asset details, available tags, and focused attach actions
- covered the new workflow with pytest for both the view model and offscreen window contract

## IR-25 | Bulk Asset Tagging Workflow Baseline

### Goal

Reduce repetitive operator work by letting one tag assignment action target multiple selected assets while preserving an asset-first mental model.

### Scope

- persist selected-asset-set state inside `TagDictionaryViewModel`
- keep one primary selected asset available for detail review
- allow existing-tag attach across the selected asset set
- allow `Create And Attach` across the selected asset set
- keep the slice compatible with the current single-asset tag service seam

### Acceptance Criteria

- operators can multi-select assets and attach one existing or new tag across the whole selected set
- the selected-asset panel still explains what the current primary asset is
- selection survives reload and filter changes as much as possible without inventing hidden state
- UI, docs, and pytest stay aligned to the bulk asset tagging interaction model

### Delivery Result

- delivered selected-asset-set state and bulk tag assignment helpers in `TagDictionaryViewModel`
- delivered multi-select tagging controls in the `Tag Dictionary` desktop screen while preserving one primary selected-asset detail panel
- covered the new workflow with pytest for both the view model and offscreen window contract

## Cross-Milestone Rules

- every milestone must update related SSOT docs in the same loop
- every architecture or workflow change must update UML
- every persistence change must have an Alembic plan
- every implemented milestone must add or update pytest coverage
- every operator-visible automation rule must be explainable from dashboard or project docs

## Exit Condition For This Roadmap Slice

This roadmap slice is complete when:

- preview and final are both timeline-driven
- narration remains non-looping by rule
- music ducking is implemented and configurable in runtime render flows
- render decisions are visible and trustworthy
- risky cases are routed into review instead of silent low-quality automation

Status on 2026-06-06:

- achieved
