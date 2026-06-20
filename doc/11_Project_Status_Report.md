# Project Status Report

## Project Manager Snapshot

- Report date: 2026-06-21
- Overall status: In Progress
- Current phase: Phase 6, operator-grade local-worker auto-factory control baseline delivered; distributed execution and deeper recovery-facing UX still pending
- Delivery mode: document-led SSOT with code and tests kept in sync

## What Is Done

- architecture baseline for `Python 3.12 + SQLite + SQLAlchemy + Alembic + PySide6 + pytest + MVVM`
- product CRUD
- asset intake with local storage
- FFprobe-backed metadata analysis
- asset readiness classification
- tag dictionary and asset tagging
- asset list filters and tag visibility
- dashboard and settings control center
- FFmpeg-backed thumbnail/proxy generation jobs
- persisted job tracking with queued/failed visibility
- dashboard recent-job visibility across library and factory workflows
- queued-job recovery orchestrator with dashboard trigger and startup policy
- failed-job retry orchestration through dashboard control
- output lineage reporting in the Recipe Builder UI
- migration-backed approval actor/time/reason persistence
- append-only immutable decision-event history with Recipe Builder visibility
- persisted composition-plan and render-decision foundation for recipe-level duration and layer planning
- persisted timeline-segment foundation with contiguous semantic coverage validation
- segment-aware preview composition with manifest-visible visual clip planning
- segment-aware final-render composition parity with composition-based rerendering
- settings-backed audio policy controls for narration looping, music looping, and duck timing
- dashboard and Recipe Builder visibility for composition-plan segments and render-decision summaries
- runtime voice/music mix path for preview and final render flows
- manifest-visible runtime audio-mix evidence for operator inspection
- review-gate reliability controls for low-diversity, loop-heavy, mismatch-heavy, audio-masking-risk, or emergency-fill preview/final compositions
- settings-backed review thresholds in `app_config.toml`, settings UI, and dashboard summary
- dashboard visibility for `needs_review` recipe count
- Recipe Builder output-detail visibility for manifest-backed review-gate evidence plus quality/duplicate-risk signals
- Recipe Builder recipe-summary visibility for persisted `recipe_score` and recipe-level `duplicate_risk`
- approval guard that requires an explicit human reason before approving a flagged recipe
- configurable duck engine with `sidechain_compressor` default plus `windowed_volume_duck` fallback
- settings-backed duck mode, threshold, and ratio controls surfaced through `.toml`, dashboard, and settings UI
- manifest-visible runtime evidence for the applied duck mode and compressor tuning
- settings-backed voice/music gain-stage controls surfaced through `.toml`, dashboard, and settings UI
- manifest-visible runtime evidence for applied voice/music balance during audio mixing
- persisted failed-job recovery-attempt metadata with configurable escalation threshold
- dashboard-visible operator playbook guidance plus deferred bulk-retry handling for escalated failed jobs
- payload-backed recovery metadata retained as the current audit seam by explicit architecture decision
- desktop-app runtime hot reload for path-root dependent services with runtime-vs-configured dashboard truthfulness
- redesigned grouped settings surface with two-column panel layout and hybrid slider-plus-exact-entry numeric controls
- settings numeric controls now use uniform slider/editor widths for more consistent operator scanning
- package-backed QSS theme loading seam now exists for Qt windows, with a shared app-window theme baseline across dashboard, library, and factory windows plus a settings-specific override
- shared app-window buttons now use balanced gradient, border-depth, focus, and pressed-state affordance so primary actions read clearly as clickable controls without feeling oversized
- Recipe Builder now explains its recipe-to-final purpose more directly, clarifies that the attach list shows only `ready` assets, keeps the asset panel tall enough for practical scanning, and offers composition-aware attach-role suggestions that combine asset type, current recipe segment order, auto-selection, and on-screen guidance instead of relying on free-typed role names alone
- Recipe Builder now uses a resizable three-column workspace so setup/actions, asset attachment, and output review can each claim more space without forcing the operator to fight one fixed grid
- Recipe Builder tables now declare vertical-scroll behavior explicitly so overflow rows stay usable without adding pagination
- Auto Factory batch planning now exists as a first automation slice, including production-order DTOs, batch-only uniqueness planning, voice-with-bounds duration resolution, planner-capacity truth, and internal recipe generation through the existing factory service seam
- Auto Factory can now also read folder contracts through `product.toml` and `pipeline.toml`, create missing products, ingest deterministic asset codes from typed media folders, and materialize internal recipes from one batch root
- Auto Factory can now also enqueue and run preview jobs automatically for a materialized batch, returning per-recipe result truth for job status, output path, output identity, and resulting review-gate state without auto-approving recipes or finals
- enterprise pipeline review and enterprise architecture blueprint now exist as SSOT so the system can evolve from local automation slices into a true Video Production Factory operating model
- production orders are now persisted independently from recipes, and control-plane orchestration stages now track `materialize`, `preview`, and `review` state across automated factory runs
- a first desktop `Auto Factory` control surface now exists so operators can choose a root folder, set `scan_depth`, pick an explicit run mode, and review recent production-order truth without leaving the app
- the `Auto Factory` screen now composes folder-intake truth with persisted `Production Order` execution, so materialize/preview runs stop bypassing the control-plane seam
- auto-factory planning can now also consume explicit asset tag requirements from `pipeline.toml`, so tagged assets can influence which ready media enters automated recipe generation
- the `Tags` screen now shows current asset tag labels and supports `Asset Type` filtering so operators can prepare automation-relevant tags more safely
- the `Tags` screen now also follows an asset-first workflow so operators can select one asset, inspect its current tags, search existing tags, and create-and-attach new tags from one focused loop
- the `Tags` screen now also supports bulk asset tagging so one existing or newly created tag can be applied across a selected asset set while one primary selected asset remains visible for review
- folder-driven `Auto Factory` intake now also reads `tags.toml` metadata, creates missing tags, and assigns normalized `group:name` labels to matching assets during the same run
- folder-driven `Auto Factory` intake now also syncs product-level `captions.toml` into runtime metadata so preview/final reruns can resolve the latest caption contract without depending on the original source folder path
- preview and final render now support runtime caption overlays from product-level caption pools, including deterministic main/sub selection, manual `\n` line breaks, workspace-font resolution, manifest-backed caption evidence, and review-gate signaling for unsafe caption fit
- product-local auto-mode run artifacts now write preview/final outputs, manifests, order snapshots, and append-only journal events under `runs/<batch_code>` inside the source product folder when auto-mode knows that source folder
- auto-mode now also reads product-level per-asset-type fill policy from `pipeline.toml`, including loop, silence-tail, freeze-last-frame, and review-visible shortfall behavior by asset type
- auto-mode composition planning now treats loop-enabled background music as a filler layer instead of a master-duration authority, so long music tracks no longer stretch short-form ad previews unintentionally
- auto-mode voiceover can now also loop intentionally when the product-level `pipeline.toml` policy explicitly sets `loop_enabled = true` and `shortfall_mode = "loop_to_timeline"`
- product-level caption contracts can now use stronger promo-card style presets and wider box-aware sizing so `main` and `sub` overlays read more like ad creative than subtitle leftovers
- auto-factory batch planning now also prioritizes early `voiceover` variation ahead of some later visual dimensions, so the first clips in one batch do not all repeat the same spoken message when multiple ready voice assets exist
- a real `Biothentic0001` live auto-mode audit has now validated product-local preview/final artifact paths, journal creation, manifest evidence, caption runtime behavior, and operator-facing contract tuning on an external product folder
- pixel-based caption layout now measures text against the real frame in pixels, supports point-to-pixel conversion, computes per-line alignment positions, and writes per-line caption layout evidence into manifests
- auto-mode visual selection now also uses seeded diversity ordering and seeded per-segment cycling so reruns stay deterministic while multi-recipe output feels less repetitive
- a live `Biothentic0001` spot-check has now validated the new pixel-layout caption manifest evidence on a real `1080x1920` preview output
- caption runtime now also supports role-specific safe vertical bands so default `main` and `sub` overlays avoid generic center-of-frame placement and behave more like title-plus-lower-third graphics
- composition planning now resolves clip duration from the longest contributing layer extent, so longer voice sequences, music sequences, or visual source extents do not get clipped by an earlier narrow fallback
- preview composition now keeps one deterministic selected visual asset per recipe-layer and lets fill policy extend that chosen asset across all segments instead of reselection per segment
- manual multi-line captions can now shrink font size per line against real pixel width while preserving operator-authored `\n` grouping and overflow review truth
- grouped manual-break captions now also normalize vertical line advance so mixed best-fit font sizes do not create visibly uneven promo-card spacing
- caption line-height measurement now also prefers ink-aware text bounds so Thai multi-line promo cards do not inherit oversized font-box spacing
- grouped promo headlines can now also apply product-local `line_advance_ratio` compression so operator-authored `\n` headline stacks look tighter and more ad-like without sacrificing deterministic pixel layout evidence
- caption runtime now also resolves textbox-first geometry so background box width can stay stable while text alignment remains independently controllable inside the box
- caption runtime now also exposes `textbox_height_mode` so grouped cards can default to compact `content_hug` behavior while `fixed` remains available for deliberate tall-card layouts
- caption runtime now also supports built-in role-aware `style_preset` values so operators can start from `sale_blast`, `clean_cta`, or `benefit_stack` and still override individual fields per product
- caption style presets now also expose preset-group metadata for `headline_main`, `support_sub`, and `proof_info`, and the built-in catalog now includes a `dark_lower_third` option for more readable sub captions over busy footage
- caption runtime now also supports box-border styling on grouped or per-line cards, with manifest-visible resolved border truth and preset-carried border defaults
- caption runtime now treats multi-line rendering as explicit author intent only, so captions without `\n` stay single-line and use box-aware best-fit font sizing instead of automatic runtime wrapping
- caption runtime now also interprets `seed_scope = "batch"` as deterministic caption cycling across output ordinals inside the same batch, reducing early-batch caption repetition without losing rerun safety
- built-in promo presets are now tuned toward lighter presenter-safe headline banners and stronger lower-third readability defaults before product-specific contract overrides are applied
- the next auto-factory operations requirements slice is now documented in SSOT, locking operator-visible progress, multi-worker gating, pause/stop/resume semantics, and restart recovery expectations before deeper distributed execution begins
- caption runtime can now also compact grouped manual-break promo headlines toward a preferred line count, helping top-band cards stay more face-safe without giving up deterministic multi-line authoring
- grouped manual-break promo cards now also keep one shared resolved font size across all rendered lines, while `per_line` cards retain independent line fitting for operator-authored stacked labels
- preview and final render now also write a versioned manifest envelope with stable `manifest_meta`, `artifact`, `run`, `composition`, `render`, and `quality` sections while preserving backward-safe reader behavior for older manifests
- folder-driven auto-factory now also supports a preferred product-folder `v2` layout with `contracts/` plus `assets/` paths, while staying backward compatible with legacy root-level contracts and typed media folders
- the new-product template kit now ships in the preferred `v2` layout, including `contracts/prod_detail.txt`, while runtime rejects ambiguous mixed old/new paths truthfully instead of guessing
- folder-driven auto-factory now also exposes a read-only product-folder preflight audit seam that validates contracts, assets, tags, and `selection_tags` viability before a real automation run
- the desktop `Auto Factory` control surface now also exposes `Audit Only`, so operators can run the same preflight validation from the UI before intake or preview work begins
- the desktop `Auto Factory` control surface now also exposes one selected-product contract/runtime detail surface so operators can inspect product contract fields, pipeline duration and tag rules, caption preset/font intent, and per-folder tag readiness without leaving the app
- the desktop `Auto Factory` control surface now also exposes operator shortcuts from that selected-product panel, including `Open Product Folder`, `Open Contracts`, `Open Runs Folder`, and `Copy Summary`
- the desktop `Auto Factory` control surface now also uses a tabbed operator workspace so overview, audit, intake, and order-stage truth stay readable without crushing buttons, headers, or recent-order history
- the desktop `Auto Factory` control surface now also runs in a background worker, shows live progress in-screen, and polls monitored production-order truth without freezing the UI
- the desktop `Auto Factory` control surface now also runs long automation through a background worker, persists production-order stage/event truth, and keeps live progress visible without freezing the UI
- blank `Batch Code` input in the desktop `Auto Factory` control surface now auto-generates a unique root-folder-based batch code so repeated runs do not collapse into one ambiguous product-local `runs/<batch_code>` folder
- `Pause Run`, `Stop Run`, and `Resume Run` remain visible operator-control groundwork only; the UI must continue to say `pending backend support` until persisted safe-checkpoint and worker-lease semantics are actually implemented
- caption runtime now also clamps grouped top-band headline height through a new `max_safe_band_height_ratio` rule so presenter-led promo cards shrink before covering the eye line, while still keeping overflow review-visible when the safer band cannot contain the text
- grouped multi-line caption solving no longer grows above the requested contract font size, while short single-line best-fit cards may still upscale when that is the intended readability behavior
- caption runtime/layout support helpers are now split into dedicated modules so the core orchestrators stay below the repo `800`-line guardrail without changing rendered behavior
- caption rendering now also rasterizes a transparent Qt bitmap per segment before FFmpeg compositing, so Thai glyph shaping and textbox rendering stay on one measured-vs-drawn engine path instead of depending on FFmpeg `drawtext`
- grouped Thai multi-line captions now also raise compressed `line_advance_ratio` to a script-safe runtime floor and report that effective resolved ratio truthfully in runtime metadata and manifests
- grouped Thai multi-line captions now also resolve pair-aware adjacent-line spacing, so low-risk pairs may stay tighter while medium/high-risk pairs surface truthful per-pair runtime evidence in manifests
- grouped Thai multi-line captions now also apply one global context-smoothing pass across arbitrary `n`-line blocks, so neighboring risky gaps can lift a middle pair when that produces safer and more coherent vertical rhythm
- assets can now be safely renamed or deleted from the `Assets` screen, with repository checks that block deletion when recipe-item or artifact-job references still exist
- the `Assets` screen now supports `Show References`, `Retire Selected`, and `Purge Media` so referenced assets can leave active use and disk without destroying audit truth
- the `Assets` screen now also supports `Replace In Recipes...` with recipe-safe validation, recipe reset-to-candidate behavior, and approval guards that prevent stale pre-replacement outputs from being reused as evidence for changed recipes
- Recipe Builder now surfaces replacement aftercare directly in the outputs area, including workflow guidance, per-output aftercare state, and historical-only visibility for outputs created before replacement
- preview and final render now normalize mixed visual source ratios into the recipe `Target Ratio` frame so output dimensions stay bounded and operator intent is respected
- preview and final render now support a layered visual compositing baseline for stacked `background_video` plus keyed `foreground_video`, with manifest-visible visual composite evidence and green-screen detection for clear presenter-over-background cases
- settings now expose a `Visual Composite` policy seam so operators can choose `auto`, `green`, `blue`, `magenta`, `custom`, or `disabled` key-color behavior for non-green studio backgrounds
- operators can now set exact preview and final output resolutions through the `Settings` UI, with `.toml` persistence and renderer enforcement for frames such as `1080x1920`
- widget-level settings UI verification coverage, including hybrid control mapping, high-value config preservation, and exact-entry synchronization
- scripted full-system release audit coverage for product-to-final workflow, recovery/escalation behavior, and runtime path hot reload
- operator-facing user manual now exists as SSOT guidance for controlled rollout and UAT
- controlled operator rollout kickoff guidance now exists as an execution-ready entry point for first real use on the current baseline
- the first controlled operator/UAT execution run has now completed a real recipe-to-final workflow and produced a verified final output at `720x1280`
- the second controlled operator/UAT run has now validated the richer-media path with voiceover, background music, two distinct foreground visuals, manifest-backed ducking evidence, and a no-review-gate final result
- initial Video Assembly Factory:
  - recipe persistence
  - recipe item assignment
  - preview render job flow
  - output approval workflow
  - recipe approval / rejection workflow
  - recipe builder view model
  - recipe builder desktop window
  - final render composition parity
  - output browsing/reporting foundation
  - output lineage details from persisted job/output records
  - approval actor/time/reason capture for outputs and recipe decisions
  - manual retry for preview/final jobs
