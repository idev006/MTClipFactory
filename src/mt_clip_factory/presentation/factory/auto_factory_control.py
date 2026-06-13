from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal

from mt_clip_factory.factory.auto_factory_folder import AutoFactoryFolderService
from mt_clip_factory.factory.auto_factory_folder_dto import AutoFactoryFolderRunReportDTO
from mt_clip_factory.factory.production_order_dto import ProductionOrderDetailsDTO, ProductionOrderSummaryDTO
from mt_clip_factory.factory.production_order_service import ProductionOrderService


class AutoFactoryControlViewModel(QObject):
    recent_orders_changed = Signal()
    run_report_changed = Signal()
    selected_order_changed = Signal()
    status_changed = Signal()
    feedback_changed = Signal()

    RUN_MODE_INTAKE_ONLY = "intake_only"
    RUN_MODE_MATERIALIZE = "materialize"
    RUN_MODE_MATERIALIZE_AND_PREVIEWS = "materialize_and_build_previews"
    RUN_MODES = (
        RUN_MODE_INTAKE_ONLY,
        RUN_MODE_MATERIALIZE,
        RUN_MODE_MATERIALIZE_AND_PREVIEWS,
    )

    def __init__(
        self,
        auto_factory_folder_service: AutoFactoryFolderService,
        production_order_service: ProductionOrderService,
    ) -> None:
        super().__init__()
        self._auto_factory_folder_service = auto_factory_folder_service
        self._production_order_service = production_order_service
        self._recent_orders: list[ProductionOrderSummaryDTO] = []
        self._run_report: AutoFactoryFolderRunReportDTO | None = None
        self._selected_order: ProductionOrderDetailsDTO | None = None
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
    def recent_orders(self) -> list[ProductionOrderSummaryDTO]:
        return list(self._recent_orders)

    @property
    def run_report(self) -> AutoFactoryFolderRunReportDTO | None:
        return self._run_report

    @property
    def selected_order(self) -> ProductionOrderDetailsDTO | None:
        return self._selected_order

    def load(self) -> None:
        self._set_status("loading")
        try:
            self._recent_orders = self._production_order_service.list_orders()
        except Exception as exc:
            self._set_feedback(str(exc))
            self._set_status("error")
            raise
        self.recent_orders_changed.emit()
        self._set_status("ready")

    def run_batch_root(
        self,
        *,
        root_folder: str,
        batch_code: str | None = None,
        scan_depth: int = 1,
        run_mode: str = RUN_MODE_INTAKE_ONLY,
    ) -> None:
        if run_mode not in self.RUN_MODES:
            raise ValueError(f"Unsupported run_mode: {run_mode}")

        normalized_root = root_folder.strip()
        if not normalized_root:
            raise ValueError("Root folder is required.")

        self._set_status("running")
        try:
            run_report = self._auto_factory_folder_service.run_batch_root(
                Path(normalized_root),
                batch_code=batch_code or None,
                scan_depth=scan_depth,
                materialize=False,
            )
            selected_order = None
            if run_mode != self.RUN_MODE_INTAKE_ONLY:
                selected_order = self._production_order_service.create_and_run_order(
                    run_report.order,
                    source_mode="folder_control_surface",
                    order_code=_build_order_code(run_report.batch_code),
                    build_previews=run_mode == self.RUN_MODE_MATERIALIZE_AND_PREVIEWS,
                )
            self._run_report = run_report
            self._selected_order = selected_order
            self.run_report_changed.emit()
            self.selected_order_changed.emit()
            self._recent_orders = self._production_order_service.list_orders()
            self.recent_orders_changed.emit()
        except Exception as exc:
            self._set_feedback(str(exc))
            self._set_status("error")
            raise

        self._set_feedback(_build_run_feedback(run_report, selected_order))
        self._set_status("ready")

    def select_order(self, production_order_id: int | None) -> None:
        if production_order_id is None:
            self._selected_order = None
            self.selected_order_changed.emit()
            return

        self._set_status("loading_order")
        try:
            self._selected_order = self._production_order_service.get_order(production_order_id)
        except Exception as exc:
            self._set_feedback(str(exc))
            self._set_status("error")
            raise
        self.selected_order_changed.emit()
        self._set_feedback(f"Loaded production order #{production_order_id}.")
        self._set_status("ready")


def _build_order_code(batch_code: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
    return f"{batch_code}_{timestamp}"


def _build_run_feedback(
    run_report: AutoFactoryFolderRunReportDTO,
    selected_order: ProductionOrderDetailsDTO | None,
) -> str:
    product_count = len(run_report.product_reports)
    registered_count = sum(report.registered_asset_count for report in run_report.product_reports)
    skipped_count = sum(report.skipped_existing_asset_count for report in run_report.product_reports)
    base = (
        f"Discovered {len(run_report.discovered_product_dirs)} product folder(s), "
        f"processed {product_count} product request(s), "
        f"registered {registered_count} asset(s), and skipped {skipped_count} existing asset(s)."
    )
    if selected_order is None:
        return f"{base} Intake completed without creating a production order."
    return (
        f"{base} Production order {selected_order.order_code} finished in state "
        f"{selected_order.status} with {len(selected_order.stages)} recorded stage(s)."
    )
