from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from mt_clip_factory.factory.dto import CompositionPlanDTO, DecisionEventDTO, OutputSummaryDTO
from mt_clip_factory.factory.manifest_envelope import read_manifest_section

_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass(slots=True, frozen=True)
class RecipeAftercareStatus:
    replacement_event_at: str | None
    replacement_reason: str | None
    historical_output_ids: frozenset[int]
    has_post_replacement_approved_output: bool
    has_post_replacement_output: bool

    @property
    def has_replacement(self) -> bool:
        return self.replacement_event_at is not None

    @property
    def requires_rebuild(self) -> bool:
        return self.has_replacement and not self.has_post_replacement_approved_output


def assess_recipe_aftercare(
    decision_events: list[DecisionEventDTO],
    outputs: list[OutputSummaryDTO],
) -> RecipeAftercareStatus:
    replacement_events = [event for event in decision_events if event.event_type == "recipe_assets_replaced"]
    if not replacement_events:
        return RecipeAftercareStatus(None, None, frozenset(), False, False)

    latest_event = max(replacement_events, key=lambda event: _parse_timestamp(event.created_at) or datetime.min)
    replacement_at = _parse_timestamp(latest_event.created_at)
    if replacement_at is None:
        return RecipeAftercareStatus(latest_event.created_at, latest_event.reason, frozenset(), False, False)

    historical_output_ids = frozenset(
        output.output_id
        for output in outputs
        if (_parse_timestamp(output.created_at) or replacement_at) <= replacement_at
    )
    has_post_replacement_output = any(
        (_parse_timestamp(output.created_at) or datetime.min) > replacement_at for output in outputs
    )
    has_post_replacement_approved_output = any(
        output.approved
        and (_parse_timestamp(output.approved_at) or datetime.min) > replacement_at
        and (_parse_timestamp(output.created_at) or datetime.min) > replacement_at
        for output in outputs
    )
    return RecipeAftercareStatus(
        replacement_event_at=latest_event.created_at,
        replacement_reason=latest_event.reason,
        historical_output_ids=historical_output_ids,
        has_post_replacement_approved_output=has_post_replacement_approved_output,
        has_post_replacement_output=has_post_replacement_output,
    )


def build_aftercare_guidance(status: RecipeAftercareStatus) -> str:
    if not status.has_replacement:
        return "Workflow guidance: Select a recipe to see rebuild and approval guidance."
    if not status.has_post_replacement_output:
        return (
            "Replacement aftercare: This recipe was changed by asset replacement. "
            "Build Preview next. Older outputs remain visible for lineage only."
        )
    if not status.has_post_replacement_approved_output:
        return (
            "Replacement aftercare: A newer preview exists after replacement. "
            "Approve that rebuilt output, then approve the recipe, then build final."
        )
    return (
        "Replacement aftercare: A post-replacement output has already been approved. "
        "Continue with normal recipe approval or final build as needed."
    )


def format_output_aftercare_state(output: OutputSummaryDTO, status: RecipeAftercareStatus) -> str:
    if not status.has_replacement:
        return ""
    if output.output_id in status.historical_output_ids:
        return "Historical only"
    if output.approved and status.has_post_replacement_approved_output:
        return "Current approved"
    return "Post-replacement"


def build_output_detail_lines(
    output: OutputSummaryDTO,
    composition_plan: CompositionPlanDTO | None,
    decision_events: list[DecisionEventDTO],
) -> list[str]:
    aftercare = assess_recipe_aftercare(decision_events, [output])
    lines = [
        f"Output ID: {output.output_id}",
        f"Recipe: {output.recipe_code} (#{output.recipe_id})",
        f"Kind: {output.output_kind}",
        f"Aftercare State: {format_output_aftercare_state(output, aftercare) or '-'}",
        f"Approved: {output.approved}",
        f"Approved By: {output.approved_by or '-'}",
        f"Approved At: {output.approved_at or '-'}",
        f"Approval Reason: {output.approval_reason or '-'}",
        f"Created At: {output.created_at}",
        f"Platform: {output.platform or '-'}",
        f"Ratio: {output.ratio or '-'}",
        f"Render Job Code: {output.rendering_job_code or '-'}",
        f"Manifest Path: {output.manifest_path or '-'}",
        f"Source Output ID: {output.source_output_id or '-'}",
        f"Source Output Code: {output.source_output_code or '-'}",
        f"Source Output Path: {output.source_output_path or '-'}",
        f"Quality Score: {output.quality_score if output.quality_score is not None else '-'}",
        f"Duplicate Risk: {output.duplicate_risk if output.duplicate_risk is not None else '-'}",
        f"File Path: {output.file_path}",
    ]
    if aftercare.has_replacement:
        lines.extend(
            [
                "",
                f"Replacement Event At: {aftercare.replacement_event_at or '-'}",
                f"Replacement Reason: {aftercare.replacement_reason or '-'}",
                f"Historical Only: {'yes' if output.output_id in aftercare.historical_output_ids else 'no'}",
            ]
        )
    if composition_plan is not None:
        lines.extend(
            [
                "",
                f"Composition Plan ID: {composition_plan.plan_id}",
                f"Duration Source: {composition_plan.duration_source}",
                f"Resolved Duration: {composition_plan.resolved_duration_sec or '-'}",
                f"Timeline Segments: {len(composition_plan.segments)}",
                f"Render Decisions: {len(composition_plan.decisions)}",
            ]
        )
        for segment in composition_plan.segments:
            lines.append(
                f"- Segment {segment.sequence_index}: {segment.segment_type} "
                f"{segment.start_sec:.3f}-{segment.end_sec:.3f}s | audio={segment.audio_policy or '-'}"
            )
        for decision in composition_plan.decisions[:6]:
            lines.append(
                f"- Decision: {decision.decision_type} -> {decision.action}"
                f"{f' | role={decision.asset_role}' if decision.asset_role else ''}"
            )
        if len(composition_plan.decisions) > 6:
            lines.append(f"- More Decisions: {len(composition_plan.decisions) - 6}")
    lines.extend(_build_manifest_review_lines(output.manifest_path))
    lines.extend(_build_manifest_audio_lines(output.manifest_path))
    lines.extend(_build_manifest_visual_lines(output.manifest_path))
    lines.extend(_build_manifest_segment_inventory_lines(output.manifest_path))
    lines.extend(_build_manifest_caption_lines(output.manifest_path))
    return lines


