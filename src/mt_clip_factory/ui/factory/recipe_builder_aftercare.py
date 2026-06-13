from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from mt_clip_factory.factory.dto import CompositionPlanDTO, DecisionEventDTO, OutputSummaryDTO

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
    return lines


def _build_manifest_review_lines(manifest_path: str | None) -> list[str]:
    payload = _read_manifest_payload(manifest_path)
    review_gate = payload.get("review_gate")
    if not isinstance(review_gate, dict):
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
    audio_mix = payload.get("audio_mix")
    if not isinstance(audio_mix, dict):
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
