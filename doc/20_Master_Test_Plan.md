# Master Test Plan

This document is the execution-ready master test plan for MTClipFactory.

It complements [07_Testing_Strategy.md](/F:/programming/python/MTClipFactory/doc/07_Testing_Strategy.md), which defines the long-lived testing direction and baseline coverage.

## Purpose

- define one practical test plan for milestone-complete system validation
- align engineering, QA, PM, and operator acceptance around the same test scope
- reduce release risk across `Resource Library Management`, `Video Assembly Factory`, and `Dashboard / Settings`

## Test Objectives

- verify that all delivered milestone behavior works as documented
- verify that core workflows are usable end to end
- verify that persisted state, review logic, retry logic, and runtime path reload remain truthful to operators
- detect regressions before UAT and release recommendation

## In-Scope Test Areas

### Resource Library Management

- product creation, update, and deletion rules
- asset intake and metadata analysis
- asset readiness classification
- asset rename/delete maintenance rules
- referenced-asset retire/purge workflow and reference visibility
- recipe-safe asset replacement workflow with approval-safety guards
- tag creation, assignment, and filtering
- thumbnail and proxy generation jobs

### Video Assembly Factory

- recipe creation and item assignment
- auto-factory batch planning and internal recipe generation
- folder-driven batch intake using `product.toml` and `pipeline.toml`
- automatic preview production from materialized auto-factory batches
- persisted production-order and orchestration-stage tracking
- persisted production-order and append-only order-event tracking
- desktop `Auto Factory` control-surface workflow for root selection, scan depth, run mode, intake reporting, and recent-order inspection
- desktop `Auto Factory` live-progress workflow plus backend-functional local-worker `Pause/Stop/Resume` semantics
- local-worker SQLite heartbeat lock tolerance so transient `database is locked` contention does not kill active Auto Factory lease monitoring
- desktop `Auto Factory` reopen-and-continue recovery surface, including stale-lease visibility, suggested action truth, and active-worker count dropping to zero after lease expiry
- desktop `Auto Factory` `Audit Only` workflow for preflight summary and issue visibility
- history-aware auto-factory anti-duplicate selection across repeated product runs
- near-duplicate score and reason visibility on planned auto-factory recipes
- persisted near-duplicate planner evidence on materialize stages plus operator visibility in the `Auto Factory` `Orders` tab
- canonical exact `fingerprint_hash` duplicate guard across persisted same-product recipe history
- `Orders`-tab duplicate-risk emphasis, including derived risk levels plus operator filter/sort controls
- recent-orders duplicate-risk summary, including persisted risk level plus raw score visibility in the lower history strip
- creative-preset orchestration baseline, including product-local `creative_presets.toml`, planner-time preset resolution, persisted preset request truth, and manifest-visible preset identity
- order-level duplicate-truth summarization so recent-order raw score reflects the stronger of materialize planner evidence and preview/review render-history evidence
- Auto Factory local-time truth so recent-order and selected-order timestamp display aligns with the operator's local wall clock while persisted audit artifacts stay timezone-explicit
- background-diversity hardening so batches with multiple feasible backgrounds do not collapse onto one repeated background unnecessarily
- foreground/music diversity hardening so fresh sequence or music choices are surfaced before the planner settles on repeated patterns unnecessarily
- frontier option-pool diversity hardening so large seeded pools reorder by historical underuse before frontier enumeration
- persistent foreground/background clip policy so each Auto Factory clip uses exactly one foreground plus one background without mid-clip foreground swaps
- segment-inventory manifest evidence so each rendered clip exposes segment asset/time composition truth plus deterministic clip-formula hashing
- segment-aware foreground assignment rendering so semantic recipe roles map to the matching timeline segments during preview/final composition
- requested-run snapshot truth for product-local Auto Factory artifacts, including operator-requested run mode and requested materialize/build-preview booleans
- tag-aware auto-factory asset-pool filtering from normalized asset labels
- asset-first tagging workflow for selected-asset details, tag search, and create-and-attach behavior
- bulk asset tagging workflow for multi-select assignment and primary selected-asset review
- folder-driven tag metadata sync from `tags.toml`
- caption runtime sync and render behavior from product-level `captions.toml`
- caption safe-band defaults and role-specific vertical placement overrides from product-level `captions.toml`
- top-band face-safe caption clamp behavior for grouped presenter-led promo headlines
- Thai-safe caption bitmap overlay rendering where Qt is responsible for both measured geometry and final glyph rasterization
- Thai script-safe grouped line-advance behavior so compressed headline stacks do not collide upper/lower vowel marks across adjacent lines
- Thai pair-aware grouped line-spacing behavior so adjacent line pairs can resolve different runtime spacing floors based on upper-mark versus lower-mark collision risk
- Thai `n`-line global context smoothing so pair decisions stay coherent across longer grouped caption blocks instead of being optimized as isolated gaps only
- textbox-based caption geometry, including independent textbox placement and text alignment
- product-local run artifact layout, order snapshot, and run journal behavior
- product-folder preflight audit behavior for contracts, assets, tags, and `selection_tags` viability
- per-asset-type fill policy from product-level `pipeline.toml`
- longest-contributing-layer duration resolution plus shorter-layer fill continuation behavior
- preview job flow
- final render flow
- target-ratio visual normalization across mixed source sizes
- output lineage reporting
- review gate and approval workflow
- decision history and audit fields
- recipe scoring and duplicate-risk visibility

