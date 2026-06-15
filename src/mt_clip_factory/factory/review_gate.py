from __future__ import annotations

from dataclasses import dataclass

from mt_clip_factory.control_center.dto import SystemSettingsDTO
from mt_clip_factory.domain.composition_plans import CompositionPlan
from mt_clip_factory.domain.enums import RecipeStatus
from mt_clip_factory.domain.recipes import Recipe
from mt_clip_factory.factory.preview_composition import PreviewComposition


@dataclass(slots=True, frozen=True)
class ReviewSettings:
    duration_mismatch_sec: float
    max_looped_segments: int
    min_distinct_visual_assets: int
    max_consecutive_same_visual_segments: int


@dataclass(slots=True, frozen=True)
class ReviewSignal:
    code: str
    message: str
    metric_value: float | int | str
    threshold: float | int | str


@dataclass(slots=True, frozen=True)
class ReviewAssessment:
    required: bool
    duplicate_risk: float
    quality_score: float
    summary: str
    signals: tuple[ReviewSignal, ...]
    metrics: dict[str, float | int]


def default_review_settings() -> ReviewSettings:
    return ReviewSettings(
        duration_mismatch_sec=1.0,
        max_looped_segments=2,
        min_distinct_visual_assets=2,
        max_consecutive_same_visual_segments=3,
    )


def review_settings_from_system_settings(settings: SystemSettingsDTO | None) -> ReviewSettings:
    if settings is None:
        return default_review_settings()
    return ReviewSettings(
        duration_mismatch_sec=float(settings.review_duration_mismatch_sec),
        max_looped_segments=int(settings.review_max_looped_segments),
        min_distinct_visual_assets=int(settings.review_min_distinct_visual_assets),
        max_consecutive_same_visual_segments=int(settings.review_max_consecutive_same_visual_segments),
    )


def review_settings_from_provider(system_settings_service) -> ReviewSettings:
    settings = None if system_settings_service is None else system_settings_service.load()
    return review_settings_from_system_settings(settings)


