# Automation Tag Taxonomy Guide 2026-06-14

This document is the SSOT guide for organizing automation-oriented asset tags in MTClipFactory.

It complements [38_Tag_Aware_Auto_Factory_Selection_Workflow_2026-06-13.md](/F:/programming/python/MTClipFactory/doc/38_Tag_Aware_Auto_Factory_Selection_Workflow_2026-06-13.md), [39_Asset_First_Tagging_Workflow_2026-06-13.md](/F:/programming/python/MTClipFactory/doc/39_Asset_First_Tagging_Workflow_2026-06-13.md), and [40_Bulk_Asset_Tagging_Workflow_2026-06-14.md](/F:/programming/python/MTClipFactory/doc/40_Bulk_Asset_Tagging_Workflow_2026-06-14.md).

## Purpose

- define one practical tag taxonomy for clip automation
- keep operator tagging understandable and reusable
- make tag-driven planner selection more deterministic
- reduce future drift in naming across products and campaigns

## Core Tag Format

Every automation-facing tag should use the normalized format:

```text
group:name
```

Examples:

- `mood:exciting`
- `scene:space`
- `message:proof`
- `language:th`

## Normalization Rules

Use these rules consistently:

1. keep tags lowercase
2. use `group:name`
3. use `_` instead of spaces inside a name
4. avoid punctuation unless it is part of a stable machine-facing token
5. treat normalized duplicates as the same tag

Examples:

- `Mood:Exciting` -> `mood:exciting`
- `scene:deep space` -> `scene:deep_space`
- `STYLE:Wow` -> `style:wow`

## Duplicate Rule

One asset must not retain duplicate tags after normalization.

This means:

- `mood:exciting` and `Mood:Exciting` are duplicates
- `scene:space` repeated from both a global rule and a local rule should be stored once

## Recommended Tag Groups

The recommended baseline groups for clip automation are:

- `mood`
- `style`
- `scene`
- `object`
- `action`
- `message`
- `audience`
- `product`
- `brand`
- `platform`
- `format`
- `role`
- `language`
- `voice_tone`
- `music_feel`
- `quality`
- `visual_theme`
- `compliance`
- `status`

## Group Meanings

- `mood`: emotional tone of the asset
- `style`: presentation style or visual treatment
- `scene`: place or world represented in the shot
- `object`: important visible thing in the asset
- `action`: what is happening in the asset
- `message`: marketing job of the asset in the edit
- `audience`: intended audience or persona relevance
- `product`: product or product-family identity
- `brand`: brand identity
- `platform`: target distribution platform
- `format`: frame or shot-format characteristic
- `role`: system-facing media role
- `language`: spoken or written language
- `voice_tone`: delivery tone for voice assets
- `music_feel`: emotional or stylistic quality of music assets
- `quality`: production or capture quality classification
- `visual_theme`: broader visual world or concept
- `compliance`: operational or approval constraint
- `status`: automation readiness or workflow status

## Suggested Starter Values

### mood

- `mood:exciting`
- `mood:warm`
- `mood:trustworthy`
- `mood:hopeful`
- `mood:premium`

### style

- `style:wow`
- `style:cinematic`
- `style:clean`
- `style:ugc`
- `style:educational`

### scene

- `scene:space`
- `scene:studio`
- `scene:warehouse`
- `scene:lab`
- `scene:home`

### object

- `object:stars`
- `object:product_pack`
- `object:box`
- `object:worker`
- `object:bottle`

### action

- `action:unboxing`
- `action:packing`
- `action:pointing`
- `action:pouring`
- `action:presenting`

### message

- `message:hook`
- `message:problem`
- `message:benefit`
- `message:proof`
- `message:cta`

### audience

- `audience:parents`
- `audience:workers`
- `audience:health_concern`
- `audience:elderly_support`

### product

- `product:biothentic`
- `product:calcium`

### brand

- `brand:biothentic`

### platform

- `platform:tiktok`
- `platform:facebook`
- `platform:youtube_shorts`

### format

- `format:9x16`
- `format:16x9`
- `format:closeup`
- `format:medium_shot`

### role

- `role:foreground`
- `role:background`
- `role:voice`
- `role:music`

### language

- `language:th`
- `language:en`

### voice_tone

- `voice_tone:energetic`
- `voice_tone:calm`
- `voice_tone:expert`

### music_feel

- `music_feel:uplifting`
- `music_feel:epic`
- `music_feel:soft`

### quality

- `quality:premium`
- `quality:studio`
- `quality:ugc`

### visual_theme

- `visual_theme:space`
- `visual_theme:science`
- `visual_theme:minimal`

### compliance

- `compliance:product_visible`
- `compliance:no_text_overlay`
- `compliance:manual_claim_review`

### status

- `status:approved_for_auto`
- `status:manual_review_preferred`

## Operator Guidance

When choosing tags, apply them with this order of thinking:

1. what role this asset plays
2. what message job it can serve
3. what the viewer sees
4. what emotional tone it carries
5. what workflow constraints matter

For example, a visually energetic clip showing stars in a dramatic product reveal could use:

- `role:foreground`
- `message:hook`
- `scene:space`
- `object:stars`
- `mood:exciting`
- `style:wow`

## Core Tag Set For Small Teams

If the full taxonomy feels too large, start with this reduced set:

- `mood`
- `style`
- `scene`
- `object`
- `action`
- `message`
- `role`
- `language`

This smaller set is enough to support many first automation cases without overwhelming operators.

## Pipeline Selection Examples

The automation planner can consume these tags through `pipeline.toml`.

Example:

```toml
[selection_tags]
foreground = ["message:hook", "scene:space"]
background = ["scene:space"]
voice = ["language:th", "voice_tone:energetic"]
music = ["music_feel:epic"]
```

## Future Folder-Auto Direction

The preferred future direction is:

1. allow `global_tags` at the folder level
2. allow per-file `local tags`
3. merge them with normalization and deduplication
4. ingest assets and apply tags automatically during folder-driven intake

That future direction remains compatible with this taxonomy guide because the machine-facing contract stays `group:name`.

## Template Kit Reference

Operators preparing a new product folder should start from:

- [doc/templates/new_product_auto_factory_template](/F:/programming/python/MTClipFactory/doc/templates/new_product_auto_factory_template)

That template kit includes starter `tags.toml` files that already match this taxonomy guide.

When a product also prepares captioned automation, the same template kit now includes `captions.toml` alongside the tag metadata files.

## Review Notes

This guide locks the following decisions:

1. automation-facing tags should remain explicit and deterministic
2. the machine-facing tag contract remains `group:name`
3. operators may think in Thai or English, but stored automation tags should favor stable normalized tokens
4. duplicate tags on one asset are not allowed after normalization
5. smaller starter taxonomies are acceptable if they remain compatible with the same naming contract