### Dashboard And Settings

- dashboard summary accuracy
- recent-job, failed-job, and escalated-job visibility
- recovery actions and operator playbook guidance
- settings persistence through `.toml`
- exact preview/final output resolution settings through the operator UI
- runtime path-root hot reload behavior

### Shared Reliability Surfaces

- migration guard behavior
- persisted jobs and retry flows
- stale-lease recovery and resume behavior for interrupted local-worker production orders
- file-backed SQLite runtime behavior, including `WAL`, `busy_timeout`, and lease-heartbeat tolerance during transient write contention
- runtime/configured path truthfulness
- filesystem-path safety across media, preview, and outputs roots

## Out-Of-Scope

- distributed-worker scale testing
- multi-user concurrency testing at enterprise scale
- media-quality benchmarking for production mastering
- external infrastructure HA/DR testing beyond the local desktop architecture

## Test Levels

### 1. Smoke Testing

- application startup sanity
- import and instantiate all six primary windows
- confirm no immediate crash in default workspace

### 2. Automated Regression Testing

- run `python -m pytest` inside `F:\programming\python\MTClipFactory\.venv`
- verify the current baseline stays green
- investigate any failure before manual UAT starts

### 3. Integration Workflow Testing

- validate cross-service flows using temporary filesystem roots and persisted state
- confirm repository, unit-of-work, and job flows behave consistently

### 4. Manual Functional Testing

- validate operator-facing workflows through the UI
- confirm data shown in screens matches persisted state and manifests

### 5. Exploratory / Risk-Based Testing

- focus on path hot reload, review gates, recovery, audio-policy visibility, and preview/final parity

## Environment

- workspace root: `F:\programming\python\MTClipFactory`
- Python runtime: `F:\programming\python\MTClipFactory\.venv`
- Python version: `3.12`
- database: SQLite
- configuration source of truth: `app_config.toml`
- UI smoke mode: `QT_QPA_PLATFORM=offscreen`

## Entry Criteria

- latest code is available in the working tree to be tested
- repo is in a known state and dependencies install successfully in `.venv`
- required docs remain aligned with the delivered baseline
- FFmpeg / FFprobe paths are configured for the chosen test environment when render workflows are included

## Exit Criteria

- full regression suite passes
- UI smoke passes
- no `Critical` or `High` severity defect remains open
- all core UAT workflows pass or have approved workaround notes
- QA summary and release recommendation are recorded

## Test Data Strategy

### Core Data Set

- one or more products
- ready visual asset set
- voiceover asset
- background music asset
- representative tags and category labels

### Edge Data Set

- missing or invalid source file path
- recipe with no items
- voice-only recipe
- repeated single-asset recipe
- failed jobs with different failure-streak counts
- alternate database/media/output roots for hot-reload validation

## Functional Test Matrix

### A. Product And Asset Flow

