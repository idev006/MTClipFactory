from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from mt_clip_factory.domain.assets import Asset
from mt_clip_factory.domain.composition_plans import CompositionPlan
from mt_clip_factory.domain.recipes import Recipe, RecipeItem
from mt_clip_factory.domain.timeline_segments import TimelineSegment
from mt_clip_factory.factory.audio_composition import PreviewAudioMixPlan, build_audio_mix_plan
from mt_clip_factory.factory.automation_policy import ProductAutomationPolicyService, default_fill_policies
from mt_clip_factory.factory.caption_runtime import CaptionRuntimeService, ResolvedCaptionRole, ResolvedSegmentCaptions
from mt_clip_factory.factory.visual_selection import seeded_choice


VISUAL_LAYER_FALLBACK = ("product_focus_visual", "background_visual")


@dataclass(slots=True, frozen=True)
class PreviewLayerClip:
    layer_name: str
    asset_id: int
    asset_code: str
    source_file: Path
    fill_mode: str


@dataclass(slots=True, frozen=True)
class PreviewSegmentClip:
    sequence_index: int
    segment_type: str
    layer_name: str
    asset_id: int
    asset_code: str
    source_file: Path
    start_sec: float
    end_sec: float
    target_duration_sec: float
    fill_mode: str
    message_text: str | None = None
    text_rule: str | None = None
    audio_policy: str | None = None
    background_layer: PreviewLayerClip | None = None
    captions: tuple[ResolvedCaptionRole, ...] = ()


@dataclass(slots=True, frozen=True)
class PreviewComposition:
    manifest_payload: dict
    source_files: tuple[Path, ...]
    segment_clips: tuple[PreviewSegmentClip, ...]
    audio_mix_plan: PreviewAudioMixPlan | None = None


def build_segmented_preview_composition(
    *,
    recipe: Recipe,
    product_code: str,
    items: Sequence[RecipeItem],
    assets: dict[int, Asset],
    plan: CompositionPlan,
    segments: Sequence[TimelineSegment],
    caption_runtime_service: CaptionRuntimeService | None = None,
    automation_policy_service: ProductAutomationPolicyService | None = None,
    caption_frame_size: tuple[int, int] | None = None,
) -> PreviewComposition:
    fill_policies = (
        default_fill_policies()
        if automation_policy_service is None
        else automation_policy_service.load_fill_policies(product_code)
    )
    visual_assets_by_layer = _build_visual_assets_by_layer(plan, assets)
    selected_visual_assets_by_layer = _select_visual_assets_by_layer(
        visual_assets_by_layer,
        recipe_code=recipe.recipe_code,
    )
    audio_mix_plan = build_audio_mix_plan(plan, assets, fill_policies=fill_policies)
    resolved_captions = _resolve_segment_captions(
        caption_runtime_service=caption_runtime_service,
        product_code=product_code,
        recipe_code=recipe.recipe_code,
        segments=segments,
        frame_size=caption_frame_size,
    )
    if not visual_assets_by_layer:
        return PreviewComposition(
            manifest_payload=_build_manifest_payload(
                recipe=recipe,
                product_code=product_code,
                items=items,
                plan=plan,
                segments=(),
                resolved_captions=resolved_captions,
                fill_policies=fill_policies.to_manifest_dict(),
            ),
            source_files=(),
            segment_clips=(),
            audio_mix_plan=audio_mix_plan,
        )

    segment_clips = tuple(
        _build_segment_clip(
            segment,
            selected_visual_assets_by_layer,
            captions_by_sequence=resolved_captions,
            fill_policies=fill_policies,
        )
        for segment in segments
    )
    if not segment_clips:
        source_files = tuple(_dedupe_files(asset.file_path for layer_assets in visual_assets_by_layer.values() for asset in layer_assets))
        return PreviewComposition(
            manifest_payload=_build_manifest_payload(
                recipe=recipe,
                product_code=product_code,
                items=items,
                plan=plan,
                segments=(),
                resolved_captions=resolved_captions,
                fill_policies=fill_policies.to_manifest_dict(),
            ),
            source_files=source_files,
            segment_clips=(),
            audio_mix_plan=audio_mix_plan,
        )
    return PreviewComposition(
        manifest_payload=_build_manifest_payload(
            recipe=recipe,
            product_code=product_code,
            items=items,
            plan=plan,
            segments=segment_clips,
            resolved_captions=resolved_captions,
            fill_policies=fill_policies.to_manifest_dict(),
        ),
        source_files=tuple(clip.source_file for clip in segment_clips),
        segment_clips=segment_clips,
        audio_mix_plan=audio_mix_plan,
    )


