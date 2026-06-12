# Controlled Operator UAT Execution Report 2026-06-13

This document records the first controlled operator/UAT execution run performed after the controlled-rollout recommendation.

It should be read together with:

- [26_Full_System_Release_Audit_Report_2026-06-11.md](/F:/programming/python/MTClipFactory/doc/26_Full_System_Release_Audit_Report_2026-06-11.md)
- [27_User_Manual_2026-06-12.md](/F:/programming/python/MTClipFactory/doc/27_User_Manual_2026-06-12.md)
- [28_Controlled_Operator_Rollout_Kickoff_2026-06-12.md](/F:/programming/python/MTClipFactory/doc/28_Controlled_Operator_Rollout_Kickoff_2026-06-12.md)

## Execution Summary

- execution date: `2026-06-13`
- workspace: `F:\programming\python\MTClipFactory`
- result: `pass with limitations noted`
- recommendation after this run: `continue controlled UAT`

## Environment Baseline

- regression baseline: `python -m pytest` in `.venv` -> `121 passed`
- UI smoke baseline: `QT_QPA_PLATFORM=offscreen` -> `ui_smoke_ok=6`
- configured ratio under test: `9:16`
- FFmpeg toolchain: `F:\ffmpeg`

## Test Data Used

- product: `Biothentic0001 | Biothentic Calcium`
- ready visual assets:
  - `a0002` as `foreground_video`, ratio `960:540`
  - `biothentic0001_a0001` as `background_video`, ratio `1080:1920`
- recipe under test: `biothentic0001_r001`

Important limitation of this run:

- no `voiceover` asset was attached
- no `background_music` asset was attached
- the run validated the visual preview/final path and target-ratio normalization, but it did not validate runtime audio-mix behavior

## Workflow Executed

1. Loaded the existing controlled-workspace product, assets, and recipe.
2. Rebuilt preview for recipe `biothentic0001_r001`.
3. Approved the latest preview output with an explicit controlled-UAT reason.
4. Approved the recipe with the same explicit controlled-UAT reason.
5. Built final output from the approved recipe.
6. Verified output files, persisted decision history, and manifest evidence.

## Output Evidence

### Preview Output

- file: [biothentic0001_r001.mp4](/F:/programming/python/MTClipFactory/outputs/preview/Biothentic0001/videos/biothentic0001_r001.mp4)
- manifest: [biothentic0001_r001.json](/F:/programming/python/MTClipFactory/outputs/preview/manifests/Biothentic0001/biothentic0001_r001.json)
- measured video frame: `720x1280`
- measured duration: `10.08s`
- approval state: `approved by operator_uat`

### Final Output

- file: [biothentic0001_r001_final.mp4](/F:/programming/python/MTClipFactory/outputs/final/Biothentic0001/videos/biothentic0001_r001_final.mp4)
- manifest: [biothentic0001_r001_final.json](/F:/programming/python/MTClipFactory/outputs/preview/manifests/Biothentic0001/biothentic0001_r001_final.json)
- measured video frame: `720x1280`
- measured duration: `10.08s`
- approval state: `auto-approved by final render pipeline`

## Findings

### Confirmed Working

- end-to-end recipe-to-final workflow completed successfully on a real controlled workspace
- preview and final output both respected the requested `9:16` target ratio
- mixed visual source ratios were normalized into one bounded vertical output frame
- approval history and decision-event history were persisted truthfully
- final render completed from the approved workflow state and produced a real final artifact

### Limitations Observed

- the review gate correctly flagged `low_visual_diversity`
- the current recipe used only one distinct visual asset in the planned segments
- the current run did not exercise voice/music runtime mixing because no audio assets were attached

## Review-Gate Evidence

From the generated manifests:

- `required = true`
- `quality_score = 0.75`
- `duplicate_risk = 0.25`
- signal: `low_visual_diversity`
- summary: `Too few distinct visual assets support the planned timeline.`

This is treated as a truthful warning, not as a workflow failure.

## Readiness Decision After This Run

- controlled operator/UAT readiness: `yes`
- broad-release readiness: `no`

Reason:

- the system completed a real product-to-final workflow successfully
- however, broader readiness still needs stronger operator evidence with richer visual coverage and a full audio-path run

## Recommended Next UAT Run

1. Add at least one more distinct visual asset for the same product.
2. Add one `voiceover` asset.
3. Add one `background_music` asset.
4. Create or revise a recipe so the run exercises `hook`, `benefit`, and `cta` with more than one visual source.
5. Re-run preview/final and inspect audio-mix evidence plus review-gate changes.
