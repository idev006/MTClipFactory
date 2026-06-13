# Asset First Tagging Workflow 2026-06-13

This document is the SSOT for the next usability slice of the `Tags` screen.

It refines [36_Folder_Discovery_Depth_And_Assisted_Tagging_Workflow_2026-06-13.md](/F:/programming/python/MTClipFactory/doc/36_Folder_Discovery_Depth_And_Assisted_Tagging_Workflow_2026-06-13.md) and remains compatible with [38_Tag_Aware_Auto_Factory_Selection_Workflow_2026-06-13.md](/F:/programming/python/MTClipFactory/doc/38_Tag_Aware_Auto_Factory_Selection_Workflow_2026-06-13.md).

## Purpose

- make tagging feel natural for operators who think from the asset first
- reduce the need to mentally coordinate two unrelated tables before every assignment
- let operators see current tags, search existing tags, and create-and-attach new tags from one focused workflow
- keep the current domain/service seam intact for this slice

## Core Decision

The main tagging flow should become `asset-first`, not `tag-first`.

The primary operator loop should be:

1. narrow the asset list
2. select one asset
3. inspect its current tags
4. attach an existing tag or create-and-attach a new tag immediately

The existing tag list remains useful, but it becomes a support tool rather than the mental starting point.

## Interaction Model

The first asset-first slice should provide:

1. one selected-asset panel
2. visible current tag labels for that asset
3. search and optional group narrowing for existing tags
4. `Create and Attach` for the selected asset
5. refresh that preserves the operator's current focus as much as possible

Explicitly deferred:

- bulk tagging
- tag removal / unassign
- tag recommendation scoring
- multi-asset compare workflows

## Reviewed Workflow

```mermaid
flowchart LR
    A["Open Tags"] --> B["Filter Assets"]
    B --> C["Select Asset"]
    C --> D["Inspect Current Tags"]
    D --> E["Search Existing Tags"]
    E --> F["Attach Existing Tag"]
    D --> G["Create New Tag"]
    G --> H["Create And Attach"]
    F --> I["Refresh Selected Asset State"]
    H --> I
```

## Asset-First Tagging Sequence

```mermaid
sequenceDiagram
    actor Operator
    participant View as TagDictionaryWindow
    participant VM as TagDictionaryViewModel
    participant TagSvc as TagManagementService
    participant AssetSvc as AssetIntakeService

    Operator->>View: open Tags
    View->>VM: load()
    VM->>TagSvc: list_tags()
    VM->>AssetSvc: list_assets()
    VM-->>View: assets + available tags
    Operator->>View: filter assets and select one asset
    View->>VM: select_asset(asset_id)
    VM-->>View: selected asset + current tag labels
    Operator->>View: search or filter existing tags
    View->>VM: apply_tag_filters(...)
    VM-->>View: narrowed available tags
    alt existing tag
        Operator->>View: attach selected tag
        View->>VM: assign_tag_to_selected_asset(tag_id)
        VM->>TagSvc: assign_tag_to_asset(...)
    else new tag
        Operator->>View: create and attach
        View->>VM: create_tag_and_assign_to_selected_asset(...)
        VM->>TagSvc: create_tag(...)
        VM->>TagSvc: assign_tag_to_asset(...)
    end
    VM->>AssetSvc: list_assets()
    VM->>TagSvc: list_tags()
    VM-->>View: refreshed selected asset + feedback
```

## Review Notes

This plan was reviewed before implementation and the following decisions were locked:

1. the main UX should optimize for one selected asset at a time because that matches current operator preparation work
2. the existing `Create Tag` behavior should remain available, but `Create and Attach` should become the fastest happy path
3. tag search and group narrowing belong next to the available tag list, not hidden behind a separate screen
4. the first slice should not invent tag removal behavior unless the service seam is designed for it
5. the workflow should stay compatible with automation-facing normalized `group:name` labels
