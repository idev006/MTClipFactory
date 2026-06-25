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
- `IR-20` Worker lease, heartbeat, and retry-policy baseline: pending after the 2026-06-20 live-progress groundwork slice
- `IR-21` Folder discovery depth and assisted tagging ergonomics: complete on 2026-06-13
- `IR-22` Auto Factory desktop control surface baseline: complete on 2026-06-13
- `IR-23` Tag-aware auto-factory selection baseline: complete on 2026-06-13
- `IR-24` Asset-first tagging workflow baseline: complete on 2026-06-13
- `IR-25` Bulk asset tagging workflow baseline: complete on 2026-06-14
- `IR-26` Folder tag metadata sync baseline: complete on 2026-06-14
- `IR-27` Caption runtime metadata and render baseline: complete on 2026-06-14
- `IR-28` Product-local run artifacts and fill-policy baseline: complete on 2026-06-14
- `IR-29` Pixel-based caption layout and diversity baseline: complete on 2026-06-14
- `IR-30` Caption safe bands and longest-layer duration baseline: complete on 2026-06-14
- `IR-31` Textbox-based caption layout baseline: complete on 2026-06-15
- `IR-32` Auto Factory product-contract inspection surface: complete on 2026-06-19
- `IR-33` Auto Factory review-surface operator actions: complete on 2026-06-20
- `IR-34` Auto Factory history-aware anti-duplicate selection baseline: complete on 2026-06-21
- `IR-35` Auto Factory near-duplicate similarity scoring baseline: complete on 2026-06-21
- `IR-36` Auto Factory operator near-duplicate risk surface: complete on 2026-06-21
- `IR-37` Auto Factory exact fingerprint hash duplicate guard baseline: complete on 2026-06-21
- `IR-38` Auto Factory Orders-tab duplicate-risk emphasis baseline: complete on 2026-06-21
- `IR-39` Auto Factory recent-orders duplicate-risk summary baseline: complete on 2026-06-21
- `IR-40` Auto Factory background-diversity hardening baseline: complete on 2026-06-21
- `IR-41` Auto Factory foreground-and-music diversity hardening baseline: complete on 2026-06-21
- `IR-42` Auto Factory frontier option-pool diversity hardening baseline: complete on 2026-06-21
- `IR-43` Auto Factory segment-aware foreground assignment rendering baseline: complete on 2026-06-21
- `IR-44` Auto Factory local-time truth baseline: complete on 2026-06-21
- `IR-45` Auto Factory persistent foreground/background clip policy baseline: complete on 2026-06-21
- `IR-46` Auto Factory segment-inventory manifest baseline: complete on 2026-06-21

## Current Execution Stream

The next mandatory implementation stream should implement and validate the pending `IR-20` local-worker baseline through persisted worker-lease semantics, safe checkpoints, recovery-facing event visibility, and clearer active-worker reporting.

The delivered 2026-06-20 control slice keeps `Pause Run`, `Stop Run`, and `Resume Run` visible in the UI as groundwork only; they must continue to report `pending backend support` until persisted worker-lease and safe-checkpoint behavior is actually implemented.

The same local-worker control stream now also hardens SQLite lease-heartbeat execution so transient `database is locked` contention skips one heartbeat attempt instead of killing the background heartbeat thread, while file-backed desktop SQLite now enables `WAL` plus a `busy_timeout` to reduce write contention.

The same local-worker control stream now also adds an operator-facing reopen-and-continue recovery surface so stale leases no longer masquerade as active workers and recent-order history can recommend `Monitor`, `Resume`, or `Resume (Recover Stale Lease)` truthfully.

The current caption-quality hardening stream should also keep presenter-led promo cards face-safe by clamping grouped top-band band height and by treating requested grouped headline size as a real upper bound instead of a suggestion.

The same caption-quality stream now also hardens Thai rendering by compositing a Qt-rendered caption bitmap in FFmpeg instead of asking FFmpeg `drawtext` to redraw already-measured caption glyphs.

The same anti-duplicate stream now also adds a hard exact-repeat guard through canonical recipe fingerprint hashes, while near-duplicate scoring remains the softer explainability layer on top.

The same operator-triage stream now also surfaces persisted duplicate-risk summary directly in the recent-orders history strip, so operators can choose which recent order to inspect before opening the detailed `Orders` tab.

The same anti-duplicate stream now also hardens `background_video` diversity by surfacing alternate backgrounds earlier in candidate generation instead of letting a large foreground search space hide them.

