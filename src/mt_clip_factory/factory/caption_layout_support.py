from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase, QFontMetricsF, QTextLayout, QTextOption
from PySide6.QtWidgets import QApplication


_FONT_FILE_FAMILY_CACHE: dict[Path, str] = {}


@dataclass(slots=True, frozen=True)
class _RawLayout:
    lines: tuple[str, ...]
    line_widths_px: tuple[int, ...]
    line_height_px: int
    overflowed: bool
    truncated_for_runtime: bool
    line_count_exceeded: bool
    width_overflowed: bool


def _resolve_line_metrics(
    *,
    lines: tuple[str, ...],
    font_family: str,
    font_file: Path | None,
    max_font_size_px: int,
    min_font_size_px: int,
    max_width_px: int,
    stroke_width: int,
    allow_per_line_scale: bool,
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...], bool, bool]:
    line_font_sizes: list[int] = []
    line_widths: list[int] = []
    line_heights: list[int] = []
    overflowed = False
    any_scaled = False
    for line in lines:
        resolved_font_size = max_font_size_px
        if allow_per_line_scale and line:
            resolved_font_size = _resolve_line_font_size(
                line=line,
                font_family=font_family,
                font_file=font_file,
                max_font_size_px=max_font_size_px,
                min_font_size_px=min_font_size_px,
                max_width_px=max_width_px,
                stroke_width=stroke_width,
            )
            if resolved_font_size < max_font_size_px:
                any_scaled = True
        font = _build_qfont(font_family=font_family, font_file=font_file, pixel_size=resolved_font_size)
        width_px = _measure_line_width(line, font=font, stroke_width=stroke_width)
        height_px = _measure_line_height(font=font, stroke_width=stroke_width)
        if width_px > max_width_px:
            overflowed = True
        line_font_sizes.append(resolved_font_size)
        line_widths.append(width_px)
        line_heights.append(height_px)
    return tuple(line_font_sizes), tuple(line_widths), tuple(line_heights), overflowed, any_scaled


def _resolve_line_spacing_px(
    *,
    base_font_size_px: int,
    line_heights_px: tuple[int, ...],
    line_spacing_ratio: float,
) -> int:
    if not line_heights_px:
        return 0
    reference_height_px = max(1, round(sum(line_heights_px) / len(line_heights_px)))
    spacing_basis_px = max(reference_height_px, round(base_font_size_px * 0.75))
    return max(0, round(spacing_basis_px * max(0.0, line_spacing_ratio)))


def _resolve_line_font_size(
    *,
    line: str,
    font_family: str,
    font_file: Path | None,
    max_font_size_px: int,
    min_font_size_px: int,
    max_width_px: int,
    stroke_width: int,
) -> int:
    if not line:
        return max_font_size_px
    low = min_font_size_px
    high = max_font_size_px
    best = min_font_size_px
    while low <= high:
        mid = (low + high) // 2
        width_px = _measure_line_width(
            line,
            font=_build_qfont(font_family=font_family, font_file=font_file, pixel_size=mid),
            stroke_width=stroke_width,
        )
        if width_px <= max_width_px:
            best = mid
            low = mid + 1
        else:
            high = mid - 1
    return best


