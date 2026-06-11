# Full System Release Audit Report 2026-06-11

This document records the executed full-system release audit for the current MTClipFactory baseline.

It follows [25_Full_System_Release_Audit_Plan_2026-06-11.md](/F:/programming/python/MTClipFactory/doc/25_Full_System_Release_Audit_Plan_2026-06-11.md).

## Execution Summary

- execution date: 2026-06-11
- tester role: senior tester / senior auditor
- environment: `F:\programming\python\MTClipFactory`
- Python runtime: `F:\programming\python\MTClipFactory\.venv`
- result: `conditional go`
- release recommendation: `ready for controlled operator rollout / UAT, not yet broad release sign-off`

## Executed Evidence Layers

### 1. Automated Regression

Executed:

- command: `python -m pytest`
- result: `105 passed`

Observed warning:

- `4` Alembic deprecation warnings about missing `path_separator=os`
- severity: `Low`

### 2. UI Smoke

Executed:

- command path: `scripts/ui_smoke_check.py`
- mode: `QT_QPA_PLATFORM=offscreen`
- result: `ui_smoke_ok=6`

### 3. Settings Audit Evidence

Referenced current-cycle focused evidence from:

- [24_Settings_UI_Audit_Execution_Report_2026-06-11.md](/F:/programming/python/MTClipFactory/doc/24_Settings_UI_Audit_Execution_Report_2026-06-11.md)

Relevant baseline confirmed in this repo state:

- widget-level settings tests are included in the `105 passed` regression baseline
- hybrid slider-plus-exact-entry controls remained covered

### 4. Scripted Full-System Workflow Audit

Executed:

- command: `python scripts/full_system_release_audit.py`

#### A. Product To Final Workflow

Observed result:

- `product_count = 1`
- `asset_count = 3`
- `ready_asset_count = 3`
- `tag_count = 1`
- hero asset tag labels included `mood:warm`
- approval guard triggered before output approval: `true`
- recipe status after full flow: `approved`
- recipe score after full flow: `0.85`
- recipe duplicate risk after full flow: `0.25`
- preview required review: `true`
- preview review signals included `low_visual_diversity`
- preview audio mode recorded as `fake_audio_mix`
- output count after final flow: `2`
- final output kind: `final`
- final output auto-approved by: `system_final_render`
- decision event history included:
  - `output_auto_approved`
  - `recipe_approved`
  - `output_approved`
  - `recipe_review_required`
- dashboard recipe count after flow: `1`
- dashboard output count after flow: `2`
- dashboard `needs_review` recipe count after final approval: `0`

Interpretation:

- the representative workflow remained truthful from product setup through final output state
- approval discipline still blocks premature recipe approval
- decision history remained append-only and understandable

#### B. Recovery And Escalation

Observed queued recovery result:

- matched jobs: `3`
- attempted jobs: `2`
- deferred jobs: `1`
- recovered job codes:
  - `queued_1`
  - `queued_2`
- deferred queued job:
  - `preview_11`

Observed failed recovery result:

- escalated failed jobs before retry: `1`
- attempted jobs: `1`
- deferred jobs: `1`
- escalated jobs: `1`
- recovered failed job code:
  - `failed_1`
- deferred and escalated job:
  - `final_08`
- operator playbook lines were present for both escalated and non-escalated failures

Interpretation:

- deferred retry ordering still prioritizes lower-risk failed work first
- escalated failed jobs remain visible instead of being silently retried
- operator guidance still matches failure context

#### C. Runtime Path Hot Reload

Observed result:

- product count before path swap: `1`
- pending changed path roots:
  - `database_path`
  - `media_root`
  - `docs_root`
  - `outputs_root`
  - `preview_root`
- applied changed path roots after reload: none
- summary reload policy: `runtime_hot_reload`
- summary restart required: `false`
- runtime and configured database paths both switched to the new database root
- runtime and configured outputs roots both switched to the new outputs root
- product count after reload: `0`

Interpretation:

- runtime hot reload still rebuilds the live service graph truthfully
- the database-root swap proved the app moved to the new active database instead of silently staying on the old one

## Coverage Assessment

### Covered Well In This Audit

- regression baseline stability
- primary window startup safety
- representative product-to-final workflow
- review-gate and approval truthfulness
- decision history visibility
- failed-job escalation ordering
- operator playbook visibility
- runtime path-root hot reload truthfulness
- settings-surface correctness via current widget baseline and focused audit evidence

### Covered By Existing Automated Baseline Rather Than Replayed Deeply In This Cycle

- product CRUD edge cases
- tag edge cases and duplicates
- asset readiness rules
- recipe duplicate-code rejection
- final-render prerequisite guards across all negative permutations
- schema migration guard behavior

### Not Fully Closed In This Audit Cycle

- real FFmpeg output quality with production-like sample media
- long-duration soak/performance behavior
- human operator UAT on a normal desktop session across all pages

## Findings

### Critical

- none

### High

- none

### Medium

1. Broad-release confidence is still limited by the absence of a real-user controlled rollout on a normal desktop workflow.
   Impact:
   - the system looks technically stable, but broad-release usability and operator discipline have not been signed off by external users yet

2. Real FFmpeg output quality was not revalidated with production-like media in this release audit cycle.
   Impact:
   - render-path business logic is covered
   - final media-quality judgment still needs a separate media-validation pass if broad release depends on it

### Low

1. Alembic emits `path_separator=os` deprecation warnings during some test paths.

## Exit Criteria Assessment

- regression passes: `yes`
- UI smoke passes: `yes`
- scripted release audit passes: `yes`
- no critical or high defect remains open: `yes`
- release recommendation recorded honestly: `yes`

## Release Recommendation

- recommendation: `conditional go`

Meaning:

- safe for controlled operator rollout, internal pilot use, and UAT-style testing
- not yet strong enough to claim broad release readiness without the next human validation step

## Why This Is Not A Full Broad-Release Go Yet

1. The audit evidence is strong on business logic, persistence, recovery, and runtime truthfulness.
2. The audit evidence is not yet strong on real-user acceptance and real-media output validation.
3. No blocking defect is open, but the remaining gaps are release-governance gaps rather than code-breakage gaps.

## Recommended Next Step

1. Let a small set of real operators use the system in a controlled rollout.
2. Capture feedback specifically on:
   - full workflow usability
   - settings ergonomics
   - output trustworthiness
3. If that pass is clean, promote the recommendation from `conditional go` to broader release readiness.
