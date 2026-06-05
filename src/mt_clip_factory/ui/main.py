from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtWidgets import QApplication, QLabel

from mt_clip_factory.bootstrap import build_product_service
from mt_clip_factory.presentation.viewmodels.product_dashboard import ProductDashboardViewModel


def main() -> int:
    app = QApplication(sys.argv)
    workspace_root = Path.cwd()
    product_service = build_product_service(workspace_root)
    view_model = ProductDashboardViewModel(product_service)
    view_model.load()

    label = QLabel(f"MTClipFactory loaded with {len(view_model.products)} products.")
    label.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

