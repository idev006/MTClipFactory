# Implementation Architecture

## Target Stack

- Python 3.12 only
- SQLite for the current local source of truth
- SQLAlchemy 2.x as ORM
- Alembic for schema migration
- PySide6 for desktop UI
- pytest for automated verification
- MVVM for presentation structure

## Architectural Layers

### Domain

Holds entities, enums, business invariants, domain policies, and protocols that should not depend on frameworks.

### Application

Holds use cases and application services such as product CRUD, asset intake, preview orchestration, approval flow, and factory automation.

### Infrastructure

Holds implementations for database access, filesystem storage, FFmpeg and FFprobe adapters, repositories, and unit-of-work wiring.

### Presentation

Holds view models that coordinate UI input and application services without embedding heavy business rules.

### UI

Holds windows, dialogs, widgets, and reusable theme assets.

Rules:

- packaged QSS theme assets should be loaded through dedicated theme helpers instead of inline stylesheet strings
- common dashboard, library, and factory surfaces should share one app-window theme baseline unless a screen has a justified local override

### Control Center

Holds dashboard, settings, and system-level orchestration visibility.

## System Modules

The business architecture is intentionally split into two major modules that share one domain and infrastructure base.

### Resource Library Management Module

Responsibilities:

- product setup
- asset lifecycle before production use
- metadata analysis
- tags
- thumbnails and proxies
- readiness state

### Video Assembly Factory Module

Responsibilities:

- recipe lifecycle
- preview and final workflow orchestration
- quality gate, approval, and output tracking
- production-order planning for automation
- internal recipe generation for factory-style runs
- folder-driven batch intake from `product.toml` and `pipeline.toml`
- batch preview orchestration up to the review boundary

## Shared Core

Both `Library` and `Factory` share:

- domain model
- SQLite schema
- identity and naming rules
- audit and traceability rules
- decision-event ledger
- dashboard and settings authority services

## Timeline-Driven Composition Rule

Render architecture must remain timeline-driven rather than simple file stitching.

Current implemented baseline includes:

- persisted `composition_plans`
- persisted `timeline_segments`
- persisted `render_decisions`
- segment-aware preview and final composition
- manifest-visible audio and visual evidence
- review-gate evidence
- recipe score and duplicate-risk persistence

Composition guardrails:

- narration does not auto-loop
- background music may loop under explicit policy
- music ducks while narration is active
- loop, trim, freeze, and duck decisions must remain operator-visible

## Control Center Architecture Rule

- `Dashboard` is the primary operational truth surface
- `Dashboard` must aggregate from service seams, not query the database directly from UI code
- `Settings` must persist through services and remain the authority surface for editable runtime policy
- runtime paths and operational thresholds must flow through the same central configuration model

## MVVM Rules

- views collect input and render state
- view models call injected services
- view models do not write SQL or manage transactions directly
- domain and application logic must stay testable without opening the UI

## Testability Seams

- repositories should be injected through protocols or explicit constructors
- unit of work should be injected through factories
- IO-heavy services should stay behind narrow abstractions
- infrastructure should remain replaceable with fake or in-memory adapters in pytest

## Documentation And Modeling Rules

- project documents must remain `.md`
- new config files must remain `.toml`
- non-trivial architecture and workflow changes must be reflected in Mermaid-backed UML
- document conversion and file-text extraction should use `markitdown` by default when such conversion is needed

## Revision Checkpoint Rule

- every milestone ends with a revision checkpoint across docs, architecture notes, Kanban, issues, and lessons learned
- if the checkpoint reveals drift, documents are corrected before the milestone is claimed complete

## Planned Evolution

The current architecture intentionally leaves room to evolve from a local desktop baseline into a stronger factory deployment:

- SQLite to PostgreSQL when multi-node state demands justify it
- local workers to distributed workers
- local filesystem assumptions to shared-storage abstractions
- one desktop shell to separated service and worker processes when needed

## Enterprise Factory Re-Baseline

The next architecture step is to treat MTClipFactory as a four-plane production system:

- `Control Plane`: production-order intake, orchestration, scheduling, retry, escalation, and policy
- `Execution Plane`: worker classes for intake, analysis, planning, preview, final, packaging, and archive work
- `State Plane`: durable SSOT for products, assets, recipes, jobs, outputs, lineage, leases, and approvals
- `Operator Plane`: manual authoring, review queues, dashboard, settings, and override tools

Before multi-node scaling is implemented, the following rules are now locked:

- queueable work must have one documented job state machine
- worker claims must use a lease or equivalent ownership rule
- repeated execution must be made safe through idempotency rules
- manual mode and automated mode are both first-class operating modes
- automation must not cross human approval boundaries silently
