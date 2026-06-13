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
- The auto-factory folder baseline now also supports explicit root-folder scan depth so valid product folders can be discovered at root, child, or deeper nested levels deterministically.
- The auto-factory baseline can now also run preview jobs automatically for those materialized internal recipes and report per-recipe success, failure, output path, and resulting review state.
- A first desktop `Auto Factory` screen now exists so operators can browse to one root folder, set `scan_depth`, choose `Intake Only` versus materializing run modes, and inspect recent production-order status from inside the app.
- The new desktop `Auto Factory` screen now composes `AutoFactoryFolderService` with `ProductionOrderService`, so any materialize/preview run records control-plane stage truth instead of hiding it behind direct service-only automation.
- Auto-factory planning can now also consume explicit asset tag requirements from `pipeline.toml`, so operators can narrow foreground, background, music, and voice pools using normalized `group:name` labels.
- The `Tags` screen now exposes `Asset Type` filtering and visible current asset tag labels, making automation-oriented tagging easier to verify before a batch run.
- An enterprise pipeline review and architecture blueprint now exist so the project can grow into a true Video Production Factory instead of accumulating disconnected automation slices.
- Production orders and orchestration stages are now persisted independently from recipe rows, giving the system a first real control-plane baseline for automated factory runs.
- The `Tags` screen now provides guided group reuse plus product/status/search filtering so operators can narrow the asset list before assigning labels.
- The first controlled operator/UAT run has now completed end to end and produced a real final output from the current workspace.
- A second controlled operator/UAT run has now validated runtime voice/music mixing, richer visual coverage, and a no-review-gate path on a stronger recipe.
- The roadmap is now split into strategic and implementation layers, and the next mandatory implementation slice remains `IR-20` worker lease, heartbeat, and retry semantics.

## Delivered In The Latest Loop

- delivered tag-aware auto-factory planning rules through optional `pipeline.toml [selection_tags]` inputs for foreground/background/music/voice asset pools
- delivered deterministic all-of tag matching against normalized `group:name` asset labels, plus truthful shortfall reporting when configured tag rules remove otherwise-ready visual assets
- delivered `Tags` screen hardening with `Asset Type` filtering, visible asset tag labels, and operator guidance that automation can consume those normalized labels
- delivered a real desktop `Auto Factory` control surface with guided root-folder browse, batch-code override, `scan_depth`, and explicit run-mode selection
- delivered truthful in-app reporting for discovered product folders, product create/reuse outcomes, deterministic asset intake actions, recent production orders, and stage-by-stage order results
- delivered a UI orchestration seam that performs folder intake first and then routes materialize/preview runs through persisted `ProductionOrderService` control-plane records

## Still Open

1. run broader controlled operator use on real campaign media and capture operator notes without service-side intervention
2. implement worker lease, heartbeat, and retry-policy semantics on top of the new control-plane baseline
3. extend the new auto-preview factory baseline into controlled final-render automation only after operators accept the current planner, tag-aware selection rules, and review-gate truth

## Verification Baseline

- `python -m pytest` in `.venv`: `179 passed, 4 warnings`
- targeted `QT_QPA_PLATFORM=offscreen` UI/theme coverage for the new `Auto Factory` window and existing app windows: passed
