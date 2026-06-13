# Master Test Plan

This document is the execution-ready master test plan for MTClipFactory.

It complements [07_Testing_Strategy.md](/F:/programming/python/MTClipFactory/doc/07_Testing_Strategy.md), which defines the long-lived testing direction and baseline coverage.

## Purpose

- define one practical test plan for milestone-complete system validation
- align engineering, QA, PM, and operator acceptance around the same test scope
- reduce release risk across `Resource Library Management`, `Video Assembly Factory`, and `Dashboard / Settings`

## Test Objectives

- verify that all delivered milestone behavior works as documented
- verify that core workflows are usable end to end
- verify that persisted state, review logic, retry logic, and runtime path reload remain truthful to operators
- detect regressions before UAT and release recommendation

## In-Scope Test Areas

### Resource Library Management

- product creation, update, and deletion rules
- asset intake and metadata analysis
- asset readiness classification
- asset rename/delete maintenance rules
- referenced-asset retire/purge workflow and reference visibility
- recipe-safe asset replacement workflow with approval-safety guards
- tag creation, assignment, and filtering
- thumbnail and proxy generation jobs

### Video Assembly Factory

- recipe creation and item assignment
- preview job flow
- final render flow
- target-ratio visual normalization across mixed source sizes
- output lineage reporting
- review gate and approval workflow
- decision history and audit fields
- recipe scoring and duplicate-risk visibility

### Dashboard And Settings

- dashboard summary accuracy
- recent-job, failed-job, and escalated-job visibility
- recovery actions and operator playbook guidance
- settings persistence through `.toml`
- exact preview/final output resolution settings through the operator UI
- runtime path-root hot reload behavior

### Shared Reliability Surfaces

- migration guard behavior
- persisted jobs and retry flows
- runtime/configured path truthfulness
- filesystem-path safety across media, preview, and outputs roots

## Out-Of-Scope

- distributed-worker scale testing
- multi-user concurrency testing at enterprise scale
- media-quality benchmarking for production mastering
- external infrastructure HA/DR testing beyond the local desktop architecture

## Test Levels

### 1. Smoke Testing

- application startup sanity
- import and instantiate all six primary windows
- confirm no immediate crash in default workspace

### 2. Automated Regression Testing

- run `python -m pytest` inside `F:\programming\python\MTClipFactory\.venv`
- verify the current baseline stays green
- investigate any failure before manual UAT starts

### 3. Integration Workflow Testing

- validate cross-service flows using temporary filesystem roots and persisted state
- confirm repository, unit-of-work, and job flows behave consistently

### 4. Manual Functional Testing

- validate operator-facing workflows through the UI
- confirm data shown in screens matches persisted state and manifests

### 5. Exploratory / Risk-Based Testing

- focus on path hot reload, review gates, recovery, audio-policy visibility, and preview/final parity

## Environment

- workspace root: `F:\programming\python\MTClipFactory`
- Python runtime: `F:\programming\python\MTClipFactory\.venv`
- Python version: `3.12`
- database: SQLite
- configuration source of truth: `app_config.toml`
- UI smoke mode: `QT_QPA_PLATFORM=offscreen`

## Entry Criteria

- latest code is available in the working tree to be tested
- repo is in a known state and dependencies install successfully in `.venv`
- required docs remain aligned with the delivered baseline
- FFmpeg / FFprobe paths are configured for the chosen test environment when render workflows are included

## Exit Criteria

- full regression suite passes
- UI smoke passes
- no `Critical` or `High` severity defect remains open
- all core UAT workflows pass or have approved workaround notes
- QA summary and release recommendation are recorded

## Test Data Strategy

### Core Data Set

- one or more products
- ready visual asset set
- voiceover asset
- background music asset
- representative tags and category labels

### Edge Data Set

- missing or invalid source file path
- recipe with no items
- voice-only recipe
- repeated single-asset recipe
- failed jobs with different failure-streak counts
- alternate database/media/output roots for hot-reload validation

## Functional Test Matrix

### A. Product And Asset Flow

1. Create product with valid data.
2. Reject duplicate product code.
3. Register asset to the correct product.
4. Confirm metadata and readiness fields are populated.
5. Create and assign tags.
6. Generate thumbnail and proxy jobs.
7. Retry failed artifact jobs and confirm dashboard reflects the outcome.
8. Rename an existing asset code and confirm the primary/artifact file paths remain aligned.
9. Attempt to delete an asset that is already referenced by a recipe item or artifact job and confirm the UI blocks it truthfully.
10. Retire a referenced asset and confirm it no longer participates in active recipe attachment.
11. Purge a retired asset's media files and confirm the record remains visible for historical truth.
12. Inspect an asset's reference report and confirm recipe/job usage is visible before destructive maintenance decisions.
13. Replace a referenced asset in affected recipes and confirm the item references move to the selected ready replacement asset.
14. Confirm affected recipes require a newly approved output after asset replacement before recipe approval can happen again.
15. Confirm Recipe Builder marks older pre-replacement outputs as historical-only and shows the next rebuild/approval action in-screen.

### B. Recipe And Preview Flow

