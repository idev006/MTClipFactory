from __future__ import annotations

import pytest

from mt_clip_factory.output_resolution import normalize_output_resolution, parse_output_resolution


def test_parse_output_resolution_accepts_x_and_star_formats() -> None:
    assert parse_output_resolution("1080x1920") == (1080, 1920)
    assert parse_output_resolution("1080*1920") == (1080, 1920)
    assert parse_output_resolution(" 720X1280 ") == (720, 1280)


def test_normalize_output_resolution_returns_canonical_x_format() -> None:
    assert normalize_output_resolution("1080*1920") == "1080x1920"
    assert normalize_output_resolution("") == ""


def test_normalize_output_resolution_rejects_invalid_or_odd_values() -> None:
    with pytest.raises(ValueError):
        normalize_output_resolution("9:16")
    with pytest.raises(ValueError):
        normalize_output_resolution("1079x1920")