def _layout_text(
    *,
    text: str,
    font: QFont,
    max_width_px: int,
    stroke_width: int,
    manual_breaks: bool,
    max_lines: int,
    overflow_policy: str,
) -> _RawLayout:
    if manual_breaks:
        lines = tuple(text.splitlines() or [""])
        line_widths_px = tuple(_measure_line_width(line, font=font, stroke_width=stroke_width) for line in lines)
        line_count_exceeded = len(lines) > max_lines
        width_overflowed = any(width > max_width_px for width in line_widths_px)
        overflowed = line_count_exceeded or width_overflowed
        truncated_for_runtime = False
        if overflowed and "truncate" in overflow_policy:
            lines = _truncate_lines(lines, font=font, max_width_px=max_width_px, max_lines=max_lines, stroke_width=stroke_width)
            line_widths_px = tuple(_measure_line_width(line, font=font, stroke_width=stroke_width) for line in lines)
            truncated_for_runtime = True
            line_count_exceeded = False
            width_overflowed = any(width > max_width_px for width in line_widths_px)
        return _RawLayout(
            lines=lines,
            line_widths_px=line_widths_px,
            line_height_px=_measure_line_height(font=font, stroke_width=stroke_width),
            overflowed=overflowed,
            truncated_for_runtime=truncated_for_runtime,
            line_count_exceeded=line_count_exceeded,
            width_overflowed=width_overflowed,
        )
    wrapped_lines = _wrap_text_to_width(text, font=font, max_width_px=max_width_px)
    line_widths_px = tuple(_measure_line_width(line, font=font, stroke_width=stroke_width) for line in wrapped_lines)
    line_count_exceeded = len(wrapped_lines) > max_lines
    width_overflowed = any(width > max_width_px for width in line_widths_px)
    overflowed = line_count_exceeded or width_overflowed
    truncated_for_runtime = False
    if overflowed and "truncate" in overflow_policy:
        wrapped_lines = _truncate_lines(wrapped_lines, font=font, max_width_px=max_width_px, max_lines=max_lines, stroke_width=stroke_width)
        line_widths_px = tuple(_measure_line_width(line, font=font, stroke_width=stroke_width) for line in wrapped_lines)
        truncated_for_runtime = True
        line_count_exceeded = False
        width_overflowed = any(width > max_width_px for width in line_widths_px)
    return _RawLayout(
        lines=wrapped_lines,
        line_widths_px=line_widths_px,
        line_height_px=_measure_line_height(font=font, stroke_width=stroke_width),
        overflowed=overflowed,
        truncated_for_runtime=truncated_for_runtime,
        line_count_exceeded=line_count_exceeded,
        width_overflowed=width_overflowed,
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

    def line_balance_score(widths: list[int]) -> float:
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

    def walk(start: int, lines_left: int, built: list[str], widths: list[int], *, total_line_count: int) -> None:
        nonlocal best_score, best_lines
        remaining = len(tokens) - start
        if lines_left == 0:
            if remaining == 0:
                score = line_balance_score(widths) + max(0, target_line_count - total_line_count) * 12
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


def _truncate_lines(lines: tuple[str, ...], *, font: QFont, max_width_px: int, max_lines: int, stroke_width: int) -> tuple[str, ...]:
    metrics = QFontMetricsF(font)
    safe_lines = list(lines[:max_lines]) or [""]
    safe_lines[-1] = metrics.elidedText(
        safe_lines[-1],
        Qt.TextElideMode.ElideRight,
        max(1, max_width_px - max(0, stroke_width * 2)),
    )
    return tuple(safe_lines)


def _measure_line_width(line: str, *, font: QFont, stroke_width: int) -> int:
    metrics = QFontMetricsF(font)
    return max(0, round(metrics.horizontalAdvance(line)) + max(0, stroke_width * 2))


def _measure_line_height(*, font: QFont, stroke_width: int) -> int:
    metrics = QFontMetricsF(font)
    return max(1, round(metrics.height()) + max(0, stroke_width * 2))


def _build_qfont(*, font_family: str, font_file: Path | None, pixel_size: int) -> QFont:
    resolved_family = font_family or "Arial"
    if font_file is not None:
        resolved_family = _resolve_qt_font_family(font_file, fallback_family=resolved_family)
    font = QFont(resolved_family)
    font.setPixelSize(max(1, pixel_size))
    return font


def _resolve_qt_font_family(font_file: Path, *, fallback_family: str) -> str:
    cached_family = _FONT_FILE_FAMILY_CACHE.get(font_file)
    if cached_family is not None:
        return cached_family
    font_id = QFontDatabase.addApplicationFont(str(font_file))
    if font_id < 0:
        _FONT_FILE_FAMILY_CACHE[font_file] = fallback_family
        return fallback_family
    families = QFontDatabase.applicationFontFamilies(font_id)
    resolved = families[0] if families else fallback_family
    _FONT_FILE_FAMILY_CACHE[font_file] = resolved
    return resolved


def _ensure_qt_application() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication([])
