# Biothentic0001 Live Auto Factory Diversity Audit 2026-06-26

This document records the live operator-grade audit of the fresh Auto Factory batch run executed against:

- product root: `G:\My Drive\tee\clip\products`
- product: `Biothentic0001`
- production order id: `20`
- order code: `products_20260626_012808_010877_20260626_012812_262072`
- batch code: `products_20260626_012808_010877`
- run mode: `materialize_and_build_previews`

## Purpose

- confirm that the new render-history operator surface reflects persisted truth on a real run
- inspect whether the produced 10-clip batch still feels at risk of duplicate content despite unique rendered formulas
- identify the next diversity bottlenecks using manifest-backed evidence instead of guesswork

## Verified Execution Result

- order status: `succeeded`
- item count: `1`
- materialized recipes: `10`
- preview outputs: `10`
- recorded stages: `30`
- recorded events: `53`
- run artifact root:
  `G:\My Drive\tee\clip\products\Biothentic0001\runs\products_20260626_012808_010877`

## Render-History Truth

- `10/10` preview outputs produced unique `clip_formula_hash` values
- `10/10` preview/review stages persisted `history_scope = auto_factory_preview`
- `10/10` preview outputs cleared review with `duplicate_risk = 0.0`
- the batch produced no `historical_render_duplicate` signal

Interpretation:

- this run did not collide with usable same-product rendered history
- the render-history operator surface was truthful on a real batch
- the duplicate pressure that remained came from planner-side same-batch reuse, not from rendered-history exact repeats

## Manifest-Backed Diversity Findings

### Strong Outcomes

- every clip kept one persistent `foreground_video` plus one persistent `background_video`
- no clip switched foreground mid-clip
- every `foreground + background` pair was unique across the 10 outputs
- every `voice` asset was unique across the 10 outputs

### Remaining Duplicate-Feel Pressure

- only `4` distinct foreground assets were used across `10` outputs
- foreground reuse distribution:
  - two assets used `3` times each
  - two assets used `2` times each
- only `6` distinct background assets were used across `10` outputs
- three background assets were each reused `2` times
- only `7` distinct music assets were used across `10` outputs
- three music assets were each reused `2` times
- the main headline pool only surfaced `3` distinct headline variants across `10` outputs

Observed headline repetition:

1. `กลับมาแจก ความสดใส / และพลังบวกได้เต็มที่`
2. `แคลเซียมดูแล / กระดูกและข้อ ได้ทุกวัน`
3. `เสริมแคลเซียม / พร้อมลุยวันใหม่ อย่างมั่นใจ`

These three headlines rotated repeatedly through the batch. Even with unique clip hashes and unique foreground/background pairing, repeated headline cadence can still make the batch feel samey to a human reviewer and potentially to platform heuristics.

## Planner-Risk Findings

- max persisted planner risk on the order: `0.730`
- early recipes `001-004` had `near_duplicate_score = 0.0`
- mid recipes `005-007` rose to `0.34-0.52`
- late recipes `008-010` rose to `0.64-0.73`

Primary persisted planner reasons:

- `foreground_asset_reused`
- `background_asset_reused`
- `music_asset_reused`

Interpretation:

- the planner did its job truthfully by exposing same-batch reuse pressure
- the tail of the batch still accumulates repeated foreground/background/music usage once the ready pool is partly exhausted
- render-history protection is working, but same-batch diversity still needs strengthening for commercial anti-duplicate goals

## Operator-Surface Follow-Up

The live run also exposed one UI wording bug:

- preview/review stage rows could show the textual reason `render_duplicate_risk` even when persisted `duplicate_risk = 0.0`

This wording was misleading because the stage had render-history traceability metadata but no actual duplicate risk.

## Corrective Direction

### Delivered In The Follow-Up Fix

- stage-row wording now omits `render_duplicate_risk` when the persisted render duplicate score is exactly `0.0`

### Recommended Next Diversity Work

1. strengthen same-batch cooldown pressure on reused `foreground`, `background`, and `music` once the first four outputs are materialized
2. widen or rebalance the caption headline pool so a 10-output batch does not rotate only 3 main hooks
3. consider explicit planner penalties for repeated `headline + foreground` or `headline + music` combinations, not only asset-level reuse
4. add a higher-level operator batch audit surface that summarizes:
   - distinct foreground count
   - distinct background count
   - distinct voice count
   - distinct music count
   - distinct headline count
   - unique pair counts

## Truth Boundary

This audit confirms improved MTClipFactory duplicate hardening on a real run, but it does not claim immunity from external platform duplicate detection.