The same anti-duplicate stream now also moves from one linear dimension scan to a deterministic candidate frontier so fresh persistent-foreground and `music` alternatives can surface earlier when the search space grows large.

The same anti-duplicate stream now also reorders large seeded option pools by historical underuse before frontier enumeration so broader low-history backgrounds, music tracks, voices, and sequence families surface earlier.

The same anti-duplicate stream now also corrects one deeper render-truth gap by using semantic foreground assignments on the matching timeline segments instead of collapsing all foreground roles into one persistent recipe-wide pick.

The same operator-grade publishing stream now also locks Auto Factory materialization to one persistent foreground plus one persistent background per clip, with the foreground looping when needed instead of switching assets mid-clip.

The same audit stream now also adds clip-level `segment_inventory` manifest evidence so operators and future duplicate-hardening tooling can read per-segment asset/time composition truth from one stable section.

The same operator-truth stream now also converts persisted Auto Factory order timestamps into local desktop display time, moves new automatic run labels onto local timestamp tokens, and keeps run-journal artifact timestamps timezone-explicit in UTC.

Backlog activation rules:

1. Further recipe-score calibration only activates if the delivered metadata, asset-diversity, and runtime-evidence baseline stops being operationally useful.
2. Distributed worker execution does not activate before the planned local-worker lease, heartbeat, and retry semantics are implemented and then validated under broader operator use.

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

### Scope

- define lease ownership fields and expiration policy
- define worker heartbeat persistence and visibility
- distinguish claimed work from merely queued work
- formalize requeue rules after lease expiration
- surface live order, stage, and worker progress truth for the operator-facing auto-factory screen
- persist operator intents for `pause`, `stop`, and `resume`
- define reopen-and-continue recovery behavior for interrupted auto-factory runs
- keep worker concurrency bounded and configurable instead of ad hoc
- keep the baseline compatible with the current local runtime before remote workers arrive

### Acceptance Criteria

- queueable work can be claimed through explicit ownership semantics
- stale work can be identified without guessing from timestamps alone
- retry policy becomes more precise than one generic failed state
- operators can tell whether a run is running, pausing, paused, stopped, blocked, resumable, or complete
- interrupted auto-factory runs can be reopened and continued from persisted state without duplicating already-completed work
- docs, UML, issues, Kanban, and tests stay aligned to the new worker-control seam

### Delivery Result

- delivered Alembic migration `20260620_0007` plus persistence support for order-level run mode, source root, preview-enabled flag, lease ownership, heartbeat timestamps, lease expiry, blocking reason, and append-only `production_order_events`
- delivered `ProductionOrderService` local-worker lease claim, background heartbeat, persisted order-control groundwork, and restart-oriented `resume_order(...)` seams
- delivered effective-stage resume behavior that reuses already-succeeded materialize/preview units and retries only remaining eligible `failed_retryable` work
- delivered `Auto Factory` UI/view-model wiring for `Pause Run`, `Stop Run`, and `Resume Run` operator surfaces, lease visibility, active-worker truth, and order-event inspection while keeping the controls truthful as pending backend support
- delivered SQLite heartbeat lock-tolerance plus file-backed `WAL` and `busy_timeout` runtime hardening so transient write contention does not kill the heartbeat thread during active local Auto Factory runs
- covered migration, service, view-model, and UI seams with pytest, and reverified the full suite at `306 passed, 4 warnings`

The latest caption hardening pass, including the Thai-safe bitmap overlay path, and the SQLite heartbeat hardening pass have now also reverified the full suite at `306 passed, 4 warnings`.

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

## IR-26 | Folder Tag Metadata Sync Baseline

### Goal

Make folder-prepared `tags.toml` metadata operational during auto-factory intake so tag-aware planner selection can work end to end in the same run.

### Scope

- allow `global_tags` plus per-file `[file_tags]` inside each asset folder
- normalize and deduplicate `group:name` labels during intake
- create missing tags automatically and assign them to matching assets
- apply the same metadata to newly registered and already-existing assets on rerun
- ignore non-media metadata files during asset intake

### Acceptance Criteria

- `tags.toml` can influence asset tag labels without manual tag-screen work
- rerunning `Intake Only` does not duplicate asset-tag links
- current `pipeline.toml [selection_tags]` rules can consume tags assigned from folder metadata in the same run
- invalid tag metadata fails truthfully

### Delivery Result

