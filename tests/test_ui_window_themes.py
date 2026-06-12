from __future__ import annotations

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

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
