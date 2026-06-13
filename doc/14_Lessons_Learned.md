# Lessons Learned

## LL-001 | 2026-06-05 | Document-First Helped

- locking `.venv`, `.md`, `.toml`, SSOT, UML, Kanban, and issue logging early reduced project ambiguity
- documentation quality directly improved implementation speed because the repo now has stable decision memory

## LL-002 | 2026-06-05 | Split By Business Capability

- separating `Resource Library Management` from `Video Assembly Factory` is more useful than splitting by screens alone
- shared core plus separate workflows kept the codebase cohesive without needing multiple repositories yet

## LL-003 | 2026-06-05 | Testability Paid Off

- keeping service seams around metadata analysis, asset generation, and preview generation made it easy to add new pytest coverage quickly
- the project now benefits from fast in-memory repository tests and focused view model tests

## LL-004 | 2026-06-05 | Persisted Jobs Improve Truthfulness

- once artifact and preview work are represented as persisted jobs, dashboard reporting becomes much more honest
- queued and failed counts are more useful than silent background actions

## LL-005 | 2026-06-05 | Preview Build Is Not Approval

- generating a preview artifact is a processing milestone, not a business approval decision
- workflow states must reflect reality or the dashboard will mislead operators

## LL-006 | 2026-06-05 | Circular Imports Are Architectural Signals

- the circular import found between control-center and artifact code exposed an unhealthy runtime dependency shape
- solving it with type-only imports kept the design cleaner and improved test collection stability

## LL-007 | 2026-06-05 | No-Hardcode Needs Constant Enforcement

- moving operational thresholds into `app_config.toml` was a good step, but path configuration is still not complete
- the team should treat remaining implicit defaults as active debt, not “good enough”

## LL-008 | 2026-06-06 | Path Config Must Be Explicit

- once path roots became first-class config, the dashboard and settings language also had to change from “runtime” to “configured” to stay truthful
- admin-facing controls are only useful when the system explains whether a change applies immediately or after restart

## LL-009 | 2026-06-06 | Output Records Matter

- writing a preview file alone is not enough; registering an output record makes reporting and product-level counts much more useful
- if work produces value, that value should usually enter the SSOT instead of living only on disk

## LL-010 | 2026-06-06 | Review Needs Explicit State

- “preview exists” and “content is approved” are different truths and should never be collapsed into one status
- separating output approval from recipe approval made the workflow much easier to explain and test

## LL-011 | 2026-06-06 | Final Render Can Start As Promotion Foundation

- a first final-render slice does not need full composition logic if it creates traceable value and preserves a clean seam for deeper rendering later
- promoting from an approved preview output gave us a safe bridge toward richer render orchestration without inventing hidden state

## LL-012 | 2026-06-06 | One Job Surface Improves Honesty

- once library and factory jobs share one dashboard surface, operators stop guessing where work is stuck
- a unified job vocabulary also makes retry behavior easier to explain, test, and document

## LL-013 | 2026-06-06 | Recovery Should Start Narrow And Truthful

- automatic recovery is safer when it begins with queued work only and leaves failed work under explicit human control
- putting recovery policy behind settings keeps the system durable without hiding side effects from operators

## LL-014 | 2026-06-06 | Reporting Can Get Better Before Schema Changes

- output reporting gained real value by correlating persisted output records with job payloads instead of waiting for a full audit-schema redesign
- deriving lineage from existing SSOT is safer than pretending approval history exists when it does not

## LL-015 | 2026-06-06 | Failed Recovery Should Stay Explicit

- allowing dashboard-driven failed-job retry improves operator control without silently re-running risky work at startup
- separating queued auto-recovery from failed manual retry keeps reliability policy easier to explain and trust

## LL-016 | 2026-06-06 | Schema Features Need Runtime Migration, Not Just Models

- once approval audit moved into persisted fields, Alembic had to become part of the real startup path instead of a document-only promise
- shipping schema changes without runtime upgrade support would have created a false sense of completeness

## LL-017 | 2026-06-06 | Immutable Audit Needs Its Own Ledger

- overwritten status fields help with the latest state, but they do not preserve review history well enough for operator trust
- adding an append-only `decision_events` ledger created a cleaner seam for UI history, testing, and future governance rules

