from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mt_clip_factory.factory.caption_layout_support import (
    _RawLayout,
    _balanced_wrap_paragraph,
    _build_qfont,
    _ensure_qt_application,
    _layout_text,
    _measure_line_height,
    _measure_line_width,
    _resolve_line_metrics,
    _resolve_line_spacing_px,
)
from mt_clip_factory.factory.caption_textbox_geometry import (
    effective_wrap_width,
    resolve_box_left,
    resolve_box_top,
    resolve_content_top_in_box,
    resolve_line_box_geometry,
    resolve_line_left,
    resolve_line_top_positions,
    resolve_line_top_positions_compressed,
    textbox_content_height,
    textbox_content_width,
    textbox_height,
    textbox_width,
)


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
    line_advance_ratio: float
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
class _LayoutCandidate:
    lines: tuple[str, ...]
    font_size_px: int
    line_font_sizes_px: tuple[int, ...]
    line_widths_px: tuple[int, ...]
    line_height_px: int
    line_heights_px: tuple[int, ...]
    line_spacing_px: int
    line_advance_ratio: float
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
    preferred_line_count: int,
    max_chars_per_line: int,
    textbox_mode: str,
    textbox_height_mode: str,
    textbox_width_ratio: float,
    textbox_height_ratio: float,
    textbox_alignment: str,
    line_spacing_ratio: float,
    line_advance_ratio: float,
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
        preferred_line_count=preferred_line_count,
        overflow_policy=overflow_policy,
        manual_breaks=manual_breaks,
        textbox_mode=textbox_mode,
        padding=padding,
        textbox_height_mode=textbox_height_mode,
        textbox_height_ratio=textbox_height_ratio,
        frame_height_px=frame_context.height_px,
        band_height_px=band_height_px,
        line_spacing_ratio=line_spacing_ratio,
        line_advance_ratio=line_advance_ratio,
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
    line_top_positions_px = (
        resolve_line_top_positions_compressed(
            content_top_px=content_top_px,
            line_heights_px=candidate.line_heights_px,
            line_spacing_px=candidate.line_spacing_px,
            line_advance_ratio=candidate.line_advance_ratio,
        )
        if abs(candidate.line_advance_ratio - 1.0) > 0.001
        else resolve_line_top_positions(
            content_top_px=content_top_px,
            line_heights_px=candidate.line_heights_px,
            line_spacing_px=candidate.line_spacing_px,
        )
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
        line_break_mode=candidate.line_break_mode,
        line_widths_px=candidate.line_widths_px,
        line_height_px=candidate.line_height_px,
        line_heights_px=candidate.line_heights_px,
        line_spacing_px=candidate.line_spacing_px,
        line_advance_ratio=candidate.line_advance_ratio,
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
    preferred_line_count: int,
    overflow_policy: str,
    manual_breaks: bool,
    textbox_mode: str,
    padding: int,
    textbox_height_mode: str,
    textbox_height_ratio: float,
    frame_height_px: int,
    band_height_px: int,
    line_spacing_ratio: float,
    line_advance_ratio: float,
) -> _LayoutCandidate:
    max_content_height_capacity_px = _resolve_max_content_height_capacity_px(
        frame_height_px=frame_height_px,
        textbox_height_mode=textbox_height_mode,
        textbox_height_ratio=textbox_height_ratio,
        band_height_px=band_height_px,
        padding=padding,
    )
    candidate_font_ceiling_px = _resolve_candidate_font_ceiling_px(
        requested_font_size_px=requested_font_size_px,
        min_font_size_px=min_font_size_px,
        max_width_px=max_width_px,
        max_content_height_capacity_px=max_content_height_capacity_px,
    )
    best_candidate: _LayoutCandidate | None = None
    for candidate_font_size_px in range(candidate_font_ceiling_px, min_font_size_px - 1, -1):
        candidate = _evaluate_layout_candidate(
            text=text,
            font_family=font_family,
            font_file=font_file,
            candidate_font_size_px=candidate_font_size_px,
            requested_font_size_px=requested_font_size_px,
            min_font_size_px=min_font_size_px,
            max_width_px=max_width_px,
            stroke_width=stroke_width,
            max_lines=max_lines,
            preferred_line_count=preferred_line_count,
            overflow_policy=overflow_policy,
            manual_breaks=manual_breaks,
            textbox_mode=textbox_mode,
            padding=padding,
            textbox_height_mode=textbox_height_mode,
            textbox_height_ratio=textbox_height_ratio,
            frame_height_px=frame_height_px,
            band_height_px=band_height_px,
            line_spacing_ratio=line_spacing_ratio,
            line_advance_ratio=line_advance_ratio,
        )
        if best_candidate is None or _candidate_sort_key(candidate) < _candidate_sort_key(best_candidate):
            best_candidate = candidate
    if best_candidate is None:
        raise ValueError("Caption solver could not evaluate any layout candidates.")
    return best_candidate


