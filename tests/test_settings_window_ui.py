from __future__ import annotations

import math

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QGroupBox

from mt_clip_factory.control_center.dto import SystemSettingsDTO
from mt_clip_factory.ui.control_center.settings_window import (
    FloatSliderField,
    IntSliderField,
    SettingsWindow,
)


@pytest.fixture()
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class FakeSettingsViewModel(QObject):
    settings_changed = Signal()
    status_changed = Signal()
    feedback_changed = Signal()

    def __init__(self, settings: SystemSettingsDTO) -> None:
        super().__init__()
        self.settings = settings
        self.status = "idle"
        self.feedback = ""
        self.saved_settings: SystemSettingsDTO | None = None
        self.load_call_count = 0

    def load(self) -> None:
        self.load_call_count += 1
        self.status = "ready"
        self.feedback = "Settings loaded."
        self.settings_changed.emit()
        self.status_changed.emit()
        self.feedback_changed.emit()

    def save(self, settings: SystemSettingsDTO) -> None:
        self.saved_settings = settings
        self.settings = settings
        self.status = "ready"
        self.feedback = "Settings saved."
        self.settings_changed.emit()
        self.status_changed.emit()
        self.feedback_changed.emit()


def _settings(
    *,
    max_recovery_jobs_per_run: int = 25,
    failed_job_escalation_threshold: int = 2,
    music_duck_ratio: float = 8.0,
    visual_key_profile: str = "auto",
    visual_key_color: str = "#00FF00",
) -> SystemSettingsDTO:
    return SystemSettingsDTO(
        database_path="ad_kitchen.db",
        media_root="media_library",
        docs_root="doc",
        outputs_root="outputs",
        preview_root="outputs\\preview",
        ffmpeg_root="F:\\ffmpeg",
        ffprobe_path="F:\\ffmpeg\\bin\\ffprobe.exe",
        ffmpeg_path="F:\\ffmpeg\\bin\\ffmpeg.exe",
        cpu_limit_percent=90,
        ram_limit_percent=80,
        disk_free_gb_min=20,
        max_preview_workers=1,
        max_final_workers=1,
        auto_refresh_seconds=10,
        auto_recover_queued_jobs=False,
        max_recovery_jobs_per_run=max_recovery_jobs_per_run,
        failed_job_escalation_threshold=failed_job_escalation_threshold,
        voice_loop_enabled=False,
        background_music_loop_enabled=True,
        music_duck_enabled=True,
        visual_key_profile=visual_key_profile,
        visual_key_color=visual_key_color,
        music_duck_mode="sidechain_compressor",
        music_duck_db=-15,
        music_duck_attack_ms=250,
        music_duck_release_ms=500,
        music_duck_threshold_db=-24,
        music_duck_ratio=music_duck_ratio,
        voice_mix_gain_db=0,
        music_mix_gain_db=-4,
        review_duration_mismatch_sec=1,
        review_max_looped_segments=2,
        review_min_distinct_visual_assets=2,
        review_max_consecutive_same_visual_segments=3,
    )


def test_int_slider_field_expands_to_preserve_loaded_value(qapp: QApplication) -> None:
    field = IntSliderField(0, 100, suffix="%")

    field.setValue(250)

    assert field.value() == 250
    assert field._editor.value() == 250


def test_int_slider_field_exact_entry_syncs_back_to_slider(qapp: QApplication) -> None:
    field = IntSliderField(0, 100, suffix="%", editor_minimum=0, editor_maximum=100000)

    field._editor.setValue(67)

    assert field.value() == 67
    assert field._slider.value() == 67
    field._editor.setValue(725)
    assert field.value() == 725
    assert field._slider.value() == 725


def test_float_slider_field_expands_and_preserves_precision(qapp: QApplication) -> None:
    field = FloatSliderField(1.0, 30.0, decimals=2, scale=100)

    field.setValue(35.5)

    assert math.isclose(field.value(), 35.5, rel_tol=0.0, abs_tol=0.01)
    assert math.isclose(field._editor.value(), 35.5, rel_tol=0.0, abs_tol=0.01)


def test_float_slider_field_exact_entry_syncs_back_to_slider(qapp: QApplication) -> None:
    field = FloatSliderField(1.0, 30.0, decimals=2, scale=100, editor_minimum=1.0, editor_maximum=100.0)

    field._editor.setValue(6.75)

    assert math.isclose(field.value(), 6.75, rel_tol=0.0, abs_tol=0.01)
    assert field._slider.value() == 675
    field._editor.setValue(32.25)
    assert math.isclose(field.value(), 32.25, rel_tol=0.0, abs_tol=0.01)
    assert field._slider.value() == 3225


def test_slider_fields_use_uniform_widths(qapp: QApplication) -> None:
    int_field = IntSliderField(0, 100, suffix="%")
    float_field = FloatSliderField(1.0, 30.0, decimals=2, scale=100)

    assert int_field._slider.minimumWidth() == IntSliderField.SLIDER_TRACK_WIDTH
    assert int_field._slider.maximumWidth() == IntSliderField.SLIDER_TRACK_WIDTH
    assert int_field._editor.minimumWidth() == IntSliderField.EDITOR_WIDTH
    assert int_field._editor.maximumWidth() == IntSliderField.EDITOR_WIDTH
    assert float_field._slider.minimumWidth() == FloatSliderField.SLIDER_TRACK_WIDTH
    assert float_field._slider.maximumWidth() == FloatSliderField.SLIDER_TRACK_WIDTH
    assert float_field._editor.minimumWidth() == FloatSliderField.EDITOR_WIDTH
    assert float_field._editor.maximumWidth() == FloatSliderField.EDITOR_WIDTH


