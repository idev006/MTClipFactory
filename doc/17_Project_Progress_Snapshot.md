# Project Progress Snapshot

## Snapshot Date

- 2026-06-21

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
- The `Tags` screen can now operate in an asset-first loop where one selected asset becomes the main focus for inspecting current tags, attaching existing tags, or creating-and-attaching a new tag immediately.
- The `Tags` screen can now also bulk-apply one existing or newly created tag across a selected asset set while still showing one primary selected asset for review.
- Folder-driven automation can now also read `tags.toml` metadata, create missing tags, and assign them to matching assets during intake instead of treating tag metadata as documentation only.
- Folder-driven automation can now also sync product-level `captions.toml` into runtime metadata so the latest caption contract remains available during preview/final reruns.
- Preview and final render can now resolve product-level caption pools into real main/sub overlays with deterministic seed behavior, workspace-font resolution, manual `\n` handling, and review-visible overflow evidence.
- Auto-mode now also writes product-local `runs/<batch_code>` artifacts plus per-asset-type fill policy so operators can audit reruns near the source product folder itself.
- Auto-mode now also treats loop-enabled background music as a fill layer instead of a clip-length authority, keeping short-form previews aligned to the intended ad duration even when music assets are much longer.
- Auto-mode voiceover can now also loop intentionally when product policy allows it, and renderer manifests now report that request/applied truth from the product contract rather than stale global settings.
- Product-local caption contracts can now lean on stronger promo-card presets plus wider textbox sizing so `main` and `sub` overlays land closer to ad creative and further from subtitle-like defaults.
- Caption runtime now also rotates deterministic caption choices across outputs when `seed_scope = "batch"` is selected, reducing repeated hook/sub lines in the first outputs of one batch.
- Built-in `sale_blast` and `dark_lower_third` promo presets are now tuned toward lighter headline holdouts, tighter grouped headline rhythm, and stronger lower-third readability defaults.
- A live `Biothentic0001` product-folder audit has now verified the real operator loop: initial review-gate truth on narrow filters plus long captions, operator contract correction in `pipeline.toml` and `captions.toml`, clean rerun previews, and one approved final output written back into the product folder.
- Caption runtime now uses pixel-based measurement plus per-line placement, and auto-mode visual selection now applies seeded diversity so outputs stay deterministic without feeling as repetitive.
- An enterprise pipeline review and architecture blueprint now exist so the project can grow into a true Video Production Factory instead of accumulating disconnected automation slices.
- Production orders and orchestration stages are now persisted independently from recipe rows, giving the system a first real control-plane baseline for automated factory runs.
- The `Tags` screen now provides guided group reuse plus product/status/search filtering so operators can narrow the asset list before assigning labels.
- The first controlled operator/UAT run has now completed end to end and produced a real final output from the current workspace.
- A second controlled operator/UAT run has now validated runtime voice/music mixing, richer visual coverage, and a no-review-gate path on a stronger recipe.
- The roadmap is now split into strategic and implementation layers, and the next major control-plane gap remains persisted worker-lease plus safe-checkpoint semantics for truthful `Pause/Stop/Resume`.
- The auto-factory operations slice defined in SSOT now has a delivered background-worker plus live-progress baseline, while backend-functional pause/stop/resume and restart-safe recovery remain open.
- Auto Factory now also auto-generates a unique root-folder-based `batch_code` when the operator leaves the field blank, keeping product-local `runs/<batch_code>` evidence separated across repeated runs from the same root.
- Auto Factory planning now also uses recent same-product recipe history to reduce repeated exact combos and overused voice-led reruns before recipes are materialized.
- Auto Factory planning now also emits per-recipe `near_duplicate_score` plus concise `near_duplicate_reasons`, creating a machine-readable seam for future operator-facing duplicate-risk review before publishing.
- A new corrective execution slice is now active for safer default caption placement bands and longest-contributing-layer duration resolution after real auto-mode preview feedback exposed layout and timeline quality gaps.

## Delivered In The Latest Loop