def _resolve_max_content_height_capacity_px(
    *,
    frame_height_px: int,
    textbox_height_mode: str,
    textbox_height_ratio: float,
    band_height_px: int,
    padding: int,
) -> int:
    if textbox_height_mode.strip().casefold() == "content_hug":
        available_box_height_px = frame_height_px if band_height_px <= 0 else band_height_px
        return textbox_content_height(textbox_height_px=max(1, available_box_height_px), padding=padding)
    if textbox_height_ratio > 0:
        requested_box_height_px = max((padding * 2) + 1, round(frame_height_px * textbox_height_ratio))
        available_box_height_px = min(requested_box_height_px, frame_height_px if band_height_px <= 0 else band_height_px)
    else:
        available_box_height_px = frame_height_px if band_height_px <= 0 else band_height_px
    return textbox_content_height(textbox_height_px=max(1, available_box_height_px), padding=padding)


def _resolve_candidate_font_ceiling_px(
    *,
    requested_font_size_px: int,
    min_font_size_px: int,
    max_width_px: int,
    max_content_height_capacity_px: int,
) -> int:
    baseline_px = max(requested_font_size_px, min_font_size_px)
    growth_headroom_px = max(
        baseline_px * 3,
        baseline_px + 96,
        max_content_height_capacity_px,
    )
    ceiling_px = min(max_width_px, growth_headroom_px)
    return max(baseline_px, ceiling_px)


