from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mt_clip_factory.presentation.control_center.dashboard import DashboardViewModel


class DashboardWindow(QMainWindow):
    def __init__(
        self,
        view_model: DashboardViewModel,
        open_products: Callable[[], None],
        open_assets: Callable[[], None],
        open_tags: Callable[[], None],
        open_settings: Callable[[], None],
    ) -> None:
        super().__init__()
        self._view_model = view_model
        self._open_products = open_products
        self._open_assets = open_assets
        self._open_tags = open_tags
        self._open_settings = open_settings
        self.setWindowTitle("MTClipFactory - Dashboard")
        self.resize(1280, 760)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        layout.addWidget(self._build_toolbar())
        content_layout = QGridLayout()
        content_layout.addWidget(self._build_system_summary_group(), 0, 0)
        content_layout.addWidget(self._build_paths_group(), 0, 1)
        content_layout.addWidget(self._build_settings_group(), 1, 0, 1, 2)
        content_layout.setColumnStretch(0, 1)
        content_layout.setColumnStretch(1, 1)
        layout.addLayout(content_layout)
        self.setCentralWidget(central)

        self._view_model.summary_changed.connect(self._refresh_summary)
        self._view_model.status_changed.connect(self._refresh_status)
        self._refresh_status()
        self._view_model.load()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._view_model.load()

    def _build_toolbar(self) -> QGroupBox:
        group = QGroupBox("System Control")
        layout = QHBoxLayout(group)
        dashboard_refresh_button = QPushButton("Refresh Dashboard")
        products_button = QPushButton("Products")
        assets_button = QPushButton("Assets")
        tags_button = QPushButton("Tags")
        settings_button = QPushButton("Settings")
        dashboard_refresh_button.clicked.connect(self._view_model.load)
        products_button.clicked.connect(self._open_products)
        assets_button.clicked.connect(self._open_assets)
        tags_button.clicked.connect(self._open_tags)
        settings_button.clicked.connect(self._open_settings)
        for button in (
            dashboard_refresh_button,
            products_button,
            assets_button,
            tags_button,
            settings_button,
        ):
            layout.addWidget(button)
        layout.addStretch(1)
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.status_label)
        return group

    def _build_system_summary_group(self) -> QGroupBox:
        group = QGroupBox("System Summary")
        layout = QVBoxLayout(group)
        self.system_summary_text = QTextEdit()
        self.system_summary_text.setReadOnly(True)
        layout.addWidget(self.system_summary_text)
        return group

    def _build_paths_group(self) -> QGroupBox:
        group = QGroupBox("Runtime Paths")
        layout = QVBoxLayout(group)
        self.paths_text = QTextEdit()
        self.paths_text.setReadOnly(True)
        layout.addWidget(self.paths_text)
        return group

    def _build_settings_group(self) -> QGroupBox:
        group = QGroupBox("Operational Settings")
        layout = QVBoxLayout(group)
        self.settings_text = QTextEdit()
        self.settings_text.setReadOnly(True)
        layout.addWidget(self.settings_text)
        return group

    def _refresh_status(self) -> None:
        self.status_label.setText(f"Status: {self._view_model.status}")

    def _refresh_summary(self) -> None:
        summary = self._view_model.summary
        if summary is None:
            return
        self.system_summary_text.setPlainText(
            "\n".join(
                [
                    f"Products: {summary.product_count}",
                    f"Assets: {summary.asset_count}",
                    f"Ready Assets: {summary.ready_asset_count}",
                    f"Needs Review Assets: {summary.needs_review_asset_count}",
                    f"Tags: {summary.tag_count}",
                    f"FFprobe Available: {summary.ffprobe_available}",
                    f"FFmpeg Available: {summary.ffmpeg_available}",
                ]
            )
        )
        self.paths_text.setPlainText(
            "\n".join(
                [
                    f"Workspace: {summary.workspace_root}",
                    f"Database: {summary.database_path}",
                    f"Media Root: {summary.media_root}",
                    f"FFprobe: {summary.ffprobe_path}",
                    f"FFmpeg: {summary.ffmpeg_path}",
                ]
            )
        )
        self.settings_text.setPlainText(
            "\n".join(
                [
                    f"CPU Limit Percent: {summary.cpu_limit_percent}",
                    f"RAM Limit Percent: {summary.ram_limit_percent}",
                    f"Disk Free GB Min: {summary.disk_free_gb_min}",
                    f"Max Preview Workers: {summary.max_preview_workers}",
                    f"Max Final Workers: {summary.max_final_workers}",
                    f"Auto Refresh Seconds: {summary.auto_refresh_seconds}",
                ]
            )
        )