def assess_review_gate(
    *,
    plan: CompositionPlan,
    composition: PreviewComposition,
    settings: ReviewSettings,
    audio_mix_summary: dict | None = None,
) -> ReviewAssessment:
    signals: list[ReviewSignal] = []
    segment_clips = composition.segment_clips
    audio_mix_plan = composition.audio_mix_plan
    target_duration_sec = plan.target_duration_sec
    resolved_duration_sec = plan.resolved_duration_sec
    if target_duration_sec is not None and resolved_duration_sec is not None:
        duration_gap = round(abs(target_duration_sec - resolved_duration_sec), 3)
        if duration_gap > settings.duration_mismatch_sec:
            signals.append(
                ReviewSignal(
                    code="duration_mismatch",
                    message="Resolved duration differs from requested target.",
                    metric_value=duration_gap,
                    threshold=settings.duration_mismatch_sec,
                )
            )
    looped_segments = sum(1 for clip in segment_clips if clip.fill_mode == "loop_to_segment")
    if looped_segments > settings.max_looped_segments:
        signals.append(
            ReviewSignal(
                code="looped_segments",
                message="Too many timeline segments require looped visuals.",
                metric_value=looped_segments,
                threshold=settings.max_looped_segments,
            )
        )
    distinct_visual_assets = len(_distinct_visual_asset_ids(segment_clips))
    if segment_clips and distinct_visual_assets < min(settings.min_distinct_visual_assets, len(segment_clips)):
        signals.append(
            ReviewSignal(
                code="low_visual_diversity",
                message="Too few distinct visual assets support the planned timeline.",
                metric_value=distinct_visual_assets,
                threshold=settings.min_distinct_visual_assets,
            )
        )
    distinct_primary_visual_assets = len(_distinct_primary_visual_asset_ids(segment_clips))
    max_consecutive_same_asset = _max_consecutive_same_asset_segments(segment_clips)
    if (
        distinct_primary_visual_assets > 1
        and max_consecutive_same_asset > settings.max_consecutive_same_visual_segments
    ):
        signals.append(
            ReviewSignal(
                code="repeated_visual_asset",
                message="The same visual asset repeats across too many consecutive segments.",
                metric_value=max_consecutive_same_asset,
                threshold=settings.max_consecutive_same_visual_segments,
            )
        )
    duration_unknown_visual_segments = sum(1 for clip in segment_clips if clip.fill_mode == "duration_unknown")
    duration_unknown_audio_tracks = 0
    if audio_mix_plan is not None:
        duration_unknown_audio_tracks = sum(
            1
            for track in (*audio_mix_plan.voice_tracks, *audio_mix_plan.music_tracks)
            if track.fill_mode == "duration_unknown"
        )
    emergency_fill_count = duration_unknown_visual_segments + duration_unknown_audio_tracks
    if emergency_fill_count > 0:
        signals.append(
            ReviewSignal(
                code="emergency_fill_detected",
                message="Composition used duration-unknown emergency fill for one or more media layers.",
                metric_value=emergency_fill_count,
                threshold=0,
            )
        )
    voice_track_count = _resolve_track_count(audio_mix_summary, track_key="voice_tracks", count_key="voice_track_count")
    music_track_count = _resolve_track_count(audio_mix_summary, track_key="music_tracks", count_key="music_track_count")
    if voice_track_count > 0 and music_track_count > 0:
        ducking_applied = _resolve_ducking_applied(audio_mix_summary)
        if ducking_applied is False:
            signals.append(
                ReviewSignal(
                    code="audio_masking_risk",
                    message="Narration and music overlap without confirmed ducking protection.",
                    metric_value=_resolve_ducking_status(audio_mix_summary),
                    threshold="ducking_applied",
                )
            )
    caption_overflow_roles = sum(
        1
        for clip in segment_clips
        for role in clip.captions
        if role.overflowed
    )
    caption_review_required_roles = sum(
        1
        for clip in segment_clips
        for role in clip.captions
        if role.review_required
    )
    visual_fill_review_segments = sum(
        1
        for clip in segment_clips
        if clip.fill_mode == "review_if_short"
        or (clip.background_layer is not None and clip.background_layer.fill_mode == "review_if_short")
    )
    audio_fill_review_layers = sum(
        1
        for summary in (
            None if audio_mix_summary is None else audio_mix_summary.get("voice_mix"),
            None if audio_mix_summary is None else audio_mix_summary.get("music_mix"),
        )
        if isinstance(summary, dict) and bool(summary.get("review_required"))
    )
    if caption_review_required_roles > 0:
        signals.append(
            ReviewSignal(
                code="caption_overflow_risk",
                message="One or more resolved captions exceeded safe fit policy and require review.",
                metric_value=caption_review_required_roles,
                threshold=0,
            )
        )
    fill_policy_review_count = visual_fill_review_segments + audio_fill_review_layers
    if fill_policy_review_count > 0:
        signals.append(
            ReviewSignal(
                code="fill_policy_review_required",
                message="One or more layers remained short under non-loop fill policy and require review.",
                metric_value=fill_policy_review_count,
                threshold=0,
            )
        )
    duplicate_risk = _duplicate_risk(signals)
    quality_score = round(max(0.0, 1.0 - duplicate_risk), 3)
    summary = "Review required." if signals else "No review gate triggered."
    if signals:
        summary = "; ".join(signal.message for signal in signals)
    return ReviewAssessment(
        required=bool(signals),
        duplicate_risk=duplicate_risk,
        quality_score=quality_score,
        summary=summary,
        signals=tuple(signals),
        metrics={
            "distinct_visual_assets": distinct_visual_assets,
            "looped_segments": looped_segments,
            "max_consecutive_same_asset_segments": max_consecutive_same_asset,
            "segment_count": len(segment_clips),
            "duration_unknown_visual_segments": duration_unknown_visual_segments,
            "duration_unknown_audio_tracks": duration_unknown_audio_tracks,
            "voice_track_count": voice_track_count,
            "music_track_count": music_track_count,
            "caption_overflow_roles": caption_overflow_roles,
            "caption_review_required_roles": caption_review_required_roles,
            "visual_fill_review_segments": visual_fill_review_segments,
            "audio_fill_review_layers": audio_fill_review_layers,
        },
    )


