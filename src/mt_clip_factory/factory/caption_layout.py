from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from mt_clip_factory.factory.caption_textbox_geometry import (
    effective_wrap_width,
    resolve_box_left,
    resolve_box_top,
    resolve_content_top_in_box,
    resolve_line_box_geometry,
    resolve_line_left,
    resolve_line_top_positions,
    textbox_content_height,
    textbox_content_width,
    textbox_height,
    textbox_width,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase, QFontMetricsF, QTextLayout, QTextOption
from PySide6.QtWidgets import QApplication


_DEFAULT_DPI = 96
_DEFAULT_FRAME_SIZE = (720, 1280)
_FONT_FILE_FAMILY_CACHE: dict[Path, str] = {}


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
    line_font_sizes_px: tuple[int, ...]
    overflowed: bool
    review_required: bool
    truncated_for_runtime: bool
    fit_strategy: str
    line_break_mode: str
    line_widths_px: tuple[int, ...]
    line_height_px: int
    line_heights_px: tuple[int, ...]
    line_spacing_px: int
    text_block_width_px: int
    text_block_height_px: int
    max_text_width_px: int
    line_left_positions_px: tuple[int, ...]
    line_top_positions_px: tuple[int, ...]
    textbox_mode: str
    line_box_left_positions_px: tuple[int, ...]
    line_box_top_positions_px: tuple[int, ...]
    line_box_widths_px: tuple[int, ...]
    line_box_heights_px: tuple[int, ...]
    box_left_px: int
    box_top_px: int
    box_width_px: int
    box_height_px: int
    frame_width_px: int
    frame_height_px: int


@dataclass(slots=True, frozen=True)
class _RawLayout:
    lines: tuple[str, ...]
    line_widths_px: tuple[int, ...]
    line_height_px: int
    overflowed: bool
    truncated_for_runtime: bool
    line_count_exceeded: bool
    width_overflowed: bool


@dataclass(slots=True, frozen=True)
class _LayoutCandidate:
    lines: tuple[str, ...]
    font_size_px: int
    line_font_sizes_px: tuple[int, ...]
    line_widths_px: tuple[int, ...]
    line_height_px: int
    line_heights_px: tuple[int, ...]
    line_spacing_px: int
    text_block_width_px: int
    text_block_height_px: int
    box_height_px: int
    content_height_capacity_px: int
    overflowed: bool
    truncated_for_runtime: bool
    fit_strategy: str
    line_break_mode: str
    score: float
    any_line_grown: bool


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
    textbox_mode: str,
    textbox_width_ratio: float,
    textbox_height_ratio: float,
    textbox_alignment: str,
    line_spacing_ratio: float,
    padding: int,
    alignment: str,
    vertical_alignment: str,
    position: str,
    stroke_width: int,
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
    textbox_width_px = textbox_width(frame_context.width_px, textbox_width_ratio=textbox_width_ratio)
    max_text_width_px = textbox_content_width(textbox_width_px=textbox_width_px, padding=padding)
    safe_top_px = round(frame_context.height_px * _bounded_ratio(safe_top_ratio))
    safe_bottom_px = round(frame_context.height_px * _bounded_ratio(safe_bottom_ratio))
    if safe_bottom_px <= safe_top_px:
        safe_top_px = round(frame_context.height_px * 0.12)
        safe_bottom_px = round(frame_context.height_px * 0.86)
    band_height_px = max(0, safe_bottom_px - safe_top_px)
    candidate = _solve_best_fit_layout(
        text=normalized_text,
        font_family=font_family,
        font_file=font_file,
        requested_font_size_px=font_size_px,
        min_font_size_px=minimum_font_px,
        max_width_px=max_text_width_px,
        stroke_width=stroke_width,
        max_lines=max_lines,
        overflow_policy=overflow_policy,
        manual_breaks=manual_breaks,
        padding=padding,
        textbox_height_ratio=textbox_height_ratio,
        frame_height_px=frame_context.height_px,
        band_height_px=band_height_px,
        line_spacing_ratio=line_spacing_ratio,
    )
    box_left_px = resolve_box_left(
        alignment=textbox_alignment,
        frame_width_px=frame_context.width_px,
        box_width_px=textbox_width_px,
    )
    box_top_px = resolve_box_top(
        position=position,
        frame_height_px=frame_context.height_px,
        safe_top_px=safe_top_px,
        safe_bottom_px=safe_bottom_px,
        box_height_px=candidate.box_height_px,
    )
    content_left_px = box_left_px + padding
    content_top_px = resolve_content_top_in_box(
        box_top_px=box_top_px,
        box_height_px=candidate.box_height_px,
        padding=padding,
        content_height_px=candidate.text_block_height_px,
        vertical_alignment=vertical_alignment,
    )
    line_left_positions_px = tuple(
        resolve_line_left(
            alignment=alignment,
            content_left_px=content_left_px,
            content_width_px=max_text_width_px,
            line_width_px=line_width_px,
        )
        for line_width_px in candidate.line_widths_px
    )
    line_top_positions_px = resolve_line_top_positions(
        content_top_px=content_top_px,
        line_heights_px=candidate.line_heights_px,
        line_spacing_px=candidate.line_spacing_px,
    )
    line_box_geometry = resolve_line_box_geometry(
        textbox_mode=textbox_mode,
        outer_box_left_px=box_left_px,
        outer_box_top_px=box_top_px,
        outer_box_width_px=textbox_width_px,
        outer_box_height_px=candidate.box_height_px,
        padding=padding,
        line_left_positions_px=line_left_positions_px,
        line_top_positions_px=line_top_positions_px,
        line_widths_px=candidate.line_widths_px,
        line_heights_px=candidate.line_heights_px,
    )
    return CaptionLayoutResult(
        rendered_lines=candidate.lines,
        rendered_text="\n".join(candidate.lines),
        font_size_px=candidate.font_size_px,
        line_font_sizes_px=candidate.line_font_sizes_px,
        overflowed=candidate.overflowed,
        review_required=candidate.overflowed and review_required_if_overflow,
        truncated_for_runtime=candidate.truncated_for_runtime,
        fit_strategy=candidate.fit_strategy,
        line_break_mode="manual" if manual_breaks else "auto_wrap",
        line_widths_px=candidate.line_widths_px,
        line_height_px=candidate.line_height_px,
        line_heights_px=candidate.line_heights_px,
        line_spacing_px=candidate.line_spacing_px,
        text_block_width_px=candidate.text_block_width_px,
        text_block_height_px=candidate.text_block_height_px,
        max_text_width_px=max_text_width_px,
        line_left_positions_px=line_left_positions_px,
        line_top_positions_px=line_top_positions_px,
        textbox_mode=textbox_mode,
        line_box_left_positions_px=line_box_geometry.left_positions_px,
        line_box_top_positions_px=line_box_geometry.top_positions_px,
        line_box_widths_px=line_box_geometry.widths_px,
        line_box_heights_px=line_box_geometry.heights_px,
        box_left_px=box_left_px,
        box_top_px=box_top_px,
        box_width_px=textbox_width_px,
        box_height_px=candidate.box_height_px,
        frame_width_px=frame_context.width_px,
        frame_height_px=frame_context.height_px,
    )


def _solve_best_fit_layout(
    *,
    text: str,
    font_family: str,
    font_file: Path | None,
    requested_font_size_px: int,
    min_font_size_px: int,
    max_width_px: int,
    stroke_width: int,
    max_lines: int,
    overflow_policy: str,
    manual_breaks: bool,
    padding: int,
    textbox_height_ratio: float,
    frame_height_px: int,
    band_height_px: int,
    line_spacing_ratio: float,
) -> _LayoutCandidate:
    best_candidate: _LayoutCandidate | None = None
    for candidate_font_size_px in range(requested_font_size_px, min_font_size_px - 1, -1):
        raw_layout = _layout_text(
            text=text,
            font=_build_qfont(
                font_family=font_family,
                font_file=font_file,
                pixel_size=candidate_font_size_px,
            ),
            max_width_px=effective_wrap_width(max_text_width_px=max_width_px, stroke_width=stroke_width),
            stroke_width=stroke_width,
            manual_breaks=manual_breaks,
            max_lines=max_lines,
            overflow_policy=overflow_policy,
        )
        line_font_sizes_px, line_widths_px, line_heights_px, per_line_width_overflow, any_line_scaled = _resolve_line_metrics(
            lines=raw_layout.lines,
            font_family=font_family,
            font_file=font_file,
            max_font_size_px=candidate_font_size_px,
            min_font_size_px=min_font_size_px,
            max_width_px=max_width_px,
            stroke_width=stroke_width,
            allow_per_line_scale=manual_breaks,
        )
        line_spacing_px = _resolve_line_spacing_px(
            base_font_size_px=candidate_font_size_px,
            line_heights_px=line_heights_px,
            line_spacing_ratio=line_spacing_ratio,
        )
        text_block_width_px = max(line_widths_px, default=0)
        text_block_height_px = sum(line_heights_px) + (max(0, len(raw_layout.lines) - 1) * line_spacing_px)
        box_height_px = min(
            frame_height_px if band_height_px <= 0 else band_height_px,
            textbox_height(
                frame_height_px=frame_height_px,
                textbox_height_ratio=textbox_height_ratio,
                content_height_px=text_block_height_px,
                padding=padding,
                band_height_px=band_height_px,
            ),
        )
        content_height_capacity_px = textbox_content_height(textbox_height_px=box_height_px, padding=padding)
        any_line_grown = False
        if manual_breaks and textbox_height_ratio > 0 and not raw_layout.truncated_for_runtime:
            (
                line_font_sizes_px,
                line_widths_px,
                line_heights_px,
                line_spacing_px,
                any_line_grown,
            ) = _grow_manual_line_sizes_to_fill_textbox(
                lines=raw_layout.lines,
                font_family=font_family,
                font_file=font_file,
                current_line_font_sizes_px=line_font_sizes_px,
                max_font_size_px=requested_font_size_px,
                max_width_px=max_width_px,
                content_height_capacity_px=content_height_capacity_px,
                stroke_width=stroke_width,
                line_spacing_ratio=line_spacing_ratio,
            )
        height_overflowed = text_block_height_px > content_height_capacity_px
        text_block_width_px = max(line_widths_px, default=0)
        text_block_height_px = sum(line_heights_px) + (max(0, len(raw_layout.lines) - 1) * line_spacing_px)
        height_overflowed = text_block_height_px > content_height_capacity_px
        overflowed = (
            raw_layout.line_count_exceeded
            or per_line_width_overflow
            or height_overflowed
            or raw_layout.truncated_for_runtime
        )
        fit_strategy = _resolve_fit_strategy(
            manual_breaks=manual_breaks,
            raw_layout=raw_layout,
            requested_font_size_px=requested_font_size_px,
            resolved_font_size_px=candidate_font_size_px,
            any_line_scaled=any_line_scaled,
            any_line_grown=any_line_grown,
        )
        candidate = _LayoutCandidate(
            lines=raw_layout.lines,
            font_size_px=candidate_font_size_px,
            line_font_sizes_px=line_font_sizes_px,
            line_widths_px=line_widths_px,
            line_height_px=max(line_heights_px, default=raw_layout.line_height_px),
            line_heights_px=line_heights_px,
            line_spacing_px=line_spacing_px,
            text_block_width_px=text_block_width_px,
            text_block_height_px=text_block_height_px,
            box_height_px=box_height_px,
            content_height_capacity_px=content_height_capacity_px,
            overflowed=overflowed,
            truncated_for_runtime=raw_layout.truncated_for_runtime,
            fit_strategy=fit_strategy,
            line_break_mode="manual" if manual_breaks else "auto_wrap",
            score=_score_layout_candidate(
                lines=raw_layout.lines,
                line_widths_px=line_widths_px,
                line_font_sizes_px=line_font_sizes_px,
                font_size_px=candidate_font_size_px,
                requested_font_size_px=requested_font_size_px,
                max_width_px=max_width_px,
                text_block_height_px=text_block_height_px,
                content_height_capacity_px=content_height_capacity_px,
                overflowed=overflowed,
                line_count_exceeded=raw_layout.line_count_exceeded,
                per_line_width_overflow=per_line_width_overflow,
                height_overflowed=height_overflowed,
                truncated_for_runtime=raw_layout.truncated_for_runtime,
            ),
            any_line_grown=any_line_grown,
        )
        if best_candidate is None or _candidate_sort_key(candidate) < _candidate_sort_key(best_candidate):
            best_candidate = candidate
    if best_candidate is None:
        raise ValueError("Caption solver could not evaluate any layout candidates.")
    return best_candidate


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


def _resolve_fit_strategy(
    *,
    manual_breaks: bool,
    raw_layout: _RawLayout,
    requested_font_size_px: int,
    resolved_font_size_px: int,
    any_line_scaled: bool,
    any_line_grown: bool,
) -> str:
    if raw_layout.truncated_for_runtime:
        return "truncated_for_runtime"
    if manual_breaks:
        if any_line_grown:
            return "per_line_best_fit"
        if any_line_scaled:
            return "per_line_scaled_to_fit"
        if resolved_font_size_px < requested_font_size_px:
            return "scaled_to_fit"
        return "manual_breaks"
    if resolved_font_size_px < requested_font_size_px:
        return "scaled_to_fit"
    return "wrapped"


def _candidate_sort_key(candidate: _LayoutCandidate) -> tuple[float, ...]:
    return (
        1.0 if candidate.overflowed else 0.0,
        -float(candidate.font_size_px),
        candidate.score,
        float(candidate.text_block_height_px),
    )


def _score_layout_candidate(
    *,
    lines: tuple[str, ...],
    line_widths_px: tuple[int, ...],
    line_font_sizes_px: tuple[int, ...],
    font_size_px: int,
    requested_font_size_px: int,
    max_width_px: int,
    text_block_height_px: int,
    content_height_capacity_px: int,
    overflowed: bool,
    line_count_exceeded: bool,
    per_line_width_overflow: bool,
    height_overflowed: bool,
    truncated_for_runtime: bool,
) -> float:
    target_width_px = max_width_px * (0.88 if len(line_widths_px) <= 1 else 0.78)
    width_balance_penalty = _line_balance_score(list(line_widths_px), target_width_px=target_width_px)
    width_underfill_penalty = sum(max(0.0, (target_width_px - width) * 0.25) for width in line_widths_px)
    font_variance_penalty = (
        0.0
        if not line_font_sizes_px
        else (max(line_font_sizes_px) - min(line_font_sizes_px)) * 2.0
    )
    whitespace_penalty = max(0.0, (content_height_capacity_px - text_block_height_px) * 0.02)
    downscale_penalty = max(0.0, requested_font_size_px - font_size_px) * 6.0
    occupancy_reward = sum(min(width / max(1, max_width_px), 1.0) for width in line_widths_px) * -180.0
    overflow_penalty = 0.0
    if overflowed:
        overflow_penalty += 1_000_000.0
    if line_count_exceeded:
        overflow_penalty += 250_000.0
    if per_line_width_overflow:
        overflow_penalty += 150_000.0
    if height_overflowed:
        overflow_penalty += 150_000.0
    if truncated_for_runtime:
        overflow_penalty += 200_000.0
    if len(lines) >= 2:
        width_balance_penalty += _layout_balance_badness(
            _RawLayout(
                lines=lines,
                line_widths_px=line_widths_px,
                line_height_px=0,
                overflowed=overflowed,
                truncated_for_runtime=truncated_for_runtime,
                line_count_exceeded=line_count_exceeded,
                width_overflowed=per_line_width_overflow,
            ),
            max_width_px=max_width_px,
        )
    return overflow_penalty + downscale_penalty + width_balance_penalty + width_underfill_penalty + font_variance_penalty + whitespace_penalty + occupancy_reward


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


def _grow_manual_line_sizes_to_fill_textbox(
    *,
    lines: tuple[str, ...],
    font_family: str,
    font_file: Path | None,
    current_line_font_sizes_px: tuple[int, ...],
    max_font_size_px: int,
    max_width_px: int,
    content_height_capacity_px: int,
    stroke_width: int,
    line_spacing_ratio: float,
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...], int, bool]:
    line_sizes = list(current_line_font_sizes_px)
    any_line_grown = False
    if not lines or not line_sizes:
        return current_line_font_sizes_px, (), (), 0, False

    def measure(sizes: list[int]) -> tuple[tuple[int, ...], tuple[int, ...], int, int]:
        widths: list[int] = []
        heights: list[int] = []
        for line, size in zip(lines, sizes, strict=False):
            font = _build_qfont(font_family=font_family, font_file=font_file, pixel_size=size)
            widths.append(_measure_line_width(line, font=font, stroke_width=stroke_width))
            heights.append(_measure_line_height(font=font, stroke_width=stroke_width))
        spacing = _resolve_line_spacing_px(
            base_font_size_px=max(sizes, default=0),
            line_heights_px=tuple(heights),
            line_spacing_ratio=line_spacing_ratio,
        )
        total_height = sum(heights) + (max(0, len(heights) - 1) * spacing)
        return tuple(widths), tuple(heights), spacing, total_height

    while True:
        progress = False
        widths, heights, spacing, total_height = measure(line_sizes)
        for index, line in enumerate(lines):
            if not line:
                continue
            if line_sizes[index] >= max_font_size_px:
                continue
            trial_sizes = list(line_sizes)
            trial_sizes[index] += 1
            trial_widths, trial_heights, trial_spacing, trial_total_height = measure(trial_sizes)
            if trial_widths[index] > max_width_px:
                continue
            if trial_total_height > content_height_capacity_px:
                continue
            line_sizes = trial_sizes
            widths, heights, spacing, total_height = trial_widths, trial_heights, trial_spacing, trial_total_height
            progress = True
            any_line_grown = True
        if not progress:
            final_widths, final_heights, final_spacing, _ = measure(line_sizes)
            return tuple(line_sizes), final_widths, final_heights, final_spacing, any_line_grown


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


def _truncate_lines(lines: tuple[str, ...], *, font: QFont, max_width_px: int, max_lines: int, stroke_width: int) -> tuple[str, ...]:
    metrics = QFontMetricsF(font)
    safe_lines = list(lines[:max_lines]) or [""]
    safe_lines[-1] = metrics.elidedText(
        safe_lines[-1],
        Qt.TextElideMode.ElideRight,
        max(1, max_width_px - max(0, stroke_width * 2)),
    )
    return tuple(safe_lines)


def _bounded_ratio(value: float) -> float:
    return min(1.0, max(0.0, value))


def _font_size_to_pixels(*, requested_font_size: int, font_size_unit: str, dpi: int) -> int:
    normalized = font_size_unit.strip().casefold()
    if normalized == "pt":
        return max(1, round(requested_font_size * dpi / 72))
    return max(1, int(requested_font_size))


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
