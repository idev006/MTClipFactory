from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from mt_clip_factory.presentation.factory.auto_factory_control import AutoFactoryControlRunRequest, AutoFactoryControlViewModel


class AutoFactoryRunWorker(QObject):
    progress_changed = Signal(object)
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    MODE_RUN_REQUEST = "run_request"
    MODE_RESUME_ORDER = "resume_order"

    def __init__(
        self,
        view_model: AutoFactoryControlViewModel,
        *,
        mode: str,
        request: AutoFactoryControlRunRequest | None = None,
        production_order_id: int | None = None,
    ) -> None:
        super().__init__()
        self._view_model = view_model
        self._mode = mode
        self._request = request
        self._production_order_id = production_order_id

    @Slot()
    def run(self) -> None:
        try:
            if self._mode == self.MODE_RUN_REQUEST and self._request is not None:
                result = self._view_model.execute_run_request(
                    self._request,
                    progress_callback=self.progress_changed.emit,
                )
            elif self._mode == self.MODE_RESUME_ORDER and self._production_order_id is not None:
                result = self._view_model.execute_resume_order(self._production_order_id)
            else:
                raise ValueError(f"Unsupported worker mode: {self._mode}")
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.completed.emit(result)
        finally:
            self.finished.emit()