1. Create recipe with valid metadata.
2. Attach valid ready assets to the recipe.
3. Confirm recipe score and duplicate risk update.
4. Build preview.
5. Confirm output record, manifest, and dashboard counts update.
6. Validate preview output dimensions follow the selected recipe `Target Ratio` even when attached visual assets use different source ratios.
7. Validate preview manifest contains composition and review evidence.
8. Validate a recipe with both `background_video` and `foreground_video` writes layered segment evidence instead of flattening to one visual choice only.
9. Validate a likely green-screen foreground is keyed over the background layer and that manifest evidence records the applied composite mode.

### C. Review And Approval Flow

1. Force a `needs_review` case.
2. Confirm manifest review signals and metrics are visible.
3. Approve preview output.
4. Confirm flagged recipe requires explicit approval reason.
5. Reject and then approve recipe in separate test cases.
6. Verify immutable decision history is complete and ordered correctly.

### D. Final Render Flow

1. Approve recipe prerequisites.
2. Build final render.
3. Confirm final output lineage is truthful.
4. Confirm final render follows composition behavior rather than blindly promoting preview bytes.

### E. Recovery And Escalation Flow

1. Queue artifact and factory jobs.
2. Recover queued jobs through the dashboard.
3. Simulate failed jobs.
4. Retry failed jobs.
5. Verify escalated jobs are deferred according to policy.
6. Verify operator playbook lines match the failure context.

### F. Settings And Path Reload Flow

1. Save updated path roots.
2. Verify `.toml` persistence.
3. Confirm runtime hot reload applies new roots in the desktop app.
4. Confirm dashboard path surfaces show active and configured roots truthfully.
5. Confirm view models continue working after runtime reload.
6. Set exact preview/final output resolutions and confirm generated outputs use the configured frame.

### G. Reporting And Operator Visibility

1. Verify dashboard counts after each major workflow.
2. Verify Recipe Builder output details.
3. Verify Recipe Builder recipe-list score/risk visibility.
4. Verify settings feedback messaging matches actual reload policy.

## Negative Test Coverage

- invalid product or recipe identifiers
- duplicate recipe code
- asset assigned across the wrong product boundary
- non-ready asset assignment
- preview build with no items
- preview/final build with no renderable visual assets
- recipe approval without approved output
- flagged recipe approval without reason
- bad runtime paths or missing dependency executables

## Non-Functional Focus

### Reliability

- repeated retry behavior remains deterministic
- persisted state survives service recreation
- runtime reload does not silently leave old path roots active
- asset maintenance does not orphan media files or silently delete referenced assets
- retired/purged asset behavior remains truthful about what was removed from disk versus what remains in history
- replaced-asset workflows do not allow stale pre-replacement outputs to be re-approved as evidence for the changed recipe

### Usability

- operator-facing feedback is understandable
- dashboard attention text highlights real operational risk
- key review and scoring data are visible without database inspection
- recipe ratio handling stays understandable when source clips do not match each other

### Performance Observation

- UI remains responsive during normal workflow usage
- preview/final test runs complete within reasonable local expectations

## Defect Severity Model

### Critical

- application cannot start
- persistent data corruption
- wrong database/media/output root used after save/reload
- core preview/final workflow unusable

### High

- approval or review logic produces incorrect business state
- retry/recovery policy behaves incorrectly
- output lineage or audit history is materially wrong

### Medium

- UI shows incorrect score/risk or dashboard counts while backend state is correct
- hot reload feedback is misleading but recoverable
- manifest evidence is incomplete for operator triage

### Low

- cosmetic issues
- wording or layout issues that do not affect business outcome

## Execution Order

1. Smoke tests
2. Full automated regression
3. Resource Library functional pass
4. Factory preview/review pass
5. Final render and lineage pass
6. Recovery and escalation pass
7. Settings and hot-reload pass
8. Exploratory testing on high-risk seams
9. Defect re-test and regression confirmation

## Evidence To Capture

- pytest result summary
- UI smoke result
- screenshots for key UI flows when needed
- sample preview/final manifest files
- defect log with severity and reproduction steps
- release recommendation summary

## Roles And Responsibilities

- Engineering: fix defects, maintain automated coverage, and preserve SSOT alignment
- QA / Tester: execute this plan, record evidence, classify defects, and recommend release readiness
- PM / Operator Reviewer: validate workflow acceptance and business usability

## Suggested UAT Gate

System is recommended for UAT when:

- automated regression is green
- dashboard and settings reflect truthful runtime state
- one full product-to-final-render walkthrough passes
- one failed-job recovery walkthrough passes
- one path-root hot-reload walkthrough passes

## Maintenance Rule

- update this document when major workflow scope, delivery baseline, or acceptance expectations change
- keep this plan aligned with [07_Testing_Strategy.md](/F:/programming/python/MTClipFactory/doc/07_Testing_Strategy.md), [11_Project_Status_Report.md](/F:/programming/python/MTClipFactory/doc/11_Project_Status_Report.md), and [19_Implementation_Roadmap.md](/F:/programming/python/MTClipFactory/doc/19_Implementation_Roadmap.md)
