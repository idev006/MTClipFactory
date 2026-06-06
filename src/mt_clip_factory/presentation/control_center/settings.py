from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from mt_clip_factory.control_center.dto import SystemSettingsDTO
from mt_clip_factory.control_center.services import SystemSettingsService


class SettingsViewModel(QObject):
    settings_changed = Signal()
    status_changed = Signal()
    feedback_changed = Signal()

    def __init__(self, settings_service: SystemSettingsService) -> None:
        super().__init__()
        self._settings_service = settings_service
        self._settings: SystemSettingsDTO | None = None
        self._status = "idle"
        self._feedback = ""

    def _get_status(self) -> str:
        return self._status

    def _set_status(self, value: str) -> None:
        if self._status == value:
            return
        self._status = value
        self.status_changed.emit()

    def _get_feedback(self) -> str:
        return self._feedback

    def _set_feedback(self, value: str) -> None:
        if self._feedback == value:
            return
        self._feedback = value
        self.feedback_changed.emit()

    status = Property(str, _get_status, notify=status_changed)
    feedback = Property(str, _get_feedback, notify=feedback_changed)

    @property
    def settings(self) -> SystemSettingsDTO | None:
        return self._settings

    @Slot()
    def load(self) -> None:
        self._set_status("loading")
        self._settings = self._settings_service.load()
        self.settings_changed.emit()
        self._set_status("ready")

    def save(self, settings: SystemSettingsDTO) -> None:
        self._set_status("saving")
        self._settings_service.save(settings)
        self._settings = self._settings_service.load()
        path_root_status = self._settings_service.path_root_status(configured_settings=self._settings)
        self.settings_changed.emit()
        changed_paths = ", ".join(path_root_status.changed_path_roots) or "none"
        if path_root_status.restart_required:
            feedback = (
                "System settings saved. Path-root reload policy is restart-driven. "
                f"Restart required for path roots: {changed_paths}. "
                "Auto-recovery startup policy applies on the next startup cycle. "
                "Failed-job escalation threshold applies on the next failed-job recovery run."
            )
        else:
            feedback = (
                "System settings saved. Path-root reload policy is restart-driven and no path-root restart is pending. "
                "Auto-recovery startup policy applies on the next startup cycle. "
                "Failed-job escalation threshold applies on the next failed-job recovery run."
            )
        self._set_feedback(feedback)
        self._set_status("ready")