## LL-018 | 2026-06-06 | Revision Checkpoints Prevent SSOT Drift

- once multiple milestones land quickly, docs can become misleading even when code is correct
- treating architecture/process review as a mandatory delivery checkpoint keeps project management artifacts useful instead of ceremonial

## LL-019 | 2026-06-06 | Composition Rules Need To Be Written Before They Are Automated

- render systems become untrustworthy quickly when looping, trimming, and filling behavior are left implicit
- locking timeline, narration, and music policy in the documents first reduces the chance of building a clever but wrong editor

## LL-020 | 2026-06-06 | Audio Priority Must Stay Human-Centric

- narration usually carries the selling message, so it should remain the foreground truth layer
- looping music is usually acceptable, but looping narration is usually not

## LL-021 | 2026-06-06 | Broad Roadmaps Need Execution Milestones

- once composition scope became more concrete, the phase-level roadmap was no longer detailed enough to guide implementation safely
- splitting strategy from execution helps the team preserve direction while still writing code in a disciplined order

## LL-022 | 2026-06-06 | Small Persistent Planning Seams Reduce Render Risk

- locking a minimal `composition_plan` and `render_decision` seam before deeper preview/final work makes later render behavior easier to test honestly
- when planning state is persisted early, Kanban, issues, UML, tests, and services can all move together instead of drifting around hidden assumptions

## LL-023 | 2026-06-06 | Segment Validation Should Arrive With Segment Persistence

- once timeline segments become real persisted data, coverage rules like contiguous timing and full-duration closure should be validated immediately
- delaying validation would make preview composition harder to trust because broken planning data could survive into later milestones

## LL-024 | 2026-06-06 | Preview Composition Needs Inspectable Manifests

- once preview composition stops being a simple file pass-through, the chosen segment order and clip mapping should be written somewhere operators can inspect
- manifest visibility is a practical bridge while richer dashboard and UI surfaces are still being built

## LL-025 | 2026-06-06 | Final Parity Needs A Corruption-Proof Test

- proving final render parity is easier when a test deliberately corrupts the approved preview file and confirms final render still rebuilds from the composition plan
- parity claims are much stronger when the test would fail under preview-promotion shortcuts

## LL-026 | 2026-06-06 | Audio Policy Should Land In Settings Before Runtime DSP

- moving loop/duck policy into `.toml`, dashboard, and factory inspection first makes the team’s intent visible and testable before deeper FFmpeg audio work begins
- separating policy visibility from runtime mix application keeps project status more honest than claiming full ducking support too early

## LL-027 | 2026-06-06 | Runtime Audio Mix Needs Its Own Evidence Surface

- once preview/final renderers started applying voice/music mixing for real, the manifest became the simplest trustworthy place to expose what ducking policy was actually applied
- operator visibility is much stronger when the UI can read runtime audio evidence instead of only showing planned composition metadata

## LL-028 | 2026-06-06 | Review Gates Must Explain Themselves

- a `needs_review` state is much more trustworthy when the system also shows the exact trigger signals, thresholds, and quality/risk summary instead of only a red flag
- review automation should route work toward humans, not pretend it replaced human judgment

## LL-029 | 2026-06-06 | Audio Quality Improvements Need Configurable Migration Paths

- moving straight from one duck strategy to another would have been risky; keeping a supported fallback mode made the audio upgrade safer and easier to verify
- when production quality improves, the dashboard, settings UI, manifests, and tests all need to move together or operators lose trust in what “applied policy” really means

## LL-030 | 2026-06-06 | Recovery Escalation Should Reuse SSOT Before Inventing New Tables

- persisted recovery history became much easier to ship once the team treated job payload metadata as a practical SSOT seam instead of blocking on a larger schema redesign
- bulk failed-job retry is more trustworthy when escalated jobs are surfaced explicitly and lower-risk retries use the limited recovery slots first

## LL-031 | 2026-06-06 | Path Config Truth Matters More Than Half-Hot-Reload

- once multiple services are wired with path roots at startup, pretending they hot-reload would be less honest than explicitly exposing runtime-active paths alongside configured next-start paths
- restart-driven policy becomes much easier for operators to trust when the dashboard says exactly which path roots are pending and which ones are currently active