- configurable path roots in `app_config.toml` for database, media, docs, outputs, and preview roots
- configurable queued-job recovery policy in `app_config.toml`

## Verification Baseline

- `python -m pytest` via `.venv`: `283 passed, 4 warnings`
- targeted `QT_QPA_PLATFORM=offscreen` UI coverage for the new `Auto Factory` window and existing themed windows: passed

## Current Focus

- keep richer review signals and approval history truthful through append-only persistence
- monitor whether runtime path reload stays truthful and easy for operators to understand
- monitor whether the new recipe scoring baseline stays operationally useful for operators
- monitor whether hybrid settings controls remain operator-friendly in real manual use
- validate whether the new asset-maintenance controls are clear enough for operators without additional UI restructuring
- validate whether the new referenced-asset lifecycle controls are clear enough for operators during controlled use
- validate broader controlled operator use on real campaign media before claiming broad release readiness
- monitor whether operators understand the distinction between recipe `Target Ratio` and settings-level exact output resolution
- validate whether the new green-screen compositing baseline is robust enough across real foreground media and not only the current controlled sample
- validate whether the new non-green key policy is clear enough for operators and whether per-asset overrides are needed after broader use
- validate whether the new resizable Recipe Builder workspace reduces operator confusion during attach-versus-review work
- validate whether the new auto-preview batch orchestration stays truthful and useful before extending automation across the final-render approval boundary
- validate whether the new `Auto Factory` desktop control surface is clear enough for operators without engineering assistance
- validate whether the new tag-aware planner rules are expressive enough before adding richer weighted or role-specific selection logic
- validate whether the new bulk asset tagging flow reduces repetitive operator work without causing accidental over-tagging
- validate whether the new folder-driven additive tag sync is sufficient before implementing tag-removal sync behavior
- keep the `Pause/Stop/Resume` surface truthful as pending backend support until persisted safe-checkpoint and worker-lease semantics are actually delivered
- keep project documents truthful through per-milestone revision checkpoints
- validate the same product-local auto-mode audit seam across additional products beyond `Biothentic0001`
- validate the new pixel-based caption layout and seeded clip diversity seam on additional products beyond `Biothentic0001`
- validate the new safe-band caption defaults on more real presenter shots and product compositions beyond the current sample
- validate the new Qt caption bitmap overlay path on more Thai-heavy products before adding any further language-specific contract knobs
- validate longest-layer duration resolution against more real product mixes so longer visual or music extents do not get clipped early
- validate the new persistent visual-layer selection and per-line manual caption sizing on more live product folders beyond the current sample
- validate the new textbox-first caption geometry on more live product folders, especially cases that need centered boxes with left-aligned text or stable lower-third card widths
- validate the new explicit-break-only caption policy on more Thai/English product copy so operators know when to author `\n` versus when to keep one strong headline line
- validate whether the new product-policy voice looping option remains acceptable for real ad use or needs guardrails such as max repetition count or per-product warnings
- validate whether the stronger promo-card caption presets are sufficient for live products or whether segment-specific preset selection should become explicit in `captions.toml`
- validate whether live product contracts should expose a clearer operator-facing choice between batch-cycled caption variation and intentionally locked repeated slogans
- validate whether the new versioned manifest envelope is sufficient for future audit tooling or whether a compact operator summary/index file should be added beside per-output manifests
- validate whether the new backward-compatible product-folder `v2` layout is clear enough for operators and whether migration guidance is needed for existing legacy product folders
- validate whether operators prefer the new scriptable preflight seam before every live auto-mode run or only for onboarding/debugging cases
- validate whether the new `Audit Only` UI mode is clear enough for operators or whether issue grouping/filtering is needed after broader use
- validate whether the new selected-product contract detail surface is sufficient for operator self-checks or whether inline fix/open shortcuts are needed later
- validate whether the new review-surface shortcuts are enough or whether direct `Open captions.toml` / `Open pipeline.toml` actions are needed next
- validate whether operators prefer the new tabbed `Auto Factory` workspace or still want some audit/intake surfaces visible side by side in later revisions
- validate whether the new append-only order-event history is sufficient for operator recovery and whether filtering or richer event summaries are needed next
- validate whether the new top-band face-safe clamp plus no-growth grouped headline rule is sufficient across more presenter-led products beyond the current Biothentic preview samples

