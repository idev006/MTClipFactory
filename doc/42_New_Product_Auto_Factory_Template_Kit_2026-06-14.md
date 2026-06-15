# New Product Auto Factory Template Kit 2026-06-14

This document is the SSOT guide for the reusable new-product template kit used to prepare folder-driven automation runs.

It complements [32_Auto_Factory_Batch_Production_Workflow.md](/F:/programming/python/MTClipFactory/doc/32_Auto_Factory_Batch_Production_Workflow.md), [41_Automation_Tag_Taxonomy_Guide_2026-06-14.md](/F:/programming/python/MTClipFactory/doc/41_Automation_Tag_Taxonomy_Guide_2026-06-14.md), and the template files under [doc/templates/new_product_auto_factory_template](/F:/programming/python/MTClipFactory/doc/templates/new_product_auto_factory_template).

## Purpose

- give operators one ready-to-copy folder kit for new products
- reduce setup mistakes in `product.toml`, `pipeline.toml`, and tag metadata
- keep the automation contract visible without requiring operators to remember every required file name

## Template Kit Location

Use this folder as the starting point for new products:

- [doc/templates/new_product_auto_factory_template](/F:/programming/python/MTClipFactory/doc/templates/new_product_auto_factory_template)

## Included Files

The template kit includes:

- `contracts/product.toml`
- `contracts/pipeline.toml`
- `contracts/captions.toml`
- `assets/foreground/tags.toml`
- `assets/background/tags.toml`
- `assets/music/tags.toml`
- `assets/voice/tags.toml`
- `README.md`

## How Operators Should Use It

1. copy the whole template folder
2. rename the copied folder to the new product folder name
3. update `contracts/product.toml`
4. update `contracts/pipeline.toml`
5. review or adjust fill-policy defaults in `pipeline.toml`
6. update `contracts/captions.toml` when captioned automation is needed
7. place media files into `assets/foreground`, `assets/background`, `assets/music`, and `assets/voice`
8. edit the matching `tags.toml` files when automation tags are needed
9. run the batch root from the `Auto Factory` screen

Operator guidance from the first live product-folder audit:

- keep `selection_tags` broad enough to preserve the intended visual pool; narrow them only when repetition is acceptable on purpose
- write `captions.toml` as publishable clip copy, not as editorial instructions to the operator
- use `\n` only when you intentionally want multiple caption lines; otherwise keep one strong line and let the runtime best-fit the font size inside the textbox
- think of caption layout as a textbox first: use `textbox_alignment` for the box and `alignment` for the text inside it
- use a rerun after contract edits as the standard recovery loop for caption overflow or overly repetitive visual selection

## Minimum Required Files

The current automation contract requires:

- `contracts/product.toml`
- `contracts/pipeline.toml`

The asset subfolders are the expected operator baseline:

- `assets/foreground/`
- `assets/background/`
- `assets/music/`
- `assets/voice/`

Current service behavior can tolerate a missing asset-type folder, but the template kit keeps all four folders so operators do not need to remember which names are valid.

Backward-compatibility rule:

- runtime still accepts legacy root-level `product.toml`, `pipeline.toml`, `captions.toml`, and root asset folders for older products
- new template work should prefer the v2 `contracts/` plus `assets/` layout
- if a product folder contains both old and new paths for the same logical contract or asset folder, the runtime should fail truthfully instead of guessing

## Tag Metadata Direction

The template kit includes `tags.toml` files as a preparation baseline for the planned folder-auto tagging workflow.

That means:

- operators can already prepare `global_tags` and per-file `file_tags`
- those files act as a stable contract and checklist for current folder-driven automation plus caption-ready preview/final runtime
- the current delivered auto-factory intake now reads `tags.toml` and applies normalized tags additively to matching assets during folder runs
- `pipeline.toml` is also the contract location for per-asset-type fill policy in auto-mode

The template kit also includes `contracts/captions.toml` as the current product-level contract for automated caption selection and rendering.

Runtime-created operator artifact folder:

- `runs/` is created by automation and stores product-local batch outputs, manifests, and journal files

## Example Operator Flow

```mermaid
flowchart LR
    A["Copy Template Folder"] --> B["Rename Product Folder"]
    B --> C["Edit product.toml"]
    C --> D["Edit pipeline.toml"]
    D --> E["Place Media Files"]
    E --> F["Edit tags.toml Files"]
    F --> G["Run Auto Factory"]
```

## Review Notes

This template kit locks the following decisions:

1. new-product setup should begin from a copied folder kit instead of handwritten files
2. the contract file names should stay explicit and operator-readable
3. tag metadata should live near the asset folders that it describes
4. the future auto-tagging seam should reuse the same template files instead of inventing a second metadata format later