def test_settings_window_populates_grouped_controls(qapp: QApplication) -> None:
    view_model = FakeSettingsViewModel(_settings())

    window = SettingsWindow(view_model)
    qapp.processEvents()

    assert view_model.load_call_count >= 1
    assert window.cpu_limit_input.value() == 90
    assert window.music_duck_ratio_input.value() == 8.0
    assert window.auto_recover_input.isChecked() is False
    assert window.preview_output_resolution_input.text() == ""
    assert window.final_output_resolution_input.text() == ""
    assert window.visual_key_profile_input.currentText() == "auto"
    assert window.visual_key_color_input.text() == "#00FF00"
    assert window.visual_key_color_input.isEnabled() is False
    assert window.feedback_label.text() == "Settings loaded."
    assert "QGroupBox#panelBox" in window.styleSheet()
    titles = {group.title() for group in window.findChildren(QGroupBox)}
    assert {
        "Workspace Paths",
        "FFmpeg Toolchain",
        "Runtime Limits",
        "Render Output",
        "Recovery Policy",
        "Visual Composite",
        "Audio Behavior",
        "Review Gate",
        "Save Guidance",
        "Status And Feedback",
    }.issubset(titles)
    window.close()


def test_settings_window_save_maps_slider_values_into_dto(qapp: QApplication) -> None:
    view_model = FakeSettingsViewModel(_settings())
    window = SettingsWindow(view_model)
    qapp.processEvents()

    window.database_path_input.setText("custom.db")
    window.preview_output_resolution_input.setText("1080*1920")
    window.final_output_resolution_input.setText("720x1280")
    window.visual_key_profile_input.setCurrentText("custom")
    window.visual_key_color_input.setText("#1122CC")
    window.cpu_limit_input._editor.setValue(77)
    window.max_recovery_jobs_input._editor.setValue(44)
    window.failed_job_escalation_threshold_input._editor.setValue(5)
    window.music_duck_ratio_input._editor.setValue(6.5)
    window.auto_recover_input.setChecked(True)
    window.music_duck_mode_input.setCurrentText("windowed_volume_duck")
    window._save_settings()

    assert view_model.saved_settings is not None
    assert view_model.saved_settings.database_path == "custom.db"
    assert view_model.saved_settings.preview_output_resolution == "1080*1920"
    assert view_model.saved_settings.final_output_resolution == "720x1280"
    assert view_model.saved_settings.visual_key_profile == "custom"
    assert view_model.saved_settings.visual_key_color == "#1122CC"
    assert view_model.saved_settings.cpu_limit_percent == 77
    assert view_model.saved_settings.max_recovery_jobs_per_run == 44
    assert view_model.saved_settings.failed_job_escalation_threshold == 5
    assert math.isclose(view_model.saved_settings.music_duck_ratio, 6.5, rel_tol=0.0, abs_tol=0.01)
    assert view_model.saved_settings.auto_recover_queued_jobs is True
    assert view_model.saved_settings.music_duck_mode == "windowed_volume_duck"
    window.close()


def test_settings_window_preserves_out_of_range_loaded_values_on_save(qapp: QApplication) -> None:
    view_model = FakeSettingsViewModel(
        _settings(max_recovery_jobs_per_run=725, failed_job_escalation_threshold=140, music_duck_ratio=31.5)
    )
    window = SettingsWindow(view_model)
    qapp.processEvents()

    assert window.max_recovery_jobs_input.value() == 725
    assert window.failed_job_escalation_threshold_input.value() == 140
    assert math.isclose(window.music_duck_ratio_input.value(), 31.5, rel_tol=0.0, abs_tol=0.01)

    window._save_settings()

    assert view_model.saved_settings is not None
    assert view_model.saved_settings.max_recovery_jobs_per_run == 725
    assert view_model.saved_settings.failed_job_escalation_threshold == 140
    assert math.isclose(view_model.saved_settings.music_duck_ratio, 31.5, rel_tol=0.0, abs_tol=0.01)
    window.close()


def test_settings_window_exact_entry_allows_precise_high_value_updates(qapp: QApplication) -> None:
    view_model = FakeSettingsViewModel(
        _settings(max_recovery_jobs_per_run=725, failed_job_escalation_threshold=140, music_duck_ratio=31.5)
    )
    window = SettingsWindow(view_model)
    qapp.processEvents()

    window.max_recovery_jobs_input._editor.setValue(730)
    window.failed_job_escalation_threshold_input._editor.setValue(145)
    window.music_duck_ratio_input._editor.setValue(32.25)
    window._save_settings()

    assert view_model.saved_settings is not None
    assert view_model.saved_settings.max_recovery_jobs_per_run == 730
    assert view_model.saved_settings.failed_job_escalation_threshold == 145
    assert math.isclose(view_model.saved_settings.music_duck_ratio, 32.25, rel_tol=0.0, abs_tol=0.01)
    window.close()


def test_settings_window_enables_custom_key_color_only_for_custom_policy(qapp: QApplication) -> None:
    view_model = FakeSettingsViewModel(_settings(visual_key_profile="blue", visual_key_color="#0000FF"))
    window = SettingsWindow(view_model)
    qapp.processEvents()

    assert window.visual_key_color_input.isEnabled() is False
    window.visual_key_profile_input.setCurrentText("custom")
    assert window.visual_key_color_input.isEnabled() is True
    window.visual_key_profile_input.setCurrentText("disabled")
    assert window.visual_key_color_input.isEnabled() is False
    window.close()