## Next Steps

1. Run broader controlled operator use on additional real campaign media on the delivered background-worker plus live-progress baseline, while keeping `Pause/Stop/Resume` explicitly marked as pending backend support.
2. Validate restart-safe recovery behavior after real interruptions, including stale-lease recovery, paused-order resume, stopped-order resume, and retryable preview reruns.
3. Decide whether the append-only order-event journal should grow into a richer operator-facing event view with filtering, grouping, or export.
4. Extend the auto-factory baseline from automated preview production into controlled final-render automation only after operators accept the current planner, tag-aware selection flow, control-surface flow, review-gate truth, and the new product-local run audit seam.
5. Decide whether production-order orchestration plus active worker truth should surface on the dashboard before multi-node execution begins.
6. Clean the Alembic `path_separator=os` warning in a maintenance pass.
7. Validate whether product-local `runs/<batch_code>` artifacts remain sufficient across multiple products and whether journal detail is enough for recovery-facing operator use.
8. Run another live end-to-end preview/final audit on `Biothentic0001` after the new policy-aware voice-loop, loop-authority, and promo-caption contract slice.
9. Validate whether product-level voice looping should surface an operator-facing repetition warning or max-repeat policy after more live runs.
10. Run another live `Biothentic0001` audit on the versioned manifest envelope and verify that output-detail surfaces remain readable from the new sectioned contract.
11. Run a live folder-intake audit on one real product folder arranged in the new `contracts/` plus `assets/` layout and verify that ambiguity failures are understandable to operators.
12. Validate the new `Audit Only` control-surface mode with operators and decide whether issue grouping/export needs to be added.

