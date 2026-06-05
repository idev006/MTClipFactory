from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication

from mt_clip_factory.bootstrap import build_resource_library_module
from mt_clip_factory.presentation.library.asset_library import AssetLibraryViewModel
from mt_clip_factory.presentation.library.product_library import ProductLibraryViewModel
from mt_clip_factory.ui.library.asset_library_window import AssetLibraryWindow
from mt_clip_factory.ui.library.product_library_window import ProductLibraryWindow


def main() -> int:
    app = QApplication(sys.argv)
    workspace_root = Path.cwd()
    resource_library = build_resource_library_module(workspace_root)
    product_view_model = ProductLibraryViewModel(resource_library.product_service)
    asset_view_model = AssetLibraryViewModel(
        product_service=resource_library.product_service,
        asset_intake_service=resource_library.asset_intake_service,
    )
    asset_window = AssetLibraryWindow(asset_view_model)
    window = ProductLibraryWindow(
        product_view_model,
        open_asset_intake=lambda: _show_window(asset_window),
    )
    window.show()
    return app.exec()


def _show_window(window) -> None:
    window.show()
    window.raise_()
    window.activateWindow()


if __name__ == "__main__":
    raise SystemExit(main())
