from __future__ import annotations

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QComboBox, QScrollArea

from mt_clip_factory.control_center.dto import SystemSettingsDTO
from mt_clip_factory.ui.control_center.dashboard_window import DashboardWindow
from mt_clip_factory.ui.factory.recipe_builder_window import RecipeBuilderWindow
from mt_clip_factory.ui.library.asset_library_window import AssetLibraryWindow
from mt_clip_factory.ui.library.product_library_window import ProductLibraryWindow
from mt_clip_factory.ui.library.tag_dictionary_window import TagDictionaryWindow


@pytest.fixture()
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class FakeDashboardViewModel(QObject):
    summary_changed = Signal()
    status_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.status = "ready"
        self.summary = None

    def load(self) -> None:
        self.status_changed.emit()

    def recover_queued_jobs(self) -> None:
        self.status = "recovering"
        self.status_changed.emit()

    def retry_failed_jobs(self) -> None:
        self.status = "retrying"
        self.status_changed.emit()


class FakeProductLibraryViewModel(QObject):
    products_changed = Signal()
    feedback_changed = Signal()
    status_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.products = []
        self.feedback = ""
        self.status = "ready"

    def load(self) -> None:
        self.products_changed.emit()
        self.feedback_changed.emit()
        self.status_changed.emit()


class FakeAssetLibraryViewModel(QObject):
    products_changed = Signal()
    assets_changed = Signal()
    feedback_changed = Signal()
    status_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.products = []
        self.assets = []
        self.feedback = ""
        self.status = "ready"

    def load(self) -> None:
        self.products_changed.emit()
        self.assets_changed.emit()
        self.feedback_changed.emit()
        self.status_changed.emit()

    def apply_filters(self, *, product_id, asset_type, status) -> None:  # noqa: ANN001
        self.load()


class FakeTagDictionaryViewModel(QObject):
    tags_changed = Signal()
    assets_changed = Signal()
    feedback_changed = Signal()
    status_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.tags = []
        self.assets = []
        self.feedback = ""
        self.status = "ready"

    def load(self) -> None:
        self.tags_changed.emit()
        self.assets_changed.emit()
        self.feedback_changed.emit()
        self.status_changed.emit()


class FakeRecipeBuilderViewModel(QObject):
    products_changed = Signal()
    assets_changed = Signal()
    recipes_changed = Signal()
    recipe_items_changed = Signal()
    outputs_changed = Signal()
    decision_events_changed = Signal()
    feedback_changed = Signal()
    status_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.products = []
        self.assets = []
        self.recipes = []
        self.recipe_items = []
        self.outputs = []
        self.decision_events = []
        self.composition_plan = None
        self.feedback = ""
        self.status = "ready"

    def load(self) -> None:
        self.products_changed.emit()
        self.assets_changed.emit()
        self.recipes_changed.emit()
        self.recipe_items_changed.emit()
        self.outputs_changed.emit()
        self.decision_events_changed.emit()
        self.feedback_changed.emit()
        self.status_changed.emit()

    def select_recipe(self, recipe_id: int | None) -> None:
        return

    def find_output(self, output_id: int) -> None:
        return None


def test_primary_windows_apply_app_theme(qapp: QApplication) -> None:
    dashboard_window = DashboardWindow(
        FakeDashboardViewModel(),
        open_products=lambda: None,
        open_assets=lambda: None,
        open_recipes=lambda: None,
        open_tags=lambda: None,
        open_settings=lambda: None,
    )
    product_window = ProductLibraryWindow(FakeProductLibraryViewModel())
    asset_window = AssetLibraryWindow(FakeAssetLibraryViewModel())
    tag_window = TagDictionaryWindow(FakeTagDictionaryViewModel())
    recipe_window = RecipeBuilderWindow(FakeRecipeBuilderViewModel())

    for window in (dashboard_window, product_window, asset_window, tag_window, recipe_window):
        assert "QMainWindow" in window.styleSheet()
        assert "QPushButton" in window.styleSheet()
        window.close()


def test_recipe_builder_window_explains_ready_assets_and_keeps_asset_panel_usable(qapp: QApplication) -> None:
    recipe_window = RecipeBuilderWindow(FakeRecipeBuilderViewModel())

    assert isinstance(recipe_window.scroll_area, QScrollArea)
    assert recipe_window.scroll_area.widgetResizable() is True
    assert recipe_window.scroll_area.widget() is recipe_window.content_widget
    assert isinstance(recipe_window.role_input, QComboBox)
    assert recipe_window.role_input.isEditable() is True
    assert recipe_window.role_input.currentText() == ""
    assert [recipe_window.role_input.itemText(index) for index in range(recipe_window.role_input.count())] == list(
        RecipeBuilderWindow.DEFAULT_ATTACH_ROLES
    )
    assert recipe_window.assets_hint_label.text().startswith("Only assets that are already in status 'ready'")
    assert recipe_window.assets_table.minimumHeight() == RecipeBuilderWindow.ASSETS_TABLE_MIN_HEIGHT
    assert recipe_window.recipe_items_table.minimumHeight() == RecipeBuilderWindow.RECIPE_ITEMS_TABLE_MIN_HEIGHT
    assert recipe_window.recipe_table.minimumHeight() == RecipeBuilderWindow.RECIPE_TABLE_MIN_HEIGHT
    recipe_window.close()


def test_recipe_builder_window_filters_role_suggestions_by_selected_asset_type(qapp: QApplication) -> None:
    recipe_window = RecipeBuilderWindow(FakeRecipeBuilderViewModel())

    recipe_window._set_role_suggestions("voiceover")
    assert [recipe_window.role_input.itemText(index) for index in range(recipe_window.role_input.count())] == ["voice"]

    recipe_window._set_role_suggestions("background_music")
    assert [recipe_window.role_input.itemText(index) for index in range(recipe_window.role_input.count())] == ["music"]

    recipe_window._set_role_suggestions("foreground_video")
    assert [recipe_window.role_input.itemText(index) for index in range(recipe_window.role_input.count())] == [
        "hero",
        "hook",
        "problem",
        "benefit",
        "proof",
        "cta",
        "broll",
    ]

    recipe_window.role_input.setCurrentText("custom_visual_role")
    recipe_window._set_role_suggestions("background_video")
    assert recipe_window.role_input.currentText() == "custom_visual_role"
    assert recipe_window.role_input.itemText(recipe_window.role_input.count() - 1) == "custom_visual_role"
    recipe_window.close()