def _build_visual_assets_by_layer(plan: CompositionPlan, assets: dict[int, Asset]) -> dict[str, tuple[Asset, ...]]:
    result: dict[str, tuple[Asset, ...]] = {}
    for assignment in plan.layer_assignments:
        if assignment.layer_name not in VISUAL_LAYER_FALLBACK:
            continue
        layer_assets = tuple(
            asset
            for asset_id in assignment.asset_ids
            for asset in [assets.get(asset_id)]
            if asset is not None
        )
        if layer_assets:
            result[assignment.layer_name] = layer_assets
    return result


def _build_segment_clip(
    segment: TimelineSegment,
    selected_visual_assets_by_layer: dict[str, Asset],
    *,
    captions_by_sequence: dict[int, ResolvedSegmentCaptions],
    fill_policies,
) -> PreviewSegmentClip:
    background_layer = _build_optional_layer_clip(
        segment,
        selected_visual_assets_by_layer,
        layer_name="background_visual",
        fill_policy=fill_policies.background_video,
    )
    foreground_layer = _build_optional_layer_clip(
        segment,
        selected_visual_assets_by_layer,
        layer_name="product_focus_visual",
        fill_policy=fill_policies.foreground_video,
    )
    primary_layer = foreground_layer or background_layer
    if primary_layer is None:
        layer_name, asset = _resolve_selected_layer_asset(segment, selected_visual_assets_by_layer)
        primary_layer = _build_layer_clip(
            layer_name=layer_name,
            asset=asset,
            target_duration_sec=segment.target_duration_sec,
            fill_policy=(
                fill_policies.background_video
                if layer_name == "background_visual"
                else fill_policies.foreground_video
            ),
        )
    return PreviewSegmentClip(
        sequence_index=segment.sequence_index,
        segment_type=segment.segment_type,
        layer_name=primary_layer.layer_name,
        asset_id=primary_layer.asset_id,
        asset_code=primary_layer.asset_code,
        source_file=primary_layer.source_file,
        start_sec=segment.start_sec,
        end_sec=segment.end_sec,
        target_duration_sec=segment.target_duration_sec,
        fill_mode=primary_layer.fill_mode,
        message_text=segment.message_text,
        text_rule=segment.text_rule,
        audio_policy=segment.audio_policy,
        background_layer=background_layer if foreground_layer is not None else None,
        captions=(
            captions_by_sequence[segment.sequence_index].roles
            if segment.sequence_index in captions_by_sequence
            else ()
        ),
    )


def _build_optional_layer_clip(
    segment: TimelineSegment,
    selected_visual_assets_by_layer: dict[str, Asset],
    *,
    layer_name: str,
    fill_policy=None,
) -> PreviewLayerClip | None:
    asset = selected_visual_assets_by_layer.get(layer_name)
    if asset is None:
        return None
    return _build_layer_clip(
        layer_name=layer_name,
        asset=asset,
        target_duration_sec=segment.target_duration_sec,
        fill_policy=fill_policy,
    )


def _build_layer_clip(*, layer_name: str, asset: Asset, target_duration_sec: float, fill_policy=None) -> PreviewLayerClip:
    return PreviewLayerClip(
        layer_name=layer_name,
        asset_id=asset.id or 0,
        asset_code=asset.asset_code,
        source_file=Path(asset.file_path),
        fill_mode=_resolve_fill_mode(asset.duration_sec, target_duration_sec, fill_policy=fill_policy),
    )


def _resolve_selected_layer_asset(
    segment: TimelineSegment,
    selected_visual_assets_by_layer: dict[str, Asset],
) -> tuple[str, Asset]:
    for layer_name in segment.preferred_layers:
        asset = selected_visual_assets_by_layer.get(layer_name)
        if asset is not None:
            return layer_name, asset
    for layer_name in VISUAL_LAYER_FALLBACK:
        asset = selected_visual_assets_by_layer.get(layer_name)
        if asset is not None:
            return layer_name, asset
    raise ValueError(f"Segment {segment.segment_type} has no renderable visual assets.")


