# Project Progress Snapshot

## Snapshot Date

- 2026-06-27

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
- The roadmap is now split into strategic and implementation layers, and the local-worker control-plane baseline now includes persisted worker-lease plus safe-checkpoint semantics for truthful `Pause/Stop/Resume`.
- The auto-factory operations slice defined in SSOT now has a delivered background-worker plus live-progress plus backend-functional local-worker pause/stop/resume baseline, while broader operator validation and later distributed-worker concerns remain open.
- Auto Factory now also auto-generates a unique root-folder-based `batch_code` when the operator leaves the field blank, keeping product-local `runs/<batch_code>` evidence separated across repeated runs from the same root.
- Auto Factory planning now also uses recent same-product recipe history to reduce repeated exact combos and overused voice-led reruns before recipes are materialized.
- Auto Factory planning now also emits per-recipe `near_duplicate_score` plus concise `near_duplicate_reasons`, creating a machine-readable seam for future operator-facing duplicate-risk review before publishing.
- Auto Factory planning now also surfaces alternate `background_video` candidates earlier and penalizes repeated background reuse more strongly, reducing the chance that one batch uses the same background across most clips when fresh options exist.
- Auto Factory planning now also uses a deterministic candidate frontier across `voice`, internal persistent-foreground signatures, `background`, and `music`, helping fresh music and foreground choices appear early instead of being hidden behind a large search space.
- Auto Factory planning now also reorders those frontier option pools by historical underuse pressure, helping broader low-history background/music/voice/foreground choices surface earlier on products with large ready pools.
- Auto Factory now also follows a persistent visual clip policy: each materialized clip uses exactly one `foreground_video` plus one `background_video`, keeps the foreground fixed for the full clip, and loops that same foreground when timeline fill is needed.
- Preview/final rendering still respects semantic foreground roles on matching timeline segments for explicit/manual recipe paths, while Auto Factory operator-grade planning now materializes one persistent foreground pick per clip instead of mid-clip foreground swaps.
- Preview/final manifests now also expose `composition.segment_inventory`, giving each clip an operator-readable segment asset/time inventory plus a deterministic clip formula hash.
- Auto Factory now also displays recent-order and selected-order timestamps in local operator time instead of raw persisted UTC wall-clock values, so order monitoring aligns with the real desktop session.
- Blank `Batch Code` defaults and derived order labels now also use local operator timestamp tokens, while product-local run journals keep explicit UTC `Z` event timestamps for audit truth.
- Output records now also persist rendered `clip_formula_hash` plus one explicit `history_scope`, giving the duplicate-protection path a render-truth seam that can distinguish usable automation output from manual draft previews.
- Auto Factory now also treats manual preview experiments as audit-visible `draft_preview` history instead of hard duplicate-blocking evidence, while approved outputs and automation previews remain usable same-product history.
- Auto Factory candidate generation now also uses deterministic permutation coverage across foreground/background/voice/music coordinates, reducing large-pool axis bias and improving early asset spread.
- Auto Factory selected-order surfaces now also show render-history truth directly, including persisted `history_scope`, rendered `clip_formula_hash`, and historical duplicate review signals in addition to planner-time duplicate-risk evidence.
- Recipe Builder output details now also expose `history_scope`, direct output-level `clip_formula_hash`, and a clearer operator-facing explanation for the `historical_render_duplicate` review signal.
- Auto Factory planner now also calibrates duplicate-risk math against the actual feasible role pool, so evenly spread reuse in one-voice or low-foreground products is scored more truthfully than avoidable early reuse.
- Auto Factory planner now also grants bounded credit for fresh same-batch headline pairings, so a widened caption pool can lower risk without hiding real reuse reasons.
- Auto Factory now also supports product-local creative preset contracts, planner-time preset resolution, persisted preset request truth on production-order items, chosen-preset evidence on materialize stages, manifest-visible preset identity, and desktop preset-mode/operator-override controls.
- Auto Factory preview/final render now also applies the materialized creative preset's caption-style override truth, so per-clip chosen presets can change rendered `main` / `sub` caption card styling instead of remaining planner-only metadata.
- Auto Factory recent-order summary now also reflects combined order-level duplicate truth from materialize-stage planner evidence plus preview/review render-history evidence instead of showing planner-only score in isolation.
- Auto Factory selected-order summaries now also report requested preset policy plus persisted chosen-preset spread/concentration, and the live `Biothentic0001` contract now includes a real preset catalog with `balanced_cycle` defaults plus preset-aware foreground/music tag tuning.
- product-local `order_snapshot.toml` now also preserves operator-requested run truth for `run_mode`, `materialize_requested`, and `build_previews_requested` even when the desktop path executes folder intake first and starts the persisted order afterward
- Auto Factory planner now also forces fresh foreground coverage before repeating a foreground that is already used in the current batch when another feasible foreground still exists
- Preview/final render execution is now split into a dedicated factory support module so `services.py` stays under the repo line-count preference without changing public workflow behavior.
- Auto Factory now also persists that duplicate-risk evidence on successful `materialize` stages and shows it in the `Orders` tab so operators can inspect order truth instead of relying on memory-only planner output.
- Auto Factory now also persists chosen creative preset evidence on successful `materialize` stages and uses the same persisted truth to enrich preview/final manifest payloads during render execution.
- Auto Factory local-worker heartbeat updates now also tolerate transient SQLite `database is locked` contention, so one missed heartbeat write no longer kills the heartbeat thread during an otherwise active run.
- File-backed desktop SQLite runtime now also enables `WAL` plus a `busy_timeout`, reducing write contention between lease heartbeats and persisted stage/event updates.
- Auto Factory now also surfaces `lease_state`, `recovery_state`, and `suggested_action` truth for reopen-and-continue monitoring, so stale leases are visible as recoverable instead of looking like still-active workers.
- Auto Factory now also computes a canonical `fingerprint_hash` and hard-blocks exact same-product recipe-formula repeats from persisted history instead of only warning after the fact.
- Production-order `materialize` stages now also persist that `fingerprint_hash`, and order resume now ignores the same order's already-materialized recipes when rebuilding duplicate history so retryable failures can continue truthfully.
- Auto Factory `Orders` now also emphasizes persisted planner risk through derived `High` / `Medium` / `Low` / `Unavailable` labels, row highlighting, and operator-facing filter/sort controls instead of showing only raw score text.
- Auto Factory `Recent Production Orders` now also surfaces persisted planner `Risk Level` plus max raw `Duplicate Risk`, so operators can triage recent orders before opening one.
- Auto Factory `Recent Production Orders` now also uses combined order-level duplicate truth for the displayed raw score while keeping planner-vs-render interpretation explicit inside selected-order detail.
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
- delivered backend-functional `Pause Run`, `Stop Run`, and `Resume Run` on the local-worker baseline, including persisted intent, stale-lease recovery truth, and checkpoint-safe transitions
- delivered a safer blank-`Batch Code` behavior so the desktop `Auto Factory` screen now generates a unique root-folder-based batch code instead of reusing the bare folder name alone
- delivered product-local traceability hardening so repeated runs from the same root now default into distinct `runs/<batch_code>` folders without requiring manual operator typing every time
- delivered history-aware anti-duplicate planning so recent same-product recipe history now penalizes repeated exact combos, repeated foreground sequences, and overused voice assets before Auto Factory materializes a new batch
- delivered an explicit near-duplicate similarity layer so each planned recipe now carries a bounded `near_duplicate_score` plus machine-readable reasons such as `exact_combo_reused`, `foreground_asset_reused`, and `voice_asset_overused`
- delivered an operator-facing duplicate-risk surface so persisted `materialize` stages now retain planner risk evidence and the desktop `Auto Factory` `Orders` tab can display per-product and per-stage duplicate-risk truth
- delivered a canonical exact-duplicate guard so persisted same-product recipe history now blocks exact `fingerprint_hash` repeats during planning instead of only surfacing risk after selection
- delivered persisted `fingerprint_hash` evidence on successful `materialize` stages so future audit and publishing policy can point to one stable exact-duplicate key
- delivered resume-safe duplicate-guard behavior so a production order with already-materialized recipes can retry preview or later work without blocking itself during replan
- delivered stronger `Orders`-tab operator triage for duplicate risk through derived risk levels, row emphasis, and risk filter/sort controls backed only by persisted planner evidence
- delivered recent-orders duplicate-risk summary so the bottom `Recent Production Orders` strip now shows persisted `Risk Level` and a combined order-level raw score with the same truthful emphasis palette
- delivered creative-preset orchestration baseline so product-local `creative_presets.toml`, planner-time preset resolution, persisted preset request truth, materialize-stage preset evidence, manifest-visible preset identity, and Auto Factory preset controls now work end to end
- delivered preset-driven caption rendering so preview/final jobs now read the materialized preset code and apply preset-specific `main_style_preset` / `sub_style_preset` overrides inside caption runtime and output manifests
- delivered preset-spread operator summary plus live-product contract hardening so selected orders can show requested preset mode, requested preset codes, chosen preset spread, and preset concentration from persisted materialize truth
- delivered background-diversity hardening so early Auto Factory candidate scans no longer hide alternate backgrounds behind a large foreground search space
- delivered foreground/music diversity hardening so candidate coverage and scoring now push fresh music and foreground sequences earlier when feasible
- delivered frontier option-pool diversity hardening so large seeded pools are reordered by historical underuse before frontier enumeration
- preserved semantic foreground assignment rendering for explicit/manual recipe paths while shifting Auto Factory operator-grade materialization onto one persistent foreground plus one persistent background per clip
- delivered truthful shortfall handling for missing ready `foreground` or `background` media under that persistent-visual Auto Factory policy
- delivered clip-level segment-inventory manifest evidence with per-segment asset/time detail, distinct visual-asset counts, and deterministic clip formula hashing
- delivered local-time truth for Auto Factory monitoring so persisted order `Started` / `Finished` values now render in operator-local time while journal artifact timestamps stay explicit in UTC `Z`
- delivered operator-readable local timestamp tokens for new default `batch_code` and derived order labels, preventing fresh runs from appearing several hours behind the current session
- delivered an operator-facing render-history truth surface for Auto Factory `Orders`, including persisted `history_scope`, `clip_formula_hash`, and historical render duplicate explanations in the selected-order summary and stage rows
- delivered Recipe Builder output-detail visibility for output-level `history_scope` plus a clearer human-readable explanation when review came from `historical_render_duplicate`
- delivered a render-orchestration refactor so preview/final execution moved into `service_render_execution.py` and `src/mt_clip_factory/factory/services.py` returned below the repo line-count guardrail
- completed a live `Biothentic0001` 10-output Auto Factory diversity audit on production order `#20`, confirming unique rendered clip hashes plus unique foreground/background pairing while exposing remaining same-batch pressure from repeated foreground, background, music, and headline reuse
- delivered a new caption runtime guard for presenter-led top headline cards through `max_safe_band_height_ratio`, so grouped top-band promo boxes shrink before covering the presenter eye line
- stopped grouped multi-line caption layouts from growing above the requested contract font size, while preserving single-line best-fit upscaling for deliberately short hooks
- split caption runtime/layout support helpers into dedicated modules so the core orchestrators stay below the repo `800`-line guardrail
- replaced direct FFmpeg caption glyph drawing with a Qt-rendered transparent bitmap overlay path so Thai caption shaping and textbox rendering stay on the same measured-vs-drawn engine
- delivered a policy-aware duration fix so loopable background music no longer stretches auto-mode previews past the intended ad timeline while non-loop music can still remain duration-authoritative when explicitly configured
- delivered product-policy voice-loop support all the way through parser, composition persistence, renderer application, and manifest truth
- tuned the live `Biothentic0001` contract toward promo-card captions with stronger `main`/`sub` sizing and explicit loop behavior for voice and foreground assets
- corrected batch-variant ordering so early outputs diversify `voiceover` sooner instead of exhausting only foreground variation first
- delivered deterministic caption cycling for `seed_scope = "batch"` so the first outputs in one automation batch vary caption picks instead of collapsing onto one repeated hook/sub pair when the pool has enough entries
- delivered caption-aware same-batch planner scoring so deterministic headline signatures now influence duplicate-risk selection before materialization
- completed a live `Biothentic0001` caption-aware planner audit, confirming `9` distinct `headline + foreground` pairs and `9` distinct `headline + music` pairs across a 10-output plan even though the product still rotated only `3` headline signatures
- completed a follow-up live `Biothentic0001` planner audit after pool-normalized scoring, confirming `10` distinct headline signatures plus a calibrated `0.374` to `0.456` risk range instead of the earlier blanket `High`
- tuned the built-in `sale_blast` and `dark_lower_third` preset defaults plus the new-product caption template toward lighter top banners, tighter grouped headline spacing, and larger lower-third readability baselines
- delivered requested-run snapshot truth for product-local Auto Factory artifacts so `order_snapshot.toml` now records the operator-requested run mode instead of only the intake substep
- delivered same-batch foreground-balance hardening so planner selection now uses each feasible foreground before repeating another one when fresh foreground coverage is still available