def review_gate_manifest_payload(assessment: ReviewAssessment) -> dict:
    return {
        "required": assessment.required,
        "duplicate_risk": assessment.duplicate_risk,
        "quality_score": assessment.quality_score,
        "summary": assessment.summary,
        "signals": [
            {
                "code": signal.code,
                "message": signal.message,
                "metric_value": signal.metric_value,
                "threshold": signal.threshold,
            }
            for signal in assessment.signals
        ],
        "metrics": dict(assessment.metrics),
    }


def apply_review_gate(uow, *, recipe: Recipe, assessment: ReviewAssessment, required_event: str, cleared_event: str, actor: str, utc_now, record_decision_event) -> None:
    if recipe.id is None:
        raise RuntimeError("Recipe identifier is required for review gate application.")
    event_time = utc_now()
    if assessment.required:
        recipe.status = RecipeStatus.NEEDS_REVIEW
        recipe.decision_actor = actor
        recipe.decision_at = event_time
        recipe.decision_reason = assessment.summary
        uow.recipes.update(recipe)
        record_decision_event(uow, recipe_id=recipe.id, event_type=required_event, actor=actor, reason=assessment.summary, created_at=event_time)
        return
    if recipe.status != RecipeStatus.NEEDS_REVIEW or recipe.decision_actor != actor:
        return
    recipe.status = RecipeStatus.CANDIDATE
    recipe.decision_actor = None
    recipe.decision_at = None
    recipe.decision_reason = None
    uow.recipes.update(recipe)
    record_decision_event(uow, recipe_id=recipe.id, event_type=cleared_event, actor=actor, reason="Review gate cleared after safer preview rebuild.", created_at=event_time)


def _max_consecutive_same_asset_segments(segment_clips) -> int:
    if not segment_clips:
        return 0
    longest = 1
    current = 1
    previous_asset_id = segment_clips[0].asset_id
    for clip in segment_clips[1:]:
        if clip.asset_id == previous_asset_id:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
            previous_asset_id = clip.asset_id
    return longest


def _distinct_visual_asset_ids(segment_clips) -> set[int]:
    asset_ids: set[int] = set()
    for clip in segment_clips:
        asset_ids.add(clip.asset_id)
        if clip.background_layer is not None:
            asset_ids.add(clip.background_layer.asset_id)
    return asset_ids


def _distinct_primary_visual_asset_ids(segment_clips) -> set[int]:
    return {clip.asset_id for clip in segment_clips}


def _duplicate_risk(signals: list[ReviewSignal]) -> float:
    if not signals:
        return 0.0
    return round(min(1.0, 0.25 * len(signals)), 3)


def _resolve_track_count(
    audio_mix_summary: dict | None,
    *,
    track_key: str,
    count_key: str,
) -> int:
    if not isinstance(audio_mix_summary, dict):
        return 0
    tracks = audio_mix_summary.get(track_key)
    if isinstance(tracks, list):
        return len(tracks)
    count = audio_mix_summary.get(count_key)
    return int(count) if isinstance(count, int | float) else 0


def _resolve_ducking_applied(audio_mix_summary: dict | None) -> bool | None:
    if not isinstance(audio_mix_summary, dict):
        return None
    ducking = audio_mix_summary.get("ducking")
    if not isinstance(ducking, dict):
        return None
    applied = ducking.get("applied")
    return applied if isinstance(applied, bool) else None


def _resolve_ducking_status(audio_mix_summary: dict | None) -> str:
    if not isinstance(audio_mix_summary, dict):
        return "unknown"
    ducking = audio_mix_summary.get("ducking")
    if not isinstance(ducking, dict):
        return "ducking_missing"
    reason = ducking.get("reason")
    if isinstance(reason, str) and reason:
        return reason
    mode = ducking.get("mode")
    if isinstance(mode, str) and mode:
        return mode
    return "not_applied"
