from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class LineBoxGeometry:
    left_positions_px: tuple[int, ...]
    top_positions_px: tuple[int, ...]
    widths_px: tuple[int, ...]
    heights_px: tuple[int, ...]


def textbox_width(frame_width_px: int, *, textbox_width_ratio: float) -> int:
    return max(32, round(frame_width_px * textbox_width_ratio))


def textbox_height(
    *,
    textbox_height_mode: str,
    frame_height_px: int,
    textbox_height_ratio: float,
    content_height_px: int,
    padding: int,
    band_height_px: int,
) -> int:
    minimum_height_px = max(0, content_height_px + (padding * 2))
    normalized_mode = textbox_height_mode.strip().casefold()
    if normalized_mode == "content_hug":
        if band_height_px > 0:
            return min(minimum_height_px, band_height_px)
        return minimum_height_px
    if textbox_height_ratio <= 0:
        return minimum_height_px
    requested_height_px = max((padding * 2) + 1, round(frame_height_px * textbox_height_ratio))
    if band_height_px > 0:
        return min(requested_height_px, band_height_px)
    return requested_height_px


def textbox_content_width(*, textbox_width_px: int, padding: int) -> int:
    return max(16, textbox_width_px - (padding * 2))


def textbox_content_height(*, textbox_height_px: int, padding: int) -> int:
    return max(0, textbox_height_px - (padding * 2))


def effective_wrap_width(*, max_text_width_px: int, stroke_width: int) -> int:
    return max(1, max_text_width_px - max(0, stroke_width * 2))


def resolve_line_left(*, alignment: str, content_left_px: int, content_width_px: int, line_width_px: int) -> int:
    normalized = alignment.strip().casefold()
    if normalized == "left":
        return content_left_px
    if normalized == "right":
        return content_left_px + max(0, content_width_px - line_width_px)
    return content_left_px + max(0, round((content_width_px - line_width_px) / 2))


def resolve_line_top_positions(*, content_top_px: int, line_heights_px: tuple[int, ...], line_spacing_px: int) -> tuple[int, ...]:
    positions: list[int] = []
    cursor = content_top_px
    for index, line_height_px in enumerate(line_heights_px):
        positions.append(cursor)
        cursor += line_height_px
        if index < len(line_heights_px) - 1:
            cursor += line_spacing_px
    return tuple(positions)


def resolve_box_top(
    *,
    position: str,
    frame_height_px: int,
    safe_top_px: int,
    safe_bottom_px: int,
    box_height_px: int,
) -> int:
    normalized = position.strip().casefold()
    if normalized == "top":
        return max(0, safe_top_px)
    if normalized == "bottom":
        return max(0, safe_bottom_px - box_height_px)
    band_height_px = max(0, safe_bottom_px - safe_top_px)
    if band_height_px <= 0:
        return max(0, round((frame_height_px - box_height_px) / 2))
    return max(0, safe_top_px + round((band_height_px - box_height_px) / 2))


def resolve_box_left(*, alignment: str, frame_width_px: int, box_width_px: int) -> int:
    normalized = alignment.strip().casefold()
    if normalized == "left":
        return 0
    if normalized == "right":
        return max(0, frame_width_px - box_width_px)
    return max(0, round((frame_width_px - box_width_px) / 2))


def resolve_content_top_in_box(
    *,
    box_top_px: int,
    box_height_px: int,
    padding: int,
    content_height_px: int,
    vertical_alignment: str,
) -> int:
    content_area_top_px = box_top_px + padding
    content_area_height_px = max(0, box_height_px - (padding * 2))
    normalized = vertical_alignment.strip().casefold()
    if normalized == "bottom":
        return content_area_top_px + max(0, content_area_height_px - content_height_px)
    if normalized == "middle":
        return content_area_top_px + max(0, round((content_area_height_px - content_height_px) / 2))
    return content_area_top_px


def resolve_line_box_geometry(
    *,
    textbox_mode: str,
    outer_box_left_px: int,
    outer_box_top_px: int,
    outer_box_width_px: int,
    outer_box_height_px: int,
    padding: int,
    line_left_positions_px: tuple[int, ...],
    line_top_positions_px: tuple[int, ...],
    line_widths_px: tuple[int, ...],
    line_heights_px: tuple[int, ...],
) -> LineBoxGeometry:
    if textbox_mode.strip().casefold() != "per_line":
        return LineBoxGeometry((), (), (), ())
    lefts: list[int] = []
    tops: list[int] = []
    widths: list[int] = []
    heights: list[int] = []
    outer_box_bottom_px = outer_box_top_px + outer_box_height_px
    outer_box_right_px = outer_box_left_px + outer_box_width_px
    vertical_padding_px = max(4, round(padding * 0.4))
    for line_left_px, line_top_px, line_width_px, line_height_px in zip(
        line_left_positions_px,
        line_top_positions_px,
        line_widths_px,
        line_heights_px,
        strict=False,
    ):
        box_left_px = max(outer_box_left_px, line_left_px - padding)
        box_top_px = max(outer_box_top_px, line_top_px - vertical_padding_px)
        box_width_px = min(outer_box_right_px - box_left_px, max(1, line_width_px + (padding * 2)))
        box_height_px = min(outer_box_bottom_px - box_top_px, max(1, line_height_px + (vertical_padding_px * 2)))
        lefts.append(box_left_px)
        tops.append(box_top_px)
        widths.append(box_width_px)
        heights.append(box_height_px)
    return LineBoxGeometry(
        left_positions_px=tuple(lefts),
        top_positions_px=tuple(tops),
        widths_px=tuple(widths),
        heights_px=tuple(heights),
    )