## Still Open

1. run broader controlled operator use on real campaign media and capture operator notes without service-side intervention
2. validate the delivered persisted worker-lease plus safe-checkpoint semantics against more real interruptions so `Pause/Stop/Resume` remain operationally trustworthy
3. extend the new auto-preview factory baseline into controlled final-render automation only after operators accept the current planner, tag-aware selection rules, and review-gate truth
4. repeat the new live auto-mode audit seam on more products so `Biothentic0001` does not remain the only proof point
5. rerun a live `Biothentic0001` preview/final audit after the new policy-aware voice-loop and music-duration-authority slice
6. rerun a live `Biothentic0001` preview/final audit after the stronger promo-card caption contract tuning
7. validate the delivered creative-preset orchestration baseline on more live products and tune preset families, cooldowns, and batch-share behavior from operator feedback
8. run one live folder-intake audit against a real product folder arranged in the new `contracts/` plus `assets/` layout
9. validate whether the new `Audit Only` UI mode needs issue export, filtering, or grouping after broader operator use
10. validate whether the new selected-product contract inspection pane should grow operator actions such as `Open Contract`, `Copy Path`, or `Open Runs Folder`
11. validate whether operators want direct file-level shortcuts for `captions.toml`, `pipeline.toml`, and `product.toml` after using the new folder-level actions
12. validate whether the new tabbed `Auto Factory` workspace gives operators enough at-a-glance context or needs split-view refinements after live use
13. decide whether the append-only order-event journal should grow into a richer operator-facing event view with filtering, grouping, or export
14. validate the new top-band face-safe clamp on more presenter-led products and decide whether future work should add subject-aware or face-detection-driven placement beyond the current contract-only geometry model
15. validate the new Qt caption bitmap overlay on more Thai-heavy products and decide whether any remaining issues are font-specific rather than render-path-specific
16. validate whether the new pool-normalized near-duplicate similarity score stays calibrated tightly enough for Shopee/TikTok publishing batches and decide whether future policy thresholds should be operator-configurable
17. validate whether the new exact `fingerprint_hash` basis should stay limited to platform/ratio/duration plus assignments or whether future work should include more contract dimensions
18. validate whether the new `Orders`-tab emphasis thresholds and row-highlighting choices are strong enough on real operator sessions or need tuning
19. validate whether the new recent-orders duplicate-risk summary is sufficient for top-level order triage or whether the strip also needs quick filters next
20. validate whether the new background-diversity hardening is enough for real publishing batches or whether operator-tunable background cooldown policy is needed next
20. validate whether the new foreground/music diversity hardening is enough for real publishing batches or whether operator-tunable foreground/music cooldown policy is needed next
21. validate whether the new frontier option-pool reordering is enough for large-pool products or whether explicit per-role cooldown windows are still needed next
22. validate whether the new persistent foreground/background clip policy is enough to reduce same-clip duplicate feel on real campaign outputs without sacrificing cross-output diversity
23. validate whether the new segment-inventory manifest evidence should surface more directly in operator UI beyond output-detail helper text
24. validate whether Auto Factory should also expose an explicit timezone badge in-screen after the new local-time display correction
25. validate whether the new render-history truth surface is sufficient for operator triage or whether recent-order summary rows also need the same deeper history evidence next
26. widen the real `Biothentic0001` foreground and voice pools so the calibrated planner has more actual variety to work with
27. validate whether the new caption-aware planner pressure should also surface explicit pair-count summaries in the operator UI before publishing decisions
28. verify whether the current lack of ready `background_music` on `Biothentic0001` is intentional policy or a product-library gap

## Verification Baseline

- `python -m pytest` in `.venv`: `331 passed, 4 warnings`
- targeted `QT_QPA_PLATFORM=offscreen` UI/theme coverage for the new `Auto Factory` window and existing app windows: passed