## LL-032 | 2026-06-06 | Review Signals Need Runtime Evidence

- audio-risk review rules became much more trustworthy once the review gate waited for renderer audio evidence instead of inferring masking risk only from planning intent
- duration-unknown fill paths are worth surfacing as first-class review evidence because fallback behavior is operationally important even when a render technically succeeds

## LL-033 | 2026-06-06 | Ducking Alone Is Not Enough Mix Control

- once duck-mode quality improved, the next reliability gap was simple layer balance: a voice-priority system still needs explicit voice/music gain staging instead of assuming a flat 1:1 final mix
- exposing mix gains through settings, dashboard, and manifest evidence keeps audio polish operator-visible instead of hiding it inside FFmpeg command details

## LL-034 | 2026-06-06 | Payload-Backed Audit Can Be A Deliberate End State

- recovery metadata proved valuable because it stayed attached to the job records operators already inspect, rather than waiting for a separate audit table before shipping visibility
- a dedicated schema should be triggered by real cross-job reporting or governance needs, not by discomfort with JSON alone

## LL-035 | 2026-06-06 | Scoring Gets Better When It Reuses Runtime Evidence

- recipe-level scoring became more useful once it stopped being only metadata math and started reusing the same asset diversity and runtime review evidence the operators already trust elsewhere
- a score is easier to defend operationally when the UI can show both the summary number and the underlying duplicate-risk context instead of hiding the heuristic behind one badge

## LL-036 | 2026-06-06 | Whole-Module Rebind Is Safer Than Partial Path Mutation

- once path roots affect the database engine, asset storage, preview manifests, and output renderers together, hot reload is safer when the app rebuilds one coherent runtime module instead of mutating each service in place
- proxy-swapping the live service set kept runtime hot reload truthful because view models could keep their references while new path-root dependent dependencies took effect together

## LL-037 | 2026-06-12 | Theme Assets Need A Real Loading Seam

- once inline stylesheet strings were declared off-limits, the practical next step was not a bigger widget rewrite but a small package-backed theme loader that can scale to other windows
- moving QSS into versioned assets plus pytest coverage keeps UI polish reusable without burying styling policy inside Python window classes

## LL-038 | 2026-06-12 | Shared Base Themes Beat One-Off Window Styling

- once the theme seam existed, the highest-value next step was a shared app-window baseline for dashboard, library, and factory screens instead of inventing disconnected per-window styles immediately
- centralized base themes reduce UI drift and make future visual tuning cheaper because common controls can move together through one asset seam

## LL-039 | 2026-06-12 | Buttons Need Explicit Affordance, Not Just Color

- once the shared theme existed, button clarity improved most when the theme added visible depth, hover contrast, and a pressed state instead of relying on flat color blocks alone
- action-heavy operator tools benefit from buttons that look tactile enough to distinguish command surfaces from passive panels at a glance
- that affordance still needs restraint: smaller buttons with theme-matched contrast can communicate clickability better than oversized controls that overpower the surrounding layout

## LL-040 | 2026-06-13 | First Controlled UAT Should Prove One Real Outcome, Then Widen Coverage

- the first controlled operator run created more trust by producing one real final output end to end than by adding more synthetic checks alone
- once that first real output exists, the next most valuable UAT step is broader media coverage, especially distinct visuals plus voice/music, rather than repeating the same narrow data set

## LL-041 | 2026-06-13 | Stronger Media Sets Improve Review Truth And Confidence Together

- once the richer-media UAT run added a second distinct foreground visual plus voice and music, the same workflow moved from `needs_review` into a clean no-review-gate result without needing hidden rule changes
- this suggests operator confidence improves most when media coverage improves first, while the review gate stays stable and honest

## LL-042 | 2026-06-13 | Automation Slices Need A Factory Operating Model Before Scale-Out

- once the project gained batch planning, folder intake, and batch preview automation, the main architectural gap stopped being one missing feature and became the lack of one factory-grade operating model
- documenting control plane, execution plane, state plane, and operator plane before distributed worker work begins is cheaper and safer than scaling local automation seams blindly