1. Create product with valid data.
2. Reject duplicate product code.
3. Register asset to the correct product.
4. Confirm metadata and readiness fields are populated.
5. Create and assign tags.
6. Generate thumbnail and proxy jobs.
7. Retry failed artifact jobs and confirm dashboard reflects the outcome.
8. Rename an existing asset code and confirm the primary/artifact file paths remain aligned.
9. Attempt to delete an asset that is already referenced by a recipe item or artifact job and confirm the UI blocks it truthfully.
10. Retire a referenced asset and confirm it no longer participates in active recipe attachment.
11. Purge a retired asset's media files and confirm the record remains visible for historical truth.
12. Inspect an asset's reference report and confirm recipe/job usage is visible before destructive maintenance decisions.
13. Replace a referenced asset in affected recipes and confirm the item references move to the selected ready replacement asset.
14. Confirm affected recipes require a newly approved output after asset replacement before recipe approval can happen again.
15. Confirm Recipe Builder marks older pre-replacement outputs as historical-only and shows the next rebuild/approval action in-screen.

### B. Recipe And Preview Flow

1. Create recipe with valid metadata.
2. Attach valid ready assets to the recipe.
3. Confirm recipe score and duplicate risk update.
4. Build preview.
5. Confirm output record, manifest, and dashboard counts update.
6. Validate preview output dimensions follow the selected recipe `Target Ratio` even when attached visual assets use different source ratios.
7. Validate preview manifest contains composition and review evidence.
8. Validate a recipe with both `background_video` and `foreground_video` writes layered segment evidence instead of flattening to one visual choice only.
9. Validate a likely green-screen foreground is keyed over the background layer and that manifest evidence records the applied composite mode.
10. Validate default `main` and `sub` caption roles render in separated safe vertical bands when no explicit override is authored.
11. Validate a longer contributing visual or music layer can raise the resolved clip duration above the previous narrower fallback source.
10. Validate a non-green keyed foreground can be driven by Settings `Key Color Policy` and that the manifest records the chosen composite mode truthfully.
11. Submit a batch production order and confirm the planner reports requested count versus planner-feasible unique count truthfully.
12. Confirm batch materialization blocks strict orders when current planner policy cannot fulfill the requested unique count exactly.
13. Confirm a satisfiable batch creates internal recipes automatically with the expected asset-role assignments.
14. Confirm a valid batch root with `product.toml` and `pipeline.toml` creates the product, ingests assets, and materializes internal recipes.
15. Confirm rerunning the same batch root skips already-ingested deterministic asset codes instead of duplicating them.
16. Confirm invalid folder contracts fail truthfully before silent partial production.
17. Confirm a materialized batch can enqueue and run preview jobs automatically and return per-recipe output status/path truth without auto-approving recipes.
18. Confirm a folder-driven batch can optionally continue into preview production and reject `build_previews=True` when `materialize=False`.
19. Confirm production orders can be persisted, listed, and inspected independently from recipe rows.
20. Confirm orchestration stages record `materialize`, `preview`, and `review` results with explicit success, retryable-failure, terminal-failure, and review-required truth.
21. Confirm the desktop `Auto Factory` screen can browse/select a root folder, set `scan_depth`, and complete `Intake Only` mode with truthful discovered-folder, product, and asset-action reporting.
22. Confirm `Intake + Materialize` creates a persisted `Production Order` and shows stage truth in the screen's recent-order surfaces.
23. Confirm `Intake + Materialize + Build Previews` records preview and review stages while still stopping at the human approval boundary.
24. Confirm Auto Factory recent-order and selected-order timestamps display in local operator time rather than raw persisted UTC wall-clock values.
25. Confirm product-local run journals keep timezone-explicit UTC `Z` timestamps even after the local display correction lands in the UI.
- Confirm `Pause Run` persists `pause_requested` truth immediately and reaches `paused` after the next safe checkpoint.
- Confirm `Stop Run` reaches `stopped` immediately for paused orders and stale active leases, while still stopping active live-worker runs at the next safe checkpoint.
- Confirm `Resume Run` continues remaining eligible work without duplicating already-succeeded units and truthfully reflects stale-lease recovery.
24. Confirm leaving `Batch Code` blank auto-generates a unique root-folder-based value and creates product-local `runs/<batch_code>` artifacts under that generated name.
25. Confirm `pipeline.toml [selection_tags]` can restrict foreground/background/music/voice pools by normalized `group:name` labels.
26. Confirm planner shortfalls caused by tag filters remain truthful and do not silently fall back to untagged visual assets.
27. Confirm the planner avoids a historically repeated exact asset-role combination when a different feasible variant exists for the same product.
28. Confirm the planner deprioritizes a historically overused voiceover when another feasible voice exists for the same product.
29. Confirm each planned recipe exposes a deterministic `near_duplicate_score` and machine-readable `near_duplicate_reasons`.
30. Confirm successful `materialize` recipe stages persist `near_duplicate_score` and `near_duplicate_reasons` in order-stage detail truth.
31. Confirm the desktop `Auto Factory` `Orders` tab shows persisted duplicate-risk values and reasons without guessing when older orders do not have that evidence.
32. Confirm `order_snapshot.toml` records the operator-requested `run_mode`, `materialize_requested`, and `build_previews_requested` truth even when the desktop Auto Factory path performs intake before background production-order execution.
33. Confirm the planner hard-blocks an exact canonical `fingerprint_hash` repeat when the same product already has that exact persisted recipe formula in history.
34. Confirm the hard guard still allows a non-identical candidate when target ratio, target duration, or role assignment differences change the canonical hash.
35. Confirm production-order resume excludes the same order's already-materialized recipes from duplicate-guard history rebuilding so retryable preview failures can continue.
36. Confirm the desktop `Auto Factory` `Orders` tab derives `High`, `Medium`, `Low`, and `Unavailable` emphasis labels from persisted planner evidence without inventing missing scores.
37. Confirm the desktop `Auto Factory` `Orders` tab can filter product/stage rows by risk emphasis and sort stage rows by duplicate risk.
38. Confirm the desktop `Auto Factory` `Recent Production Orders` strip shows persisted `Risk Level` plus raw `Duplicate Risk` and highlights higher-risk rows without guessing when evidence is missing.
39. Confirm product-local `creative_presets.toml` can be parsed, audited, and synced into runtime metadata without code edits.
40. Confirm Auto Factory planner can resolve one eligible creative preset deterministically from the product-local runtime contract and persist preset code/reasons on the planned recipe and materialize stage.
41. Confirm Auto Factory UI can pass preset mode plus optional preset-code overrides into a folder-driven run and that `order_snapshot.toml` preserves that requested preset truth.
42. Confirm preview/final manifests expose chosen creative preset identity when materialize-stage preset truth exists for the recipe.
43. Confirm the recent-orders duplicate-risk strip uses combined order-level truth from planner-time materialize evidence plus preview/review render-history evidence instead of planner-only score.
44. Confirm Auto Factory uses more than one feasible `background_video` across early batch outputs when alternatives exist, even if the product has a large foreground search space.
45. Confirm Auto Factory can surface a fresh `background_music` alternative early enough to choose it when the default early scan would otherwise be dominated by other dimensions.
46. Confirm the planner uses every feasible foreground at least once before repeating another foreground that is already used in the same batch when a fresh foreground still exists.
47. Confirm Auto Factory deprioritizes a historically repeated foreground sequence when a feasible fresh sequence exists.
48. Confirm large ready asset pools reorder `background`, `music`, or `voice` options by historical underuse before frontier enumeration.
49. Confirm equal-history role assets preserve deterministic seeded tie order after the new frontier option-pool reordering.
50. Confirm a large ready background pool prefers fresher backgrounds before falling back to historically reused ones.
51. Confirm Auto Factory planned recipes contain exactly one `foreground` assignment and one `background` assignment per clip.
52. Confirm Auto Factory never switches foreground assets mid-clip and instead loops the same foreground asset when timeline fill is needed.
53. Confirm missing ready `foreground` or `background` assets produce truthful Auto Factory shortfall or terminal-order status instead of silent partial visual fallback.
54. Confirm semantic foreground roles such as `hook`, `problem`, `benefit`, `proof`, and `cta` still render on the matching timeline segments for explicit/manual recipe paths.
55. Confirm older non-semantic foreground roles still keep the persistent recipe-wide foreground fallback behavior.
56. Confirm preview/final manifests expose `composition.segment_inventory` with per-segment asset, timing, fill-mode, and source-duration evidence.
57. Confirm the same manifest also keeps a backward-safe top-level `segment_inventory` alias.
51. Confirm each manifest inventory exposes deterministic segment and clip formula hashes.
52. Confirm the `Tags` screen shows current asset tag labels and supports `Asset Type` filtering during assignment work.
53. Confirm the `Tags` screen keeps a selected asset in focus and allows `Create And Attach` plus existing-tag attach from the same workflow.
54. Confirm the `Tags` screen can multi-select assets and attach one existing tag across the selected asset set.
55. Confirm `Create And Attach` can create one tag and apply it across the selected asset set while preserving one primary selected-asset detail panel.
56. Confirm folder-driven intake can read `tags.toml` global and per-file tag metadata, create missing tags, and assign them to matching assets.
57. Confirm rerunning folder-driven intake does not duplicate tag assignment links for existing assets.
58. Confirm invalid `tags.toml` labels fail truthfully.
59. Confirm folder-driven automation syncs `captions.toml` into runtime metadata under the media library.
60. Confirm preview/final manifests record resolved caption text, font resolution, and caption-fit evidence when caption metadata exists.
61. Confirm unsafe caption fit raises a review signal instead of silently treating the render as clean.
62. Confirm folder-driven automation syncs `pipeline.toml` and source product context into runtime metadata.
63. Confirm auto-mode preview artifacts can be written into `Product/runs/<batch_code>/previews/videos`.
64. Confirm auto-mode final artifacts can be written into `Product/runs/<batch_code>/finals/videos`.
65. Confirm `order_snapshot.toml` and `journal.toml` are created for product-local auto runs.
66. Confirm per-asset-type fill policy is reflected in manifest evidence for voice, music, background video, and foreground video.
67. Confirm non-loop foreground shortfall can use `freeze_last_frame` or raise review-visible shortfall instead of silently looping.
68. Confirm a real prepared product folder can move from review-required preview output to clean rerun by correcting overly narrow `selection_tags` and non-publishable or overlong caption copy in the product-local contract files.
69. Confirm caption layout uses pixel-based fit evidence, supports `left`/`center`/`right` line alignment, and writes per-line layout truth into the manifest.
70. Confirm seeded auto-mode visual selection yields varied but deterministic foreground/background choices across multiple recipes in one batch.
71. Confirm textbox-based caption layout can center the textbox while left-aligning the text inside it, and that manifest evidence keeps box width distinct from text-content width.
72. Confirm textbox-only caption rendering can be verified from one segmented frame path without requiring a full product-folder audit, including one `drawbox` plus one `drawtext` per rendered line.
73. Confirm textbox-based caption layout supports `top`/`middle`/`bottom` text placement inside a taller textbox and still keeps best-fit line widths within textbox content bounds.
74. Confirm the best-fit caption solver can reduce font size to satisfy textbox height constraints, not only width constraints, while preserving honest overflow signals when no clean candidate exists.
75. Confirm caption contracts can render one textbox per line for advertising-style captions and that FFmpeg emits one `drawbox` per rendered line.
76. Confirm product-folder preflight reports `ready`, `warning`, and `error` truthfully, including missing recommended contracts and `selection_tags` that do not match any current ingestible asset files.
77. Confirm the desktop `Auto Factory` screen can run `Audit Only` and show dedicated preflight product summaries plus actionable issue rows without creating a production order.
78. Confirm grouped top-band promo headlines respect `max_safe_band_height_ratio` and shrink before covering the presenter eye line.
79. Confirm grouped multi-line captions do not grow above the requested contract font size, while short single-line best-fit captions may still upscale intentionally.

