from __future__ import annotations

import pytest

from mt_clip_factory.domain.timeline_segments import TimelineSegment, TimelineSegmentValidationError, validate_timeline_segments


def test_validate_timeline_segments_accepts_contiguous_coverage() -> None:
    segments = [
        TimelineSegment(
            recipe_id=1,
            segment_type="hook",
            sequence_index=1,
            start_sec=0.0,
            end_sec=3.0,
            target_duration_sec=3.0,
        ),
        TimelineSegment(
            recipe_id=1,
            segment_type="cta",
            sequence_index=2,
            start_sec=3.0,
            end_sec=5.0,
            target_duration_sec=2.0,
        ),
    ]

    validated = validate_timeline_segments(segments, resolved_duration_sec=5.0)

    assert len(validated) == 2


def test_validate_timeline_segments_rejects_gaps() -> None:
    segments = [
        TimelineSegment(
            recipe_id=1,
            segment_type="hook",
            sequence_index=1,
            start_sec=0.0,
            end_sec=3.0,
            target_duration_sec=3.0,
        ),
        TimelineSegment(
            recipe_id=1,
            segment_type="cta",
            sequence_index=2,
            start_sec=3.5,
            end_sec=5.0,
            target_duration_sec=1.5,
        ),
    ]

    with pytest.raises(TimelineSegmentValidationError):
        validate_timeline_segments(segments, resolved_duration_sec=5.0)
