# Settings UI Audit Test Plan 2026-06-11

This document is the focused audit and test plan for the redesigned `Settings` surface in MTClipFactory.

It complements the broader [20_Master_Test_Plan.md](/F:/programming/python/MTClipFactory/doc/20_Master_Test_Plan.md) and narrows attention to the highest-risk changes introduced by the grouped two-column layout and the numeric-control redesign from spinners toward slider-led interaction.

## Audit Goal

- verify the redesigned `Settings` window remains functionally correct
- verify the new layout improves operator scanability without breaking persistence behavior
- verify slider-based numeric controls do not silently corrupt or clamp existing configuration values
- verify exact numeric entry remains available for precise edits where slider motion alone is not ideal
- verify the desktop app still remains safe for operator testing after the redesign

## In-Scope

- `SettingsWindow` structure and grouped panel layout
- settings load behavior from `app_config.toml`
- settings save behavior into `SystemSettingsDTO`
- slider, checkbox, combo-box, and path-field interaction mapping
- preservation of pre-existing high-value settings that exceed default slider ranges
- status and feedback surfaces after load/save
- startup/UI smoke sanity for the six-window desktop shell

## Out-Of-Scope

- full end-to-end media rendering quality
- operator acceptance of every wording choice in the new visual design
- screen-reader certification or formal accessibility conformance audit
- long-duration soak/performance testing

## Key Risks To Audit

### R1. Silent Value Clamp

- replacing spinners with sliders can reduce the editable domain
- pre-existing config values could be clamped on load or save without operator awareness
- impact: wrong runtime policy, wrong recovery thresholds, wrong audio tuning

### R2. DTO Mapping Regression

- UI redesign could disconnect fields from `SystemSettingsDTO`
- impact: save appears successful but persisted behavior becomes untruthful

### R3. Visual Grouping Regression

- grouped panels could hide or omit previously visible settings
- impact: operators lose confidence or miss critical controls

### R4. Feedback Truthfulness

- the new footer/status arrangement could under-report save/reload outcomes
- impact: operators misunderstand runtime-reload behavior

### R5. Interaction Precision

- slider-led interaction may be less precise than direct numeric entry for some fields if no exact-entry path exists
- impact: tuning feels awkward even when functionally correct

## Test Approach

### 1. Code/Design Audit

- inspect the `SettingsWindow` widget composition
- inspect numeric field range decisions
- inspect save/load wiring through `SettingsViewModel`

### 2. Widget-Level Automated Tests

- instantiate the redesigned window offscreen
- verify grouped panels render
- verify loaded settings populate sliders and non-slider controls
- verify save produces a truthful `SystemSettingsDTO`
- verify out-of-range loaded values survive load/save without clamp

### 3. Regression Suite

- run full `pytest` inside `.venv`
- confirm no unrelated behavior regressed

### 4. UI Smoke

- instantiate all six primary windows with `QT_QPA_PLATFORM=offscreen`
- confirm redesign did not destabilize the desktop shell

### 5. Real Persistence Round-Trip

- drive `SystemSettingsService + SettingsViewModel + SettingsWindow` against a temporary `app_config.toml`
- verify large values persist truthfully after a UI save

### 6. Visual Audit

- capture an offscreen screenshot of the redesigned `Settings` surface
- confirm the panel grouping and two-column structure are present
- record any headless-only rendering caveats

## Test Cases

1. `AUD-SET-01` Grouped panels are present and titled correctly.
2. `AUD-SET-02` Window load populates path, checkbox, combo, and numeric controls from settings.
3. `AUD-SET-03` Save maps edited slider or exact-entry values into a persisted DTO without swapping fields.
4. `AUD-SET-04` Slider controls preserve pre-existing high numeric values that exceed default initial ranges.
5. `AUD-SET-05` Float slider preserves audio ratio precision within acceptable tolerance.
6. `AUD-SET-06` Status and feedback surfaces update after load/save.
7. `AUD-SET-07` Full regression remains green after the redesign.
8. `AUD-SET-08` UI smoke still reports `ui_smoke_ok=6`.
9. `AUD-SET-09` Real service round-trip preserves large recovery threshold and duck-ratio values.
10. `AUD-SET-10` Visual grouping remains scanable in the rendered window layout.
11. `AUD-SET-11` Exact numeric entry can update values beyond default slider spans when the underlying domain allows it.

## Environment

- workspace: `F:\programming\python\MTClipFactory`
- Python runtime: `F:\programming\python\MTClipFactory\.venv`
- Python version: `3.12.4`
- UI mode for automation: `QT_QPA_PLATFORM=offscreen`
- config source of truth: `app_config.toml`

## Entry Criteria

- current repo state is available locally
- `.venv` is usable
- docs remain the SSOT for expected behavior
- redesigned `Settings` window code is present in the workspace

## Exit Criteria

- focused widget-level tests pass
- full regression passes
- UI smoke passes
- no `Critical` or `High` settings-surface defect remains open
- residual usability concerns are documented honestly

## Evidence To Capture

- `pytest` results
- focused `test_settings_window_ui.py` results
- `ui_smoke_ok=6` result
- real persistence round-trip output
- screenshot or recorded visual observation for the grouped layout

## Severity Guidance For This Audit

- `Critical`: settings save corrupts persisted configuration or makes the app unusable
- `High`: one or more high-impact settings silently map to the wrong DTO values or are hidden/unreachable
- `Medium`: layout or control design impairs precision or creates misleading operator expectations
- `Low`: cosmetic or wording issues without functional impact
