from __future__ import annotations

import pytest

from mt_clip_factory.factory.caption_line_pair_spacing import (
    analyze_line_script_profile,
    resolve_line_pair_spacing_details,
    resolve_pair_aware_line_top_positions,
    resolve_pair_aware_text_block_height_px,
)


_LINE_BY_STATE = {
    "N": "\u0e01\u0e32",
    "U": "\u0e01\u0e34",
    "D": "\u0e01\u0e38",
    "B": "\u0e01\u0e38\u0e49",
}


@pytest.mark.parametrize(
    ("state", "expected_upper", "expected_lower"),
    [
        ("N", False, False),
        ("U", True, False),
        ("D", False, True),
        ("B", True, True),
    ],
)
def test_analyze_line_script_profile_distinguishes_upper_and_lower_thai_marks(
    state: str,
    expected_upper: bool,
    expected_lower: bool,
) -> None:
    profile = analyze_line_script_profile(_LINE_BY_STATE[state])

    assert profile.has_upper_marks is expected_upper
    assert profile.has_lower_marks is expected_lower
    assert profile.requires_script_safe_line_height is (expected_upper or expected_lower)


@pytest.mark.parametrize("upper_state", ["N", "U", "D", "B"])
@pytest.mark.parametrize("lower_state", ["N", "U", "D", "B"])
def test_resolve_line_pair_spacing_details_covers_all_basic_upper_lower_combinations(
    upper_state: str,
    lower_state: str,
) -> None:
    details = resolve_line_pair_spacing_details(
        lines=(_LINE_BY_STATE[upper_state], _LINE_BY_STATE[lower_state]),
        line_heights_px=(100, 100),
        line_spacing_px=8,
        base_line_advance_ratio=0.80,
    )

    assert len(details) == 1
    detail = details[0]
    expected_risk = _expected_risk(upper_state=upper_state, lower_state=lower_state)
    expected_ratio = _expected_ratio(expected_risk)

    assert detail.risk_level == expected_risk
    assert detail.local_risk_level == expected_risk
    assert detail.applied_line_advance_ratio == pytest.approx(expected_ratio)
    assert detail.advance_px == round(100 * expected_ratio) + 8


def test_pair_aware_positions_and_height_use_pair_specific_applied_ratios() -> None:
    details = resolve_line_pair_spacing_details(
        lines=(_LINE_BY_STATE["D"], _LINE_BY_STATE["U"], _LINE_BY_STATE["N"]),
        line_heights_px=(100, 100, 100),
        line_spacing_px=8,
        base_line_advance_ratio=0.80,
    )

    assert [detail.local_risk_level for detail in details] == ["high", "low"]
    assert [detail.risk_level for detail in details] == ["high", "medium"]
    assert [detail.advance_px for detail in details] == [108, 100]

    positions = resolve_pair_aware_line_top_positions(
        content_top_px=200,
        line_heights_px=(100, 100, 100),
        line_spacing_px=8,
        pair_spacing_details=details,
        fallback_line_advance_ratio=0.80,
    )
    height = resolve_pair_aware_text_block_height_px(
        line_heights_px=(100, 100, 100),
        line_spacing_px=8,
        pair_spacing_details=details,
        fallback_line_advance_ratio=0.80,
    )

    assert positions == (200, 308, 408)
    assert height == 308


def test_global_context_smoothing_promotes_low_middle_pair_between_high_risk_pairs() -> None:
    details = resolve_line_pair_spacing_details(
        lines=(_LINE_BY_STATE["D"], _LINE_BY_STATE["U"], _LINE_BY_STATE["D"], _LINE_BY_STATE["U"]),
        line_heights_px=(100, 100, 100, 100),
        line_spacing_px=8,
        base_line_advance_ratio=0.80,
    )

    assert [detail.local_risk_level for detail in details] == ["high", "low", "high"]
    assert [detail.risk_level for detail in details] == ["high", "medium", "high"]
    assert [detail.applied_line_advance_ratio for detail in details] == [1.0, 0.92, 1.0]


def _expected_risk(*, upper_state: str, lower_state: str) -> str:
    upper_has_lower = upper_state in {"D", "B"}
    lower_has_upper = lower_state in {"U", "B"}
    if upper_has_lower and lower_has_upper:
        return "high"
    if upper_has_lower or lower_has_upper:
        return "medium"
    return "low"


def _expected_ratio(risk_level: str) -> float:
    if risk_level == "high":
        return 1.0
    if risk_level == "medium":
        return 0.92
    return 0.80
