# Biothentic0001 Live Auto Mode Audit Report 2026-06-14

This document records the first real product-folder audit for the new product-local run artifacts, caption runtime, and per-asset-type fill policy baseline.

It complements [44_Biothentic0001_Auto_Factory_Test_And_Audit_Plan_2026-06-14.md](/F:/programming/python/MTClipFactory/doc/44_Biothentic0001_Auto_Factory_Test_And_Audit_Plan_2026-06-14.md), [46_Caption_Runtime_Metadata_And_Render_Workflow_2026-06-14.md](/F:/programming/python/MTClipFactory/doc/46_Caption_Runtime_Metadata_And_Render_Workflow_2026-06-14.md), and [47_Product_Local_Run_Artifacts_And_Fill_Policy_Workflow_2026-06-14.md](/F:/programming/python/MTClipFactory/doc/47_Product_Local_Run_Artifacts_And_Fill_Policy_Workflow_2026-06-14.md).

## Audit Scope

- target product folder: `G:\My Drive\tee\clip\products\Biothentic0001`
- runtime workspace: `F:\programming\python\MTClipFactory`
- runtime Python: `F:\programming\python\MTClipFactory\.venv`
- objective:
  - validate product-local `runs/<batch_code>` preview/final output layout
  - validate `order_snapshot.toml` and append-only `journal.toml`
  - validate runtime caption resolution from `captions.toml`
  - validate fill-policy evidence from `pipeline.toml`
  - validate the real operator correction loop when the first run requires review

## Starting Product Contract

The prepared product folder already contained:

- `product.toml`
- `pipeline.toml`
- `captions.toml`
- `foreground/`, `background/`, `voice/`, and `music/`
- per-folder `tags.toml`

Operator-ready contract corrections were still needed before the folder was production-clean:

1. `pipeline.toml` did not yet include the new `fill_policy` tables.
2. `pipeline.toml [selection_tags.foreground]` was too narrow and collapsed the foreground pool to one asset.
3. `captions.toml` still contained several long or editorial-note style `sub` captions that were not suitable as publishable overlay copy.

## Audit Execution

### Run C

- batch code: `biothentic0001_liveaudit_20260614_c`
- mode: folder-driven intake plus materialize plus preview build
- result:
  - preview renders succeeded `3/3`
  - outputs were written under the product folder:
    - `runs/biothentic0001_liveaudit_20260614_c/previews/videos/`
    - `runs/biothentic0001_liveaudit_20260614_c/manifests/`
    - `runs/biothentic0001_liveaudit_20260614_c/order_snapshot.toml`
    - `runs/biothentic0001_liveaudit_20260614_c/journal.toml`
  - all three recipes were routed to `needs_review`

### Run C Findings

Review-gate truth was correct, not a renderer failure.

Manifest evidence showed two main causes:

1. overly repetitive foreground selection because `selection_tags.foreground` filtered the pool down to one visual asset
2. caption overflow and truncation because some `sub` caption strings were too long or still written as operator notes instead of audience-facing copy

## Operator Corrections Applied

The live audit then applied the same contract corrections a real operator should make:

1. added the `fill_policy` tables to `pipeline.toml`
2. widened `selection_tags.foreground` so the foreground pool could include both prepared UGC clips
3. rewrote the long or non-publishable `sub` caption lines in `captions.toml` into shorter audience-facing text

## Verified Rerun

### Run D

- batch code: `biothentic0001_liveaudit_20260614_d`
- mode: folder-driven intake plus materialize plus preview build
- result:
  - preview renders succeeded `3/3`
  - all three preview recipes stayed in `candidate`
  - manifest evidence showed:
    - `overflow_role_count = 0`
    - `review_required_role_count = 0`
    - fill-policy evidence present for `voiceover`, `background_music`, `background_video`, and `foreground_video`
  - journal events were appended with `status = "succeeded"`

### Final Path Verification

One preview from Run D was then approved through the normal recipe/output approval path and rendered to final.

Verified final artifact locations:

- video:
  `G:\My Drive\tee\clip\products\Biothentic0001\runs\biothentic0001_liveaudit_20260614_d\finals\videos\biothentic0001_biothentic0001_liveaudit_20260614_d_001_final.mp4`
- manifest:
  `G:\My Drive\tee\clip\products\Biothentic0001\runs\biothentic0001_liveaudit_20260614_d\manifests\biothentic0001_biothentic0001_liveaudit_20260614_d_001_final.json`

## Conclusions

The delivered `IR-28` baseline is operational on a real product folder.

Specifically verified:

- runtime sync of `captions.toml`, `pipeline.toml`, and source-folder context
- product-local preview output path
- product-local final output path
- append-only run journal creation
- order snapshot creation
- caption runtime font resolution from the workspace fonts folder
- manifest-visible fill-policy evidence
- truthful review-gate behavior when contract quality is not yet good enough
- truthful clean rerun after operator correction

## Process Guidance Locked By This Audit

1. a review-required first run is an acceptable operator signal when contract files are still too narrow or too verbose
2. `captions.toml` must contain real publishable overlay text, not planning notes
3. `selection_tags` should preserve diversity unless intentional repetition is part of the campaign style
4. the correct recovery loop is edit product-local contract files and rerun, not bypass review signals

## Remaining Follow-Up

1. repeat the same audit seam on additional products to confirm the findings are not unique to `Biothentic0001`
2. decide whether future automation should support role-specific foreground selection rules beyond the current asset-type-wide tag filter
3. continue with `IR-20` worker lease, heartbeat, and retry-policy semantics on the production-order control plane
