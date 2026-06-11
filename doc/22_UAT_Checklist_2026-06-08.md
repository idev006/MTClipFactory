# UAT Checklist 2026-06-08

This checklist is the operator-facing UAT companion for MTClipFactory.

It should be used together with:

- [20_Master_Test_Plan.md](/F:/programming/python/MTClipFactory/doc/20_Master_Test_Plan.md)
- [21_Test_Execution_Report_2026-06-08.md](/F:/programming/python/MTClipFactory/doc/21_Test_Execution_Report_2026-06-08.md)

## UAT Goal

- confirm the delivered baseline is usable in real operator workflows
- confirm the system behavior is understandable from the UI without database inspection
- confirm there is no blocking issue in the common product-to-output workflow

## Pre-UAT Setup

- confirm the app starts successfully
- optional quick start helpers are available at repo root:
  `run_mtclipfactory_ui.bat`, `run_mtclipfactory_pytest.bat`, and `run_mtclipfactory_ui_smoke.bat`
- confirm `app_config.toml` points to the intended test workspace
- confirm FFmpeg / FFprobe paths are valid for the UAT machine
- confirm the tester is using a non-production workspace or test data set
- confirm at least one sample product and a few sample media files are available

## Result Legend

- `Pass`
- `Fail`
- `Blocked`
- `Not Run`

## Section A: Startup And Navigation

1. Launch the application.
   Expected:
   - app opens without crash
   - dashboard is shown
   Result:
   - ________
   Notes:
   - ______________________________

2. Open each main window from the dashboard.
   Expected:
   - Products opens
   - Assets opens
   - Recipes opens
   - Tags opens
   - Settings opens
   Result:
   - ________
   Notes:
   - ______________________________

## Section B: Product And Asset Intake

1. Create a new product.
   Expected:
   - product appears in product list
   - dashboard product count updates after refresh
   Result:
   - ________
   Notes:
   - ______________________________

2. Register a valid visual asset to the product.
   Expected:
   - asset appears in asset list
   - readiness reaches expected state
   - metadata fields are populated
   Result:
   - ________
   Notes:
   - ______________________________

3. Register a voiceover asset and a background music asset.
   Expected:
   - both assets appear with correct type
   Result:
   - ________
   Notes:
   - ______________________________

4. Generate thumbnail and proxy for one asset.
   Expected:
   - jobs complete
   - dashboard job visibility updates
   - asset record reflects generated artifacts if applicable
   Result:
   - ________
   Notes:
   - ______________________________

## Section C: Tag Workflow

1. Create at least one tag.
   Expected:
   - tag appears in dictionary
   Result:
   - ________
   Notes:
   - ______________________________

2. Assign tag to a test asset and verify filtering.
   Expected:
   - assigned tag is visible
   - filtered view returns the expected asset set
   Result:
   - ________
   Notes:
   - ______________________________

## Section D: Recipe Creation And Scoring

1. Create a recipe for the test product.
   Expected:
   - recipe appears in Recipe Builder
   - recipe code is normalized correctly
   - initial recipe score / duplicate risk are visible
   Result:
   - ________
   Notes:
   - ______________________________

2. Attach visual, voice, and music assets to the recipe.
   Expected:
   - recipe items appear in the list
   - recipe score changes
   - duplicate risk updates
   Result:
   - ________
   Notes:
   - ______________________________

## Section E: Preview And Review Workflow

1. Build preview for the recipe.
   Expected:
   - preview job completes
   - preview output appears
   - manifest-backed details are visible in output details
   Result:
   - ________
   Notes:
   - ______________________________

2. Inspect preview output details.
   Expected:
   - output kind is correct
   - render job code is visible
   - quality score is visible
   - duplicate risk is visible
   - review-gate evidence is visible when applicable
   - audio-mix evidence is visible when applicable
   Result:
   - ________
   Notes:
   - ______________________________

3. If recipe enters `needs_review`, verify the UI makes that clear.
   Expected:
   - recipe status shows `needs_review`
   - supporting evidence is visible in output details or decision history
   Result:
   - ________
   Notes:
   - ______________________________

## Section F: Approval And Decision History

1. Approve the preview output.
   Expected:
   - output approval fields update
   - decision history records the action
   Result:
   - ________
   Notes:
   - ______________________________

2. Approve the recipe.
   Expected:
   - recipe status becomes `approved`
   - if recipe was flagged for review, an approval reason is required
   - decision history records the action
   Result:
   - ________
   Notes:
   - ______________________________

3. Optional negative check: try approving a flagged recipe without reason.
   Expected:
   - system blocks the action
   Result:
   - ________
   Notes:
   - ______________________________

## Section G: Final Render And Lineage

1. Build final render from an approved recipe.
   Expected:
   - final render job completes
   - final output appears in the output list
   - final output is marked as final, not preview
   Result:
   - ________
   Notes:
   - ______________________________

2. Inspect final output details.
   Expected:
   - source output lineage is visible
   - final manifest path is visible when applicable
   - approval trail remains truthful
   Result:
   - ________
   Notes:
   - ______________________________

## Section H: Dashboard And Recovery

1. Refresh dashboard after the above workflow.
   Expected:
   - product, asset, recipe, output, and job counts are plausible
   - no misleading state is shown
   Result:
   - ________
   Notes:
   - ______________________________

2. If there is a failed test job available, retry it from the dashboard workflow.
   Expected:
   - retry result is reflected in dashboard summary
   - operator playbook guidance remains understandable
   Result:
   - ________
   Notes:
   - ______________________________

## Section I: Settings And Path Reload

1. Open Settings and change one or more path roots in the test workspace only.
   Expected:
   - save succeeds
   - feedback message matches the real reload policy
   Result:
   - ________
   Notes:
   - ______________________________

2. Confirm runtime path reload behavior.
   Expected:
   - dashboard path section updates to the active roots
   - no stale restart-required warning appears when hot reload completed successfully
   Result:
   - ________
   Notes:
   - ______________________________

3. Re-open Products, Assets, and Recipes after path reload.
   Expected:
   - screens still function
   - data shown is consistent with the active runtime roots
   Result:
   - ________
   Notes:
   - ______________________________

## Section J: Negative And Usability Checks

1. Try assigning a non-ready asset or wrong-product asset if available in the test set.
   Expected:
   - system blocks invalid action
   - error message is understandable
   Result:
   - ________
   Notes:
   - ______________________________

2. Try building preview for a recipe with missing required inputs if a safe test case is available.
   Expected:
   - system fails safely
   - failure is visible in job/reporting surface
   Result:
   - ________
   Notes:
   - ______________________________

3. General usability review.
   Expected:
   - operator can understand what happened from the UI
   - review, scoring, and recovery information are not hidden
   Result:
   - ________
   Notes:
   - ______________________________

## UAT Summary

- overall result:
  - `Pass / Fail / Blocked`
- blocking issues:
  - ______________________________
- medium / low issues:
  - ______________________________
- operator confidence summary:
  - ______________________________
- recommendation:
  - `Ready for use / Needs fixes / Needs retest`

## Sign-Off

- tester name:
  - ______________________________
- date:
  - ______________________________
- approver:
  - ______________________________