def _build_manifest_review_lines(manifest_path: str | None) -> list[str]:
    payload = _read_manifest_payload(manifest_path)
    review_gate = read_manifest_section(payload, section_name="quality", legacy_key="review_gate")
    if not review_gate:
        return []
    lines = [
        "",
        "Review Gate:",
        f"- Required: {review_gate.get('required', '-')}",
        f"- Duplicate Risk: {review_gate.get('duplicate_risk', '-')}",
        f"- Quality Score: {review_gate.get('quality_score', '-')}",
        f"- Summary: {review_gate.get('summary', '-')}",
    ]
    signals = review_gate.get("signals")
    if isinstance(signals, list):
        for signal in signals:
            if not isinstance(signal, dict):
                continue
            lines.append(
                f"- Signal: {signal.get('code', '-')} | value={signal.get('metric_value', '-')} | threshold={signal.get('threshold', '-')}"
            )
    metrics = review_gate.get("metrics")
    if isinstance(metrics, dict):
        for metric_name, metric_value in sorted(metrics.items()):
            lines.append(f"- Metric: {metric_name}={metric_value}")
    return lines


def _build_manifest_audio_lines(manifest_path: str | None) -> list[str]:
    payload = _read_manifest_payload(manifest_path)
    audio_mix = read_manifest_section(payload, section_name="render", legacy_key="audio_mix")
    if not audio_mix:
        return []
    lines = [
        "",
        "Runtime Audio Mix:",
        f"- Mode: {audio_mix.get('mode', '-')}",
        f"- Audio Present: {audio_mix.get('audio_present', '-')}",
        f"- Voice Loop Applied: {audio_mix.get('voice_loop_applied', '-')}",
    ]
    mix_balance = audio_mix.get("mix_balance")
    if isinstance(mix_balance, dict):
        lines.append(f"- Mix Strategy: {mix_balance.get('strategy', '-')}")
        lines.append(f"- Voice Mix Gain (dB): {mix_balance.get('voice_mix_gain_db', '-')}")
        lines.append(f"- Music Mix Gain (dB): {mix_balance.get('music_mix_gain_db', '-')}")
    ducking = audio_mix.get("ducking")
    if isinstance(ducking, dict):
        lines.append(f"- Duck Applied: {ducking.get('applied', '-')}")
        lines.append(f"- Duck Mode: {ducking.get('mode', ducking.get('reason', '-'))}")
        if ducking.get("duck_db") is not None:
            lines.append(f"- Duck Gain (dB): {ducking.get('duck_db')}")
        if ducking.get("threshold_db") is not None:
            lines.append(f"- Duck Threshold (dB): {ducking.get('threshold_db')}")
        if ducking.get("ratio") is not None:
            lines.append(f"- Duck Ratio: {ducking.get('ratio')}")
    voice_tracks = audio_mix.get("voice_tracks")
    music_tracks = audio_mix.get("music_tracks")
    if isinstance(voice_tracks, list):
        lines.append(f"- Voice Track Count: {len(voice_tracks)}")
    if isinstance(music_tracks, list):
        lines.append(f"- Music Track Count: {len(music_tracks)}")
    return lines


