from __future__ import annotations

from dataclasses import dataclass
import unicodedata


_SCRIPT_SAFE_MARK_CATEGORIES = frozenset({"Mn", "Mc", "Me"})
_THAI_UPPER_MARK_RANGES = (
    (0x0E31, 0x0E31),
    (0x0E34, 0x0E37),
    (0x0E47, 0x0E4E),
)
_THAI_LOWER_MARK_RANGES = (
    (0x0E38, 0x0E3A),
)
_MEDIUM_RISK_LINE_ADVANCE_FLOOR = 0.92
_HIGH_RISK_LINE_ADVANCE_FLOOR = 1.0


@dataclass(slots=True, frozen=True)
class LineScriptProfile:
    has_upper_marks: bool
    has_lower_marks: bool
    requires_script_safe_line_height: bool


@dataclass(slots=True, frozen=True)
class LinePairSpacingDetail:
    pair_index: int
    risk_level: str
    base_line_advance_ratio: float
    minimum_line_advance_ratio: float
    applied_line_advance_ratio: float
    advance_px: int
    upper_has_upper_marks: bool
    upper_has_lower_marks: bool
    lower_has_upper_marks: bool
    lower_has_lower_marks: bool


def text_requires_script_safe_line_spacing(text: str) -> bool:
    return analyze_line_script_profile(text).requires_script_safe_line_height


def analyze_line_script_profile(text: str) -> LineScriptProfile:
    has_upper_marks = False
    has_lower_marks = False
    generic_combining_marks = False
    for character in text:
        if character.isspace():
            continue
        codepoint = ord(character)
        if _codepoint_in_ranges(codepoint, _THAI_UPPER_MARK_RANGES):
            has_upper_marks = True
            continue
        if _codepoint_in_ranges(codepoint, _THAI_LOWER_MARK_RANGES):
            has_lower_marks = True
            continue
        if unicodedata.category(character) in _SCRIPT_SAFE_MARK_CATEGORIES:
            generic_combining_marks = True
    if generic_combining_marks and not has_upper_marks and not has_lower_marks:
        has_upper_marks = True
        has_lower_marks = True
    return LineScriptProfile(
        has_upper_marks=has_upper_marks,
        has_lower_marks=has_lower_marks,
        requires_script_safe_line_height=has_upper_marks or has_lower_marks or generic_combining_marks,
    )


def resolve_line_pair_spacing_details(
    *,
    lines: tuple[str, ...],
    line_heights_px: tuple[int, ...],
    line_spacing_px: int,
    base_line_advance_ratio: float,
) -> tuple[LinePairSpacingDetail, ...]:
    normalized_base_ratio = max(0.5, min(1.2, base_line_advance_ratio))
    if len(lines) <= 1:
        return ()
    profiles = tuple(analyze_line_script_profile(line) for line in lines)
    details: list[LinePairSpacingDetail] = []
    for pair_index, line_height_px in enumerate(line_heights_px[:-1]):
        upper = profiles[pair_index]
        lower = profiles[pair_index + 1]
        risk_level, minimum_ratio = _resolve_pair_risk_and_floor(
            upper_profile=upper,
            lower_profile=lower,
            base_line_advance_ratio=normalized_base_ratio,
        )
        applied_ratio = max(normalized_base_ratio, minimum_ratio)
        advance_px = max(1, round(line_height_px * applied_ratio)) + line_spacing_px
        details.append(
            LinePairSpacingDetail(
                pair_index=pair_index,
                risk_level=risk_level,
                base_line_advance_ratio=normalized_base_ratio,
                minimum_line_advance_ratio=minimum_ratio,
                applied_line_advance_ratio=applied_ratio,
                advance_px=advance_px,
                upper_has_upper_marks=upper.has_upper_marks,
                upper_has_lower_marks=upper.has_lower_marks,
                lower_has_upper_marks=lower.has_upper_marks,
                lower_has_lower_marks=lower.has_lower_marks,
            )
        )
    return tuple(details)


def resolve_pair_aware_line_top_positions(
    *,
    content_top_px: int,
    line_heights_px: tuple[int, ...],
    line_spacing_px: int,
    pair_spacing_details: tuple[LinePairSpacingDetail, ...],
    fallback_line_advance_ratio: float,
) -> tuple[int, ...]:
    if not line_heights_px:
        return ()
    positions: list[int] = []
    cursor = content_top_px
    normalized_fallback_ratio = max(0.5, min(1.2, fallback_line_advance_ratio))
    for index, line_height_px in enumerate(line_heights_px):
        positions.append(cursor)
        if index >= len(line_heights_px) - 1:
            continue
        if index < len(pair_spacing_details):
            cursor += pair_spacing_details[index].advance_px
        else:
            cursor += max(1, round(line_height_px * normalized_fallback_ratio)) + line_spacing_px
    return tuple(positions)


def resolve_pair_aware_text_block_height_px(
    *,
    line_heights_px: tuple[int, ...],
    line_spacing_px: int,
    pair_spacing_details: tuple[LinePairSpacingDetail, ...],
    fallback_line_advance_ratio: float,
) -> int:
    if not line_heights_px:
        return 0
    if len(line_heights_px) == 1:
        return line_heights_px[0]
    normalized_fallback_ratio = max(0.5, min(1.2, fallback_line_advance_ratio))
    stacked_height_px = 0
    for index, line_height_px in enumerate(line_heights_px[:-1]):
        if index < len(pair_spacing_details):
            stacked_height_px += pair_spacing_details[index].advance_px
        else:
            stacked_height_px += max(1, round(line_height_px * normalized_fallback_ratio)) + line_spacing_px
    return stacked_height_px + line_heights_px[-1]


def _resolve_pair_risk_and_floor(
    *,
    upper_profile: LineScriptProfile,
    lower_profile: LineScriptProfile,
    base_line_advance_ratio: float,
) -> tuple[str, float]:
    if upper_profile.has_lower_marks and lower_profile.has_upper_marks:
        return "high", max(base_line_advance_ratio, _HIGH_RISK_LINE_ADVANCE_FLOOR)
    if upper_profile.has_lower_marks or lower_profile.has_upper_marks:
        return "medium", max(base_line_advance_ratio, _MEDIUM_RISK_LINE_ADVANCE_FLOOR)
    return "low", base_line_advance_ratio


def _codepoint_in_ranges(codepoint: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(start <= codepoint <= end for start, end in ranges)
