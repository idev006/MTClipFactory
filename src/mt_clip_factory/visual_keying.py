from __future__ import annotations

import re

VISUAL_KEY_PROFILE_OPTIONS = ("auto", "green", "blue", "magenta", "custom", "disabled")

KEY_COLOR_PRESETS = {
    "green": "#00FF00",
    "blue": "#0000FF",
    "magenta": "#FF00FF",
}

_HEX_COLOR_PATTERN = re.compile(r"^#?[0-9a-fA-F]{6}$")


def normalize_visual_key_profile(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized in VISUAL_KEY_PROFILE_OPTIONS:
        return normalized
    return "auto"


def normalize_visual_key_color(value: str | None, *, fallback: str = "#00FF00") -> str:
    cleaned = (value or "").strip()
    if not _HEX_COLOR_PATTERN.fullmatch(cleaned):
        return fallback.upper()
    if not cleaned.startswith("#"):
        cleaned = f"#{cleaned}"
    return cleaned.upper()


def resolve_profile_key_color(profile: str, custom_color: str) -> str | None:
    normalized_profile = normalize_visual_key_profile(profile)
    if normalized_profile == "disabled":
        return None
    if normalized_profile == "custom":
        return normalize_visual_key_color(custom_color)
    return KEY_COLOR_PRESETS.get(normalized_profile)
