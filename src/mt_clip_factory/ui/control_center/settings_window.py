from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from mt_clip_factory.control_center.dto import SystemSettingsDTO
from mt_clip_factory.presentation.control_center.settings import SettingsViewModel


class IntSliderField(QWidget):
    def __init__(
        self,
        minimum: int,
        maximum: int,
        *,
        suffix: str = "",
        editor_minimum: int | None = None,
        editor_maximum: int | None = None,
    ) -> None:
        super().__init__()
        self._suffix = suffix
        self._syncing = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(minimum, maximum)
        self._slider.valueChanged.connect(self._sync_from_slider)
        self._editor = QSpinBox()
        self._editor.setRange(
            minimum if editor_minimum is None else editor_minimum,
            maximum if editor_maximum is None else editor_maximum,
        )
        self._editor.setSuffix(suffix)
        self._editor.setMinimumWidth(110)
        self._editor.valueChanged.connect(self._sync_from_editor)

        layout.addWidget(self._slider, 1)
        layout.addWidget(self._editor)
        self._sync_from_slider(self._slider.value())

    def value(self) -> int:
        return self._editor.value()

    def setValue(self, value: int) -> None:  # noqa: N802
        self._expand_range_for_value(value)
        self._editor.setValue(value)

    def _sync_from_slider(self, value: int) -> None:
        if self._syncing:
            return
        self._syncing = True
        self._expand_range_for_value(value)
        self._editor.setValue(value)
        self._syncing = False

    def _sync_from_editor(self, value: int) -> None:
        if self._syncing:
            return
        self._syncing = True
        self._expand_range_for_value(value)
        self._slider.setValue(value)
        self._syncing = False

    def _expand_range_for_value(self, value: int) -> None:
        slider_minimum = min(self._slider.minimum(), value)
        slider_maximum = max(self._slider.maximum(), value)
        if slider_minimum != self._slider.minimum() or slider_maximum != self._slider.maximum():
            self._slider.setRange(slider_minimum, slider_maximum)

        editor_minimum = min(self._editor.minimum(), value)
        editor_maximum = max(self._editor.maximum(), value)
        if editor_minimum != self._editor.minimum() or editor_maximum != self._editor.maximum():
            self._editor.setRange(editor_minimum, editor_maximum)


class FloatSliderField(QWidget):
    def __init__(
        self,
        minimum: float,
        maximum: float,
        *,
        decimals: int = 2,
        scale: int = 100,
        suffix: str = "",
        editor_minimum: float | None = None,
        editor_maximum: float | None = None,
    ) -> None:
        super().__init__()
        self._decimals = decimals
        self._scale = scale
        self._suffix = suffix
        self._syncing = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(int(round(minimum * scale)), int(round(maximum * scale)))
        self._slider.valueChanged.connect(self._sync_from_slider)
        self._editor = QDoubleSpinBox()
        self._editor.setRange(
            minimum if editor_minimum is None else editor_minimum,
            maximum if editor_maximum is None else editor_maximum,
        )
        self._editor.setDecimals(decimals)
        self._editor.setSingleStep(1 / scale)
        self._editor.setSuffix(suffix)
        self._editor.setMinimumWidth(120)
        self._editor.valueChanged.connect(self._sync_from_editor)

        layout.addWidget(self._slider, 1)
        layout.addWidget(self._editor)
        self._sync_from_slider(self._slider.value())

    def value(self) -> float:
        return self._editor.value()

    def setValue(self, value: float) -> None:  # noqa: N802
        scaled_value = int(round(value * self._scale))
        self._expand_range_for_value(scaled_value)
        self._editor.setValue(value)

    def _sync_from_slider(self, value: int) -> None:
        if self._syncing:
            return
        self._syncing = True
        self._expand_range_for_value(value)
        self._editor.setValue(value / self._scale)
        self._syncing = False

    def _sync_from_editor(self, value: float) -> None:
        if self._syncing:
            return
        self._syncing = True
        scaled_value = int(round(value * self._scale))
        self._expand_range_for_value(scaled_value)
        self._slider.setValue(scaled_value)
        self._syncing = False

    def _expand_range_for_value(self, value: int) -> None:
        slider_minimum = min(self._slider.minimum(), value)
        slider_maximum = max(self._slider.maximum(), value)
        if slider_minimum != self._slider.minimum() or slider_maximum != self._slider.maximum():
            self._slider.setRange(slider_minimum, slider_maximum)

        editor_minimum = min(self._editor.minimum(), value / self._scale)
        editor_maximum = max(self._editor.maximum(), value / self._scale)
        if editor_minimum != self._editor.minimum() or editor_maximum != self._editor.maximum():
            self._editor.setRange(editor_minimum, editor_maximum)


