from __future__ import annotations

import json
from dataclasses import dataclass

from mt_clip_factory.domain.assets import Asset
from mt_clip_factory.domain.composition_plans import CompositionLayerAssignment, CompositionPlan
from mt_clip_factory.domain.enums import AssetType
from mt_clip_factory.domain.recipes import Recipe, RecipeItem
from mt_clip_factory.domain.render_decisions import RenderDecision
from mt_clip_factory.domain.timeline_segments import TimelineSegment, validate_timeline_segments


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
    segments: tuple[TimelineSegment, ...]
    decisions: tuple[RenderDecision, ...]


def build_default_composition(recipe: Recipe, items: list[RecipeItem], assets: dict[int, Asset]) -> PlannedComposition:
    layer_assignments = tuple(_build_layer_assignments(items, assets))
    layer_duration_extents = _layer_duration_extents(items, assets)
    resolved_duration_sec, duration_source = _resolve_duration(recipe, items, assets, layer_duration_extents=layer_duration_extents)
    timeline_segments = _build_timeline_segments(recipe, resolved_duration_sec)
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
                    "layer_duration_extents_sec": layer_duration_extents,
                },
                sort_keys=True,
            ),
        ),
        *tuple(_layer_decisions(recipe.id or 0, layer_assignments)),
        *tuple(_segment_decisions(recipe.id or 0, timeline_segments)),
    )
    return PlannedComposition(plan=plan, segments=timeline_segments, decisions=decisions)


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


def _resolve_duration(
    recipe: Recipe,
    items: list[RecipeItem],
    assets: dict[int, Asset],
    *,
    layer_duration_extents: dict[str, float] | None = None,
) -> tuple[float | None, str]:
    layer_extents = layer_duration_extents or _layer_duration_extents(items, assets)
    longest_layer_duration = max(layer_extents.values(), default=0.0)
    recipe_duration = recipe.duration_sec if recipe.duration_sec is not None and recipe.duration_sec > 0 else None
    if recipe_duration is not None and recipe_duration >= longest_layer_duration:
        return round(recipe_duration, 3), "recipe_duration"
    if longest_layer_duration > 0:
        return round(longest_layer_duration, 3), "longest_contributing_layer"
    if recipe_duration is not None:
        return round(recipe_duration, 3), "recipe_duration"
    return None, "unresolved"


def _layer_duration_extents(items: list[RecipeItem], assets: dict[int, Asset]) -> dict[str, float]:
    primary_voice = _sum_durations(
        asset.duration_sec
        for item in items
        for asset in [assets.get(item.asset_id)]
        if asset is not None and asset.asset_type == AssetType.VOICEOVER
    )
    background_music = _sum_durations(
        asset.duration_sec
        for item in items
        for asset in [assets.get(item.asset_id)]
        if asset is not None and asset.asset_type == AssetType.BACKGROUND_MUSIC
    )
    background_visual = _max_duration(
        asset.duration_sec
        for item in items
        for asset in [assets.get(item.asset_id)]
        if asset is not None and asset.asset_type == AssetType.BACKGROUND_VIDEO
    )
    product_focus_visual = _max_duration(
        asset.duration_sec
        for item in items
        for asset in [assets.get(item.asset_id)]
        if asset is not None and asset.asset_type == AssetType.FOREGROUND_VIDEO
    )
    return {
        "primary_voice": primary_voice,
        "background_music": background_music,
        "background_visual": background_visual,
        "product_focus_visual": product_focus_visual,
    }


def _sum_durations(values) -> float:
    durations = [float(value) for value in values if value is not None and value > 0]
    return round(sum(durations), 3) if durations else 0.0


def _max_duration(values) -> float:
    durations = [float(value) for value in values if value is not None and value > 0]
    return round(max(durations), 3) if durations else 0.0


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


