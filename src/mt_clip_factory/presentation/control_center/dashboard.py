from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from mt_clip_factory.control_center.dto import DashboardSummaryDTO
from mt_clip_factory.control_center.services import DashboardService


class DashboardViewModel(QObject):
    summary_changed = Signal()
    status_changed = Signal()

    def __init__(self, dashboard_service: DashboardService) -> None:
        super().__init__()
        self._dashboard_service = dashboard_service
        self._summary: DashboardSummaryDTO | None = None
        self._status = "idle"

    def _get_status(self) -> str:
        return self._status

    def _set_status(self, value: str) -> None:
        if self._status == value:
            return
        self._status = value
        self.status_changed.emit()

    status = Property(str, _get_status, notify=status_changed)

    @property
    def summary(self) -> DashboardSummaryDTO | None:
        return self._summary

    @Slot()
    def load(self) -> None:
        self._set_status("loading")
        self._summary = self._dashboard_service.build_summary()
        self.summary_changed.emit()
        self._set_status("ready")

    @Slot()
    def recover_queued_jobs(self) -> None:
        self._set_status("recovering")
        self._dashboard_service.recover_queued_jobs(trigger="manual")
        self._summary = self._dashboard_service.build_summary()
        self.summary_changed.emit()
        self._set_status("ready")

    @Slot()
    def retry_failed_jobs(self) -> None:
        self._set_status("recovering")
        self._dashboard_service.retry_failed_jobs(trigger="manual")
        self._summary = self._dashboard_service.build_summary()
        self.summary_changed.emit()
        self._set_status("ready")
