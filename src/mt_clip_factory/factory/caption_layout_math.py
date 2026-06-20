from __future__ import annotations

from mt_clip_factory.factory.caption_layout_support import _RawLayout


def _line_balance_score(widths: list[int], *, target_width_px: float) -> float:
    if not widths:
        return float("inf")
    score = 0.0
    for width in widths:
        score += abs(target_width_px - width)
    if len(widths) >= 2:
        last_width = widths[-1]
        previous_width = widths[-2]
        if last_width < (target_width_px * 0.42):
            score += (target_width_px * 2.5)
        score += abs(previous_width - last_width) * 0.5
    return score


def _layout_balance_badness(layout: _RawLayout, *, max_width_px: int) -> float:
    if not layout.line_widths_px:
        return 0.0
    badness = 0.0
    if len(layout.line_widths_px) >= 2:
        last_width = layout.line_widths_px[-1]
        previous_width = layout.line_widths_px[-2]
        orphan_threshold = max(120, round(max_width_px * 0.2))
        if last_width < orphan_threshold and previous_width > round(max_width_px * 0.7):
            badness += (orphan_threshold - last_width) * 12
        badness += abs(previous_width - last_width) * 0.3
    badness += max(layout.line_widths_px, default=0) * 0.01
    badness += len(layout.line_widths_px) * 5
    return badness


def _needs_balance_adjustment(layout: _RawLayout, *, max_width_px: int) -> bool:
    if len(layout.line_widths_px) < 2:
        return False
    last_width = layout.line_widths_px[-1]
    previous_width = layout.line_widths_px[-2]
    orphan_threshold = max(120, round(max_width_px * 0.2))
    return last_width < orphan_threshold and previous_width > round(max_width_px * 0.7)


def _bounded_ratio(value: float) -> float:
    return min(1.0, max(0.0, value))


def _font_size_to_pixels(*, requested_font_size: int, font_size_unit: str, dpi: int) -> int:
    normalized = font_size_unit.strip().casefold()
    if normalized == "pt":
        return max(1, round(requested_font_size * dpi / 72))
    return max(1, int(requested_font_size))
