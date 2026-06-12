from __future__ import annotations


def build_visual_filter(*, target_ratio: str | None, max_dimension: int = 1280) -> str:
    dimensions = _resolve_target_dimensions(target_ratio=target_ratio, max_dimension=max_dimension)
    if dimensions is None:
        return "scale='min(1280,iw)':-2"
    target_width, target_height = dimensions
    return (
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
    )


def _resolve_target_dimensions(*, target_ratio: str | None, max_dimension: int) -> tuple[int, int] | None:
    ratio_pair = _parse_ratio(target_ratio)
    if ratio_pair is None:
        return None
    width_ratio, height_ratio = ratio_pair
    scale = max_dimension / max(width_ratio, height_ratio)
    target_width = _round_even(width_ratio * scale)
    target_height = _round_even(height_ratio * scale)
    return target_width, target_height


def _parse_ratio(value: str | None) -> tuple[int, int] | None:
    if value is None:
        return None
    cleaned = value.strip().replace("/", ":")
    if ":" not in cleaned:
        return None
    width_text, height_text = cleaned.split(":", maxsplit=1)
    try:
        width = int(width_text)
        height = int(height_text)
    except ValueError:
        return None
    if width <= 0 or height <= 0:
        return None
    return width, height


def _round_even(value: float) -> int:
    rounded = max(2, int(round(value)))
    return rounded if rounded % 2 == 0 else rounded + 1