### C. Review And Approval Flow

1. Force a `needs_review` case.
2. Confirm manifest review signals and metrics are visible.
3. Approve preview output.
4. Confirm flagged recipe requires explicit approval reason.
5. Reject and then approve recipe in separate test cases.
6. Verify immutable decision history is complete and ordered correctly.

### D. Final Render Flow

1. Approve recipe prerequisites.
2. Build final render.
3. Confirm final output lineage is truthful.
4. Confirm final render follows composition behavior rather than blindly promoting preview bytes.

### E. Recovery And Escalation Flow

1. Queue artifact and factory jobs.
2. Recover queued jobs through the dashboard.
3. Simulate failed jobs.
4. Retry failed jobs.
5. Verify escalated jobs are deferred according to policy.
6. Verify operator playbook lines match the failure context.

### F. Settings And Path Reload Flow

1. Save updated path roots.
2. Verify `.toml` persistence.
3. Confirm runtime hot reload applies new roots in the desktop app.
4. Confirm dashboard path surfaces show active and configured roots truthfully.
5. Confirm view models continue working after runtime reload.
6. Set exact preview/final output resolutions and confirm generated outputs use the configured frame.

### G. Reporting And Operator Visibility

1. Verify dashboard counts after each major workflow.
2. Verify Recipe Builder output details.
3. Verify Recipe Builder recipe-list score/risk visibility.
4. Verify settings feedback messaging matches actual reload policy.

