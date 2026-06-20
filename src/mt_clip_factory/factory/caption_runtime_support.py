from __future__ import annotations

from pathlib import Path

from mt_clip_factory.factory.caption_style_presets import resolve_caption_style_preset


class CaptionContractError(ValueError):
    """Raised when a product caption contract is invalid."""


def _resolve_style_preset_defaults(*, style_preset: str | None, role: str) -> dict[str, object]:
    if not style_preset:
        return {}
    try:
        return resolve_caption_style_preset(preset_name=style_preset, role=role)
    except ValueError as exc:
        raise CaptionContractError(str(exc)) from exc


def _resolve_font(
    *,
    fonts_root: Path,
    font_family: str,
    fallbacks: tuple[str, ...],
) -> tuple[Path | None, str, str]:
    for requested_name, resolution_mode in ((font_family, "workspace_primary"), *[(item, "workspace_fallback") for item in fallbacks]):
        resolved_file = _find_font_file(fonts_root, requested_name)
        if resolved_file is not None:
            return resolved_file, requested_name, resolution_mode
    if fallbacks:
        return None, fallbacks[0], "system_fallback"
    return None, font_family, "system_primary"


def _find_font_file(fonts_root: Path, requested_name: str) -> Path | None:
    if not fonts_root.exists():
        return None
    requested = _normalize_font_name(requested_name)
    if not requested:
        return None
    direct_matches: list[Path] = []
    loose_matches: list[Path] = []
    for file_path in sorted(path for path in fonts_root.iterdir() if path.is_file() and path.suffix.lower() in {".ttf", ".otf"}):
        candidate = _normalize_font_name(file_path.stem)
        if candidate == requested:
            direct_matches.append(file_path)
        elif requested in candidate or candidate in requested:
            loose_matches.append(file_path)
    if direct_matches:
        return direct_matches[0]
    if loose_matches:
        return loose_matches[0]
    return None


def _normalize_font_name(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _text_list(value, *, context: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise CaptionContractError(f"Expected text list for {context}.")
    result: list[str] = []
    for item in value:
        text = _optional_text(item)
        if text is None:
            continue
        result.append(text)
    return tuple(result)


def _optional_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _positive_int(value, *, default: int, context: str) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise CaptionContractError(f"Expected positive integer for {context}.") from exc
    if parsed <= 0:
        raise CaptionContractError(f"Expected positive integer for {context}.")
    return parsed


def _non_negative_int(value, *, default: int, context: str) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise CaptionContractError(f"Expected non-negative integer for {context}.") from exc
    if parsed < 0:
        raise CaptionContractError(f"Expected non-negative integer for {context}.")
    return parsed


def _bounded_float(value, *, default: float, minimum: float, maximum: float, context: str) -> float:
    if value is None:
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise CaptionContractError(f"Expected numeric value for {context}.") from exc
    if parsed < minimum or parsed > maximum:
        raise CaptionContractError(f"Expected {context} to stay within {minimum}..{maximum}.")
    return parsed


def _choice_text(value, *, default: str, allowed: tuple[str, ...], context: str) -> str:
    if value is None:
        return default
    text = _optional_text(value)
    if text is None:
        return default
    normalized = text.casefold()
    if normalized not in allowed:
        raise CaptionContractError(f"Expected {context} to be one of: {', '.join(allowed)}.")
    return normalized


def _boolean(value, *, default: bool, context: str) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise CaptionContractError(f"Expected boolean for {context}.")


def _escape_toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
