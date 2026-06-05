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
- queued job count
- failed job count
- runtime dependency readiness
- workspace, database, and media paths
- FFmpeg / FFprobe paths
- operational thresholds

## Settings Requirements

Settings are the current authority surface for editable runtime policy.

Current editable fields:

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
- persisted preview jobs for recipe preview manifests
- dashboard visibility of queued and failed jobs
- settings-based FFmpeg path control
- automated tests for success and failure job paths

## Current Gaps

1. Preview jobs currently create manifests, not final preview videos.
2. Recovery policy is not yet unified across all job types.
3. Path-root configurability is still incomplete.
4. Dashboard does not yet show detailed alert history, only summary counts.
