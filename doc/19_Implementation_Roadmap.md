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
- `IR-07` Audio-mix quality refinement beyond windowed-duck baseline: ready

## Current Execution Stream

The next work should follow this order unless a documented issue changes priority:

1. `IR-07` Audio-mix quality refinement beyond the current windowed-duck baseline
2. Recovery escalation rules and richer orchestration policy
3. Optional path-root hot-reload support if restart semantics prove too costly

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
