from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetricsF, QTextLayout, QTextOption
from PySide6.QtWidgets import QApplication


_DEFAULT_DPI = 96
_DEFAULT_FRAME_SIZE = (720, 1280)


@dataclass(slots=True, frozen=True)
class CaptionFrameContext:
    width_px: int
    height_px: int
    dpi: int = _DEFAULT_DPI


@dataclass(slots=True, frozen=True)
class CaptionLayoutResult:
    rendered_lines: tuple[str, ...]
    rendered_text: str
    font_size_px: int
    overflowed: bool
    review_required: bool
    truncated_for_runtime: bool
    fit_strategy: str
    line_break_mode: str
    line_widths_px: tuple[int, ...]
    line_height_px: int
    line_spacing_px: int
    text_block_width_px: int
    text_block_height_px: int
    max_text_width_px: int
    line_left_positions_px: tuple[int, ...]
    line_top_positions_px: tuple[int, ...]
    box_left_px: int
    box_top_px: int
    box_width_px: int
    box_height_px: int
    frame_width_px: int
    frame_height_px: int


def resolve_caption_layout(
    *,
    source_text: str,
    frame: CaptionFrameContext | None,
    font_family: str,
    font_file: Path | None,
    requested_font_size: int,
    font_size_unit: str,
    min_font_size: int,
    max_lines: int,
    max_chars_per_line: int,
    max_width_ratio: float,
    line_spacing_ratio: float,
    padding: int,
    alignment: str,
    position: str,
    safe_top_ratio: float,
    safe_bottom_ratio: float,
    overflow_policy: str,
    review_required_if_overflow: bool,
) -> CaptionLayoutResult:
    qt_app = _ensure_qt_application()
    del qt_app
    frame_context = frame or CaptionFrameContext(*_DEFAULT_FRAME_SIZE)
    manual_breaks = "\\n" in source_text or "\n" in source_text
    normalized_text = source_text.replace("\\n", "\n")
    font_size_px = _font_size_to_pixels(
        requested_font_size=requested_font_size,
        font_size_unit=font_size_unit,
        dpi=frame_context.dpi,
    )
    minimum_font_px = _font_size_to_pixels(
        requested_font_size=min_font_size,
        font_size_unit=font_size_unit,
        dpi=frame_context.dpi,
    )
    safe_width_px = _safe_max_width(frame_context.width_px, max_width_ratio=max_width_ratio)
    fit_strategy = "manual_breaks" if manual_breaks else "wrapped"
    layout = _layout_text(
        text=normalized_text,
        font=_build_qfont(
            font_family=font_family,
            font_file=font_file,
            pixel_size=font_size_px,
        ),
        max_width_px=safe_width_px,
        manual_breaks=manual_breaks,
        max_lines=max_lines,
        overflow_policy=overflow_policy,
    )
    if not manual_breaks and _needs_balance_adjustment(layout, max_width_px=safe_width_px):
        current_badness = _layout_balance_badness(layout, max_width_px=safe_width_px)
        while font_size_px > minimum_font_px:
            next_font_px = max(minimum_font_px, font_size_px - 2)
            if next_font_px == font_size_px:
                break
            next_layout = _layout_text(
                text=normalized_text,
                font=_build_qfont(
                    font_family=font_family,
                    font_file=font_file,
                    pixel_size=next_font_px,
                ),
                max_width_px=safe_width_px,
                manual_breaks=manual_breaks,
                max_lines=max_lines,
                overflow_policy=overflow_policy,
            )
            next_badness = _layout_balance_badness(next_layout, max_width_px=safe_width_px)
            if next_badness >= current_badness:
                break
            font_size_px = next_font_px
            layout = next_layout
            current_badness = next_badness
            fit_strategy = "scaled_for_balance"
    overflowed = layout.overflowed
    while overflowed and "scale" in overflow_policy and font_size_px > minimum_font_px:
        next_font_px = max(minimum_font_px, font_size_px - max(2, (font_size_px - minimum_font_px) // 2 or 1))
        if next_font_px == font_size_px:
            break
        font_size_px = next_font_px
        layout = _layout_text(
            text=normalized_text,
            font=_build_qfont(
                font_family=font_family,
                font_file=font_file,
                pixel_size=font_size_px,
            ),
            max_width_px=safe_width_px,
            manual_breaks=manual_breaks,
            max_lines=max_lines,
            overflow_policy=overflow_policy,
        )
        overflowed = layout.overflowed
        fit_strategy = "scaled_to_fit"
    if layout.truncated_for_runtime:
        fit_strategy = "truncated_for_runtime"
    line_spacing_px = max(0, round(font_size_px * max(0.0, line_spacing_ratio)))
    line_height_px = layout.line_height_px
    line_widths_px = layout.line_widths_px
    content_width_px = max(line_widths_px, default=0)
    content_height_px = (len(layout.lines) * line_height_px) + (max(0, len(layout.lines) - 1) * line_spacing_px)
    safe_left_px = max(0, round((frame_context.width_px - safe_width_px) / 2))
    safe_top_px = round(frame_context.height_px * _bounded_ratio(safe_top_ratio))
    safe_bottom_px = round(frame_context.height_px * _bounded_ratio(safe_bottom_ratio))
    if safe_bottom_px <= safe_top_px:
        safe_top_px = round(frame_context.height_px * 0.12)
        safe_bottom_px = round(frame_context.height_px * 0.86)
    content_top_px = _resolve_content_top(
        position=position,
        frame_height_px=frame_context.height_px,
        safe_top_px=safe_top_px,
        safe_bottom_px=safe_bottom_px,
        content_height_px=content_height_px,
    )
    line_left_positions_px = tuple(
        _resolve_line_left(
            alignment=alignment,
            safe_left_px=safe_left_px,
            safe_width_px=safe_width_px,
            line_width_px=line_width_px,
        )
        for line_width_px in line_widths_px
    )
    line_top_positions_px = tuple(
        content_top_px + (index * (line_height_px + line_spacing_px))
        for index in range(len(layout.lines))
    )
    if line_left_positions_px:
        box_left_px = max(0, min(line_left_positions_px) - padding)
    else:
        box_left_px = max(0, safe_left_px - padding)
    box_top_px = max(0, content_top_px - padding)
    box_width_px = min(
        frame_context.width_px - box_left_px,
        max(0, content_width_px + (padding * 2)),
    )
    box_height_px = min(
        frame_context.height_px - box_top_px,
        max(0, content_height_px + (padding * 2)),
    )
    return CaptionLayoutResult(
        rendered_lines=layout.lines,
        rendered_text="\n".join(layout.lines),
        font_size_px=font_size_px,
        overflowed=layout.overflowed,
        review_required=layout.overflowed and review_required_if_overflow,
        truncated_for_runtime=layout.truncated_for_runtime,
        fit_strategy=fit_strategy,
        line_break_mode="manual" if manual_breaks else "auto_wrap",
        line_widths_px=line_widths_px,
        line_height_px=line_height_px,
        line_spacing_px=line_spacing_px,
        text_block_width_px=content_width_px,
        text_block_height_px=content_height_px,
        max_text_width_px=safe_width_px,
        line_left_positions_px=line_left_positions_px,
        line_top_positions_px=line_top_positions_px,
        box_left_px=box_left_px,
        box_top_px=box_top_px,
        box_width_px=box_width_px,
        box_height_px=box_height_px,
        frame_width_px=frame_context.width_px,
        frame_height_px=frame_context.height_px,
    )


@dataclass(slots=True, frozen=True)
class _RawLayout:
    lines: tuple[str, ...]
    line_widths_px: tuple[int, ...]
    line_height_px: int
    overflowed: bool
    truncated_for_runtime: bool


def _layout_text(
    *,
    text: str,
    font: QFont,
    max_width_px: int,
    manual_breaks: bool,
    max_lines: int,
    overflow_policy: str,
) -> _RawLayout:
    metrics = QFontMetricsF(font)
    if manual_breaks:
        lines = tuple(text.splitlines() or [""])
        line_widths_px = tuple(round(metrics.horizontalAdvance(line)) for line in lines)
        overflowed = len(lines) > max_lines or any(width > max_width_px for width in line_widths_px)
        truncated_for_runtime = False
        if overflowed and "truncate" in overflow_policy:
            lines = _truncate_lines(lines, font=font, max_width_px=max_width_px, max_lines=max_lines)
            line_widths_px = tuple(round(metrics.horizontalAdvance(line)) for line in lines)
            truncated_for_runtime = True
        return _RawLayout(
            lines=lines,
            line_widths_px=line_widths_px,
            line_height_px=max(1, round(metrics.height())),
            overflowed=overflowed,
            truncated_for_runtime=truncated_for_runtime,
        )
    wrapped_lines = _wrap_text_to_width(text, font=font, max_width_px=max_width_px)
    line_widths_px = tuple(round(metrics.horizontalAdvance(line)) for line in wrapped_lines)
    overflowed = len(wrapped_lines) > max_lines or any(width > max_width_px for width in line_widths_px)
    truncated_for_runtime = False
    if overflowed and "truncate" in overflow_policy:
        wrapped_lines = _truncate_lines(wrapped_lines, font=font, max_width_px=max_width_px, max_lines=max_lines)
        line_widths_px = tuple(round(metrics.horizontalAdvance(line)) for line in wrapped_lines)
        truncated_for_runtime = True
    return _RawLayout(
        lines=wrapped_lines,
        line_widths_px=line_widths_px,
        line_height_px=max(1, round(metrics.height())),
        overflowed=overflowed,
        truncated_for_runtime=truncated_for_runtime,
    )


def _wrap_text_to_width(text: str, *, font: QFont, max_width_px: int) -> tuple[str, ...]:
    wrapped_lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        if not paragraph:
            wrapped_lines.append("")
            continue
        paragraph_lines = _wrap_paragraph_to_width(paragraph, font=font, max_width_px=max_width_px)
        wrapped_lines.extend(paragraph_lines)
    return tuple(wrapped_lines or [""])


def _wrap_paragraph_to_width(paragraph: str, *, font: QFont, max_width_px: int) -> tuple[str, ...]:
    raw_lines = _qt_wrap_paragraph(paragraph, font=font, max_width_px=max_width_px)
    balanced = _balanced_wrap_paragraph(
        paragraph,
        font=font,
        max_width_px=max_width_px,
        target_line_count=len(raw_lines),
    )
    return balanced or raw_lines


def _qt_wrap_paragraph(paragraph: str, *, font: QFont, max_width_px: int) -> tuple[str, ...]:
    wrapped_lines: list[str] = []
    layout = QTextLayout(paragraph, font)
    option = QTextOption()
    option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
    layout.setTextOption(option)
    layout.beginLayout()
    while True:
        line = layout.createLine()
        if not line.isValid():
            break
        line.setLineWidth(max_width_px)
        start = line.textStart()
        length = line.textLength()
        wrapped_lines.append(paragraph[start : start + length].rstrip())
    layout.endLayout()
    return tuple(wrapped_lines or [""])


def _balanced_wrap_paragraph(
    paragraph: str,
    *,
    font: QFont,
    max_width_px: int,
    target_line_count: int,
) -> tuple[str, ...] | None:
    tokens = [token for token in paragraph.split(" ") if token]
    if len(tokens) < 3 or target_line_count <= 1:
        return None
    metrics = QFontMetricsF(font)
    cache: dict[tuple[int, int], int] = {}

    def line_text(start: int, end: int) -> str:
        return " ".join(tokens[start:end]).strip()

    def line_width(start: int, end: int) -> int:
        key = (start, end)
        cached = cache.get(key)
        if cached is not None:
            return cached
        width = round(metrics.horizontalAdvance(line_text(start, end)))
        cache[key] = width
        return width

    best_score: float | None = None
    best_lines: tuple[str, ...] | None = None
    target_width_px = max_width_px * 0.72

    def walk(start: int, lines_left: int, built: list[str], widths: list[int], *, total_line_count: int) -> None:
        nonlocal best_score, best_lines
        remaining = len(tokens) - start
        if lines_left == 0:
            if remaining == 0:
                score = _line_balance_score(widths, target_width_px=target_width_px) + max(0, target_line_count - total_line_count) * 12
                if best_score is None or score < best_score:
                    best_score = score
                    best_lines = tuple(built)
            return
        if remaining < lines_left:
            return
        max_end = len(tokens) - (lines_left - 1)
        for end in range(start + 1, max_end + 1):
            width = line_width(start, end)
            if width > max_width_px:
                break
            walk(
                end,
                lines_left - 1,
                [*built, line_text(start, end)],
                [*widths, width],
                total_line_count=total_line_count,
            )

    for candidate_line_count in range(2, target_line_count + 1):
        walk(0, candidate_line_count, [], [], total_line_count=candidate_line_count)
    return best_lines


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


def _truncate_lines(lines: tuple[str, ...], *, font: QFont, max_width_px: int, max_lines: int) -> tuple[str, ...]:
    metrics = QFontMetricsF(font)
    safe_lines = list(lines[:max_lines]) or [""]
    safe_lines[-1] = metrics.elidedText(safe_lines[-1], Qt.TextElideMode.ElideRight, max_width_px)
    return tuple(safe_lines)


def _resolve_line_left(*, alignment: str, safe_left_px: int, safe_width_px: int, line_width_px: int) -> int:
    normalized = alignment.strip().casefold()
    if normalized == "left":
        return safe_left_px
    if normalized == "right":
        return safe_left_px + max(0, safe_width_px - line_width_px)
    return safe_left_px + max(0, round((safe_width_px - line_width_px) / 2))


def _resolve_content_top(
    *,
    position: str,
    frame_height_px: int,
    safe_top_px: int,
    safe_bottom_px: int,
    content_height_px: int,
) -> int:
    normalized = position.strip().casefold()
    if normalized == "top":
        return max(0, safe_top_px)
    if normalized == "bottom":
        return max(0, safe_bottom_px - content_height_px)
    band_height_px = max(0, safe_bottom_px - safe_top_px)
    if band_height_px <= 0:
        return max(0, round((frame_height_px - content_height_px) / 2))
    return max(0, safe_top_px + round((band_height_px - content_height_px) / 2))


def _safe_max_width(frame_width_px: int, *, max_width_ratio: float) -> int:
    return max(32, round(frame_width_px * max_width_ratio))


def _bounded_ratio(value: float) -> float:
    return min(1.0, max(0.0, value))


def _font_size_to_pixels(*, requested_font_size: int, font_size_unit: str, dpi: int) -> int:
    normalized = font_size_unit.strip().casefold()
    if normalized == "pt":
        return max(1, round(requested_font_size * dpi / 72))
    return max(1, int(requested_font_size))


def _build_qfont(*, font_family: str, font_file: Path | None, pixel_size: int) -> QFont:
    del font_file
    font = QFont(font_family or "Arial")
    font.setPixelSize(max(1, pixel_size))
    return font


def _ensure_qt_application() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication([])