def _resolve_fill_mode(source_duration_sec: float | None, target_duration_sec: float, *, fill_policy=None) -> str:
    if source_duration_sec is None or source_duration_sec <= 0:
        return "duration_unknown"
    if source_duration_sec >= target_duration_sec:
        return "trim_to_segment"
    if fill_policy is None:
        return "loop_to_segment"
    return fill_policy.shortfall_mode


def _build_manifest_payload(
    *,
    recipe: Recipe,
    product_code: str,
    items: Sequence[RecipeItem],
    plan: CompositionPlan,
    segments: Sequence[PreviewSegmentClip],
    resolved_captions: dict[int, ResolvedSegmentCaptions],
    fill_policies: dict[str, dict[str, object]],
) -> dict:
    return {
        "composition_plan": {
            "duration_source": plan.duration_source,
            "resolved_duration_sec": plan.resolved_duration_sec,
            "target_duration_sec": plan.target_duration_sec,
        },
        "fill_policy": fill_policies,
        "items": [
            {
                "asset_code": item.asset_code,
                "asset_id": item.asset_id,
                "asset_type": item.asset_type,
                "role": item.role,
            }
            for item in items
        ],
        "product_code": product_code,
        "recipe_code": recipe.recipe_code,
        "segments": [
            {
                "asset_code": segment.asset_code,
                "asset_id": segment.asset_id,
                "audio_policy": segment.audio_policy,
                "end_sec": segment.end_sec,
                "fill_mode": segment.fill_mode,
                "layer_name": segment.layer_name,
                "message_text": segment.message_text,
                "segment_type": segment.segment_type,
                "sequence_index": segment.sequence_index,
                "source_file": str(segment.source_file),
                "start_sec": segment.start_sec,
                "target_duration_sec": segment.target_duration_sec,
                "text_rule": segment.text_rule,
                "background_layer": (
                    {
                        "asset_code": segment.background_layer.asset_code,
                        "asset_id": segment.background_layer.asset_id,
                        "fill_mode": segment.background_layer.fill_mode,
                        "layer_name": segment.background_layer.layer_name,
                        "source_file": str(segment.background_layer.source_file),
                    }
                    if segment.background_layer is not None
                    else None
                ),
            }
            for segment in segments
        ],
        "captions": _build_caption_manifest_payload(resolved_captions),
        "status": recipe.status.value,
        "target_platform": recipe.target_platform,
        "target_ratio": recipe.target_ratio,
    }


def _dedupe_files(file_paths: Sequence[str]) -> list[Path]:
    seen: set[str] = set()
    ordered: list[Path] = []
    for file_path in file_paths:
        if file_path in seen:
            continue
        seen.add(file_path)
        ordered.append(Path(file_path))
    return ordered


def _resolve_segment_captions(
    *,
    caption_runtime_service: CaptionRuntimeService | None,
    product_code: str,
    recipe_code: str,
    segments: Sequence[TimelineSegment],
    frame_size: tuple[int, int] | None,
) -> dict[int, ResolvedSegmentCaptions]:
    if caption_runtime_service is None:
        return {}
    frame_width_px, frame_height_px = (None, None) if frame_size is None else frame_size
    resolved_segments = caption_runtime_service.resolve_for_segments(
        product_code=product_code,
        recipe_code=recipe_code,
        segments=tuple(segments),
        frame_width_px=frame_width_px,
        frame_height_px=frame_height_px,
    )
    return {segment.sequence_index: segment for segment in resolved_segments}


def _select_visual_assets_by_layer(
    visual_assets_by_layer: dict[str, tuple[Asset, ...]],
    *,
    recipe_code: str,
) -> dict[str, Asset]:
    selected: dict[str, Asset] = {}
    for layer_name, candidate_assets in visual_assets_by_layer.items():
        selected[layer_name] = seeded_choice(
            candidate_assets,
            seed_key="|".join((recipe_code, layer_name, "persistent_layer_asset")),
        )
    return selected