## Negative Test Coverage

- invalid product or recipe identifiers
- duplicate recipe code
- asset assigned across the wrong product boundary
- non-ready asset assignment
- preview build with no items
- preview/final build with no renderable visual assets
- recipe approval without approved output
- flagged recipe approval without reason
- bad runtime paths or missing dependency executables

## Non-Functional Focus

### Reliability

- repeated retry behavior remains deterministic
- persisted state survives service recreation
- runtime reload does not silently leave old path roots active
- asset maintenance does not orphan media files or silently delete referenced assets
- retired/purged asset behavior remains truthful about what was removed from disk versus what remains in history
- replaced-asset workflows do not allow stale pre-replacement outputs to be re-approved as evidence for the changed recipe

### Usability

- operator-facing feedback is understandable
- dashboard attention text highlights real operational risk
- key review and scoring data are visible without database inspection
- recipe ratio handling stays understandable when source clips do not match each other

### Performance Observation

- UI remains responsive during normal workflow usage
- preview/final test runs complete within reasonable local expectations

## Defect Severity Model

### Critical

- application cannot start
- persistent data corruption
- wrong database/media/output root used after save/reload
- core preview/final workflow unusable

### High

- approval or review logic produces incorrect business state
- retry/recovery policy behaves incorrectly
- output lineage or audit history is materially wrong

