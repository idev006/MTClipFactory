# Controlled Operator UAT Round 2 Report 2026-06-13

This document records the second controlled operator/UAT run, focused on richer media coverage after the first end-to-end pass.

It should be read together with:

- [29_Controlled_Operator_UAT_Execution_Report_2026-06-13.md](/F:/programming/python/MTClipFactory/doc/29_Controlled_Operator_UAT_Execution_Report_2026-06-13.md)
- [27_User_Manual_2026-06-12.md](/F:/programming/python/MTClipFactory/doc/27_User_Manual_2026-06-12.md)
- [28_Controlled_Operator_Rollout_Kickoff_2026-06-12.md](/F:/programming/python/MTClipFactory/doc/28_Controlled_Operator_Rollout_Kickoff_2026-06-12.md)

## Execution Summary

- execution date: `2026-06-13`
- focus: `audio path plus richer visual coverage`
- result: `pass`
- recommendation after this run: `controlled UAT evidence is now materially stronger`

## Goal Of This Round

The first controlled run proved one real final output.

This second run was intended to cover the gaps left by that first pass:

- add `voiceover`
- add `background_music`
- add one more distinct visual asset
- validate runtime `audio_mix` evidence
- confirm review-gate improvement when visual diversity increases

## Test Data Used

- product: `Biothentic0001 | Biothentic Calcium`
- new controlled-run assets registered:
  - `a0003_fg_round2` as `foreground_video`
  - `a0004_voice_round2` as `voiceover`
  - `a0005_music_round2` as `background_music`
- existing visual asset reused:
  - `a0002` as `foreground_video`
- recipe under test: `biothentic0001_r002_audio`

Additional artifact coverage in this round:

- thumbnail generated for `a0003_fg_round2`
- proxy generated for `a0003_fg_round2`

## Workflow Executed

1. Registered one additional foreground video.
2. Registered one voiceover asset.
3. Registered one background music asset.
4. Generated thumbnail and proxy for the new foreground video.
5. Created recipe `biothentic0001_r002_audio`.
6. Attached two foreground videos, one voiceover, and one background music asset.
7. Built preview.
8. Approved preview output with a controlled-UAT reason.
9. Approved the recipe with the same explicit reason.
10. Built final output.
11. Verified output dimensions, manifests, review-gate evidence, and runtime audio-mix evidence.

## Output Evidence

### Preview Output

- file: [biothentic0001_r002_audio.mp4](/F:/programming/python/MTClipFactory/outputs/preview/Biothentic0001/videos/biothentic0001_r002_audio.mp4)
- manifest: [biothentic0001_r002_audio.json](/F:/programming/python/MTClipFactory/outputs/preview/manifests/Biothentic0001/biothentic0001_r002_audio.json)
- measured video frame: `720x1280`
- measured duration: `19.906641s`

### Final Output

- file: [biothentic0001_r002_audio_final.mp4](/F:/programming/python/MTClipFactory/outputs/final/Biothentic0001/videos/biothentic0001_r002_audio_final.mp4)
- manifest: [biothentic0001_r002_audio_final.json](/F:/programming/python/MTClipFactory/outputs/preview/manifests/Biothentic0001/biothentic0001_r002_audio_final.json)
- measured video frame: `720x1280`
- measured duration: `19.906641s`

## Manifest-Backed Findings

### Audio Path

- `audio_present = true`
- `voice_track_count = 1`
- `music_track_count = 1`
- ducking `applied = true`
- ducking mode: `sidechain_compressor`
- `voice_loop_applied = false`
- `background_music_loop_enabled = true`
- music gain stage was applied

This confirms the runtime voice/music path executed in a real controlled run.

### Review Gate

- `required = false`
- `quality_score = 1.0`
- `duplicate_risk = 0.0`
- `distinct_visual_assets = 2`
- `max_consecutive_same_asset_segments = 1`
- summary: `No review gate triggered.`

This confirms the richer media set removed the low-visual-diversity warning seen in the first run.

### Segment Coverage

The recipe resolved into five semantic segments:

1. `hook`
2. `problem`
3. `benefit`
4. `proof`
5. `cta`

The visual assets alternated across these segments, which materially improved composition diversity over the first controlled run.

## Readiness Decision After Round 2

- controlled operator/UAT readiness: `yes`
- next-step readiness: `ready for broader controlled operator use with real media`
- broad-release readiness: `not yet claimed`

Reason:

- preview/final visual normalization is now proven in two controlled runs
- the runtime audio-mix path is now proven in one richer-media controlled run
- review-gate behavior improved as expected when the media set improved
- however, broad-release claims should still wait for more real operator evidence on real campaign media

## Recommended Next Step

1. Run the same workflow with real operator-provided media instead of only controlled synthetic test assets.
2. Confirm the UI remains understandable without service-side assistance.
3. Collect operator notes on recipe setup, role selection, and output review comfort.
4. Reassess broad-release readiness only after those real-media findings are documented.
