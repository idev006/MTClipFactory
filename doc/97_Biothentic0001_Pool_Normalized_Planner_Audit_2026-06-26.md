# Biothentic0001 Pool-Normalized Planner Audit 2026-06-26

This document records the live planner-only audit executed after the pool-normalized duplicate-scoring slice in [96_Auto_Factory_Pool_Normalized_Duplicate_Scoring_Workflow_2026-06-26.md](/F:/programming/python/MTClipFactory/doc/96_Auto_Factory_Pool_Normalized_Duplicate_Scoring_Workflow_2026-06-26.md).

## Audit Target

- workspace: `F:\programming\python\MTClipFactory`
- product root already synced into the current runtime
- product: `biothentic0001`
- requested outputs: `10`
- target platform: `shopee`
- target ratio: `9:16`
- batch code used for planning audit: `audit_pool_normalized_20260626`

## Verified Product Pool Facts

- ready `foreground_video`: `3`
- ready `background_video`: `9`
- ready `voiceover`: `1`
- ready `background_music`: `0`

Interpretation:

- the product still has a real foreground and voice bottleneck
- the planner must not pretend those constraints do not exist
- the score should reflect that the planner spread reuse as fairly as possible inside those limits

## Verified Execution Result

- live planner execution succeeded with the latest code
- the plan returned `10` recipes
- no preview or final render was needed for this audit

## Verified Diversity Outcomes

- distinct headline signatures across the 10 planned outputs: `10`
- distinct `headline + foreground` pairs across the 10 planned outputs: `10`
- distinct `headline + music` pairs across the 10 planned outputs: `10`
- calibrated score range across the 10 planned outputs: `0.374` to `0.456`

Under the current operator threshold:

- `0.374` to `0.456` maps to `Medium`
- the same product/pool shape should no longer surface as `High` only because historical reuse existed in a small constrained pool

## Example Risk Signals Observed

Persisted planner reasons still remained truthful about the constrained pool:

- `foreground_asset_reused`
- `voice_asset_overused`
- `background_asset_reused`
- `music_asset_reused`

Interpretation:

- the planner still admits that reuse exists
- the lower score comes from calibrated math, not from hiding the reasons
- the product would still benefit from more real foreground and voice variation

## What Improved

- the planner now distinguishes constrained reuse from avoidable reuse
- a fresh widened headline pool now meaningfully lowers same-batch risk instead of being drowned out by full historical asset penalties
- operator review should now see a more truthful `Medium` signal for this product shape instead of a blanket `High`

## What Is Still Open

- `Biothentic0001` still has only `3` ready foreground videos and `1` ready voiceover, so commercial diversity is still bottlenecked by real asset supply
- the current product has no ready `background_music`, which should stay visible as a content-library gap
- broader live validation is still needed on more products before treating the calibration as final

## Recommended Next Work

1. widen the real `foreground_video` pool for `Biothentic0001`
2. add at least one more ready `voiceover` variant for this product
3. verify whether the current lack of ready `background_music` is intentional policy or a product-library gap
4. rerun the same planner audit after new real assets are added so the calibrated score can be compared against a less constrained product

## Truth Boundary

This audit confirms that the latest planner calibration is more truthful for constrained same-batch reuse, but it does not claim that the product is now safe from external duplicate-content detection.
