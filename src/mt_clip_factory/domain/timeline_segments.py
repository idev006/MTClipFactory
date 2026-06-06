from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from mt_clip_factory.domain.entities import utc_now


SEGMENT_TYPES = ("hook", "problem", "benefit", "proof", "cta")
VALIDATION_TOLERANCE_SEC = 0.02


class TimelineSegmentValidationError(ValueError):
    """Raised when planned timeline segments do not satisfy baseline rules."""


@dataclass(slots=True)
class TimelineSegment:
    recipe_id: int
    segment_type: str
    sequence_index: int
    start_sec: float
    end_sec: float
    target_duration_sec: float
    composition_plan_id: int | None = None
    message_text: str | None = None
    preferred_layers: tuple[str, ...] = ()
    text_rule: str | None = None
    audio_policy: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    id: int | None = None


def validate_timeline_segments(
    segments: Sequence[TimelineSegment],
    *,
    resolved_duration_sec: float | None,
) -> tuple[TimelineSegment, ...]:
    if resolved_duration_sec is None:
        if segments:
            raise TimelineSegmentValidationError("Timeline segments require a resolved master duration.")
        return tuple(segments)

    if resolved_duration_sec <= 0:
        raise TimelineSegmentValidationError("Resolved duration must be positive.")
    if not segments:
        raise TimelineSegmentValidationError("At least one timeline segment is required when duration is resolved.")

    expected_index = 1
    expected_start = 0.0
    for segment in segments:
        _validate_segment_type(segment.segment_type)
        if segment.sequence_index != expected_index:
            raise TimelineSegmentValidationError("Timeline segments must use contiguous sequence indexes.")
        if segment.start_sec < 0 or segment.end_sec <= segment.start_sec:
            raise TimelineSegmentValidationError("Timeline segment timing is invalid.")
        if segment.target_duration_sec <= 0:
            raise TimelineSegmentValidationError("Timeline segment duration must be positive.")
        actual_duration = round(segment.end_sec - segment.start_sec, 3)
        if abs(actual_duration - segment.target_duration_sec) > VALIDATION_TOLERANCE_SEC:
            raise TimelineSegmentValidationError("Timeline segment target duration must match its timing window.")
        if abs(segment.start_sec - expected_start) > VALIDATION_TOLERANCE_SEC:
            raise TimelineSegmentValidationError("Timeline segments must be contiguous from the master timeline start.")
        expected_index += 1
        expected_start = round(segment.end_sec, 3)

    final_end = round(segments[-1].end_sec, 3)
    if abs(final_end - round(resolved_duration_sec, 3)) > VALIDATION_TOLERANCE_SEC:
        raise TimelineSegmentValidationError("Timeline segments must cover the full resolved duration.")
    return tuple(segments)


def _validate_segment_type(segment_type: str) -> None:
    if segment_type not in SEGMENT_TYPES:
        raise TimelineSegmentValidationError(f"Unsupported segment type: {segment_type}")