- delivered tag-aware auto-factory planning rules through optional `pipeline.toml [selection_tags]` inputs for foreground/background/music/voice asset pools
- delivered deterministic all-of tag matching against normalized `group:name` asset labels, plus truthful shortfall reporting when configured tag rules remove otherwise-ready visual assets
- delivered `Tags` screen hardening with `Asset Type` filtering, visible asset tag labels, and operator guidance that automation can consume those normalized labels
- delivered an asset-first tagging workflow with selected-asset state, tag search/group narrowing, and `Create And Attach` for the current asset
- delivered a bulk asset tagging workflow with multi-select asset targeting, selected-set preservation, and one-primary-asset review behavior
- delivered folder-driven tag metadata sync through `global_tags` and per-file `[file_tags]`, including rerun-safe additive assignment and truthful invalid-contract failure
- delivered caption runtime support through product-level `captions.toml` sync, deterministic main/sub resolution, runtime font lookup, FFmpeg caption overlays, manifest evidence, and caption-overflow review signaling
- delivered product-local run artifacts through `runs/<batch_code>` previews, finals, manifests, order snapshots, and append-only journal events for folder-driven automation
- delivered runtime cache sync for `pipeline.toml` plus `context.toml` so reruns can recover product-local automation context without the original browse session
- delivered per-asset-type fill policy parsing and renderer/runtime evidence for loop, silence-tail, freeze-last-frame, trim, and review-visible shortfall behavior
- completed a real `Biothentic0001` live audit, including one initial review-required run, operator-level contract correction, one clean rerun with `3/3` preview success, and one approved final render stored under the product-local `runs/<batch_code>/finals/videos` path
- delivered a pixel-based caption layout engine with point-to-pixel sizing, per-line width measurement, per-line alignment coordinates, box geometry, and manifest-visible layout evidence
- delivered seeded diversity ordering plus seeded visual cycling so foreground/background choices vary more across recipes while staying rerun-safe
- completed a live `Biothentic0001` spot-check on the new caption layout engine and verified manifest-visible pixel layout fields on a real `1080x1920` preview output
- delivered a real desktop `Auto Factory` control surface with guided root-folder browse, batch-code override, `scan_depth`, and explicit run-mode selection
- delivered truthful in-app reporting for discovered product folders, product create/reuse outcomes, deterministic asset intake actions, recent production orders, and stage-by-stage order results
- delivered a UI orchestration seam that performs folder intake first and then routes materialize/preview runs through persisted `ProductionOrderService` control-plane records
- began the next corrective SSOT slice for operator-safe caption bands plus longest-layer duration resolution based on real preview evidence from product-folder automation
- completed the corrective caption safe-band and longest-layer duration slice so default main/sub overlays land in separated vertical bands and resolved clip duration now rises to the longest contributing layer extent when needed
- delivered pytest coverage that locks the new defaults: separated `main`/`sub` safe bands plus duration escalation when a contributing visual layer exceeds the older requested recipe length
- delivered a corrective runtime slice so each recipe now keeps one deterministic selected visual asset per visual layer across all segments, with fill policy extending that asset instead of per-segment reselection
- delivered per-line manual-caption font fitting so operator-authored `\n` lines can shrink independently by pixel width while still surfacing overflow for review when `min_font_size` is not enough
- delivered steadier grouped-caption vertical spacing so per-line best-fit sizing does not leave promo cards looking uneven between lines
- delivered ink-aware caption line-height measurement so Thai multi-line cards no longer look over-spaced from raw font metrics alone
- delivered product-local promo headline compression through `line_advance_ratio`, allowing grouped manual-break captions to tighten vertical stacking without losing deterministic layout or manifest traceability
- delivered an SSOT requirements slice for the next auto-factory operations control surface so the upcoming worker-control implementation can answer operator questions about progress, multi-worker use, pause, stop, resume, and reopen-and-continue behavior before code expands
- delivered manual-break headline compaction with `preferred_line_count` so grouped promo cards can prefer 2 lines over 3 when the text can be safely rebalanced inside the available width
- delivered grouped headline-card typography hardening so compacted promo cards now keep one shared line size instead of letting each rendered line grow independently
- delivered a textbox-first caption layout slice so resolved caption boxes now hold stable geometry while text alignment remains controllable inside the box
- delivered a caption-card height-policy slice with explicit `textbox_height_mode`, making grouped promo cards default to `content_hug` while preserving deliberate tall cards through `fixed`
- delivered manifest-visible textbox height policy truth plus pytest coverage for compact-card and fixed-height caption behavior
- delivered built-in caption style presets with role-aware defaults for `sale_blast`, `clean_cta`, and `benefit_stack`, plus per-field override behavior in `captions.toml`
- delivered preset-group metadata plus a new `dark_lower_third` support preset so future UI flows can filter style choices by caption job and sub captions can keep stronger readability over complex footage
- updated the new-product caption template and SSOT so operators can start from presets instead of tuning every style field manually
- delivered caption box-border styling with manifest-visible `box_border_*` fields plus grouped/per-line FFmpeg drawbox coverage
- locked caption composition to `explicit \n only` multi-line behavior so captions without authored breaks now stay single-line and use box-aware best-fit sizing instead of runtime auto-wrap
- strengthened single-line caption scoring so short hooks grow more aggressively toward textbox width while long hooks shrink deterministically and remain reviewable when minimum size is still unsafe
- delivered a versioned manifest envelope with stable `manifest_meta`, `artifact`, `run`, `composition`, `render`, and `quality` sections while keeping manifest readers backward-safe for older flat payloads
- delivered a backward-compatible product-folder `v2` layout with `contracts/` plus `assets/` resolution, truthful ambiguity failure when old/new paths overlap, and pytest coverage for both legacy and `v2` discovery
- updated the new-product auto-factory template kit to ship in the preferred `v2` layout, including `contracts/prod_detail.txt` for operator-facing product context capture
- delivered a read-only product-folder preflight audit seam plus CLI script so operators can validate contracts, assets, tags, and `selection_tags` viability before a real automation run
- delivered `Audit Only` inside the desktop `Auto Factory` screen so the same preflight seam is available through guided UI controls and dedicated audit result tables
- delivered selected-product contract/runtime detail inspection inside the desktop `Auto Factory` screen so operators can review product metadata, pipeline policy, caption preset/font intent, and tag-readiness evidence from the currently highlighted product row
- delivered selected-product operator actions inside that same `Auto Factory` panel so operators can open the product folder, contracts location, batch-local runs folder, or copy the current summary without leaving the app
- delivered a tabbed `Auto Factory` workspace layout so overview, audit, intake, and order-stage surfaces no longer collapse into one over-compressed vertical stack
- delivered background-run execution plus live progress polling for the desktop `Auto Factory` screen so operators can monitor production-order stage truth without freezing the window
- delivered truthful operator-control groundwork in that same screen, with active `Refresh Progress` and a visible control seam for `Pause/Stop/Resume`
- delivered background-run execution plus live progress polling for the desktop `Auto Factory` screen so operators can monitor production-order stage truth without freezing the window
- delivered a Thai script-safe grouped-caption spacing correction so multi-line Thai promo stacks now clamp compressed `line_advance_ratio` back to a safe runtime floor and manifest evidence reports the effective resolved ratio instead of the unsafe requested value
- refined Thai grouped-caption spacing again into a pair-aware solver that inspects adjacent upper/lower mark collisions, allowing low-risk pairs to keep tighter promo rhythm while medium/high-risk pairs receive stronger runtime spacing floors with manifest-visible pair evidence
- extended that Thai grouped-caption solver into `n`-line global context smoothing so one low-risk middle gap can still be promoted when surrounding high-risk gaps would otherwise make the full block look uneven or unsafe
- delivered truthful operator-control groundwork in that same screen, with active `Refresh Progress` and a visible control seam for `Pause/Stop/Resume`
- kept `Pause Run`, `Stop Run`, and `Resume Run` explicitly at `pending backend support` until persisted safe-checkpoint and worker-lease semantics exist
- delivered a safer blank-`Batch Code` behavior so the desktop `Auto Factory` screen now generates a unique root-folder-based batch code instead of reusing the bare folder name alone
- delivered product-local traceability hardening so repeated runs from the same root now default into distinct `runs/<batch_code>` folders without requiring manual operator typing every time
- delivered history-aware anti-duplicate planning so recent same-product recipe history now penalizes repeated exact combos, repeated foreground sequences, and overused voice assets before Auto Factory materializes a new batch
- delivered an explicit near-duplicate similarity layer so each planned recipe now carries a bounded `near_duplicate_score` plus machine-readable reasons such as `exact_combo_reused`, `foreground_sequence_reused`, and `voice_asset_overused`
- delivered a new caption runtime guard for presenter-led top headline cards through `max_safe_band_height_ratio`, so grouped top-band promo boxes shrink before covering the presenter eye line
- stopped grouped multi-line caption layouts from growing above the requested contract font size, while preserving single-line best-fit upscaling for deliberately short hooks
- split caption runtime/layout support helpers into dedicated modules so the core orchestrators stay below the repo `800`-line guardrail
- replaced direct FFmpeg caption glyph drawing with a Qt-rendered transparent bitmap overlay path so Thai caption shaping and textbox rendering stay on the same measured-vs-drawn engine
- delivered a policy-aware duration fix so loopable background music no longer stretches auto-mode previews past the intended ad timeline while non-loop music can still remain duration-authoritative when explicitly configured
- delivered product-policy voice-loop support all the way through parser, composition persistence, renderer application, and manifest truth
- tuned the live `Biothentic0001` contract toward promo-card captions with stronger `main`/`sub` sizing and explicit loop behavior for voice and foreground assets
- corrected batch-variant ordering so early outputs diversify `voiceover` sooner instead of exhausting only foreground variation first
- delivered deterministic caption cycling for `seed_scope = "batch"` so the first outputs in one automation batch vary caption picks instead of collapsing onto one repeated hook/sub pair when the pool has enough entries
- tuned the built-in `sale_blast` and `dark_lower_third` preset defaults plus the new-product caption template toward lighter top banners, tighter grouped headline spacing, and larger lower-third readability baselines