def _evaluate_layout_candidate(
    *,
    text: str,
    font_family: str,
    font_file: Path | None,
    candidate_font_size_px: int,
    requested_font_size_px: int,
    min_font_size_px: int,
    max_width_px: int,
    stroke_width: int,
    max_lines: int,
    preferred_line_count: int,
    overflow_policy: str,
    manual_breaks: bool,
    textbox_mode: str,
    padding: int,
    textbox_height_mode: str,
    textbox_height_ratio: float,
    frame_height_px: int,
    band_height_px: int,
    line_spacing_ratio: float,
    line_advance_ratio: float,
) -> _LayoutCandidate:
    normalized_textbox_mode = textbox_mode.strip().casefold()
    allow_per_line_scale = manual_breaks and normalized_textbox_mode == "per_line"
    source_manual_line_count = len(text.splitlines()) if manual_breaks else 1
    allow_manual_break_compaction = (
        manual_breaks
        and normalized_textbox_mode == "grouped"
        and preferred_line_count > 1
        and preferred_line_count < source_manual_line_count
    )
    use_uniform_line_height = manual_breaks and normalized_textbox_mode != "per_line"
    effective_line_advance_ratio = (
        max(0.5, min(1.2, line_advance_ratio))
        if use_uniform_line_height
        else 1.0
    )
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
        preferred_line_count=preferred_line_count,
        allow_manual_break_compaction=allow_manual_break_compaction,
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
        allow_per_line_scale=allow_per_line_scale,
    )
    line_heights_px = _normalize_line_heights(
        line_heights_px=line_heights_px,
        use_uniform_line_height=use_uniform_line_height,
    )
    line_spacing_px = _resolve_line_spacing_px(
        base_font_size_px=candidate_font_size_px,
        line_heights_px=line_heights_px,
        line_spacing_ratio=line_spacing_ratio,
    )
    text_block_height_px = _resolve_text_block_height_px(
        line_heights_px=line_heights_px,
        line_spacing_px=line_spacing_px,
        line_advance_ratio=effective_line_advance_ratio,
    )
    box_height_px = min(
        frame_height_px if band_height_px <= 0 else band_height_px,
        textbox_height(
            textbox_height_mode=textbox_height_mode,
            frame_height_px=frame_height_px,
            textbox_height_ratio=textbox_height_ratio,
            content_height_px=text_block_height_px,
            padding=padding,
            band_height_px=band_height_px,
        ),
    )
    content_height_capacity_px = textbox_content_height(textbox_height_px=box_height_px, padding=padding)
    any_line_grown = False
    if allow_per_line_scale and not raw_layout.truncated_for_runtime:
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
            max_font_size_px=_resolve_candidate_font_ceiling_px(
                requested_font_size_px=requested_font_size_px,
                min_font_size_px=min_font_size_px,
                max_width_px=max_width_px,
                max_content_height_capacity_px=content_height_capacity_px,
            ),
            max_width_px=max_width_px,
            content_height_capacity_px=content_height_capacity_px,
            stroke_width=stroke_width,
            line_spacing_ratio=line_spacing_ratio,
            use_uniform_line_height=use_uniform_line_height,
            line_advance_ratio=effective_line_advance_ratio,
        )
    text_block_width_px = max(line_widths_px, default=0)
    text_block_height_px = _resolve_text_block_height_px(
        line_heights_px=line_heights_px,
        line_spacing_px=line_spacing_px,
        line_advance_ratio=effective_line_advance_ratio,
    )
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
        allow_per_line_scale=allow_per_line_scale,
        any_line_scaled=any_line_scaled,
        any_line_grown=any_line_grown,
    )
    return _LayoutCandidate(
        lines=raw_layout.lines,
        font_size_px=candidate_font_size_px,
        line_font_sizes_px=line_font_sizes_px,
        line_widths_px=line_widths_px,
        line_height_px=max(line_heights_px, default=raw_layout.line_height_px),
        line_heights_px=line_heights_px,
        line_spacing_px=line_spacing_px,
        line_advance_ratio=effective_line_advance_ratio,
        text_block_width_px=text_block_width_px,
        text_block_height_px=text_block_height_px,
        box_height_px=box_height_px,
        content_height_capacity_px=content_height_capacity_px,
        overflowed=overflowed,
        truncated_for_runtime=raw_layout.truncated_for_runtime,
        fit_strategy=fit_strategy,
        line_break_mode=(
            "manual_compacted"
            if raw_layout.manual_break_compacted
            else ("manual" if manual_breaks else "single_line")
        ),
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
            preferred_line_count=preferred_line_count if allow_manual_break_compaction else 0,
        ),
        any_line_grown=any_line_grown,
    )


def _normalize_line_heights(
    *,
    line_heights_px: tuple[int, ...],
    use_uniform_line_height: bool,
) -> tuple[int, ...]:
    if not line_heights_px or not use_uniform_line_height:
        return line_heights_px
    uniform_height_px = max(line_heights_px)
    return tuple(uniform_height_px for _ in line_heights_px)


def _resolve_text_block_height_px(
    *,
    line_heights_px: tuple[int, ...],
    line_spacing_px: int,
    line_advance_ratio: float,
) -> int:
    if not line_heights_px:
        return 0
    if len(line_heights_px) == 1:
        return line_heights_px[0]
    normalized_ratio = max(0.5, min(1.2, line_advance_ratio))
    stacked_height_px = 0
    for line_height_px in line_heights_px[:-1]:
        stacked_height_px += max(1, round(line_height_px * normalized_ratio)) + line_spacing_px
    return stacked_height_px + line_heights_px[-1]