- delivered `tags.toml` parsing for `global_tags` and `[file_tags]` in folder-driven intake
- delivered normalized additive tag assignment through `TagManagementService` for both newly registered and skipped-existing assets
- delivered media-file filtering that now ignores metadata files such as `desktop.ini` and `tags.toml`
- covered folder tag metadata application, rerun safety, invalid tag labels, and end-to-end selection-tag planning with pytest

## IR-27 | Caption Runtime Metadata And Render Baseline

### Goal

Turn product-level `captions.toml` preparation into real preview/final caption rendering with truthful manifest and review visibility.

### Scope

- sync `captions.toml` from the product folder into runtime metadata under the media library
- resolve deterministic `main` and `sub` captions per segment from product-level pools
- preserve manual `\n` line breaks and apply bounded wrap/scale/truncate fit behavior
- resolve fonts from the workspace `fonts` folder before falling back to system-family references
- draw caption overlays during preview/final rendering and expose caption evidence in manifests plus review-gate outcomes

### Acceptance Criteria

- folder-driven automation can make the current `captions.toml` available to preview/final runtime without manual copy steps after the first run
- preview and final can render main/sub caption overlays from product-level pools
- manifest evidence shows resolved caption text, font resolution, and caption-fit behavior
- unsafe caption fit can trigger review instead of silently pretending the text fit was clean

### Delivery Result

- delivered runtime metadata sync for product-level `captions.toml` under `media_library/products/<product_code>/automation/`
- delivered deterministic main/sub caption resolution with stable seed behavior per recipe segment
- delivered manual `\n` preservation plus bounded runtime fit handling and review-required overflow signaling
- delivered FFmpeg caption overlay rendering plus manifest-backed caption evidence and output-detail visibility
- covered caption contract parsing, runtime sync, renderer command generation, manifest visibility, and review-gate behavior with pytest

## IR-31 | Textbox-Based Caption Layout Baseline

### Goal

Make caption layout easier to control and evolve by resolving textbox geometry first and placing text inside that box second.

### Scope

- add textbox-first caption layout policy with stable box geometry
- separate textbox placement from text alignment
- fit measured text against textbox content width instead of shrinking a text-derived box only
- keep the contract backward compatible for older `max_width_ratio` caption metadata
- expose textbox geometry truth through runtime objects, manifests, docs, and pytest

### Acceptance Criteria

- one caption role can center the textbox while left-aligning the text inside it
- background box width remains stable for one role even when line widths differ
- measured fit remains pixel-based and review-truthful
- new-product caption templates and docs explain the new textbox fields

### Delivery Result

- delivered `textbox_width_ratio` and `textbox_alignment` support in the caption runtime contract
- delivered textbox-first caption geometry resolution in the layout engine with text fit measured against textbox content width
- delivered stroke-aware line measurement, manifest evidence, and renderer parity for textbox-backed caption rendering
- covered textbox geometry behavior and render compatibility with pytest and kept the full regression suite green

## IR-32 | Auto Factory Product-Contract Inspection Surface

### Goal

Make the desktop `Auto Factory` screen show the selected product's contract/runtime intent clearly enough that operators can validate pipeline and caption setup without opening raw files first.

### Scope

- expose product contract summary from preflight DTOs
- expose pipeline duration/tag-rule summary from preflight DTOs
- expose caption preset/font intent from `captions.toml` summary data
- show selected-product runtime request and asset intake actions after intake-mode runs
- keep the surface read-only and aligned with product-local `runs/<batch_code>` audit behavior

### Acceptance Criteria

- operators can select one audit product row and inspect product, pipeline, caption, and tag-readiness truth
- operators can select one intake product row and inspect the resolved runtime request plus asset actions
- the UI uses service DTO output rather than reparsing contracts inside the window
- pytest covers both the DTO summary seam and the upgraded window surface

### Delivery Result

- delivered caption-contract, product-contract, and pipeline-contract summaries through the folder preflight seam
- delivered a selected-product detail panel inside the desktop `Auto Factory` screen for both audit and intake tables
- delivered run-mode guidance that explains what each mode does and reminds operators where product-local run artifacts land
- covered the new summary seam and UI surface with targeted pytest

## IR-33 | Auto Factory Review-Surface Operator Actions

### Goal

Turn the selected-product review panel into a more practical operator surface by adding safe navigation and handoff shortcuts without turning it into an editor.

### Scope

- expose product-folder navigation from the selected product row
- expose contracts-folder navigation with legacy-layout fallback
- expose batch-aware runs-folder navigation when intake already knows the batch code
- expose one truthful copy-to-clipboard summary action
- keep all actions DTO-backed and read-only

