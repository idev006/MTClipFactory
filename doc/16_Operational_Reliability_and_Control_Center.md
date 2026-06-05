# Operational Reliability and Control Center

## Dashboard Requirements

The dashboard is the operational truth surface for both admin and user roles.

It must show at least:

- product count
- asset count
- recipe count
- output count
- ready / needs-review asset counts
- tag count
- total / active / processing / failed job counts
- queued job count
- runtime dependency readiness
- workspace, database, and media paths
- FFmpeg / FFprobe paths
- operational thresholds
- recent persisted jobs with enough detail for operator triage

## Settings Requirements

Settings are the current authority surface for editable runtime policy.

Current editable fields:

- database path
- media root
- docs root
- outputs root
- preview root
- FFmpeg root
- FFprobe path
- FFmpeg path
- CPU limit threshold
- RAM limit threshold
- disk free minimum
- preview worker limit
- final worker limit
- auto refresh cadence

## Reliability Principles

- state must be persisted before the system claims work exists
- background processing must appear on the dashboard as job state, not hidden side effects
- failures must become visible to operators immediately
- partial dependency failure should degrade capability, not corrupt data

## Recoverability Principles

- jobs should be retryable from persisted state
- artifact generation and preview generation should not require manual database repair after normal failures
- operators must be able to tell whether work is queued, failed, or completed from the dashboard

## Durability Principles

- asset files and generated artifacts live in filesystem storage
- metadata and job state live in SQLite
- operational settings live in `app_config.toml`

## No-Hardcode Rule

The following must flow through config or services whenever user control is appropriate:

- runtime tool paths
- operational thresholds
- worker limits
- refresh cadence
- path roots that the operator may need to relocate

## Current Reliability Baseline

- persisted artifact jobs for thumbnail/proxy generation
- persisted preview jobs for recipe preview outputs
- persisted final-render jobs for recipe final-output foundation
- uniform manual retry across artifact, preview, and final persisted jobs
- output approval and recipe approval decisions captured in SSOT workflow
- configurable path roots through `[paths]` in `app_config.toml`
- dashboard visibility of recent, queued, processing, and failed jobs
- settings-based FFmpeg path control
- automated tests for success and failure job paths
- restart-style retry tests for factory jobs

## Current Gaps

1. Automatic resume/orchestration after restart is not yet implemented.
2. Preview composition is still simple and not yet a full layered edit pipeline.
3. Final render is still a foundation path and not yet a full recomposition pipeline.
4. Path-root changes are not fully hot-reloaded across all runtime services.
