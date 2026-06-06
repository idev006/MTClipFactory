from __future__ import annotations

import json
from dataclasses import dataclass

from mt_clip_factory.domain.assets import Asset
from mt_clip_factory.domain.composition_plans import CompositionLayerAssignment, CompositionPlan
from mt_clip_factory.domain.enums import AssetType
from mt_clip_factory.domain.recipes import Recipe, RecipeItem
from mt_clip_factory.domain.render_decisions import RenderDecision


LAYER_ORDER = (
    "primary_voice",
    "background_music",
    "background_visual",
    "product_focus_visual",
    "text_overlay",
)


@dataclass(slots=True, frozen=True)
class PlannedComposition:
    plan: CompositionPlan
    decisions: tuple[RenderDecision, ...]


def build_default_composition(recipe: Recipe, items: list[RecipeItem], assets: dict[int, Asset]) -> PlannedComposition:
    layer_assignments = tuple(_build_layer_assignments(items, assets))
    resolved_duration_sec, duration_source = _resolve_duration(recipe, items, assets)
    plan = CompositionPlan(
        recipe_id=recipe.id or 0,
        duration_source=duration_source,
        target_duration_sec=recipe.duration_sec,
        resolved_duration_sec=resolved_duration_sec,
        layer_assignments=layer_assignments,
    )
    decisions = (
        RenderDecision(
            recipe_id=recipe.id or 0,
            decision_type="master_duration_resolved",
            action=duration_source,
            details_json=json.dumps(
                {
                    "target_duration_sec": recipe.duration_sec,
                    "resolved_duration_sec": resolved_duration_sec,
                },
                sort_keys=True,
            ),
        ),
        *tuple(_layer_decisions(recipe.id or 0, layer_assignments)),
    )
    return PlannedComposition(plan=plan, decisions=decisions)


def _build_layer_assignments(items: list[RecipeItem], assets: dict[int, Asset]) -> list[CompositionLayerAssignment]:
    grouped: dict[str, list[tuple[int, str]]] = {layer_name: [] for layer_name in LAYER_ORDER}
    for item in items:
        asset = assets.get(item.asset_id)
        if asset is None or asset.id is None:
            continue
        layer_name = _asset_type_to_layer(asset.asset_type)
        if layer_name is None:
            continue
        grouped[layer_name].append((asset.id, asset.asset_code))
    return [
        CompositionLayerAssignment(
            layer_name=layer_name,
            asset_ids=tuple(asset_id for asset_id, _ in grouped[layer_name]),
            asset_codes=tuple(asset_code for _, asset_code in grouped[layer_name]),
        )
        for layer_name in LAYER_ORDER
        if grouped[layer_name]
    ]


def _resolve_duration(recipe: Recipe, items: list[RecipeItem], assets: dict[int, Asset]) -> tuple[float | None, str]:
    if recipe.duration_sec is not None and recipe.duration_sec > 0:
        return recipe.duration_sec, "recipe_duration"

    voice_durations = [
        asset.duration_sec
        for item in items
        for asset in [assets.get(item.asset_id)]
        if asset is not None and asset.asset_type == AssetType.VOICEOVER and asset.duration_sec is not None
    ]
    if voice_durations:
        return round(sum(voice_durations), 3), "voiceover_total_duration"

    background_durations = [
        asset.duration_sec
        for item in items
        for asset in [assets.get(item.asset_id)]
        if asset is not None and asset.asset_type == AssetType.BACKGROUND_VIDEO and asset.duration_sec is not None
    ]
    if background_durations:
        return max(background_durations), "background_visual_max_duration"

    fallback_durations = [
        asset.duration_sec
        for item in items
        for asset in [assets.get(item.asset_id)]
        if asset is not None and asset.duration_sec is not None
    ]
    if fallback_durations:
        return max(fallback_durations), "asset_duration_fallback"
    return None, "unresolved"


def _layer_decisions(recipe_id: int, layer_assignments: tuple[CompositionLayerAssignment, ...]) -> list[RenderDecision]:
    return [
        RenderDecision(
            recipe_id=recipe_id,
            decision_type="layer_assignment_inferred",
            asset_role=layer.layer_name,
            action="assign_assets",
            details_json=json.dumps(
                {
                    "asset_ids": list(layer.asset_ids),
                    "asset_codes": list(layer.asset_codes),
                    "asset_count": len(layer.asset_ids),
                },
                sort_keys=True,
            ),
        )
        for layer in layer_assignments
    ]


def _asset_type_to_layer(asset_type: AssetType) -> str | None:
    match asset_type:
        case AssetType.VOICEOVER:
            return "primary_voice"
        case AssetType.BACKGROUND_MUSIC:
            return "background_music"
        case AssetType.BACKGROUND_VIDEO:
            return "background_visual"
        case AssetType.FOREGROUND_VIDEO:
            return "product_focus_visual"
        case AssetType.TEMPLATE | AssetType.SCRIPT:
            return "text_overlay"
        case _:
            return None
