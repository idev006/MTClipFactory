# Test Execution Report 2026-06-08

This document records the executed test cycle against the current milestone-complete MTClipFactory baseline.

It follows [20_Master_Test_Plan.md](/F:/programming/python/MTClipFactory/doc/20_Master_Test_Plan.md).

## Execution Summary

- execution date: 2026-06-08
- tester role: senior QA / system tester
- scope: full regression, UI smoke, and targeted UAT-style workflow validation
- environment: `F:\programming\python\MTClipFactory`
- Python runtime: `F:\programming\python\MTClipFactory\.venv`
- result: `pass with minor warning`

## Executed Test Layers

### 1. Automated Regression

- command: `python -m pytest -q`
- result: `97 passed`
- duration observed: about `23.06s`

### 2. UI Smoke

- mode: `QT_QPA_PLATFORM=offscreen`
- result: `ui_smoke_ok=6`
- coverage intent: startup and construction sanity for the six main windows

### 3. Scripted UAT-Style Workflow Validation

Executed additional scripted checks beyond baseline pytest to simulate operator-facing workflows more directly.

#### A. Full Factory Workflow

Validated:

- product and asset preparation
- recipe creation and multi-asset assignment
- preview generation
- review-gate evidence
- output approval
- recipe approval with explicit reason
- final render generation
- output lineage and decision history

Observed result:

- preview moved recipe to `needs_review`
- final state returned to `approved`
- final output kind was `final`
- recipe score after final flow: `0.85`
- recipe duplicate risk after final flow: `0.25`
- review manifest contained `low_visual_diversity`
- runtime audio summary was present with mode `fake_audio_mix`
- decision history remained append-only and truthful

#### B. Recovery And Escalation Workflow

Validated:

- failed-job dashboard visibility
- escalated-job detection
- deferred retry ordering
- operator playbook messaging

Observed result:

- initial failed job count: `2`
- initial escalated failed job count: `1`
- manual retry attempted only the lower-risk failed job under the configured cap
- escalated job `final_08` remained deferred as designed
- operator playbook messages matched the failure context

#### C. Runtime Path-Root Hot Reload Workflow

Validated:

- settings save with changed path roots
- runtime hot reload signal emission
- runtime/configured path truthfulness after reload
- database root switch effect

Observed result:

- runtime reload signal emitted once
- dashboard policy remained `runtime_hot_reload`
- no stale changed-path residue remained after successful reload
- active database and outputs roots changed to the newly configured paths
- product count dropped from `1` to `0` after database-root switch, which correctly proved the runtime moved to the new database instead of silently staying on the old one

## Requirement Coverage Summary

### Covered Well In This Execution Cycle

- full automated regression baseline
- UI smoke baseline
- product-to-final-render happy path
- review-gate routing and approval discipline
- output lineage and decision history truthfulness
- recovery and escalation behavior
- dashboard operator guidance
- runtime path hot reload and runtime/configured path truth

### Covered By Existing Regression Baseline And Reconfirmed Indirectly

- product CRUD
- asset intake and readiness
- tag behaviors
- thumbnail/proxy job persistence
- recipe scoring propagation
- hot-reload whole-module rebind behavior

### Not Deep-Tested In This Cycle Beyond Current Baseline

- real FFmpeg media rendering quality with production-like sample media
- widget-level interaction testing beyond smoke and scripted workflow coverage
- long-duration soak or performance testing

## Findings

### No Critical Or High Severity Defects Found

- none

### Warning / Technical Debt

- automated regression produced `4` Alembic deprecation warnings:
  - `No path_separator found in configuration ... Consider adding path_separator=os to Alembic config.`
- severity assessment: `Low`
- impact: no current functional break; test cycle remained green
- recommendation: clean this warning in a future maintenance pass to keep startup/test output quieter and reduce future Alembic upgrade risk

## Exit Criteria Assessment

- full regression suite passes: `yes`
- UI smoke passes: `yes`
- no critical or high severity defect open from this cycle: `yes`
- core UAT workflows pass: `yes`
- QA summary and release recommendation recorded: `yes`

## Release Readiness Recommendation

- recommendation: `ready for UAT / operator testing`

Rationale:

- the delivered milestone baseline remained stable under full regression
- the UI still initializes cleanly
- the core factory workflow completed successfully through final render
- review, retry, and path-reload behaviors remained truthful to operators
- no blocking defect surfaced in this cycle

## Follow-Up Recommendation

1. Keep the current baseline for UAT as-is.
2. Log the Alembic `path_separator` warning cleanup as a low-priority maintenance item.
3. If UAT reveals weak operator value from recipe scoring, open the next optional scoring-calibration milestone.