def _build_caption_manifest_payload(resolved_captions: dict[int, ResolvedSegmentCaptions]) -> dict:
    caption_segments = [resolved_captions[index] for index in sorted(resolved_captions)]
    all_roles = [role for segment in caption_segments for role in segment.roles]
    return {
        "enabled": bool(caption_segments),
        "segment_count": len(caption_segments),
        "role_count": len(all_roles),
        "overflow_role_count": sum(1 for role in all_roles if role.overflowed),
        "review_required_role_count": sum(1 for role in all_roles if role.review_required),
        "segments": [
            {
                "sequence_index": segment.sequence_index,
                "segment_type": segment.segment_type,
                "roles": [
                    {
                        "role": role.role,
                        "source_text": role.source_text,
                        "rendered_text": role.rendered_text,
                        "rendered_lines": list(role.rendered_lines),
                        "seed_key": role.seed_key,
                        "selection_index": role.selection_index,
                        "line_break_mode": role.line_break_mode,
                        "fit_strategy": role.fit_strategy,
                        "line_count": role.line_count,
                        "font_family": role.font_family,
                        "font_source": role.font_source,
                        "font_resolution_mode": role.font_resolution_mode,
                        "font_resolution_target": role.font_resolution_target,
                        "font_file": None if role.font_file is None else str(role.font_file),
                        "font_size": role.font_size,
                        "requested_font_size": role.requested_font_size,
                        "font_size_unit": role.font_size_unit,
                        "min_font_size": role.min_font_size,
                        "position": role.position,
                        "alignment": role.alignment,
                        "vertical_alignment": role.vertical_alignment,
                        "textbox_alignment": role.textbox_alignment,
                        "textbox_mode": role.textbox_mode,
                        "textbox_height_mode": role.textbox_height_mode,
                        "style_preset": role.style_preset,
                        "text_color": role.text_color,
                        "stroke_color": role.stroke_color,
                        "stroke_width": role.stroke_width,
                        "background_color": role.background_color,
                        "background_opacity": role.background_opacity,
                        "box_border_color": role.box_border_color,
                        "box_border_opacity": role.box_border_opacity,
                        "box_border_width": role.box_border_width,
                        "padding": role.padding,
                        "max_lines": role.max_lines,
                        "preferred_line_count": role.preferred_line_count,
                        "max_chars_per_line": role.max_chars_per_line,
                        "max_width_ratio": role.max_width_ratio,
                        "textbox_width_ratio": role.textbox_width_ratio,
                        "textbox_height_ratio": role.textbox_height_ratio,
                        "line_spacing_ratio": role.line_spacing_ratio,
                        "line_advance_ratio": role.line_advance_ratio,
                        "safe_top_ratio": role.safe_top_ratio,
                        "safe_bottom_ratio": role.safe_bottom_ratio,
                        "max_safe_band_height_ratio": role.max_safe_band_height_ratio,
                        "effective_safe_bottom_ratio": role.effective_safe_bottom_ratio,
                        "line_spacing_px": role.line_spacing_px,
                        "line_font_sizes_px": list(role.line_font_sizes_px),
                        "line_widths_px": list(role.line_widths_px),
                        "line_height_px": role.line_height_px,
                        "line_heights_px": list(role.line_heights_px),
                        "text_block_width_px": role.text_block_width_px,
                        "text_block_height_px": role.text_block_height_px,
                        "max_text_width_px": role.max_text_width_px,
                        "line_left_positions_px": list(role.line_left_positions_px),
                        "line_top_positions_px": list(role.line_top_positions_px),
                        "line_box_left_positions_px": list(role.line_box_left_positions_px),
                        "line_box_top_positions_px": list(role.line_box_top_positions_px),
                        "line_box_widths_px": list(role.line_box_widths_px),
                        "line_box_heights_px": list(role.line_box_heights_px),
                        "box_left_px": role.box_left_px,
                        "box_top_px": role.box_top_px,
                        "box_width_px": role.box_width_px,
                        "box_height_px": role.box_height_px,
                        "frame_width_px": role.frame_width_px,
                        "frame_height_px": role.frame_height_px,
                        "overflow_policy": role.overflow_policy,
                        "enter_animation": role.enter_animation,
                        "overflowed": role.overflowed,
                        "review_required": role.review_required,
                        "truncated_for_runtime": role.truncated_for_runtime,
                    }
                    for role in segment.roles
                ],
            }
            for segment in caption_segments
        ],
    }
