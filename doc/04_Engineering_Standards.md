# Engineering Standards

## Source Layout

- `src/mt_clip_factory/domain`
- `src/mt_clip_factory/application`
- `src/mt_clip_factory/control_center`
- `src/mt_clip_factory/infrastructure`
- `src/mt_clip_factory/presentation`
- `src/mt_clip_factory/ui`
- `src/mt_clip_factory/library`
- `src/mt_clip_factory/factory`
- `tests`
- `doc`

## File Format Standards

- project documentation must use `.md`
- new config files must use `.toml`
- diagrams may live inside `.md` files by using Mermaid
- avoid introducing multiple config formats unless there is a strong reason
- runtime tool paths such as FFmpeg and FFprobe must be resolved through the central `.toml` project config
- document-to-Markdown conversion and file-text extraction should use `markitdown` as the project default unless a specific workflow requires another tool

## Coding Rules

- use the `src/` layout consistently
- use type hints in public APIs
- write classes and functions with explicit dependencies that can be injected
- avoid global mutable state
- separate pure logic from IO as much as possible
- prefer simple dataclasses or clear domain models in the domain layer
- keep `Library` and `Factory` use cases in clearly separated modules
- do not duplicate the same business rule across modules without a shared abstraction
- do not hardcode operational values, runtime paths, thresholds, or policy defaults when those values should be configurable

## Composition Rules

- future composition logic must resolve one master timeline per render
- narration must not be auto-looped
- background music may loop only through explicit policy
- ducking, trim, freeze, and loop decisions must be operator-visible and testable

## Database Rules

- immutable review or approval history must be stored as append-only records, not only overwritten status fields
- do not edit production schema state manually
- every schema change must include an Alembic migration
- SQLite is the workflow source of truth in the current architecture

## UI Rules

- stylesheet rules must live in reusable theme assets or theme-loading seams, not inline inside window or widget code
- UI components must not make domain decisions on their own
- UI must display operational state from the view model
- long-running work must stay off the main thread
- the dashboard must remain an operational summary that can be understood quickly
- the settings UI must work through services and persist changes explicitly

## Change Design Rules

- every non-trivial implementation should begin with a sequence-diagram draft that describes the intended runtime flow before code is changed
- the sequence diagram should be analyzed against SSOT, existing architecture seams, failure paths, and testability before implementation starts
- implementation should begin only after the sequence-level workflow is coherent enough that the team is confident the change fits the system correctly
- when the workflow changes materially, the verified sequence diagram must be reflected in the UML SSOT

## Logging And Errors

- every use case must return understandable errors
- every background job must expose queryable status
- every failure path should be designed for recovery when feasible

## Project Management Standards

- every milestone must include a revision checkpoint that re-validates docs, architecture, process, and project status before merge
- maintain the central project Kanban
- keep a status report that the team can read quickly to understand the whole project state
- keep an issue log for problems, risks, and blockers
- keep a lessons-learned log for important milestone or incident takeaways

## Reliability Standards

- every component should have a clear responsibility and be replaceable
- important state must have persistence or another explicit source of truth
- config and runtime dependencies must be inspectable from the dashboard
- when a key dependency is unavailable, the system should degrade gracefully as far as practical