### Acceptance Criteria

- operators can open product, contracts, or runs context from the selected-product panel
- intake rows prefer `runs/<batch_code>` when it exists
- audit rows can still navigate to product-local context without a persisted run
- pytest covers the new UI actions

### Delivery Result

- delivered product-folder, contracts-folder, and runs-folder shortcuts from the selected-product review panel
- delivered batch-aware runs resolution through intake DTO product-path truth
- delivered clipboard copy for the currently rendered product summary
- covered audit-mode and intake-mode operator actions with targeted pytest

## IR-39 | Auto Factory Recent-Orders Duplicate-Risk Summary Baseline

### Goal

Make the bottom `Recent Production Orders` strip useful for duplicate-risk triage before an operator opens a specific order.

### Scope

- derive one persisted order-level duplicate-risk summary from successful `materialize` stage detail
- expose `Risk Level` plus max raw `Duplicate Risk` through `ProductionOrderSummaryDTO`
- render those fields directly in the desktop recent-orders strip
- reuse the existing `High` / `Medium` / `Low` / `Unavailable` emphasis palette for fast operator scanning

### Acceptance Criteria

- recent-order summaries carry persisted duplicate-risk truth without reparsing raw stage rows in the UI
- the recent-orders strip shows both a human-readable risk level and the raw score
- higher-risk recent orders are visually emphasized for quicker triage
- pytest covers service derivation and offscreen window rendering

### Delivery Result

- delivered `ProductionOrderService.list_orders()` risk-summary derivation from persisted successful `materialize` stages
- delivered `ProductionOrderSummaryDTO` fields for order-level risk level and max raw score
- delivered `Auto Factory` recent-orders strip columns plus row emphasis for duplicate-risk triage
- covered the new summary seam with service and offscreen UI pytest, then reverified the full suite at `302 passed, 4 warnings`

## IR-40 | Auto Factory Background-Diversity Hardening Baseline

### Goal

Reduce repeated `background_video` reuse across one batch when fresh alternatives exist.

### Scope

- interleave `background` alternatives earlier in deterministic candidate generation
- strengthen planner-side background reuse avoidance without overtaking `voice` as the highest-priority diversity signal
- keep persisted duplicate-risk evidence truthful when background reuse still becomes necessary
- cover the regression scenario with pytest

### Acceptance Criteria

- alternate backgrounds appear early enough in the candidate pool for greedy selection to choose them
- a batch with multiple feasible backgrounds should not collapse onto the same background across all early clips
- `voice` remains more heavily weighted than `background`
- docs and pytest stay aligned to the delivered behavior

### Delivery Result

- delivered earlier `background` interleaving in Auto Factory candidate generation
- delivered stronger background reuse penalties while keeping `voice` as the strongest role-level anti-duplicate weight
- delivered pytest coverage for the regression case where a large foreground search space previously hid alternate backgrounds, then reverified the full suite at `302 passed, 4 warnings`

## IR-41 | Auto Factory Foreground-And-Music Diversity Hardening Baseline

### Goal

Reduce repeated foreground-pattern and music reuse when fresh alternatives exist.

### Scope

- replace simple linear variant scanning with a deterministic candidate frontier across key diversity axes
- surface alternate `music` choices earlier instead of hiding them behind deep Cartesian scan depth
- strengthen planner pressure against historically repeated foreground sequences and music reuse
- keep `voice` as the strongest single role-level anti-duplicate signal

### Acceptance Criteria

- candidate coverage must expose alternate music and foreground choices early enough for greedy selection to use them
- historically repeated foreground sequences should be deprioritized when feasible fresh sequences exist
- historically repeated music should be deprioritized when feasible fresh music exists
- docs and pytest stay aligned to the delivered behavior

### Delivery Result

- delivered deterministic frontier-style candidate enumeration across `voice`, `foreground_sequence`, `background`, and `music`
- delivered stronger foreground-sequence and music reuse penalties in the planner
- delivered pytest coverage for hidden-music and repeated-foreground regression cases
- reverified the full suite at `302 passed, 4 warnings`

## IR-42 | Auto Factory Frontier Option-Pool Diversity Hardening Baseline

### Goal

Broaden early planner coverage across large ready pools so low-history backgrounds, music, voices, and foreground sequences surface before heavily reused options.

### Scope