### Medium

- UI shows incorrect score/risk or dashboard counts while backend state is correct
- hot reload feedback is misleading but recoverable
- manifest evidence is incomplete for operator triage

### Low

- cosmetic issues
- wording or layout issues that do not affect business outcome

## Execution Order

1. Smoke tests
2. Full automated regression
3. Resource Library functional pass
4. Factory preview/review pass
5. Final render and lineage pass
6. Recovery and escalation pass
7. Settings and hot-reload pass
8. Exploratory testing on high-risk seams
9. Defect re-test and regression confirmation

## Evidence To Capture

- pytest result summary
- UI smoke result
- screenshots for key UI flows when needed
- sample preview/final manifest files
- defect log with severity and reproduction steps
- release recommendation summary

## Roles And Responsibilities

- Engineering: fix defects, maintain automated coverage, and preserve SSOT alignment
- QA / Tester: execute this plan, record evidence, classify defects, and recommend release readiness
- PM / Operator Reviewer: validate workflow acceptance and business usability

## Suggested UAT Gate

System is recommended for UAT when:

- automated regression is green
- dashboard and settings reflect truthful runtime state
- one full product-to-final-render walkthrough passes
- one failed-job recovery walkthrough passes
- one path-root hot-reload walkthrough passes

## Maintenance Rule

- update this document when major workflow scope, delivery baseline, or acceptance expectations change
- keep this plan aligned with [07_Testing_Strategy.md](/F:/programming/python/MTClipFactory/doc/07_Testing_Strategy.md), [11_Project_Status_Report.md](/F:/programming/python/MTClipFactory/doc/11_Project_Status_Report.md), and [19_Implementation_Roadmap.md](/F:/programming/python/MTClipFactory/doc/19_Implementation_Roadmap.md)
