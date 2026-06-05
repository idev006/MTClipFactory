# Issues Log

## Open Issues

| ID | Date | Severity | Topic | Description | Owner | Status | Next Action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ISS-001 | 2026-06-05 | Medium | UI Direction | The original blueprint referenced Streamlit ideas, but the implementation SSOT is now PySide6 + MVVM. Team members must ignore legacy UI assumptions. | Engineering | Open | Continue updating docs and screens only from current repo behavior. |
| ISS-002 | 2026-06-05 | Medium | Module Boundary | `Video Assembly Factory` must consume prepared assets without mutating core asset metadata ownership owned by `Resource Library Management`. | Engineering | Open | Keep ownership rule explicit in architecture and service contracts. |
| ISS-003 | 2026-06-05 | Medium | Preview Depth | Current preview flow writes a persisted manifest, not a rendered preview video. This is intentional scaffolding, but not the final capability. | Engineering | Open | Add preview render adapter and output registration. |
| ISS-004 | 2026-06-05 | Medium | Recovery Depth | Job persistence exists, but recovery policy is not yet uniform across artifact and preview jobs. | Engineering | Open | Add resume/retry policy and restart tests. |
| ISS-005 | 2026-06-05 | Medium | Path Configurability | Some important roots still default from `workspace_root` instead of a user-editable `[paths]` config surface. This is below the desired no-hardcode bar. | Engineering | Open | Add `[paths]` support to `app_config.toml` for database, media, docs, and output roots. |

## Closed Issues

| ID | Date Closed | Topic | Resolution |
| --- | --- | --- | --- |
| ISS-006-CLOSED | 2026-06-05 | Artifact Generation Gap | Closed by delivering persisted thumbnail/proxy generation jobs and dashboard visibility. |
| ISS-007-CLOSED | 2026-06-05 | Empty Factory Package | Closed by delivering recipe persistence, preview jobs, and recipe builder UI scaffolding. |

## Rule

- anything affecting scope, architecture, reliability, or schedule goes here
- closing an issue requires a concrete resolution statement, not only code merged
