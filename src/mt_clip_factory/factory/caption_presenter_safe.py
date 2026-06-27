from __future__ import annotations


def resolve_presenter_safe_shift_px(
    *,
    role: str,
    textbox_mode: str,
    frame_width_px: int,
    frame_height_px: int,
    box_left_px: int,
    box_top_px: int,
    box_width_px: int,
    box_height_px: int,
    effective_safe_bottom_ratio: float,
) -> int:
    if role.strip().casefold() != "main":
        return 0
    if textbox_mode.strip().casefold() != "per_line":
        return 0
    if frame_width_px <= 0 or frame_height_px <= 0 or box_width_px <= 0 or box_height_px <= 0:
        return 0
    if box_top_px >= round(frame_height_px * 0.34):
        return 0
    if effective_safe_bottom_ratio > 0.56:
        return 0

    zone_left = round(frame_width_px * 0.30)
    zone_right = round(frame_width_px * 0.70)
    zone_top = round(frame_height_px * 0.09)
    zone_bottom = round(frame_height_px * 0.40)
    if not _rectangles_overlap(
        left_a=box_left_px,
        top_a=box_top_px,
        right_a=box_left_px + box_width_px,
        bottom_a=box_top_px + box_height_px,
        left_b=zone_left,
        top_b=zone_top,
        right_b=zone_right,
        bottom_b=zone_bottom,
    ):
        return 0

    edge_margin_px = max(12, round(frame_width_px * 0.04))
    zone_gap_px = max(8, round(frame_width_px * 0.015))
    min_left_px = edge_margin_px
    max_left_px = max(edge_margin_px, frame_width_px - edge_margin_px - box_width_px)

    left_delta = (zone_left - zone_gap_px) - (box_left_px + box_width_px)
    right_delta = (zone_right + zone_gap_px) - box_left_px
    candidates = []
    for delta in (left_delta, right_delta):
        shifted_left_px = box_left_px + delta
        if shifted_left_px < min_left_px or shifted_left_px > max_left_px:
            continue
        candidates.append(delta)
    if candidates:
        return min(candidates, key=lambda delta: (abs(delta), delta > 0))

    edge_deltas = (min_left_px - box_left_px, max_left_px - box_left_px)
    return min(
        edge_deltas,
        key=lambda delta: (
            _horizontal_overlap_width(
                left_a=box_left_px + delta,
                right_a=box_left_px + delta + box_width_px,
                left_b=zone_left,
                right_b=zone_right,
            ),
            abs(delta),
            delta > 0,
        ),
    )


def _rectangles_overlap(
    *,
    left_a: int,
    top_a: int,
    right_a: int,
    bottom_a: int,
    left_b: int,
    top_b: int,
    right_b: int,
    bottom_b: int,
) -> bool:
    return left_a < right_b and right_a > left_b and top_a < bottom_b and bottom_a > top_b


def _horizontal_overlap_width(
    *,
    left_a: int,
    right_a: int,
    left_b: int,
    right_b: int,
) -> int:
    return max(0, min(right_a, right_b) - max(left_a, left_b))
