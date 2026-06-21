from __future__ import annotations

from hashlib import sha256
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mt_clip_factory.factory.preview_composition import PreviewSegmentClip


_SEGMENT_INVENTORY_VERSION = "1.0"


def build_segment_inventory_payload(
    *,
    segments: Sequence["PreviewSegmentClip"],
    resolved_duration_sec: float | None,
) -> dict[str, object]:
    if not segments:
        return {
            "enabled": False,
            "inventory_version": _SEGMENT_INVENTORY_VERSION,
            "segment_count": 0,
            "resolved_clip_duration_sec": _round_optional(resolved_duration_sec),
            "timeline_end_sec": None,
            "distinct_primary_asset_count": 0,
            "distinct_background_asset_count": 0,
            "primary_asset_codes": [],
            "background_asset_codes": [],
            "clip_formula_hash": None,
            "segments": [],
        }

    segment_entries: list[dict[str, object]] = []
    segment_formulas: list[str] = []
    primary_codes: list[str] = []
    background_codes: list[str] = []

    for segment in segments:
        caption_roles = [role.role for role in segment.captions]
        background_layer_payload = None
        background_asset_code = ""
        background_fill_mode = ""
        if segment.background_layer is not None:
            background_asset_code = segment.background_layer.asset_code
            background_fill_mode = segment.background_layer.fill_mode
            background_codes.append(background_asset_code)
            background_layer_payload = {
                "asset_id": segment.background_layer.asset_id,
                "asset_code": segment.background_layer.asset_code,
                "layer_name": segment.background_layer.layer_name,
                "fill_mode": segment.background_layer.fill_mode,
                "source_duration_sec": _round_optional(segment.background_layer.source_duration_sec),
                "source_file": str(segment.background_layer.source_file),
            }

        primary_codes.append(segment.asset_code)
        segment_formula = "|".join(
            (
                str(segment.sequence_index),
                segment.segment_type,
                _format_float(segment.start_sec),
                _format_float(segment.end_sec),
                _format_float(segment.target_duration_sec),
                segment.layer_name,
                segment.asset_code,
                segment.fill_mode,
                _format_float(segment.source_duration_sec),
                background_asset_code,
                background_fill_mode,
                segment.audio_policy or "",
                segment.text_rule or "",
                segment.message_text or "",
                ",".join(caption_roles),
            )
        )
        segment_formulas.append(segment_formula)
        segment_entries.append(
            {
                "sequence_index": segment.sequence_index,
                "segment_type": segment.segment_type,
                "start_sec": _round_optional(segment.start_sec),
                "end_sec": _round_optional(segment.end_sec),
                "target_duration_sec": _round_optional(segment.target_duration_sec),
                "audio_policy": segment.audio_policy,
                "message_text": segment.message_text,
                "text_rule": segment.text_rule,
                "caption_roles": caption_roles,
                "primary_layer": {
                    "asset_id": segment.asset_id,
                    "asset_code": segment.asset_code,
                    "layer_name": segment.layer_name,
                    "fill_mode": segment.fill_mode,
                    "source_duration_sec": _round_optional(segment.source_duration_sec),
                    "source_file": str(segment.source_file),
                },
                "background_layer": background_layer_payload,
                "segment_formula": segment_formula,
                "segment_formula_hash": _hash_text(segment_formula),
            }
        )

    timeline_end_sec = max(segment.end_sec for segment in segments)
    clip_formula_basis = "||".join(segment_formulas)
    return {
        "enabled": True,
        "inventory_version": _SEGMENT_INVENTORY_VERSION,
        "segment_count": len(segment_entries),
        "resolved_clip_duration_sec": _round_optional(resolved_duration_sec),
        "timeline_end_sec": _round_optional(timeline_end_sec),
        "distinct_primary_asset_count": len(dict.fromkeys(primary_codes)),
        "distinct_background_asset_count": len(dict.fromkeys(background_codes)),
        "primary_asset_codes": list(dict.fromkeys(primary_codes)),
        "background_asset_codes": list(dict.fromkeys(background_codes)),
        "clip_formula_hash": _hash_text(clip_formula_basis),
        "segments": segment_entries,
    }


def _hash_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _format_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{float(value):.3f}"


def _round_optional(value: float | None) -> float | None:
    return None if value is None else round(float(value), 3)