def _build_timeline_segments(recipe: Recipe, resolved_duration_sec: float | None) -> tuple[TimelineSegment, ...]:
    if resolved_duration_sec is None or resolved_duration_sec <= 0:
        return ()

    segment_specs = _resolve_segment_specs(recipe, resolved_duration_sec)
    cursor = 0.0
    segments: list[TimelineSegment] = []
    for index, spec in enumerate(segment_specs, start=1):
        if index == len(segment_specs):
            end_sec = round(resolved_duration_sec, 3)
        else:
            end_sec = round(cursor + (resolved_duration_sec * spec["weight"]), 3)
        start_sec = round(cursor, 3)
        target_duration_sec = round(end_sec - start_sec, 3)
        segments.append(
            TimelineSegment(
                recipe_id=recipe.id or 0,
                segment_type=spec["segment_type"],
                sequence_index=index,
                start_sec=start_sec,
                end_sec=end_sec,
                target_duration_sec=target_duration_sec,
                message_text=spec["message_text"],
                preferred_layers=spec["preferred_layers"],
                text_rule=spec["text_rule"],
                audio_policy=spec["audio_policy"],
            )
        )
        cursor = end_sec
    return validate_timeline_segments(segments, resolved_duration_sec=resolved_duration_sec)


def _resolve_segment_specs(recipe: Recipe, resolved_duration_sec: float) -> tuple[dict[str, object], ...]:
    if resolved_duration_sec < 12:
        return (
            _segment_spec("hook", 0.25, recipe.hook_text or recipe.recipe_code, ("primary_voice", "text_overlay", "product_focus_visual"), "headline_priority"),
            _segment_spec("benefit", 0.5, recipe.script_angle or recipe.mood, ("primary_voice", "product_focus_visual", "text_overlay"), "benefit_overlay"),
            _segment_spec("cta", 0.25, recipe.cta_text or recipe.target_platform, ("text_overlay", "product_focus_visual", "primary_voice"), "cta_emphasis"),
        )
    if resolved_duration_sec < 20:
        return (
            _segment_spec("hook", 0.2, recipe.hook_text or recipe.recipe_code, ("primary_voice", "text_overlay", "product_focus_visual"), "headline_priority"),
            _segment_spec("problem", 0.2, recipe.target_audience or recipe.script_angle, ("primary_voice", "background_visual", "text_overlay"), "problem_caption"),
            _segment_spec("benefit", 0.35, recipe.script_angle or recipe.mood, ("primary_voice", "product_focus_visual", "text_overlay"), "benefit_overlay"),
            _segment_spec("cta", 0.25, recipe.cta_text or recipe.target_platform, ("text_overlay", "product_focus_visual", "primary_voice"), "cta_emphasis"),
        )
    return (
        _segment_spec("hook", 0.18, recipe.hook_text or recipe.recipe_code, ("primary_voice", "text_overlay", "product_focus_visual"), "headline_priority"),
        _segment_spec("problem", 0.18, recipe.target_audience or recipe.script_angle, ("primary_voice", "background_visual", "text_overlay"), "problem_caption"),
        _segment_spec("benefit", 0.28, recipe.script_angle or recipe.mood, ("primary_voice", "product_focus_visual", "text_overlay"), "benefit_overlay"),
        _segment_spec("proof", 0.18, recipe.mood or recipe.target_platform, ("product_focus_visual", "subtitle", "primary_voice"), "proof_support"),
        _segment_spec("cta", 0.18, recipe.cta_text or recipe.target_platform, ("text_overlay", "product_focus_visual", "primary_voice"), "cta_emphasis"),
    )


def _segment_spec(
    segment_type: str,
    weight: float,
    message_text: str | None,
    preferred_layers: tuple[str, ...],
    text_rule: str,
) -> dict[str, object]:
    return {
        "segment_type": segment_type,
        "weight": weight,
        "message_text": message_text,
        "preferred_layers": preferred_layers,
        "text_rule": text_rule,
        "audio_policy": "voice_priority_with_music_duck",
    }


def _segment_decisions(recipe_id: int, timeline_segments: tuple[TimelineSegment, ...]) -> list[RenderDecision]:
    return [
        RenderDecision(
            recipe_id=recipe_id,
            decision_type="timeline_segment_planned",
            asset_role=segment.segment_type,
            action="schedule_segment",
            details_json=json.dumps(
                {
                    "audio_policy": segment.audio_policy,
                    "end_sec": segment.end_sec,
                    "preferred_layers": list(segment.preferred_layers),
                    "sequence_index": segment.sequence_index,
                    "start_sec": segment.start_sec,
                    "target_duration_sec": segment.target_duration_sec,
                    "text_rule": segment.text_rule,
                },
                sort_keys=True,
            ),
        )
        for segment in timeline_segments
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
