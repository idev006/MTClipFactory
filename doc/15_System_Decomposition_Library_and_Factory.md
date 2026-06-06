# System Decomposition: Library and Factory

This document defines the required business split of the system.

## Decision

MTClipFactory is intentionally divided into two major capabilities:

1. `Resource Library Management`
2. `Video Assembly Factory`

## Resource Library Management

### Purpose

Prepare and govern reusable video components before they enter assembly workflows.

### Current Responsibilities

- product creation and maintenance
- asset intake
- file placement by convention
- metadata analysis
- tag dictionary and tag assignment
- asset readiness classification
- thumbnail/proxy generation
- searchable library views

### Owned SSOT

- product identity
- asset identity
- asset metadata
- asset tag relationships
- asset readiness state

## Video Assembly Factory

### Purpose

Compose prepared assets into reviewable preview and later final-output workflows.

### Current Responsibilities

- recipe creation
- recipe item assignment
- preview job enqueue
- preview output generation
- output approval decisions
- recipe approval / rejection decisions
- segment-aware preview composition
- final-render composition parity
- runtime voice/music mixing with manifest-visible audio evidence
- review-threshold evaluation and `needs_review` workflow routing
- configurable duck-mode orchestration for narration/music runtime mixing
- preview job status tracking
- final job status tracking
- manual retry for persisted factory jobs
- output lineage reporting
- output quality/duplicate-risk visibility
- dashboard-driven failed-job retry orchestration
- approval actor/time/reason persistence
- immutable decision-event history

### Future Responsibilities

- richer multi-layer audio-aware preview/final composition
- deeper audio-risk and emergency-fill review signals

### Owned SSOT

- recipe records
- recipe item relationships
- preview/final job state
- review decisions
- output records
- decision-event history
- review-gate evidence carried in manifests and output summaries

## Shared Core

- SQLite database
- SQLAlchemy models
- job persistence
- unit of work
- dashboard and settings aggregation
- cross-capability job visibility
- queued-job recovery orchestration
- runtime migration guard

## Ownership Rule

- `Library` may supply assets to `Factory`
- `Factory` must not silently rewrite owned library metadata
- cross-module changes must happen through explicit contracts and documented workflows

## Current Implementation Shape

```text
src/mt_clip_factory/
  domain/
  infrastructure/
  control_center/
  library/
  factory/
  presentation/
  ui/
```

## Context Diagram

```mermaid
flowchart LR
    U["User"] --> L["Resource Library Management"]
    U --> F["Video Assembly Factory"]
    U --> D["Dashboard / Settings"]
    L --> DB["Shared SQLite SSOT"]
    F --> DB
    D --> DB
    L --> FS["Media Storage"]
    F --> FS
```

## Delivery Rule

Before implementing any feature, classify it as:

- `Library`
- `Factory`
- `Shared Core`
