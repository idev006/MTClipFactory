from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from mt_clip_factory.ui.theme import apply_theme, load_theme_stylesheet


@pytest.fixture()
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_load_theme_stylesheet_reads_qss_asset() -> None:
    stylesheet = load_theme_stylesheet("app_window")

    assert "QMainWindow" in stylesheet
    assert "QPushButton" in stylesheet
    assert "qlineargradient" in stylesheet
    assert "border-bottom: 3px solid" in stylesheet
    assert "QPushButton:pressed" in stylesheet


def test_load_theme_stylesheet_composes_base_and_window_specific_qss() -> None:
    stylesheet = load_theme_stylesheet("settings_window")

    assert "QMainWindow" in stylesheet
    assert "QGroupBox#panelBox" in stylesheet
    assert "QLabel#statusValue" in stylesheet


def test_apply_theme_sets_widget_stylesheet(qapp: QApplication) -> None:
    widget = QWidget()

    stylesheet = apply_theme(widget, "settings_window")

    assert widget.styleSheet() == stylesheet


def test_load_theme_stylesheet_rejects_unknown_theme() -> None:
    with pytest.raises(ValueError, match="Unknown theme"):
        load_theme_stylesheet("missing_theme")
