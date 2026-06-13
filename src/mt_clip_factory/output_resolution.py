from __future__ import annotations


def parse_output_resolution(value: str | None) -> tuple[int, int] | None:
    if value is None:
        return None
    cleaned = value.strip().replace(" ", "")
    if not cleaned:
        return None
    separator = next((candidate for candidate in ("x", "X", "*") if candidate in cleaned), None)
    if separator is None:
        return None
    width_text, height_text = cleaned.split(separator, maxsplit=1)
    try:
        width = int(width_text)
        height = int(height_text)
    except ValueError:
        return None
    if width <= 0 or height <= 0:
        return None
    return width, height


def normalize_output_resolution(value: str | None) -> str:
    if value is None:
        return ""
    cleaned = value.strip()
    if not cleaned:
        return ""
    parsed = parse_output_resolution(cleaned)
    if parsed is None:
        raise ValueError("Output resolution must use WIDTHxHEIGHT or WIDTH*HEIGHT, for example 1080x1920.")
    width, height = parsed
    if width % 2 != 0 or height % 2 != 0:
        raise ValueError("Output resolution width and height must be even numbers, for example 1080x1920.")
    return f"{width}x{height}"
