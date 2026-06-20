from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from mt_clip_factory.presentation.factory.auto_factory_control import AutoFactoryControlRunRequest, AutoFactoryControlViewModel


class AutoFactoryRunWorker(QObject):
    progress_changed = Signal(object)
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, view_model: AutoFactoryControlViewModel, request: AutoFactoryControlRunRequest) -> None:
        super().__init__()
        self._view_model = view_model
        self._request = request

    @Slot()
    def run(self) -> None:
        try:
            result = self._view_model.execute_run_request(
                self._request,
                progress_callback=self.progress_changed.emit,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.completed.emit(result)
        finally:
            self.finished.emit()
