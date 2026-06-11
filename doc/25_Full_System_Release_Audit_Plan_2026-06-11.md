# Full System Release Audit Plan 2026-06-11

This document is the execution-ready release audit plan for the current MTClipFactory baseline.

It builds on [20_Master_Test_Plan.md](/F:/programming/python/MTClipFactory/doc/20_Master_Test_Plan.md), [21_Test_Execution_Report_2026-06-08.md](/F:/programming/python/MTClipFactory/doc/21_Test_Execution_Report_2026-06-08.md), and [24_Settings_UI_Audit_Execution_Report_2026-06-11.md](/F:/programming/python/MTClipFactory/doc/24_Settings_UI_Audit_Execution_Report_2026-06-11.md).

## Audit Goal

- decide whether the current system is safe to hand to additional users
- verify the latest baseline still behaves truthfully across the main product, factory, dashboard, and settings surfaces
- combine automated regression evidence with fresh current-cycle scripted workflow evidence
- produce a release recommendation as `go`, `conditional go`, or `no-go`

## Scope

### In Scope

- automated regression baseline
- UI smoke baseline
- settings-surface audit evidence
- product-to-preview-to-final workflow
- approval guard and decision history
- recovery and escalation behavior
- runtime path-root hot reload behavior
- dashboard truthfulness for the above flows

### Out Of Scope

- production-like media quality benchmarking with real rendered deliverables
- long-duration soak or memory-leak testing
- multi-user concurrency at scale
- formal accessibility certification

## Release Questions To Answer

1. Does the system still pass its automated baseline?
2. Do the six primary windows still initialize safely?
3. Can one representative workflow go from product intake to final render state?
4. Are review gates, approvals, and lineage still truthful?
5. Do recovery and escalation controls still behave as documented?
6. Does runtime hot reload still swap path-root dependent services truthfully?
7. Is there any open `Critical` or `High` defect that should block broader use?

## Evidence Layers

### 1. Automated Regression

- run `python -m pytest`
- expected result: full green baseline

### 2. UI Smoke

- run `scripts/ui_smoke_check.py` with `QT_QPA_PLATFORM=offscreen`
- expected result: `ui_smoke_ok=6`

### 3. Focused Settings Evidence

- reuse the latest settings audit report plus the current widget-level baseline
- expected result: grouped controls, hybrid exact-entry behavior, and persistence truth remain green

### 4. Scripted Full-System Workflow Audit

- run `python scripts/full_system_release_audit.py`
- expected result:
  - happy-path factory workflow succeeds
  - approval guard blocks premature recipe approval
  - final output is produced through the final-render path
  - recovery and escalation ordering remain truthful
  - runtime hot reload changes active path roots without stale runtime state

## Risk Focus

### High-Risk Functional Areas

- approval state truthfulness
- failed-job escalation and deferral
- runtime/configured path-root divergence
- settings persistence influencing runtime behavior

### Residual Non-Blocking Risks To Watch

- operator ergonomics and preference in the redesigned settings UI
- lack of real-media mastering validation in this cycle
- low-priority Alembic warning noise during some test paths

## Environment

- workspace: `F:\programming\python\MTClipFactory`
- Python runtime: `F:\programming\python\MTClipFactory\.venv`
- Python version: `3.12.4`
- configuration source: `app_config.toml`
- FFmpeg configured at:
  - `F:\ffmpeg\bin\ffprobe.exe`
  - `F:\ffmpeg\bin\ffmpeg.exe`

## Exit Criteria

- `python -m pytest` passes
- `ui_smoke_ok=6` passes
- scripted release audit completes successfully
- no open `Critical` or `High` defect remains from the audit cycle
- release recommendation is recorded honestly with residual risks called out

## Decision Model

- `Go`: safe for broader release, no blocking or material residual concerns
- `Conditional Go`: safe for controlled rollout or UAT, but some non-blocking coverage gaps or usability validation remain
- `No-Go`: one or more blocking functional issues or release-level unknowns remain
