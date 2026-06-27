# Biothentic0001 Creative Preset Live Audit 2026-06-27

This document records the live audit performed after the creative preset baseline was bound to the real `Biothentic0001` product contract.

## Audit Scope

- product root: `G:\My Drive\tee\clip\products`
- product: `Biothentic0001`
- runtime path: repo workspace baseline on `2026-06-27`
- execution style: real product-folder intake and planner audit with `materialize=False`, using live contracts and live asset-tag metadata

## Verified Inputs

- preflight status: `ready`
- discovered products: `1`
- errors: `0`
- warnings: `0`
- product-local preset contract: present
- enabled presets: `4 / 4`
- preset codes:
  - `benefit_stack_clean`
  - `daily_cta_reminder`
  - `presenter_urgency`
  - `proof_pack_trust`

## Audit Runs

### Balanced Cycle

- mode: `balanced_cycle`
- requested codes: all enabled presets
- planned outputs: `10`
- preset spread:
  - `benefit_stack_clean`: `3`
  - `daily_cta_reminder`: `2`
  - `presenter_urgency`: `3`
  - `proof_pack_trust`: `2`
- risk range:
  - min: `0.102`
  - avg: `0.304`
  - max: `0.388`

### Auto Best Fit

- mode: `auto_best_fit`
- requested codes: all enabled presets
- planned outputs: `10`
- preset spread:
  - `benefit_stack_clean`: `3`
  - `daily_cta_reminder`: `2`
  - `presenter_urgency`: `3`
  - `proof_pack_trust`: `2`
- risk range:
  - min: `0.102`
  - avg: `0.304`
  - max: `0.388`

### Preset Mix

- mode: `preset_mix`
- requested codes:
  - `presenter_urgency`
  - `benefit_stack_clean`
  - `proof_pack_trust`
- planned outputs: `10`
- preset spread:
  - `benefit_stack_clean`: `3`
  - `presenter_urgency`: `4`
  - `proof_pack_trust`: `3`
- risk range:
  - min: `0.102`
  - avg: `0.304`
  - max: `0.388`

## Findings

1. The live product contract is valid and planner-consumable without repo code edits.
2. `balanced_cycle` now produces a visibly distributed preset spread instead of collapsing the full batch into one preset family.
3. The current live product is no longer sitting in the old blanket `High / 1.000` planner-only zone for this planning slice; the observed risk range is now mostly `Low` to `Medium`.
4. `auto_best_fit` and `balanced_cycle` converged to the same spread on this product during this audit, which suggests the current eligibility plus same-batch diversity pressure is already strong enough to flatten the difference for this catalog.
5. `preset_mix` truthfully narrowed the family set and redistributed the batch inside that allowed subset.

## Truth Boundary

- this audit confirms planner-time preset spread and planner-time duplicate-risk behavior on the live product
- this audit does not claim a platform verdict
- this audit does not prove that `headline_pool_names` and `cta_pool_names` already override caption runtime end to end
- preview/review render-history truth still remains a separate later check when operators run full preview production

## Recommended Next Tuning

1. If stronger distinction between `auto_best_fit` and `balanced_cycle` is desired, increase mode-sensitive penalties or bonuses in preset selection scoring.
2. If operators want preset-specific headline/runtime behavior rather than planner-only evidence, add a later caption-runtime integration slice for preset-aware pool routing.
3. Run the same audit on additional real products once more product folders become available in the live library.
