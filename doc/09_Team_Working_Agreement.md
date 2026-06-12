# Team Working Agreement

## Shared Rules

- use Python only from `F:\programming\python\MTClipFactory\.venv`
- activate `.venv` before installing packages or running Python commands
- official project documents must live in `doc` and use `.md`
- if a new config file is required, use `.toml`
- if work requires converting documents to Markdown or extracting readable text from files, use `markitdown` by default
- `doc/00_Document_Index.md` is the SSOT index for project documents
- important architecture or workflow changes must be reflected in UML and may use Mermaid
- update documents in `doc` whenever behavior, workflow, or structure changes
- do not merge code without appropriate test coverage
- do not place business logic directly in the UI
- do not add new inline `setStyleSheet(...)` UI styling in window or widget code; move styling into reusable theme files or a dedicated theme-loading layer
- do not modify the database manually outside Alembic
- update `Kanban`, `Project Status`, `Issues Log`, and `Lessons Learned` when the work materially changes project state

## Delivery Checklist

1. documentation is updated
2. related UML and diagrams are updated
3. code still matches the architecture
4. related tests exist
5. tests pass in `.venv`
6. Kanban and project status reflect the latest state
7. issues and lessons learned are recorded when there is meaningful new information
8. the implementation still leaves a clean path for future extension
9. an architecture/process review checkpoint is completed when the milestone changes workflow, persistence, or delivery policy

## Decision Rule

For composition behavior specifically:

- follow [18_Composition_and_Timeline_Policy.md](/F:/programming/python/MTClipFactory/doc/18_Composition_and_Timeline_Policy.md)
- do not implement silent loop, trim, or duck behavior that is not described in SSOT

If code and documents disagree, treat the implementation as incomplete until code and SSOT are realigned.

## Project Manager Cadence

- every milestone must include a revision checkpoint for architecture, process, and SSOT docs before commit/push
- every work slice should leave a clear owner and next step in the progress documents
- if a blocker appears, reflect it in the issue log and Kanban in the same work loop
- when a milestone ends, record meaningful lessons learned
