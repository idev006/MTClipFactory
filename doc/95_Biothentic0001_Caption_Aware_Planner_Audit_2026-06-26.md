# Biothentic0001 Caption Aware Planner Audit 2026-06-26

This document records the live planner-only audit executed after the caption-aware same-batch diversity slice in [94_Auto_Factory_Caption_Aware_Same_Batch_Diversity_Workflow_2026-06-26.md](/F:/programming/python/MTClipFactory/doc/94_Auto_Factory_Caption_Aware_Same_Batch_Diversity_Workflow_2026-06-26.md).

Audit target:

- workspace: `F:\programming\python\MTClipFactory`
- product root already synced into the current runtime
- product: `biothentic0001`
- requested outputs: `10`
- target platform: `shopee`
- target ratio: `9:16`
- batch code used for planning audit: `audit_captionaware_20260626`

## Purpose

- verify that the new planner can see deterministic caption signatures before materialization
- inspect whether headline reuse now spreads across fresher foreground/music pairings instead of collapsing onto the same combinations
- document what still remains open even after the planner becomes caption-aware

## Verified Execution Result

- live planner execution succeeded
- no preview/final render was needed for this audit
- the plan returned `10` recipes with persisted caption signatures and caption-aware duplicate-risk reasons

## Verified Caption Diversity Outcomes

- distinct headline signatures across the 10 planned outputs: `3`
- distinct `headline + foreground` pairs across the 10 planned outputs: `9`
- distinct `headline + music` pairs across the 10 planned outputs: `9`

Interpretation:

- the planner is now actively spreading repeated headlines across fresher foreground and music combinations instead of letting the same headline collapse back onto the same asset pairing every time
- the commercial same-batch feel is healthier even though the caption pool itself is still small

## Example Risk Signals Observed

The live plan now surfaces caption-aware reasons such as:

- `headline_reused`
- `headline_music_combo_reused`
- `headline_foreground_combo_reused`

These reasons appeared only on later slots where the planner had already consumed most of the fresh pair space.

## What Improved

- the planner can now explain that a later recipe looks risky partly because the headline itself repeated
- the planner can now distinguish plain asset reuse from repeated `headline + foreground` or `headline + music` reuse
- persisted `materialize` stage detail can now retain predicted caption-signature evidence for audit

## What Is Still Open

- the live product still exposes only `3` distinct headline signatures, so headline repetition itself remains unavoidable in a 10-output request
- planner pressure can spread repeated headlines across fresher asset pairings, but it cannot invent new headlines when the pool is too small
- the strongest remaining product-level improvement is still to widen the headline/copy pool for `Biothentic0001`

## Recommended Next Work

1. widen the `Biothentic0001` main headline pool beyond the current `3` rotating variants
2. consider product-level minimum headline-pool guidance when operators request large output counts
3. consider adding a dedicated operator summary for:
   - distinct headlines
   - distinct `headline + foreground` pairs
   - distinct `headline + music` pairs
4. repeat this planner audit on additional products so `Biothentic0001` does not remain the only live proof point

## Truth Boundary

This audit confirms that MTClipFactory now plans around same-batch headline repetition more intelligently, but it does not claim immunity from external platform duplicate detection.