def _build_manifest_visual_lines(manifest_path: str | None) -> list[str]:
    payload = _read_manifest_payload(manifest_path)
    visual_composite = read_manifest_section(payload, section_name="render", legacy_key="visual_composite")
    if not visual_composite:
        return []
    lines = [
        "",
        "Runtime Visual Composite:",
        f"- Mode: {visual_composite.get('mode', '-')}",
        f"- Background Segment Count: {visual_composite.get('background_segment_count', '-')}",
        f"- Keyed Segment Count: {visual_composite.get('keyed_segment_count', '-')}",
    ]
    segments = visual_composite.get("segments")
    if isinstance(segments, list):
        for segment in segments[:5]:
            if not isinstance(segment, dict):
                continue
            lines.append(
                f"- Segment Composite: #{segment.get('sequence_index', '-')} "
                f"{segment.get('segment_type', '-')} | mode={segment.get('composite_mode', '-')} "
                f"| primary={segment.get('primary_asset_code', '-')} "
                f"| background={segment.get('background_asset_code', '-')}"
            )
            if segment.get("key_color_profile") is not None:
                lines.append(
                    f"- Key Policy: {segment.get('key_color_profile', '-')} | color={segment.get('key_color', '-')}"
                )
        if len(segments) > 5:
            lines.append(f"- More Segment Composites: {len(segments) - 5}")
    return lines


def _build_manifest_segment_inventory_lines(manifest_path: str | None) -> list[str]:
    payload = _read_manifest_payload(manifest_path)
    segment_inventory = read_manifest_section(payload, section_name="composition", legacy_key="segment_inventory")
    if not segment_inventory or not segment_inventory.get("enabled"):
        return []
    lines = [
        "",
        "Segment Inventory:",
        f"- Segment Count: {segment_inventory.get('segment_count', '-')}",
        f"- Resolved Clip Duration (s): {segment_inventory.get('resolved_clip_duration_sec', '-')}",
        f"- Distinct Primary Assets: {segment_inventory.get('distinct_primary_asset_count', '-')}",
        f"- Distinct Background Assets: {segment_inventory.get('distinct_background_asset_count', '-')}",
        f"- Clip Formula Hash: {segment_inventory.get('clip_formula_hash', '-')}",
    ]
    segments = segment_inventory.get("segments")
    if isinstance(segments, list):
        for segment in segments[:5]:
            if not isinstance(segment, dict):
                continue
            primary_layer = segment.get("primary_layer")
            background_layer = segment.get("background_layer")
            if not isinstance(primary_layer, dict):
                continue
            background_asset_code = "-"
            background_fill_mode = "-"
            if isinstance(background_layer, dict):
                background_asset_code = str(background_layer.get("asset_code", "-"))
                background_fill_mode = str(background_layer.get("fill_mode", "-"))
            lines.append(
                f"- Segment Asset: #{segment.get('sequence_index', '-')} {segment.get('segment_type', '-')} "
                f"| {segment.get('start_sec', '-')}-{segment.get('end_sec', '-')}s "
                f"| primary={primary_layer.get('asset_code', '-')} ({primary_layer.get('fill_mode', '-')}) "
                f"| background={background_asset_code} ({background_fill_mode})"
            )
        if len(segments) > 5:
            lines.append(f"- More Inventory Segments: {len(segments) - 5}")
    return lines


def _build_manifest_caption_lines(manifest_path: str | None) -> list[str]:
    payload = _read_manifest_payload(manifest_path)
    captions = read_manifest_section(payload, section_name="composition", legacy_key="captions")
    if not captions or not captions.get("enabled"):
        return []
    lines = [
        "",
        "Runtime Captions:",
        f"- Segment Count: {captions.get('segment_count', '-')}",
        f"- Role Count: {captions.get('role_count', '-')}",
        f"- Overflow Role Count: {captions.get('overflow_role_count', '-')}",
        f"- Review Required Role Count: {captions.get('review_required_role_count', '-')}",
    ]
    segments = captions.get("segments")
    if isinstance(segments, list):
        for segment in segments[:5]:
            if not isinstance(segment, dict):
                continue
            segment_prefix = (
                f"- Caption Segment: #{segment.get('sequence_index', '-')} "
                f"{segment.get('segment_type', '-')}"
            )
            lines.append(segment_prefix)
            roles = segment.get("roles")
            if not isinstance(roles, list):
                continue
            for role in roles[:2]:
                if not isinstance(role, dict):
                    continue
                lines.append(
                    f"- Caption Role: {role.get('role', '-')} | fit={role.get('fit_strategy', '-')} "
                    f"| font={role.get('font_resolution_target', role.get('font_family', '-'))} "
                    f"| review={role.get('review_required', '-')}"
                )
                lines.append(f"- Caption Text: {role.get('rendered_text', '-')}")
        if len(segments) > 5:
            lines.append(f"- More Caption Segments: {len(segments) - 5}")
    return lines


def _read_manifest_payload(manifest_path: str | None) -> dict:
    if not manifest_path:
        return {}
    manifest_file = Path(manifest_path)
    if not manifest_file.exists():
        return {}
    try:
        payload = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, _TIMESTAMP_FORMAT)
    except ValueError:
        return None
