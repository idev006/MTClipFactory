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
- auto recover queued jobs on startup
- max recovery jobs per run

Future composition-related settings should include:

- master duration source
- voice fill mode
- background video fill mode
- background music fill mode
- duck enable/disable
- duck level and attack/release timing
- loop warning thresholds

## Reliability Principles

- state must be persisted before the system claims work exists
- background processing must appear on the dashboard as job state, not hidden side effects
- failures must become visible to operators immediately
- partial dependency failure should degrade capability, not corrupt data

## Recoverability Principles

- jobs should be retryable from persisted state
- artifact generation and preview generation should not require manual database repair after normal failures
- operators must be able to tell whether work is queued, failed, or completed from the dashboard
- automatic recovery should be policy-driven and visible, not hidden magic
- failed-job retry should remain an explicit operator decision unless a stronger policy is later designed

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
- configurable queued-job recovery orchestrator for dashboard/manual and startup execution
- dashboard-driven failed-job retry orchestration
- output approval and recipe approval decisions captured in SSOT workflow
- output lineage reporting derived from persisted jobs and outputs
- migration-backed approval actor/time/reason fields
- append-only decision-event history visible in the Recipe Builder workflow
- configurable path roots through `[paths]` in `app_config.toml`
- dashboard visibility of recent, queued, processing, and failed jobs
- settings-based FFmpeg path control
- automated tests for success and failure job paths
- restart-style retry tests for factory jobs
- queued-job orchestration tests plus startup policy coverage
- document-led composition policy for narration, music ducking, and timeline fill behavior

## Current Gaps

1. Recovery scope is still narrower for failed-job escalation and advanced orchestration rules.
2. Preview composition is still simple and not yet a full layered edit pipeline.
3. Final render is still a foundation path and not yet a full recomposition pipeline.
4. Path-root changes are not fully hot-reloaded across all runtime services.

## Composition Reliability Direction

To keep future renders trustworthy:

- narration must not auto-loop
- music may loop only under explicit policy
- music ducking decisions must be explainable and eventually visible to operators
- duration mismatch handling must be logged instead of silently hidden
