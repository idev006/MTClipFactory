from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from mt_clip_factory.control_center.dto import SystemSettingsDTO
from mt_clip_factory.presentation.control_center.settings import SettingsViewModel


class SettingsWindow(QMainWindow):
    def __init__(self, view_model: SettingsViewModel) -> None:
        super().__init__()
        self._view_model = view_model
        self.setWindowTitle("MTClipFactory - Settings")
        self.resize(900, 620)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        layout.addWidget(self._build_settings_group())
        self.setCentralWidget(central)

        self._view_model.settings_changed.connect(self._populate_form)
        self._view_model.status_changed.connect(self._refresh_feedback)
        self._view_model.feedback_changed.connect(self._refresh_feedback)
        self._refresh_feedback()
        self._view_model.load()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._view_model.load()

    def _build_settings_group(self) -> QGroupBox:
        group = QGroupBox("God Mode System Settings")
        layout = QVBoxLayout(group)
        form_layout = QFormLayout()

        self.ffmpeg_root_input = QLineEdit()
        self.ffprobe_path_input = QLineEdit()
        self.ffmpeg_path_input = QLineEdit()
        self.database_path_input = QLineEdit()
        self.media_root_input = QLineEdit()
        self.docs_root_input = QLineEdit()
        self.outputs_root_input = QLineEdit()
        self.preview_root_input = QLineEdit()
        self.cpu_limit_input = QSpinBox()
        self.ram_limit_input = QSpinBox()
        self.disk_free_input = QSpinBox()
        self.max_preview_input = QSpinBox()
        self.max_final_input = QSpinBox()
        self.auto_refresh_input = QSpinBox()
        self.auto_recover_input = QCheckBox("Enable queued-job auto recovery on startup")
        self.max_recovery_jobs_input = QSpinBox()
        self.failed_job_escalation_threshold_input = QSpinBox()
        self.voice_loop_input = QCheckBox("Allow narration looping when timeline is longer than voice assets")
        self.music_loop_input = QCheckBox("Allow background music looping to fill timeline gaps")
        self.music_duck_input = QCheckBox("Enable music ducking while narration is active")
        self.music_duck_mode_input = QComboBox()
        self.music_duck_db_input = QSpinBox()
        self.music_duck_attack_input = QSpinBox()
        self.music_duck_release_input = QSpinBox()
        self.music_duck_threshold_input = QSpinBox()
        self.music_duck_ratio_input = QDoubleSpinBox()
        self.voice_mix_gain_input = QSpinBox()
        self.music_mix_gain_input = QSpinBox()
        self.review_duration_mismatch_input = QSpinBox()
        self.review_max_looped_segments_input = QSpinBox()
        self.review_min_distinct_visual_assets_input = QSpinBox()
        self.review_max_consecutive_visual_input = QSpinBox()

        for spinbox in (
            self.cpu_limit_input,
            self.ram_limit_input,
            self.disk_free_input,
            self.max_preview_input,
            self.max_final_input,
            self.auto_refresh_input,
            self.max_recovery_jobs_input,
            self.failed_job_escalation_threshold_input,
            self.music_duck_attack_input,
            self.music_duck_release_input,
            self.music_duck_threshold_input,
            self.review_duration_mismatch_input,
            self.review_max_looped_segments_input,
            self.review_min_distinct_visual_assets_input,
            self.review_max_consecutive_visual_input,
        ):
            spinbox.setRange(0, 100000)
        self.music_duck_db_input.setRange(-60, 0)
        self.music_duck_threshold_input.setRange(-60, 0)
        self.voice_mix_gain_input.setRange(-24, 24)
        self.music_mix_gain_input.setRange(-24, 24)
        self.music_duck_mode_input.addItems(["sidechain_compressor", "windowed_volume_duck"])
        self.music_duck_ratio_input.setRange(1.0, 30.0)
        self.music_duck_ratio_input.setDecimals(2)
        self.music_duck_ratio_input.setSingleStep(0.5)

        form_layout.addRow("Database Path", self.database_path_input)
        form_layout.addRow("Media Root", self.media_root_input)
        form_layout.addRow("Docs Root", self.docs_root_input)
        form_layout.addRow("Outputs Root", self.outputs_root_input)
        form_layout.addRow("Preview Root", self.preview_root_input)
        form_layout.addRow("FFmpeg Root", self.ffmpeg_root_input)
        form_layout.addRow("FFprobe Path", self.ffprobe_path_input)
        form_layout.addRow("FFmpeg Path", self.ffmpeg_path_input)
        form_layout.addRow("CPU Limit Percent", self.cpu_limit_input)
        form_layout.addRow("RAM Limit Percent", self.ram_limit_input)
        form_layout.addRow("Disk Free GB Min", self.disk_free_input)
        form_layout.addRow("Max Preview Workers", self.max_preview_input)
        form_layout.addRow("Max Final Workers", self.max_final_input)
        form_layout.addRow("Auto Refresh Seconds", self.auto_refresh_input)
        form_layout.addRow("Auto Recover Queued Jobs", self.auto_recover_input)
        form_layout.addRow("Max Recovery Jobs Per Run", self.max_recovery_jobs_input)
        form_layout.addRow("Failed Job Escalation Threshold", self.failed_job_escalation_threshold_input)
        form_layout.addRow("Voice Loop Enabled", self.voice_loop_input)
        form_layout.addRow("Background Music Loop Enabled", self.music_loop_input)
        form_layout.addRow("Music Duck Enabled", self.music_duck_input)
        form_layout.addRow("Music Duck Mode", self.music_duck_mode_input)
        form_layout.addRow("Music Duck Gain (dB)", self.music_duck_db_input)
        form_layout.addRow("Music Duck Attack (ms)", self.music_duck_attack_input)
        form_layout.addRow("Music Duck Release (ms)", self.music_duck_release_input)
        form_layout.addRow("Music Duck Threshold (dB)", self.music_duck_threshold_input)
        form_layout.addRow("Music Duck Ratio", self.music_duck_ratio_input)
        form_layout.addRow("Voice Mix Gain (dB)", self.voice_mix_gain_input)
        form_layout.addRow("Music Mix Gain (dB)", self.music_mix_gain_input)
        form_layout.addRow("Review Duration Mismatch (sec)", self.review_duration_mismatch_input)
        form_layout.addRow("Review Max Looped Segments", self.review_max_looped_segments_input)
        form_layout.addRow("Review Min Distinct Visual Assets", self.review_min_distinct_visual_assets_input)
        form_layout.addRow("Review Max Consecutive Same Visual", self.review_max_consecutive_visual_input)
        layout.addLayout(form_layout)

        button_row = QHBoxLayout()
        save_button = QPushButton("Save Settings")
        refresh_button = QPushButton("Reload")
        save_button.clicked.connect(self._save_settings)
        refresh_button.clicked.connect(self._view_model.load)
        button_row.addWidget(save_button)
        button_row.addWidget(refresh_button)
        layout.addLayout(button_row)

        self.feedback_label = QLabel()
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.feedback_label)
        layout.addStretch(1)
        return group

    def _populate_form(self) -> None:
        settings = self._view_model.settings
        if settings is None:
            return
        self.database_path_input.setText(settings.database_path)
        self.media_root_input.setText(settings.media_root)
        self.docs_root_input.setText(settings.docs_root)
        self.outputs_root_input.setText(settings.outputs_root)
        self.preview_root_input.setText(settings.preview_root)
        self.ffmpeg_root_input.setText(settings.ffmpeg_root)
        self.ffprobe_path_input.setText(settings.ffprobe_path)
        self.ffmpeg_path_input.setText(settings.ffmpeg_path)
        self.cpu_limit_input.setValue(settings.cpu_limit_percent)
        self.ram_limit_input.setValue(settings.ram_limit_percent)
        self.disk_free_input.setValue(settings.disk_free_gb_min)
        self.max_preview_input.setValue(settings.max_preview_workers)
        self.max_final_input.setValue(settings.max_final_workers)
        self.auto_refresh_input.setValue(settings.auto_refresh_seconds)
        self.auto_recover_input.setChecked(settings.auto_recover_queued_jobs)
        self.max_recovery_jobs_input.setValue(settings.max_recovery_jobs_per_run)
        self.failed_job_escalation_threshold_input.setValue(settings.failed_job_escalation_threshold)
        self.voice_loop_input.setChecked(settings.voice_loop_enabled)
        self.music_loop_input.setChecked(settings.background_music_loop_enabled)
        self.music_duck_input.setChecked(settings.music_duck_enabled)
        self.music_duck_mode_input.setCurrentText(settings.music_duck_mode)
        self.music_duck_db_input.setValue(settings.music_duck_db)
        self.music_duck_attack_input.setValue(settings.music_duck_attack_ms)
        self.music_duck_release_input.setValue(settings.music_duck_release_ms)
        self.music_duck_threshold_input.setValue(settings.music_duck_threshold_db)
        self.music_duck_ratio_input.setValue(settings.music_duck_ratio)
        self.voice_mix_gain_input.setValue(settings.voice_mix_gain_db)
        self.music_mix_gain_input.setValue(settings.music_mix_gain_db)
        self.review_duration_mismatch_input.setValue(settings.review_duration_mismatch_sec)
        self.review_max_looped_segments_input.setValue(settings.review_max_looped_segments)
        self.review_min_distinct_visual_assets_input.setValue(settings.review_min_distinct_visual_assets)
        self.review_max_consecutive_visual_input.setValue(settings.review_max_consecutive_same_visual_segments)

    def _refresh_feedback(self) -> None:
        self.feedback_label.setText(f"Status: {self._view_model.status}\n{self._view_model.feedback}".strip())

    def _save_settings(self) -> None:
        try:
            self._view_model.save(
                SystemSettingsDTO(
                    database_path=self.database_path_input.text(),
                    media_root=self.media_root_input.text(),
                    docs_root=self.docs_root_input.text(),
                    outputs_root=self.outputs_root_input.text(),
                    preview_root=self.preview_root_input.text(),
                    ffmpeg_root=self.ffmpeg_root_input.text(),
                    ffprobe_path=self.ffprobe_path_input.text(),
                    ffmpeg_path=self.ffmpeg_path_input.text(),
                    cpu_limit_percent=self.cpu_limit_input.value(),
                    ram_limit_percent=self.ram_limit_input.value(),
                    disk_free_gb_min=self.disk_free_input.value(),
                    max_preview_workers=self.max_preview_input.value(),
                    max_final_workers=self.max_final_input.value(),
                    auto_refresh_seconds=self.auto_refresh_input.value(),
                    auto_recover_queued_jobs=self.auto_recover_input.isChecked(),
                    max_recovery_jobs_per_run=self.max_recovery_jobs_input.value(),
                    failed_job_escalation_threshold=self.failed_job_escalation_threshold_input.value(),
                    voice_loop_enabled=self.voice_loop_input.isChecked(),
                    background_music_loop_enabled=self.music_loop_input.isChecked(),
                    music_duck_enabled=self.music_duck_input.isChecked(),
                    music_duck_mode=self.music_duck_mode_input.currentText(),
                    music_duck_db=self.music_duck_db_input.value(),
                    music_duck_attack_ms=self.music_duck_attack_input.value(),
                    music_duck_release_ms=self.music_duck_release_input.value(),
                    music_duck_threshold_db=self.music_duck_threshold_input.value(),
                    music_duck_ratio=self.music_duck_ratio_input.value(),
                    voice_mix_gain_db=self.voice_mix_gain_input.value(),
                    music_mix_gain_db=self.music_mix_gain_input.value(),
                    review_duration_mismatch_sec=self.review_duration_mismatch_input.value(),
                    review_max_looped_segments=self.review_max_looped_segments_input.value(),
                    review_min_distinct_visual_assets=self.review_min_distinct_visual_assets_input.value(),
                    review_max_consecutive_same_visual_segments=self.review_max_consecutive_visual_input.value(),
                )
            )
        except OSError as exc:
            QMessageBox.warning(self, "Save Settings", str(exc))
