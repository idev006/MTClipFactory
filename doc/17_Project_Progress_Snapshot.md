# Project Progress Snapshot

## Snapshot Date

- 2026-06-13

## Where To See Progress

1. In the desktop app dashboard:
   [src/mt_clip_factory/ui/control_center/dashboard_window.py](/F:/programming/python/MTClipFactory/src/mt_clip_factory/ui/control_center/dashboard_window.py)
2. Project manager status report:
   [11_Project_Status_Report.md](/F:/programming/python/MTClipFactory/doc/11_Project_Status_Report.md)
3. SSOT Kanban:
   [12_Kanban_Board.md](/F:/programming/python/MTClipFactory/doc/12_Kanban_Board.md)
4. Open issues and risks:
   [13_Issues_Log.md](/F:/programming/python/MTClipFactory/doc/13_Issues_Log.md)
5. Delivery learning log:
   [14_Lessons_Learned.md](/F:/programming/python/MTClipFactory/doc/14_Lessons_Learned.md)

## Honest Current State

- Foundation stack is established and testable on `Python 3.12 + SQLite + SQLAlchemy + PySide6 + pytest`.
- `Resource Library Management` is at a useful MVP baseline.
- `Video Assembly Factory` now has segment-aware preview/final visual composition plus a gain-staged runtime voice/music mix path, though it is still not a full audio-effects engine.
- Dashboard and settings are now a stronger operational truth surface.
- Dashboard now also exposes `needs_review` recipe count and the active review thresholds.
- Automatic queued-job recovery now exists when enabled. Failed jobs can now be retried from the dashboard, but they are still not auto-startup work.
- Output lineage is now visible from persisted output/job records.
- Approval actor/time/reason is persisted with migration support, and immutable decision-event history is now available in the Recipe Builder workflow.
- The composition direction is now documented: master timeline, semantic segments, `voice no-loop`, and `music ducking`.
- The first composition persistence seam now exists through `composition_plans` and `render_decisions`.
- Semantic segment persistence now exists through `timeline_segments` with baseline contiguous-coverage validation.
- Preview composition is now segment-aware and writes inspectable manifest data for chosen visual clips.
- Final render now rerenders from the planned composition path instead of depending on the approved preview file alone.
- Settings now expose `voice_loop_enabled`, `background_music_loop_enabled`, and music duck controls through `.toml` and the desktop settings screen.
- Settings now also allow exact preview/final output frame entry so operators can request sizes like `1080x1920` without editing code.
- Dashboard and Recipe Builder now show more of the composition/render story instead of only output lineage.
- Preview and final renderers now emit manifest-visible runtime audio-mix evidence.
- Preview and final renderers now also emit manifest-visible review-gate evidence plus quality/duplicate-risk summaries.
- Review gates now also detect missing ducking protection during narration/music overlap and duration-unknown emergency fill across visual or audio layers.
- Preview and final renderers now support configurable duck modes with sidechain-compressor tuning evidence.
- Preview and final renderers now also support configurable voice/music gain staging with manifest-visible balance evidence.
- Failed jobs now retain persisted recovery-attempt history, escalate visibly after repeated failures, and surface operator playbook guidance on the dashboard.
- Recovery history now remains intentionally payload-backed on the `jobs` record until stronger cross-job audit needs appear.
- Path roots can now hot-reload inside the desktop app through a whole-module runtime rebind, and the dashboard still shows runtime-active versus configured paths truthfully.
- Recipe records now retain persisted score/risk summaries derived from metadata, asset composition, and runtime review evidence, and Recipe Builder now shows those summaries in the recipe list.
- The settings window now loads its styling from a package-backed QSS theme seam instead of embedding stylesheet text inline.
- Dashboard, resource-library, tag-dictionary, and recipe-builder windows now also consume a shared package-backed app-window theme baseline.
- Primary action buttons now have clearer but more restrained visual affordance through the shared theme, including balanced depth and pressed-state feedback.
- A controlled operator rollout kickoff guide now exists so the first real-use session can start from one practical SSOT entry point.
- Recipe Builder now explains its main workflow directly in the screen, makes the `ready`-asset-only attach list more explicit, gives the asset panel a more usable height, and provides composition-aware attach-role suggestions that auto-select the next likely role from the current semantic flow.
- The `Assets` screen now supports safe rename/delete maintenance actions for selected assets, while blocking deletion when recipes or artifact jobs still reference the asset.
- The `Assets` screen now also supports `Show References`, `Retire Selected`, and `Purge Media` so bad assets can leave active use and disk without corrupting history.
- The `Assets` screen now also supports recipe-safe asset replacement so affected recipes can move to corrected media without hand-editing the database or pretending old outputs match new content.
- Recipe Builder now makes post-replacement aftercare visible in-screen so operators can tell when older outputs are historical-only and what rebuild/approval step comes next.
- The render path now has a layered visual compositing baseline so a keyed `foreground_video` can sit over a `background_video` instead of forcing the operator to accept raw green-screen output.
- The settings surface now also exposes a `Visual Composite` policy so non-green keyed foregrounds can be handled without code edits.
- Preview and final render now normalize mixed visual source ratios into the selected recipe frame so one output ratio can contain differently sized source clips safely.
- Recipe Builder now uses a resizable multi-column workspace so operators can expand setup, asset-attachment, or output-review surfaces based on the current step.
- Recipe Builder tables now keep explicit vertical-scroll behavior for overflow rows instead of depending on one long page or pagination.
- An Auto Factory batch-planning baseline now exists so operators can request counts by product, enforce batch-only uniqueness, and materialize internal recipes automatically without hand-building each one.
- The auto-factory baseline can now also read product folders with `product.toml` and `pipeline.toml`, create missing products, ingest deterministic asset codes, and materialize internal recipes from one batch root.
- The auto-factory baseline can now also run preview jobs automatically for those materialized internal recipes and report per-recipe success, failure, output path, and resulting review state.
- An enterprise pipeline review and architecture blueprint now exist so the project can grow into a true Video Production Factory instead of accumulating disconnected automation slices.
- Production orders and orchestration stages are now persisted independently from recipe rows, giving the system a first real control-plane baseline for automated factory runs.
- The first controlled operator/UAT run has now completed end to end and produced a real final output from the current workspace.
- A second controlled operator/UAT run has now validated runtime voice/music mixing, richer visual coverage, and a no-review-gate path on a stronger recipe.
- The roadmap is now split into strategic and implementation layers, and the current mandatory implementation slice is complete.

