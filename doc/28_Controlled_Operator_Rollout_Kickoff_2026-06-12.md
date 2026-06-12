# Controlled Operator Rollout Kickoff 2026-06-12

This document is the practical kickoff guide for starting controlled operator use of MTClipFactory on the current baseline.

It should be used together with:

- [26_Full_System_Release_Audit_Report_2026-06-11.md](/F:/programming/python/MTClipFactory/doc/26_Full_System_Release_Audit_Report_2026-06-11.md)
- [27_User_Manual_2026-06-12.md](/F:/programming/python/MTClipFactory/doc/27_User_Manual_2026-06-12.md)
- [22_UAT_Checklist_2026-06-08.md](/F:/programming/python/MTClipFactory/doc/22_UAT_Checklist_2026-06-08.md)

## Current Readiness

- recommendation: `go for controlled operator rollout / UAT`
- broad-release status: `not yet approved`
- current verified regression baseline: `121 passed`
- current UI smoke baseline: `ui_smoke_ok=6`

First controlled execution result now available:

- the first controlled operator/UAT run on `2026-06-13` completed the recipe-to-final workflow successfully
- the run confirmed real final-output generation and `9:16` target-ratio normalization on mixed-ratio visual assets
- the run also confirmed the next UAT should add voiceover, background music, and more distinct visual assets

Second controlled execution result now available:

- a richer-media controlled run on `2026-06-13` added voiceover, background music, and a second foreground visual asset
- the run confirmed runtime audio-mix evidence, applied ducking, five semantic segments, and a no-review-gate result on the stronger media set

Meaning:

- the system is ready for you to use in a controlled workspace
- the system is not yet claiming unrestricted broad-release readiness

## Intended Use Right Now

Use the system now if all of the following are true:

- you will use a test workspace or controlled internal workspace
- FFmpeg and FFprobe paths are valid on this machine
- you understand this is a controlled rollout, not a public broad release
- you will record any usability or workflow issue you observe during use

Do not treat the current baseline as a broad-production sign-off if:

- you still need human operator acceptance evidence
- you still need real-media quality sign-off
- you still need long-duration soak confidence

## Launch Decision

### You May Start Using It Now When

- you are the operator or internal reviewer for this rollout
- you can use non-production or controlled data
- you are prepared to follow the UAT checklist during the first serious run

### You Should Pause Before Use When

- FFmpeg or FFprobe is not configured correctly
- `app_config.toml` points at the wrong workspace paths
- you plan to run against unknown production data on the first pass
- you need a broad-release guarantee rather than a controlled-rollout baseline

## First-Run Checklist

1. Open [app_config.toml](/F:/programming/python/MTClipFactory/app_config.toml) and confirm database, media, docs, outputs, and preview roots match the intended test workspace.
2. Confirm FFmpeg and FFprobe paths in `app_config.toml` are valid on this machine.
3. Launch the app with [run_mtclipfactory_ui.bat](/F:/programming/python/MTClipFactory/run_mtclipfactory_ui.bat).
4. Confirm the `Dashboard` opens.
5. Follow the quick workflow in [27_User_Manual_2026-06-12.md](/F:/programming/python/MTClipFactory/doc/27_User_Manual_2026-06-12.md).
6. Use [22_UAT_Checklist_2026-06-08.md](/F:/programming/python/MTClipFactory/doc/22_UAT_Checklist_2026-06-08.md) to record pass/fail notes during the first controlled run.

## Recommended First Controlled Workflow

1. Create one test product.
2. Register one visual asset, one voiceover, and one background music file.
3. Create one tag and assign it to one asset.
4. Create one recipe and attach ready assets.
5. Build one preview.
6. Review output details, review-gate evidence, and audio-mix evidence.
7. Approve the preview output and recipe with a meaningful note.
8. Build one final output.
9. Refresh the dashboard and inspect counts, jobs, and path surfaces.

## What To Watch Closely

- whether the workflow is understandable without inspecting the database
- whether recipe review and approval steps feel clear
- whether output details feel trustworthy
- whether settings and path-root behavior remain understandable after save/reload
- whether button clarity, spacing, and table readability feel comfortable in real use

## If Something Goes Wrong

- use the dashboard to inspect failed jobs and operator playbook guidance
- retry failed jobs only after reading the on-screen guidance
- compare runtime-active paths versus configured paths if a path change behaves unexpectedly
- keep notes directly in the UAT checklist instead of relying on memory

## Exit Condition For This Rollout Step

This rollout step is considered successful when:

- the full product-to-final workflow completes on a normal desktop session
- there is no blocking operator-facing defect
- the operator can explain what happened from the UI
- any issues found are recorded clearly enough for follow-up

Current note:

- this exit condition has now been met once in a controlled workspace
- broader rollout confidence still benefits from an additional richer-media UAT pass

## Honest Recommendation

- yes, you can start using the system now in controlled rollout / UAT conditions
- no, this is not yet a broad-release or unrestricted-production sign-off