- reorder seeded option pools by historical underuse before frontier enumeration
- preserve seeded deterministic order as the tie-break path for equally weighted options
- keep duplicate-risk persistence truthful when the product really is diversity-limited
- add pytest coverage for option-pool ordering and large-pool fresh-background selection

### Acceptance Criteria

- historically underused role assets should surface ahead of heavily reused ones in frontier option ordering
- equal-history options should preserve deterministic seeded tie order
- a large ready background pool should prefer fresher backgrounds before falling back to reused ones
- docs and pytest stay aligned to the delivered behavior

### Delivery Result

- delivered history-aware frontier option-pool reordering for `voice`, `background`, `music`, and `foreground_sequence`
- delivered helper-level pytest coverage for underuse ordering plus deterministic equal-history tie behavior
- delivered service-level pytest coverage for large-pool fresh-background preference
- reverified the full suite at `302 passed, 4 warnings`

## IR-43 | Auto Factory Segment-Aware Foreground Assignment Rendering Baseline

### Goal

Make Auto Factory foreground-sequence planning affect actual rendered segment visuals instead of only recipe metadata.

### Scope

- use semantic foreground roles such as `hook`, `problem`, `benefit`, `proof`, and `cta` on their matching timeline segments
- keep recipe-wide persistent foreground fallback for older non-semantic manual roles
- keep background-layer persistence intact
- add pytest coverage for semantic per-segment rendering plus backward-safe fallback behavior

### Acceptance Criteria

- semantic foreground assignments must render on the matching segment types
- manifests and visual-composite evidence must reflect the actual per-segment primary foreground assets
- older manual recipes without semantic foreground roles must keep the previous persistent fallback behavior
- docs and pytest stay aligned to the delivered behavior

### Delivery Result

- delivered segment-aware semantic foreground resolution in preview/final composition
- preserved recipe-wide foreground fallback for non-semantic manual roles
- delivered regression coverage for semantic per-segment rendering while preserving the older persistent fallback path
- reverified the full suite at `302 passed, 4 warnings`

## IR-45 | Auto Factory Persistent Foreground Background Clip Policy Baseline

### Goal

Align Auto Factory with operator-grade short-form ad publishing by keeping one coherent foreground/background pair per generated clip.

### Scope

- require at least one ready `foreground_video` and one ready `background_video` for Auto Factory planning
- materialize exactly one `foreground` assignment and one `background` assignment per Auto Factory recipe
- keep the foreground fixed for the whole clip and loop that same foreground when timeline fill is needed
- preserve semantic per-segment foreground rendering only for explicit/manual recipe paths and backward-safe composition support

### Acceptance Criteria

- Auto Factory planned recipes expose one `foreground` assignment plus one `background` assignment per clip
- Auto Factory clips do not switch foreground mid-clip
- missing foreground or background assets produce truthful planning shortfall instead of partial visual fallback
- docs and pytest stay aligned to the delivered behavior

### Delivery Result

- delivered persistent-foreground sequence planning that now represents one clip-level foreground asset instead of semantic per-segment foreground swaps
- delivered default foreground loop policy for Auto Factory-safe timeline fill using the same foreground asset
- delivered folder-intake and production-order truth updates so missing background media no longer pretends to be a review-only case
- delivered targeted regression coverage for planner, folder-intake, automation-policy, and production-order behavior under the new policy
- reverified the full suite at `302 passed, 4 warnings`

## IR-46 | Auto Factory Segment-Inventory Manifest Baseline

### Goal

Expose one operator-readable clip-composition audit seam that summarizes segment assets, timings, and deterministic clip formula evidence.

### Scope

- add `composition.segment_inventory` to preview/final manifests
- keep one backward-safe top-level `segment_inventory` alias
- expose primary/background layer identity, fill modes, and source durations per segment
- compute deterministic segment and clip formula hashes from the resolved segment inventory

### Acceptance Criteria

- preview/final manifests expose segment inventory in a stable sectioned shape
- segment inventory shows enough detail for operators to answer which assets appear where and for how long
- output-detail helper surfaces can summarize the new inventory evidence
- docs and pytest stay aligned to the delivered behavior

### Delivery Result

- delivered manifest segment-inventory payload generation from resolved preview segment clips
- delivered per-segment primary/background layer evidence plus source-duration truth
- delivered deterministic clip formula hashing for future duplicate-hardening support
- delivered pytest coverage for manifest-writing and output-detail helper reading of the new inventory section
- reverified the full suite at `302 passed, 4 warnings`

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
