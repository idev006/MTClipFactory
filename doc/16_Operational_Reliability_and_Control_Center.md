# Operational Reliability and Control Center

## Dashboard Requirements

The dashboard is the operational truth surface for both admin and user roles.

It must show at least:

- product count
- asset count
- recipe count
- output count
- ready / needs-review asset counts
- needs-review recipe count
- tag count
- total / active / processing / failed job counts
- queued job count
- runtime dependency readiness
- workspace, database, and media paths
- FFmpeg / FFprobe paths
- operational thresholds
- review thresholds
- recent persisted jobs with enough detail for operator triage
- runtime-active and configured-next-start path roots

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
- failed-job escalation threshold
- voice loop enabled
- background music loop enabled
- music duck enabled
- music duck mode
- music duck gain
- music duck attack/release timing
- music duck threshold
- music duck ratio
- review duration mismatch threshold
- review max looped segments
- review min distinct visual assets
- review max consecutive same visual segments

Future composition-related settings should still include:

- master duration source
- voice fill mode
- background video fill mode
- background music fill mode
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
- bulk failed-job retry should prioritize lower-risk retries first and surface escalated jobs with operator guidance
- path-root activation policy should be explicit; operators must not be told a runtime root changed when the running services still use the old root

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
- persisted recovery-attempt metadata carried with jobs
- failed-job escalation threshold with deferred bulk-retry ordering
- dashboard operator playbook lines for current failed and escalated jobs
- output approval and recipe approval decisions captured in SSOT workflow
- output lineage reporting derived from persisted jobs and outputs
- migration-backed approval actor/time/reason fields
- append-only decision-event history visible in the Recipe Builder workflow
- persisted composition plans and render decisions for recipe-level duration and layer planning
- persisted timeline segments with contiguous-duration validation
- segment-aware preview manifests with chosen segment clip mapping
- segment-aware final manifests with composition-based rerender lineage
- configurable path roots through `[paths]` in `app_config.toml`
- restart-driven path-root activation with runtime/configured divergence visibility
- configurable audio policy through `[audio]` in `app_config.toml`
- dashboard visibility of recent, queued, processing, and failed jobs
- settings-based FFmpeg path control
- dashboard visibility of current narration/music loop and duck policy
- dashboard visibility of duck mode selection and compressor tuning
- runtime preview/final audio mixing with manifest-visible applied-audio evidence
- review-gate routing with persisted `needs_review` recipe state
- dashboard visibility of flagged recipe count plus configured review thresholds
- Recipe Builder visibility for manifest-backed review signals, metrics, quality score, and duplicate risk
- automated tests for success and failure job paths
- restart-style retry tests for factory jobs
- queued-job orchestration tests plus startup policy coverage
- document-led composition policy for narration, music ducking, and timeline fill behavior

## Current Gaps

1. Preview and final now share a configurable duck-engine foundation, but richer multi-layer parity and deeper polish are still incomplete.
2. Review gates now cover audio masking loss and emergency fill, but broader composition-confidence scoring is still heuristic.
3. Recovery history currently rides on persisted job payload metadata rather than a dedicated audit schema.
4. Optional path-root hot-reload remains a future backlog item if restart-driven semantics become operationally too costly.

## Composition Reliability Direction

To keep future renders trustworthy:

- narration must not auto-loop
- music may loop only under explicit policy
- music ducking decisions must be explainable and visible to operators
- duration mismatch handling must be logged instead of silently hidden
- risky visual repetition must be routed to human review instead of being silently normalized
- repeated failed-job retries must escalate visibly instead of blending into one generic failure count
