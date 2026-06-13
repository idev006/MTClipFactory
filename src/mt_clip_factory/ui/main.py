from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication

from mt_clip_factory.app_runtime import ApplicationRuntime
from mt_clip_factory.presentation.control_center.dashboard import DashboardViewModel
from mt_clip_factory.presentation.control_center.settings import SettingsViewModel
from mt_clip_factory.presentation.factory.auto_factory_control import AutoFactoryControlViewModel
from mt_clip_factory.presentation.factory.recipe_builder import RecipeBuilderViewModel
from mt_clip_factory.presentation.library.asset_library import AssetLibraryViewModel
from mt_clip_factory.presentation.library.product_library import ProductLibraryViewModel
from mt_clip_factory.presentation.library.tag_dictionary import TagDictionaryViewModel
from mt_clip_factory.ui.control_center.dashboard_window import DashboardWindow
from mt_clip_factory.ui.factory.auto_factory_control_window import AutoFactoryControlWindow
from mt_clip_factory.ui.factory.recipe_builder_window import RecipeBuilderWindow
from mt_clip_factory.ui.control_center.settings_window import SettingsWindow
from mt_clip_factory.ui.library.asset_library_window import AssetLibraryWindow
from mt_clip_factory.ui.library.product_library_window import ProductLibraryWindow
from mt_clip_factory.ui.library.tag_dictionary_window import TagDictionaryWindow


def main() -> int:
    app = QApplication(sys.argv)
    workspace_root = Path.cwd()
    runtime = ApplicationRuntime(workspace_root)
    resource_library = runtime.module
    product_view_model = ProductLibraryViewModel(resource_library.product_service)
    asset_view_model = AssetLibraryViewModel(
        product_service=resource_library.product_service,
        asset_intake_service=resource_library.asset_intake_service,
        artifact_generation_service=resource_library.artifact_generation_service,
    )
    tag_view_model = TagDictionaryViewModel(
        tag_management_service=resource_library.tag_management_service,
        asset_intake_service=resource_library.asset_intake_service,
    )
    recipe_view_model = RecipeBuilderViewModel(
        product_service=resource_library.product_service,
        asset_intake_service=resource_library.asset_intake_service,
        video_assembly_factory_service=resource_library.video_assembly_factory_service,
    )
    auto_factory_view_model = AutoFactoryControlViewModel(
        auto_factory_folder_service=resource_library.auto_factory_folder_service,
        production_order_service=resource_library.production_order_service,
    )
    dashboard_view_model = DashboardViewModel(resource_library.dashboard_service)
    settings_view_model = SettingsViewModel(
        resource_library.system_settings_service,
        runtime_path_reloader=runtime,
    )
    settings_view_model.runtime_reloaded.connect(product_view_model.load)
    settings_view_model.runtime_reloaded.connect(asset_view_model.load)
    settings_view_model.runtime_reloaded.connect(tag_view_model.load)
    settings_view_model.runtime_reloaded.connect(recipe_view_model.load)
    settings_view_model.runtime_reloaded.connect(auto_factory_view_model.load)
    settings_view_model.runtime_reloaded.connect(dashboard_view_model.load)
    tag_window = TagDictionaryWindow(tag_view_model)
    recipe_window = RecipeBuilderWindow(recipe_view_model)
    auto_factory_window = AutoFactoryControlWindow(auto_factory_view_model)
    settings_window = SettingsWindow(settings_view_model)
    asset_window = AssetLibraryWindow(
        asset_view_model,
        open_tag_dictionary=lambda: _show_window(tag_window),
    )
    product_window = ProductLibraryWindow(
        product_view_model,
        open_asset_intake=lambda: _show_window(asset_window),
    )
    dashboard_window = DashboardWindow(
        dashboard_view_model,
        open_products=lambda: _show_window(product_window),
        open_assets=lambda: _show_window(asset_window),
        open_recipes=lambda: _show_window(recipe_window),
        open_auto_factory=lambda: _show_window(auto_factory_window),
        open_tags=lambda: _show_window(tag_window),
        open_settings=lambda: _show_window(settings_window),
    )
    dashboard_window.show()
    return app.exec()


def _show_window(window) -> None:
    window.show()
    window.raise_()
    window.activateWindow()


if __name__ == "__main__":
    raise SystemExit(main())