def _resolve_fit_strategy(
    *,
    manual_breaks: bool,
    raw_layout: _RawLayout,
    requested_font_size_px: int,
    resolved_font_size_px: int,
    allow_per_line_scale: bool,
    any_line_scaled: bool,
    any_line_grown: bool,
) -> str:
    if raw_layout.truncated_for_runtime:
        return "truncated_for_runtime"
    if manual_breaks:
        if allow_per_line_scale:
            if any_line_grown:
                return "per_line_best_fit"
            if any_line_scaled or resolved_font_size_px < requested_font_size_px:
                return "per_line_scaled_to_fit"
        if resolved_font_size_px > requested_font_size_px:
            return "manual_best_fit"
        if resolved_font_size_px < requested_font_size_px:
            return "scaled_to_fit"
        return "manual_breaks"
    if resolved_font_size_px > requested_font_size_px:
        return "single_line_best_fit"
    if resolved_font_size_px < requested_font_size_px:
        return "scaled_to_fit"
    return "single_line"


def _candidate_sort_key(candidate: _LayoutCandidate) -> tuple[float, ...]:
    return (
        1.0 if candidate.overflowed else 0.0,
        candidate.score,
        -float(candidate.font_size_px),
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
    preferred_line_count: int,
) -> float:
    single_line = len(line_widths_px) <= 1
    target_fill_ratio = 0.985 if single_line else 0.84
    target_width_px = max_width_px * target_fill_ratio
    width_balance_penalty = _line_balance_score(list(line_widths_px), target_width_px=target_width_px)
    width_underfill_penalty = sum(
        max(0.0, (target_width_px - width)) ** 2 / max(1.0, target_width_px)
        for width in line_widths_px
    ) * (1.8 if single_line else 1.0)
    width_overfill_soft_penalty = sum(
        max(0.0, (width - max_width_px * 0.985)) * 2.0
        for width in line_widths_px
    )
    font_variance_penalty = (
        0.0
        if not line_font_sizes_px
        else (max(line_font_sizes_px) - min(line_font_sizes_px)) * 2.0
    )
    whitespace_penalty = max(0.0, (content_height_capacity_px - text_block_height_px) * 0.02)
    line_count_preference_penalty = 0.0
    if preferred_line_count > 0:
        line_count_distance = abs(len(lines) - preferred_line_count)
        line_count_preference_penalty = float(line_count_distance * 250_000)
    if font_size_px >= requested_font_size_px:
        size_distance_penalty = (font_size_px - requested_font_size_px) * 0.35
    else:
        size_distance_penalty = (requested_font_size_px - font_size_px) * 1.5
    occupancy_reward_factor = -340.0 if single_line else -260.0
    occupancy_reward = sum(min(width / max(1, max_width_px), 1.0) for width in line_widths_px) * occupancy_reward_factor
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
    return (
        overflow_penalty
        + line_count_preference_penalty
        + size_distance_penalty
        + width_balance_penalty
        + width_underfill_penalty
        + width_overfill_soft_penalty
        + font_variance_penalty
        + whitespace_penalty
        + occupancy_reward
    )


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
    use_uniform_line_height: bool,
    line_advance_ratio: float,
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
            heights.append(_measure_line_height(font=font, stroke_width=stroke_width, line=line))
        normalized_heights = _normalize_line_heights(
            line_heights_px=tuple(heights),
            use_uniform_line_height=use_uniform_line_height,
        )
        spacing = _resolve_line_spacing_px(
            base_font_size_px=max(sizes, default=0),
            line_heights_px=normalized_heights,
            line_spacing_ratio=line_spacing_ratio,
        )
        total_height = _resolve_text_block_height_px(
            line_heights_px=normalized_heights,
            line_spacing_px=spacing,
            line_advance_ratio=line_advance_ratio,
        )
        return tuple(widths), normalized_heights, spacing, total_height

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