## Still Open

1. run broader controlled operator use on real campaign media and capture operator notes without service-side intervention
2. implement and validate persisted worker-lease plus safe-checkpoint semantics so `Pause/Stop/Resume` can become truthful backend-backed controls instead of groundwork-only buttons
3. extend the new auto-preview factory baseline into controlled final-render automation only after operators accept the current planner, tag-aware selection rules, and review-gate truth
4. repeat the new live auto-mode audit seam on more products so `Biothentic0001` does not remain the only proof point
5. rerun a live `Biothentic0001` preview/final audit after the new policy-aware voice-loop and music-duration-authority slice
6. rerun a live `Biothentic0001` preview/final audit after the stronger promo-card caption contract tuning
7. run one live folder-intake audit against a real product folder arranged in the new `contracts/` plus `assets/` layout
8. validate whether the new `Audit Only` UI mode needs issue export, filtering, or grouping after broader operator use
9. validate whether the new selected-product contract inspection pane should grow operator actions such as `Open Contract`, `Copy Path`, or `Open Runs Folder`
10. validate whether operators want direct file-level shortcuts for `captions.toml`, `pipeline.toml`, and `product.toml` after using the new folder-level actions
11. validate whether the new tabbed `Auto Factory` workspace gives operators enough at-a-glance context or needs split-view refinements after live use
12. decide whether the append-only order-event journal should grow into a richer operator-facing event view with filtering, grouping, or export
13. validate the new top-band face-safe clamp on more presenter-led products and decide whether future work should add subject-aware or face-detection-driven placement beyond the current contract-only geometry model
14. validate the new Qt caption bitmap overlay on more Thai-heavy products and decide whether any remaining issues are font-specific rather than render-path-specific
15. validate whether the new near-duplicate similarity score is calibrated tightly enough for Shopee/TikTok publishing batches and decide whether future policy thresholds should be operator-configurable

## Verification Baseline

- `python -m pytest` in `.venv`: `288 passed, 4 warnings`
- targeted `QT_QPA_PLATFORM=offscreen` UI/theme coverage for the new `Auto Factory` window and existing app windows: passed
