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
        open_recipes: Callable[[], None],
        open_tags: Callable[[], None],
        open_settings: Callable[[], None],
    ) -> None:
        super().__init__()
        self._view_model = view_model
        self._open_products = open_products
        self._open_assets = open_assets
        self._open_recipes = open_recipes
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
        content_layout.addWidget(self._build_recent_jobs_group(), 1, 0)
        content_layout.addWidget(self._build_settings_group(), 1, 1)
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
        recipes_button = QPushButton("Recipes")
        tags_button = QPushButton("Tags")
        settings_button = QPushButton("Settings")
        dashboard_refresh_button.clicked.connect(self._view_model.load)
        products_button.clicked.connect(self._open_products)
        assets_button.clicked.connect(self._open_assets)
        recipes_button.clicked.connect(self._open_recipes)
        tags_button.clicked.connect(self._open_tags)
        settings_button.clicked.connect(self._open_settings)
        for button in (
            dashboard_refresh_button,
            products_button,
            assets_button,
            recipes_button,
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
        group = QGroupBox("Configured Paths")
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

    def _build_recent_jobs_group(self) -> QGroupBox:
        group = QGroupBox("Operational Attention")
        layout = QVBoxLayout(group)
        self.recent_jobs_text = QTextEdit()
        self.recent_jobs_text.setReadOnly(True)
        layout.addWidget(self.recent_jobs_text)
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
                    f"Generated At: {summary.generated_at}",
                    f"Products: {summary.product_count}",
                    f"Assets: {summary.asset_count}",
                    f"Recipes: {summary.recipe_count}",
                    f"Outputs: {summary.output_count}",
                    f"Ready Assets: {summary.ready_asset_count}",
                    f"Needs Review Assets: {summary.needs_review_asset_count}",
                    f"Tags: {summary.tag_count}",
                    f"Total Jobs: {summary.total_job_count}",
                    f"Active Jobs: {summary.active_job_count}",
                    f"Queued Jobs: {summary.queued_job_count}",
                    f"Processing Jobs: {summary.processing_job_count}",
                    f"Failed Jobs: {summary.failed_job_count}",
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
                    f"Docs Root: {summary.docs_root}",
                    f"Outputs Root: {summary.outputs_root}",
                    f"Preview Root: {summary.preview_root}",
                    f"FFprobe: {summary.ffprobe_path}",
                    f"FFmpeg: {summary.ffmpeg_path}",
                ]
            )
        )
        self.recent_jobs_text.setPlainText(_format_operational_attention(summary))
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


def _format_operational_attention(summary) -> str:
    lines: list[str] = []
    if summary.failed_job_count > 0:
        lines.append("Attention: failed jobs need operator review or retry.")
    if summary.needs_review_asset_count > 0:
        lines.append("Attention: some assets are still waiting for review.")
    if not summary.ffprobe_available or not summary.ffmpeg_available:
        lines.append("Attention: one or more FFmpeg dependencies are unavailable.")
    if not lines:
        lines.append("Attention: no active alerts.")
    lines.append("")
    lines.append("Recent Jobs:")
    if not summary.recent_jobs:
        lines.append("- No persisted jobs yet.")
        return "\n".join(lines)
    for job in summary.recent_jobs:
        target = f"{job.subject_reference} | {job.job_source}"
        output = f" | output={job.output_path}" if job.output_path else ""
        error = f" | error={job.error_message}" if job.error_message else ""
        lines.append(
            f"- #{job.job_id} {job.job_code} [{job.status}] {job.job_type} "
            f"{target} | progress={job.progress:.1f}{output}{error}"
        )
    return "\n".join(lines)