class SettingsWindow(QMainWindow):
    def __init__(self, view_model: SettingsViewModel) -> None:
        super().__init__()
        self._view_model = view_model
        self.setWindowTitle("MTClipFactory - Settings")
        self.resize(1180, 820)
        self._apply_styles()

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        layout.addWidget(self._build_header())
        layout.addWidget(self._build_settings_group(), 1)
        layout.addWidget(self._build_feedback_panel())
        self.setCentralWidget(central)

        self._view_model.settings_changed.connect(self._populate_form)
        self._view_model.status_changed.connect(self._refresh_feedback)
        self._view_model.feedback_changed.connect(self._refresh_feedback)
        self._refresh_feedback()
        self._view_model.load()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._view_model.load()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QGroupBox#panelBox {
                background-color: #f7f9fc;
                border: 1px solid #ccd5e3;
                border-radius: 12px;
                margin-top: 14px;
                padding-top: 10px;
            }
            QGroupBox#panelBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
                color: #183153;
                font-weight: 600;
            }
            QLabel#sectionHint {
                color: #5a677a;
            }
            QLabel#headerTitle {
                color: #183153;
                font-size: 18px;
                font-weight: 700;
            }
            QLabel#headerHint {
                color: #566273;
            }
            QLabel#statusValue {
                background-color: #e9eef7;
                border-radius: 8px;
                color: #183153;
                font-weight: 600;
                padding: 6px 10px;
            }
            """
        )

    def _build_header(self) -> QWidget:
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)

        title = QLabel("System Settings")
        title.setObjectName("headerTitle")
        hint = QLabel(
            "Grouped controls for path roots, runtime policy, recovery, audio behavior, and review rules."
        )
        hint.setObjectName("headerHint")
        hint.setWordWrap(True)
        text_layout.addWidget(title)
        text_layout.addWidget(hint)
        layout.addLayout(text_layout, 1)

        self.save_button = QPushButton("Save Settings")
        self.reload_button = QPushButton("Reload")
        self.save_button.clicked.connect(self._save_settings)
        self.reload_button.clicked.connect(self._view_model.load)
        layout.addWidget(self.reload_button)
        layout.addWidget(self.save_button)
        return header

    def _build_settings_group(self) -> QWidget:
        self._build_inputs()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        grid = QGridLayout(content)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        grid.addWidget(
            self._build_form_panel(
                "Workspace Paths",
                "These paths define where the live workspace reads and writes its operational data.",
                [
                    ("Database Path", self.database_path_input),
                    ("Media Root", self.media_root_input),
                    ("Docs Root", self.docs_root_input),
                    ("Outputs Root", self.outputs_root_input),
                    ("Preview Root", self.preview_root_input),
                ],
            ),
            0,
            0,
        )
        grid.addWidget(
            self._build_form_panel(
                "FFmpeg Toolchain",
                "Point the application at the exact FFmpeg and FFprobe binaries used for analysis and rendering.",
                [
                    ("FFmpeg Root", self.ffmpeg_root_input),
                    ("FFprobe Path", self.ffprobe_path_input),
                    ("FFmpeg Path", self.ffmpeg_path_input),
                ],
            ),
            0,
            1,
        )
        grid.addWidget(
            self._build_form_panel(
                "Runtime Limits",
                "These limits affect refresh cadence, resource ceilings, and worker concurrency.",
                [
                    ("CPU Limit Percent", self.cpu_limit_input),
                    ("RAM Limit Percent", self.ram_limit_input),
                    ("Disk Free GB Min", self.disk_free_input),
                    ("Max Preview Workers", self.max_preview_input),
                    ("Max Final Workers", self.max_final_input),
                    ("Auto Refresh Seconds", self.auto_refresh_input),
                ],
            ),
            1,
            0,
        )
        grid.addWidget(
            self._build_form_panel(
                "Recovery Policy",
                "Startup recovery and escalation thresholds help operators control how aggressively failed work is revisited.",
                [
                    ("Auto Recovery", self.auto_recover_input),
                    ("Max Recovery Jobs Per Run", self.max_recovery_jobs_input),
                    ("Failed Job Escalation Threshold", self.failed_job_escalation_threshold_input),
                ],
            ),
            1,
            1,
        )
        grid.addWidget(
            self._build_form_panel(
                "Audio Behavior",
                "Looping, ducking, and mix gain controls shape how narration and music behave during assembly.",
                [
                    ("Voice Looping", self.voice_loop_input),
                    ("Music Looping", self.music_loop_input),
                    ("Music Ducking", self.music_duck_input),
                    ("Music Duck Mode", self.music_duck_mode_input),
                    ("Music Duck Gain (dB)", self.music_duck_db_input),
                    ("Music Duck Attack (ms)", self.music_duck_attack_input),
                    ("Music Duck Release (ms)", self.music_duck_release_input),
                    ("Music Duck Threshold (dB)", self.music_duck_threshold_input),
                    ("Music Duck Ratio", self.music_duck_ratio_input),
                    ("Voice Mix Gain (dB)", self.voice_mix_gain_input),
                    ("Music Mix Gain (dB)", self.music_mix_gain_input),
                ],
            ),
            2,
            0,
            1,
            2,
        )
        grid.addWidget(
            self._build_form_panel(
                "Review Gate",
                "These signals decide when a recipe should be surfaced for extra operator review before final delivery.",
                [
                    ("Duration Mismatch (sec)", self.review_duration_mismatch_input),
                    ("Max Looped Segments", self.review_max_looped_segments_input),
                    ("Min Distinct Visual Assets", self.review_min_distinct_visual_assets_input),
                    ("Max Consecutive Same Visual", self.review_max_consecutive_visual_input),
                ],
            ),
            3,
            0,
        )
        grid.addWidget(self._build_save_guidance_panel(), 3, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        scroll_area.setWidget(content)
        return scroll_area

    def _build_inputs(self) -> None:
        self.ffmpeg_root_input = QLineEdit()
        self.ffprobe_path_input = QLineEdit()
        self.ffmpeg_path_input = QLineEdit()
        self.database_path_input = QLineEdit()
        self.media_root_input = QLineEdit()
        self.docs_root_input = QLineEdit()
        self.outputs_root_input = QLineEdit()
        self.preview_root_input = QLineEdit()
        self.cpu_limit_input = IntSliderField(0, 100, suffix="%", editor_minimum=0, editor_maximum=100)
        self.ram_limit_input = IntSliderField(0, 100, suffix="%", editor_minimum=0, editor_maximum=100)
        self.disk_free_input = IntSliderField(0, 1000, suffix=" GB", editor_minimum=0, editor_maximum=100000)
        self.max_preview_input = IntSliderField(0, 64, editor_minimum=0, editor_maximum=100000)
        self.max_final_input = IntSliderField(0, 64, editor_minimum=0, editor_maximum=100000)
        self.auto_refresh_input = IntSliderField(0, 3600, suffix=" s", editor_minimum=0, editor_maximum=100000)
        self.auto_recover_input = QCheckBox("Enable queued-job auto recovery on startup")
        self.max_recovery_jobs_input = IntSliderField(0, 500, editor_minimum=0, editor_maximum=100000)
        self.failed_job_escalation_threshold_input = IntSliderField(0, 100, editor_minimum=0, editor_maximum=100000)
        self.voice_loop_input = QCheckBox("Allow narration looping when timeline is longer than voice assets")
        self.music_loop_input = QCheckBox("Allow background music looping to fill timeline gaps")
        self.music_duck_input = QCheckBox("Enable music ducking while narration is active")
        self.music_duck_mode_input = QComboBox()
        self.music_duck_db_input = IntSliderField(-60, 0, suffix=" dB", editor_minimum=-60, editor_maximum=0)
        self.music_duck_attack_input = IntSliderField(0, 10000, suffix=" ms", editor_minimum=0, editor_maximum=100000)
        self.music_duck_release_input = IntSliderField(0, 10000, suffix=" ms", editor_minimum=0, editor_maximum=100000)
        self.music_duck_threshold_input = IntSliderField(-60, 0, suffix=" dB", editor_minimum=-60, editor_maximum=0)
        self.music_duck_ratio_input = FloatSliderField(
            1.0,
            30.0,
            decimals=2,
            scale=100,
            editor_minimum=1.0,
            editor_maximum=100.0,
        )
        self.voice_mix_gain_input = IntSliderField(-24, 24, suffix=" dB", editor_minimum=-24, editor_maximum=24)
        self.music_mix_gain_input = IntSliderField(-24, 24, suffix=" dB", editor_minimum=-24, editor_maximum=24)
        self.review_duration_mismatch_input = IntSliderField(0, 300, suffix=" s", editor_minimum=0, editor_maximum=100000)
        self.review_max_looped_segments_input = IntSliderField(0, 100, editor_minimum=0, editor_maximum=100000)
        self.review_min_distinct_visual_assets_input = IntSliderField(0, 100, editor_minimum=0, editor_maximum=100000)
        self.review_max_consecutive_visual_input = IntSliderField(0, 100, editor_minimum=0, editor_maximum=100000)

        self.music_duck_mode_input.addItems(["sidechain_compressor", "windowed_volume_duck"])

        self.auto_recover_input.setText("Recover queued jobs during startup")
        self.voice_loop_input.setText("Allow narration looping when the timeline runs longer than voice assets")
        self.music_loop_input.setText("Allow background music looping to fill timeline gaps")
        self.music_duck_input.setText("Reduce music while narration is active")

    def _build_form_panel(self, title: str, hint: str, rows: list[tuple[str, QWidget]]) -> QGroupBox:
        panel = QGroupBox(title)
        panel.setObjectName("panelBox")
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        hint_label = QLabel(hint)
        hint_label.setObjectName("sectionHint")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

        form_layout = QFormLayout()
        form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignTop)
        form_layout.setFormAlignment(Qt.AlignTop)
        form_layout.setHorizontalSpacing(14)
        form_layout.setVerticalSpacing(10)
        for label, widget in rows:
            form_layout.addRow(label, widget)
        layout.addLayout(form_layout)
        return panel

    def _build_save_guidance_panel(self) -> QGroupBox:
        panel = QGroupBox("Save Guidance")
        panel.setObjectName("panelBox")
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        guidance = QLabel(
            "Save writes the current settings to app_config.toml. Path-root changes may hot-reload immediately "
            "or may apply on next startup depending on runtime policy."
        )
        guidance.setObjectName("sectionHint")
        guidance.setWordWrap(True)
        layout.addWidget(guidance)

        note = QLabel(
            "Use Reload if another operator or tool has modified configuration and you want to refresh the live form."
        )
        note.setObjectName("sectionHint")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        return panel

    def _build_feedback_panel(self) -> QGroupBox:
        panel = QGroupBox("Status And Feedback")
        panel.setObjectName("panelBox")
        layout = QHBoxLayout(panel)
        layout.setSpacing(14)

        status_title = QLabel("Current Status")
        self.status_value_label = QLabel()
        self.status_value_label.setObjectName("statusValue")
        status_column = QVBoxLayout()
        status_column.addWidget(status_title)
        status_column.addWidget(self.status_value_label, 0, Qt.AlignLeft)
        status_column.addStretch(1)
        layout.addLayout(status_column)

        self.feedback_label = QLabel()
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.feedback_label, 1)
        return panel

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
        self.status_value_label.setText(self._view_model.status.title())
        self.feedback_label.setText(self._view_model.feedback or "No feedback yet.")

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