## Direction Locked In This Documentation Revision

- future composition is timeline-driven, not simple file stitching
- narration looping is product-policy gated and must be explicit, reviewable, and manifest-visible
- background music may loop and must duck under narration
- loop/trim/freeze/duck decisions must become operator-visible and persistable
- the roadmap is now split into strategic and implementation layers
- `IR-01` composition-plan persistence is now implemented and becomes the baseline for `IR-02`
- `IR-02` timeline-segment persistence and validation are now implemented and become the baseline for `IR-03`
- `IR-03` preview composition now follows planned segments and becomes the baseline for `IR-04`
- `IR-04` final render now follows the planned composition path and becomes the baseline for `IR-05`
- `IR-05a` now covers operator-controlled audio policy settings plus visible composition/render summaries, while runtime audio mixing remains a separate follow-up
- `IR-05b` now adds runtime voice/music mixing plus manifest-visible applied-audio evidence
- `IR-06` now adds review gates, configurable thresholds, dashboard visibility, and manifest-backed operator evidence for risky compositions
- `IR-07` now adds configurable duck modes, sidechain-compressor tuning, and higher-quality runtime audio evidence
- `IR-08` now adds persisted failed-job recovery history, escalation thresholds, deferred bulk retry, and operator playbook visibility
- `IR-09` now locks path-root reload semantics to restart-driven behavior and makes runtime-vs-configured path truth explicit to operators
- `IR-10` now adds runtime-backed audio masking review signals plus duration-unknown emergency-fill detection in manifest-backed review evidence
- `IR-11` now adds settings-backed voice/music gain staging with runtime manifest evidence and operator-visible balance controls
- `IR-12` now locks recovery audit shape to the current payload-backed seam until stronger cross-job audit requirements justify schema promotion
- `IR-13` now persists recipe-level score/risk summaries derived from metadata, asset composition, and runtime review evidence, and exposes them in Recipe Builder recipe surfaces
- `IR-14` now hot-reloads path-root dependent desktop services by rebuilding the runtime module and swapping live service proxies instead of requiring an app restart
- `IR-15` now adds batch-only production-order planning plus internal recipe generation for auto-factory runs
- `IR-16` now adds folder-driven product/asset intake through `product.toml` and `pipeline.toml`
- `IR-17` now adds automatic preview-job production from materialized auto-factory batches while keeping approval and final render human-gated
- `IR-18` now locks the enterprise factory pipeline review plus architecture blueprint before scalable orchestration implementation begins
- `IR-19` now persists production orders plus orchestration stages for `materialize`, `preview`, and `review` control-plane truth
- `IR-25` now adds multi-select bulk asset tagging while preserving an asset-first operator review loop
- `IR-26` now applies folder-prepared `tags.toml` metadata during auto-factory intake so planner-facing asset tags can be assigned in the same run
- `IR-27` now applies product-level `captions.toml` during preview/final runtime so caption pools, font resolution, and caption-fit review signals become operational
- `IR-28` now adds product-local run artifacts plus per-asset-type fill policy for safer auto-mode reruns and traceability

## Ownership

- Engineering owner: implementation and automated verification
- Project management owner: SSOT status, Kanban, issue log, lesson log
