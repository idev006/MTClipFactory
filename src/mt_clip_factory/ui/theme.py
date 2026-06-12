from __future__ import annotations

from importlib.resources import files

from PySide6.QtWidgets import QWidget

THEME_PACKAGE = "mt_clip_factory.ui.themes"

_THEME_FILES = {
    "app_window": ("app_window.qss",),
    "settings_window": ("app_window.qss", "settings_window.qss"),
}


def load_theme_stylesheet(theme_name: str) -> str:
    try:
        resource_names = _THEME_FILES[theme_name]
    except KeyError as exc:
        available_themes = ", ".join(sorted(_THEME_FILES))
        raise ValueError(f"Unknown theme '{theme_name}'. Available themes: {available_themes}") from exc

    stylesheet_parts: list[str] = []
    for resource_name in resource_names:
        theme_path = files(THEME_PACKAGE).joinpath(resource_name)
        stylesheet_parts.append(theme_path.read_text(encoding="utf-8").strip())
    return "\n\n".join(part for part in stylesheet_parts if part)


def apply_theme(widget: QWidget, theme_name: str) -> str:
    stylesheet = load_theme_stylesheet(theme_name)
    widget.setStyleSheet(stylesheet)
    return stylesheet