## Delivered In The Latest Loop

- desktop app path-root changes now hot-reload by rebuilding the runtime service module and swapping live service proxies instead of waiting for a full restart
- settings save now emits runtime hot-reload feedback, and dashboard/path summaries stay aligned to the newly active roots
- pytest now covers pending hot-reload status, runtime module rebind, and settings-view-model hot-reload signaling
- architecture, reliability, roadmap, Kanban, issues, lessons learned, and UML were aligned to the delivered `IR-14` baseline
- settings UI now uses grouped panels and a two-column layout for clearer operator scanning
- hybrid slider-plus-exact-entry settings controls are now covered by widget-level pytest checks
- slider/editor width uniformity polish now keeps settings numeric controls visually aligned while preserving the hybrid control model
- a reusable `ui.theme` seam now loads packaged QSS assets, and the settings window theme was extracted out of Python code
- the broader desktop UI now shares one packaged app-window theme baseline, with focused window-level overrides reserved for justified differences
- packaged app-window buttons now read more clearly as clickable controls instead of flat color blocks, while staying proportionate to the rest of the UI
- a controlled operator rollout kickoff document now packages the go/no-go answer, first-run checklist, and first workflow for immediate use
- Recipe Builder layout hardening now improves asset-panel scanability and reduces confusion about why only `ready` assets appear in the attach list
- asset maintenance now covers selected-asset rename/delete behavior plus repository-safe blocking for in-use media
- preview/final render hardening now applies recipe-target frame normalization to mixed-ratio visual clips
- audit hardening now confirms pre-existing high-value config settings survive settings load/save without silent clamp
- audit hardening now also confirms exact numeric entry can push values beyond default slider spans without losing persistence truth
- full-system release audit now re-executes factory happy path, recovery/escalation flow, and runtime hot reload through a dedicated scripted audit runner
- operator-facing user manual is now published as SSOT document `27` for controlled rollout and UAT use
- first controlled operator/UAT execution now confirms a real `9:16` preview/final output can be produced successfully from the current workspace baseline
- second controlled operator/UAT execution now confirms manifest-backed audio mixing, ducking, and five-segment richer-media composition on the same baseline
- render configuration now also supports UI-managed exact preview/final frame sizing with `.toml` persistence instead of a fixed code-only normalization ceiling
- the asset-lifecycle SSOT now separates hard delete from retire/purge behavior so referenced assets can be cleaned up safely
- corrective asset replacement now rewires affected recipe items onto a chosen ready replacement asset, resets those recipes for rebuild, and blocks stale pre-replacement outputs from being re-approved
- Recipe Builder output surfaces now expose replacement aftercare guidance plus per-output historical/current state so the rebuild flow can be followed without database inspection
- preview/final rendering now also writes manifest-visible visual composite evidence for stacked background-plus-foreground segments, including keyed green-screen overlays
- the real `r0003` sample now rebuilds to a presenter-over-background result instead of exposing raw green-screen output, and its review-gate evidence clears at `distinct_visual_assets = 2`
- operators can now steer compositing toward `auto`, `green`, `blue`, `magenta`, `custom`, or `disabled` key-color behavior from Settings instead of living with a green-only baseline
- Recipe Builder now groups workflow into resizable setup, inventory, and review panes instead of keeping every surface trapped in one fixed grid
- Recipe Builder overflow hardening now keeps each major table vertically scrollable when row counts exceed panel height
- the first auto-factory delivery slice now plans batch-unique output variants per product and can create the internal recipes needed for later automated preview/final runs
- the second auto-factory delivery slice now turns folder contracts into product creation, asset intake, and batch recipe materialization without duplicating already-ingested deterministic asset codes
- the third auto-factory delivery slice now turns materialized batches into real preview outputs with per-recipe batch reporting, while still stopping before output approval, recipe approval, or final render
- the latest architecture loop now locks the four-plane factory vocabulary: `Control Plane`, `Execution Plane`, `State Plane`, and `Operator Plane`
- the latest implementation loop now persists control-plane `materialize`, `preview`, and `review` stage truth through dedicated production-order tables and service orchestration

## Still Open

1. run broader controlled operator use on real campaign media and capture operator notes without service-side intervention
2. implement worker lease, heartbeat, and retry-policy semantics on top of the new control-plane baseline
3. extend the new auto-preview factory baseline into controlled final-render automation only after operators accept the current planner and review-gate truth

## Verification Baseline

- `python -m pytest` in `.venv`: `170 passed`
- `QT_QPA_PLATFORM=offscreen` UI smoke: `6` main windows instantiated
