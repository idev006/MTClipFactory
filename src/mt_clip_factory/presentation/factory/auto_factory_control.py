from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import json

from PySide6.QtCore import QObject, Property, Signal

from mt_clip_factory.factory.auto_factory_folder import AutoFactoryFolderService
from mt_clip_factory.factory.auto_factory_folder_dto import (
    AutoFactoryFolderPreflightReportDTO,
    AutoFactoryFolderRunReportDTO,
)
from mt_clip_factory.factory.production_order_dto import (
    ProductionOrderDetailsDTO,
    ProductionOrderStageDTO,
    ProductionOrderSummaryDTO,
)
from mt_clip_factory.factory.production_order_service import ProductionOrderService
from mt_clip_factory.time_utils import build_local_timestamp_token

TERMINAL_STAGE_STATUSES = {"succeeded", "review_required", "failed_retryable", "failed_terminal", "cancelled"}
ACTIVE_ORDER_STATUSES = {"leased", "processing", "pause_requested", "stop_requested", "resume_requested"}
RESUMABLE_ORDER_STATUSES = {"paused", "stopped", "failed_retryable", "review_required", "blocked"}


@dataclass(slots=True, frozen=True)
class AutoFactoryControlRunRequest:
    root_folder: str
    batch_code: str | None
    scan_depth: int
    run_mode: str


@dataclass(slots=True, frozen=True)
class AutoFactoryControlExecutionResult:
    request: AutoFactoryControlRunRequest
    preflight_report: AutoFactoryFolderPreflightReportDTO | None
    run_report: AutoFactoryFolderRunReportDTO | None
    selected_order: ProductionOrderDetailsDTO | None
    created_order_id: int | None = None
    created_order_code: str | None = None


@dataclass(slots=True, frozen=True)
class AutoFactoryControlProgressSnapshot:
    run_state: str
    phase: str
    run_mode: str | None
    root_folder: str | None
    batch_code: str | None
    monitored_order_id: int | None
    monitored_order_code: str | None
    order_status: str | None
    current_stage: str | None
    lease_owner: str | None
    lease_expires_at: str | None
    lease_heartbeat_at: str | None
    total_products: int
    products_with_stage_activity: int
    total_requested_outputs: int
    materialized_recipe_count: int
    preview_completed_count: int
    review_required_count: int
    stage_count: int
    active_worker_count: int
    last_event: str
    blocking_reason: str | None
    started_at: str | None
    finished_at: str | None
    command_note: str

    @classmethod
    def idle(cls) -> AutoFactoryControlProgressSnapshot:
        return cls(
            run_state="idle",
            phase="idle",
            run_mode=None,
            root_folder=None,
            batch_code=None,
            monitored_order_id=None,
            monitored_order_code=None,
            order_status=None,
            current_stage=None,
            lease_owner=None,
            lease_expires_at=None,
            lease_heartbeat_at=None,
            total_products=0,
            products_with_stage_activity=0,
            total_requested_outputs=0,
            materialized_recipe_count=0,
            preview_completed_count=0,
            review_required_count=0,
            stage_count=0,
            active_worker_count=0,
            last_event="No active run.",
            blocking_reason=None,
            started_at=None,
            finished_at=None,
            command_note=_build_command_note(order_status=None, run_active=False),
        )


class AutoFactoryControlViewModel(QObject):
    recent_orders_changed = Signal()
    run_report_changed = Signal()
    preflight_report_changed = Signal()
    selected_order_changed = Signal()
    status_changed = Signal()
    feedback_changed = Signal()
    progress_changed = Signal()
    run_active_changed = Signal()

    RUN_MODE_AUDIT_ONLY = "audit_only"
    RUN_MODE_INTAKE_ONLY = "intake_only"
    RUN_MODE_MATERIALIZE = "materialize"
    RUN_MODE_MATERIALIZE_AND_PREVIEWS = "materialize_and_build_previews"
    RUN_MODES = (
        RUN_MODE_AUDIT_ONLY,
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
        self._preflight_report: AutoFactoryFolderPreflightReportDTO | None = None
        self._selected_order: ProductionOrderDetailsDTO | None = None
        self._status = "idle"
        self._feedback = ""
        self._progress_snapshot = AutoFactoryControlProgressSnapshot.idle()
        self._run_active = False
        self._run_request: AutoFactoryControlRunRequest | None = None
        self._monitored_order_id: int | None = None

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
    def preflight_report(self) -> AutoFactoryFolderPreflightReportDTO | None:
        return self._preflight_report

    @property
    def selected_order(self) -> ProductionOrderDetailsDTO | None:
        return self._selected_order

    @property
    def progress_snapshot(self) -> AutoFactoryControlProgressSnapshot:
        return self._progress_snapshot

    @property
    def run_active(self) -> bool:
        return self._run_active

    @property
    def monitored_order_id(self) -> int | None:
        return self._monitored_order_id

    def load(self) -> None:
        self._set_status("loading")
        try:
            self._refresh_recent_orders()
        except Exception as exc:
            self._set_feedback(str(exc))
            self._set_status("error")
            raise
        self._set_status("ready")

    def prepare_run_request(
        self,
        *,
        root_folder: str,
        batch_code: str | None = None,
        scan_depth: int = 1,
        run_mode: str = RUN_MODE_INTAKE_ONLY,
    ) -> AutoFactoryControlRunRequest:
        if run_mode not in self.RUN_MODES:
            raise ValueError(f"Unsupported run_mode: {run_mode}")

        normalized_root = root_folder.strip()
        if not normalized_root:
            raise ValueError("Root folder is required.")

        normalized_batch_code = None if batch_code is None or not batch_code.strip() else batch_code.strip()
        return AutoFactoryControlRunRequest(
            root_folder=normalized_root,
            batch_code=normalized_batch_code,
            scan_depth=scan_depth,
            run_mode=run_mode,
        )

    def mark_run_started(self, request: AutoFactoryControlRunRequest) -> None:
        self._run_request = request
        self._set_run_active(True)
        self._set_status("running")
        self._set_feedback("Auto Factory run started.")
        self.update_progress_snapshot(_build_initial_progress_snapshot(request))

    def mark_resume_started(self, production_order_id: int) -> None:
        self._set_run_active(True)
        self._set_status("running")
        self._monitored_order_id = production_order_id
        self._set_feedback(f"Resuming production order #{production_order_id}.")
        try:
            selected_order = self._production_order_service.get_order(production_order_id)
        except Exception:
            return
        self._selected_order = selected_order
        self.selected_order_changed.emit()
        self.update_progress_snapshot(
            _build_order_progress_snapshot(
                selected_order,
                request=_request_from_order(selected_order, fallback=self._run_request),
                run_state="running",
                phase="resuming_order",
                command_note=_build_command_note(
                    order_status=selected_order.status,
                    run_active=True,
                ),
            )
        )

    def execute_run_request(
        self,
        request: AutoFactoryControlRunRequest,
        *,
        progress_callback=None,
    ) -> AutoFactoryControlExecutionResult:
        if progress_callback is not None:
            progress_callback(_build_initial_progress_snapshot(request))

        if request.run_mode == self.RUN_MODE_AUDIT_ONLY:
            preflight_report = self._auto_factory_folder_service.audit_batch_root(
                Path(request.root_folder),
                scan_depth=request.scan_depth,
            )
            return AutoFactoryControlExecutionResult(
                request=request,
                preflight_report=preflight_report,
                run_report=None,
                selected_order=None,
            )

        run_report = self._auto_factory_folder_service.run_batch_root(
            Path(request.root_folder),
            batch_code=request.batch_code,
            scan_depth=request.scan_depth,
            materialize=False,
        )
        if request.run_mode == self.RUN_MODE_INTAKE_ONLY:
            return AutoFactoryControlExecutionResult(
                request=request,
                preflight_report=None,
                run_report=run_report,
                selected_order=None,
            )

        order_code = _build_order_code(run_report.batch_code)
        order_id = self._production_order_service.create_order(
            run_report.order,
            source_mode="folder_control_surface",
            order_code=order_code,
            build_previews=request.run_mode == self.RUN_MODE_MATERIALIZE_AND_PREVIEWS,
            run_mode=request.run_mode,
            source_root=request.root_folder,
        )
        if progress_callback is not None:
            progress_callback(
                _build_order_bootstrap_progress_snapshot(
                    request=request,
                    run_report=run_report,
                    order_id=order_id,
                    order_code=order_code,
                )
            )
        selected_order = self._production_order_service.run_order(
            order_id,
            build_previews=request.run_mode == self.RUN_MODE_MATERIALIZE_AND_PREVIEWS,
        )
        return AutoFactoryControlExecutionResult(
            request=request,
            preflight_report=None,
            run_report=run_report,
            selected_order=selected_order,
            created_order_id=order_id,
            created_order_code=order_code,
        )

    def execute_resume_order(self, production_order_id: int) -> AutoFactoryControlExecutionResult:
        selected_order = self._production_order_service.resume_order(production_order_id)
        request = _request_from_order(selected_order, fallback=self._run_request)
        return AutoFactoryControlExecutionResult(
            request=request,
            preflight_report=None,
            run_report=self._run_report,
            selected_order=selected_order,
            created_order_id=selected_order.production_order_id,
            created_order_code=selected_order.order_code,
        )

    def apply_execution_result(self, result: AutoFactoryControlExecutionResult) -> None:
        self._run_report = result.run_report
        self._preflight_report = result.preflight_report
        self._selected_order = result.selected_order
        self._run_request = result.request
        self._monitored_order_id = result.created_order_id
        self.run_report_changed.emit()
        self.preflight_report_changed.emit()
        self.selected_order_changed.emit()
        self._refresh_recent_orders()

        if result.preflight_report is not None:
            self.update_progress_snapshot(_build_preflight_progress_snapshot(result.request, result.preflight_report))
            self._set_feedback(_build_preflight_feedback(result.preflight_report))
        elif result.run_report is not None and result.selected_order is None:
            self.update_progress_snapshot(_build_intake_progress_snapshot(result.request, result.run_report))
            self._set_feedback(_build_run_feedback(result.run_report, result.selected_order))
        elif result.selected_order is not None:
            self.update_progress_snapshot(
                _build_order_progress_snapshot(
                    result.selected_order,
                    request=result.request,
                    run_state=_snapshot_run_state(result.selected_order.status, run_active=False),
                    phase="completed" if result.selected_order.status in TERMINAL_STAGE_STATUSES else "order_controlled",
                    command_note=_build_command_note(
                        order_status=result.selected_order.status,
                        run_active=False,
                    ),
                )
            )
            self._set_feedback(_build_run_feedback(result.run_report, result.selected_order))

        self._set_run_active(False)
        self._set_status("ready")

    def handle_run_failure(self, error_message: str) -> None:
        self._set_feedback(error_message)
        self._set_status("error")
        self.update_progress_snapshot(
            AutoFactoryControlProgressSnapshot(
                run_state="failed",
                phase="failed",
                run_mode=None if self._run_request is None else self._run_request.run_mode,
                root_folder=None if self._run_request is None else self._run_request.root_folder,
                batch_code=None if self._run_request is None else self._run_request.batch_code,
                monitored_order_id=self._monitored_order_id,
                monitored_order_code=None,
                order_status="failed_terminal",
                current_stage=self._progress_snapshot.current_stage,
                lease_owner=None,
                lease_expires_at=None,
                lease_heartbeat_at=None,
                total_products=self._progress_snapshot.total_products,
                products_with_stage_activity=self._progress_snapshot.products_with_stage_activity,
                total_requested_outputs=self._progress_snapshot.total_requested_outputs,
                materialized_recipe_count=self._progress_snapshot.materialized_recipe_count,
                preview_completed_count=self._progress_snapshot.preview_completed_count,
                review_required_count=self._progress_snapshot.review_required_count,
                stage_count=self._progress_snapshot.stage_count,
                active_worker_count=0,
                last_event=error_message,
                blocking_reason=error_message,
                started_at=self._progress_snapshot.started_at,
                finished_at=None,
                command_note=_build_command_note(order_status="failed_terminal", run_active=False),
            )
        )
        self._set_run_active(False)

    def update_progress_snapshot(self, snapshot: AutoFactoryControlProgressSnapshot) -> None:
        self._progress_snapshot = snapshot
        if snapshot.monitored_order_id is not None:
            self._monitored_order_id = snapshot.monitored_order_id
        self.progress_changed.emit()

    def refresh_progress(self) -> None:
        self._refresh_recent_orders()
        if self._monitored_order_id is None:
            return
        selected_order = self._production_order_service.get_order(self._monitored_order_id)
        self._selected_order = selected_order
        self.selected_order_changed.emit()
        self.update_progress_snapshot(
            _build_order_progress_snapshot(
                selected_order,
                request=self._run_request,
                run_state=_snapshot_run_state(selected_order.status, run_active=self._run_active),
                phase="monitoring_order",
                command_note=_build_command_note(order_status=selected_order.status, run_active=self._run_active),
            )
        )

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
        self._monitored_order_id = production_order_id
        self.selected_order_changed.emit()
        self.update_progress_snapshot(
            _build_order_progress_snapshot(
                self._selected_order,
                request=_request_from_order(self._selected_order, fallback=self._run_request),
                run_state=_snapshot_run_state(self._selected_order.status, run_active=self._run_active),
                phase="selected_order",
                command_note=_build_command_note(order_status=self._selected_order.status, run_active=self._run_active),
            )
        )
        self._set_feedback(f"Loaded production order #{production_order_id}.")
        self._set_status("ready")

    def request_pause(self) -> None:
        order = self._require_order_context()
        updated = self._production_order_service.request_pause(order.production_order_id)
        self._selected_order = updated
        self.selected_order_changed.emit()
        self.update_progress_snapshot(
            _build_order_progress_snapshot(
                updated,
                request=_request_from_order(updated, fallback=self._run_request),
                run_state=_snapshot_run_state(updated.status, run_active=self._run_active),
                phase="pause_requested",
                command_note=_build_command_note(order_status=updated.status, run_active=self._run_active),
            )
        )
        self._set_feedback(f"Pause requested for production order {updated.order_code}.")

    def request_stop(self) -> None:
        order = self._require_order_context()
        updated = self._production_order_service.request_stop(order.production_order_id)
        self._selected_order = updated
        self.selected_order_changed.emit()
        self.update_progress_snapshot(
            _build_order_progress_snapshot(
                updated,
                request=_request_from_order(updated, fallback=self._run_request),
                run_state=_snapshot_run_state(updated.status, run_active=self._run_active),
                phase="stop_requested" if updated.status == "stop_requested" else "stopped",
                command_note=_build_command_note(order_status=updated.status, run_active=self._run_active),
            )
        )
        self._set_feedback(f"Stop requested for production order {updated.order_code}.")

    def get_resume_order_id(self) -> int:
        return self._require_order_context().production_order_id

    def run_batch_root(
        self,
        *,
        root_folder: str,
        batch_code: str | None = None,
        scan_depth: int = 1,
        run_mode: str = RUN_MODE_INTAKE_ONLY,
    ) -> None:
        request = self.prepare_run_request(
            root_folder=root_folder,
            batch_code=batch_code,
            scan_depth=scan_depth,
            run_mode=run_mode,
        )
        self.mark_run_started(request)
        try:
            result = self.execute_run_request(request)
        except Exception as exc:
            self.handle_run_failure(str(exc))
            raise
        self.apply_execution_result(result)

    def _refresh_recent_orders(self) -> None:
        self._recent_orders = self._production_order_service.list_orders()
        self.recent_orders_changed.emit()

    def _set_run_active(self, value: bool) -> None:
        if self._run_active == value:
            return
        self._run_active = value
        self.run_active_changed.emit()

    def _require_order_context(self) -> ProductionOrderDetailsDTO:
        if self._selected_order is not None:
            return self._selected_order
        if self._monitored_order_id is not None:
            order = self._production_order_service.get_order(self._monitored_order_id)
            self._selected_order = order
            self.selected_order_changed.emit()
            return order
        raise ValueError("Select or start a production order first.")


def _build_order_code(batch_code: str) -> str:
    return f"{batch_code}_{build_local_timestamp_token()}"


def _build_run_feedback(
    run_report: AutoFactoryFolderRunReportDTO | None,
    selected_order: ProductionOrderDetailsDTO | None,
) -> str:
    if run_report is None:
        return "Auto Factory run completed."
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


def _build_preflight_feedback(preflight_report: AutoFactoryFolderPreflightReportDTO) -> str:
    base = (
        f"Audited {len(preflight_report.discovered_product_dirs)} product folder(s): "
        f"{preflight_report.error_count} error(s), {preflight_report.warning_count} warning(s)."
    )
    if preflight_report.error_count > 0:
        return f"{base} Resolve blocking issues before running Auto Factory."
    if preflight_report.warning_count > 0:
        return f"{base} Automation can proceed, but cleanup is recommended."
    return f"{base} Product folders are ready for automation."


def _build_initial_progress_snapshot(request: AutoFactoryControlRunRequest) -> AutoFactoryControlProgressSnapshot:
    resolved_phase = "running_preflight" if request.run_mode == AutoFactoryControlViewModel.RUN_MODE_AUDIT_ONLY else "running_intake"
    return AutoFactoryControlProgressSnapshot(
        run_state="running",
        phase=resolved_phase,
        run_mode=request.run_mode,
        root_folder=request.root_folder,
        batch_code=request.batch_code,
        monitored_order_id=None,
        monitored_order_code=None,
        order_status=None,
        current_stage=resolved_phase,
        lease_owner=None,
        lease_expires_at=None,
        lease_heartbeat_at=None,
        total_products=0,
        products_with_stage_activity=0,
        total_requested_outputs=0,
        materialized_recipe_count=0,
        preview_completed_count=0,
        review_required_count=0,
        stage_count=0,
        active_worker_count=1,
        last_event=f"Started {resolved_phase.replace('_', ' ')}.",
        blocking_reason=None,
        started_at=None,
        finished_at=None,
        command_note=_build_command_note(order_status="processing", run_active=True),
    )


def _build_preflight_progress_snapshot(
    request: AutoFactoryControlRunRequest,
    preflight_report: AutoFactoryFolderPreflightReportDTO,
) -> AutoFactoryControlProgressSnapshot:
    return AutoFactoryControlProgressSnapshot(
        run_state="completed",
        phase="audit_complete",
        run_mode=request.run_mode,
        root_folder=request.root_folder,
        batch_code=request.batch_code,
        monitored_order_id=None,
        monitored_order_code=None,
        order_status=preflight_report.status,
        current_stage="audit_complete",
        lease_owner=None,
        lease_expires_at=None,
        lease_heartbeat_at=None,
        total_products=len(preflight_report.product_reports),
        products_with_stage_activity=len(preflight_report.product_reports),
        total_requested_outputs=sum(report.requested_output_count or 0 for report in preflight_report.product_reports),
        materialized_recipe_count=0,
        preview_completed_count=0,
        review_required_count=preflight_report.warning_count,
        stage_count=0,
        active_worker_count=0,
        last_event=f"Audit completed with {preflight_report.error_count} error(s) and {preflight_report.warning_count} warning(s).",
        blocking_reason=None if preflight_report.error_count == 0 else "Blocking preflight issues detected.",
        started_at=None,
        finished_at=None,
        command_note=_build_command_note(order_status=preflight_report.status, run_active=False),
    )


def _build_intake_progress_snapshot(
    request: AutoFactoryControlRunRequest,
    run_report: AutoFactoryFolderRunReportDTO,
) -> AutoFactoryControlProgressSnapshot:
    total_requested_outputs = sum(product_request.requested_output_count for product_request in run_report.order.product_requests)
    return AutoFactoryControlProgressSnapshot(
        run_state="completed",
        phase="intake_complete",
        run_mode=request.run_mode,
        root_folder=request.root_folder,
        batch_code=run_report.batch_code,
        monitored_order_id=None,
        monitored_order_code=None,
        order_status="intake_complete",
        current_stage="intake_complete",
        lease_owner=None,
        lease_expires_at=None,
        lease_heartbeat_at=None,
        total_products=len(run_report.order.product_requests),
        products_with_stage_activity=len(run_report.product_reports),
        total_requested_outputs=total_requested_outputs,
        materialized_recipe_count=0,
        preview_completed_count=0,
        review_required_count=0,
        stage_count=0,
        active_worker_count=0,
        last_event=f"Intake completed for batch {run_report.batch_code}.",
        blocking_reason=None,
        started_at=None,
        finished_at=None,
        command_note=_build_command_note(order_status="intake_complete", run_active=False),
    )


def _build_order_bootstrap_progress_snapshot(
    *,
    request: AutoFactoryControlRunRequest,
    run_report: AutoFactoryFolderRunReportDTO,
    order_id: int,
    order_code: str,
) -> AutoFactoryControlProgressSnapshot:
    total_requested_outputs = sum(product_request.requested_output_count for product_request in run_report.order.product_requests)
    return AutoFactoryControlProgressSnapshot(
        run_state="running",
        phase="running_order",
        run_mode=request.run_mode,
        root_folder=request.root_folder,
        batch_code=run_report.batch_code,
        monitored_order_id=order_id,
        monitored_order_code=order_code,
        order_status="processing",
        current_stage="order_created",
        lease_owner=None,
        lease_expires_at=None,
        lease_heartbeat_at=None,
        total_products=len(run_report.order.product_requests),
        products_with_stage_activity=0,
        total_requested_outputs=total_requested_outputs,
        materialized_recipe_count=0,
        preview_completed_count=0,
        review_required_count=0,
        stage_count=0,
        active_worker_count=1,
        last_event=f"Created production order {order_code}; monitoring stage execution.",
        blocking_reason=None,
        started_at=None,
        finished_at=None,
        command_note=_build_command_note(order_status="processing", run_active=True),
    )


def _build_order_progress_snapshot(
    order: ProductionOrderDetailsDTO,
    *,
    request: AutoFactoryControlRunRequest | None,
    run_state: str,
    phase: str,
    command_note: str,
) -> AutoFactoryControlProgressSnapshot:
    effective_stages = _effective_order_stages(order.stages)
    latest_stage = None if not effective_stages else max(effective_stages, key=lambda stage: stage.sequence_index)
    product_ids_with_stage_activity = {
        stage.production_order_item_id for stage in effective_stages if stage.production_order_item_id is not None
    }
    materialized_recipe_count = len(
        {
            stage.recipe_id
            for stage in effective_stages
            if stage.stage_name == "materialize" and stage.status == "succeeded" and stage.recipe_id is not None
        }
    )
    preview_completed_count = sum(
        1 for stage in effective_stages if stage.stage_name == "preview" and stage.status == "succeeded"
    )
    review_required_count = sum(
        1 for stage in effective_stages if stage.stage_name == "review" and stage.status == "review_required"
    )
    total_requested_outputs = sum(item.requested_output_count for item in order.items)
    blocking_reason = order.blocking_reason
    if blocking_reason is None and latest_stage is not None and latest_stage.failure_class:
        blocking_reason = latest_stage.failure_class

    latest_event = order.events[-1].message if order.events else None

    return AutoFactoryControlProgressSnapshot(
        run_state=run_state,
        phase=phase,
        run_mode=(None if request is None else request.run_mode) or order.run_mode,
        root_folder=(None if request is None else request.root_folder) or order.source_root,
        batch_code=order.batch_code,
        monitored_order_id=order.production_order_id,
        monitored_order_code=order.order_code,
        order_status=order.status,
        current_stage="queued" if latest_stage is None else latest_stage.stage_name,
        lease_owner=order.lease_owner,
        lease_expires_at=order.lease_expires_at,
        lease_heartbeat_at=order.lease_heartbeat_at,
        total_products=len(order.items),
        products_with_stage_activity=len(product_ids_with_stage_activity),
        total_requested_outputs=total_requested_outputs,
        materialized_recipe_count=materialized_recipe_count,
        preview_completed_count=preview_completed_count,
        review_required_count=review_required_count,
        stage_count=len(effective_stages),
        active_worker_count=1 if order.lease_owner and order.status in ACTIVE_ORDER_STATUSES else 0,
        last_event=(
            latest_event
            or "Order created; waiting for first recorded stage."
            if latest_stage is None
            else f"Last Stage #{latest_stage.sequence_index}: {latest_stage.stage_name} -> {latest_stage.status}"
        ),
        blocking_reason=blocking_reason,
        started_at=order.started_at,
        finished_at=order.finished_at,
        command_note=command_note,
    )


def _build_command_note(*, order_status: str | None, run_active: bool) -> str:
    if order_status in {"processing", "leased", "resume_requested"}:
        return (
            "Live monitoring is active. Pause and Stop are persisted requests that apply at the next recipe-boundary "
            "safe checkpoint. Resume is used after pause, stop, or stale-lease recovery."
        )
    if order_status == "pause_requested":
        return "Pause has been requested. The worker will drain the current recipe-boundary unit and then mark the run paused."
    if order_status == "paused":
        return "This run is paused. Resume continues remaining eligible work without redoing succeeded stages."
    if order_status in {"stop_requested", "stopped"}:
        return "This run is stopping or stopped. Resume continues remaining eligible work; completed work is preserved."
    if order_status in RESUMABLE_ORDER_STATUSES:
        return "This run can be resumed from persisted order, stage, and lease truth."
    if run_active:
        return "Live monitoring is active. Refresh Progress reads persisted order truth."
    return "You can inspect persisted order truth here and refresh the latest run snapshot."


def _snapshot_run_state(order_status: str, *, run_active: bool) -> str:
    if run_active:
        return "running"
    if order_status in {"succeeded", "failed_retryable", "failed_terminal", "review_required", "cancelled"}:
        return "completed"
    if order_status in ACTIVE_ORDER_STATUSES:
        return "ready"
    return order_status


def _request_from_order(
    order: ProductionOrderDetailsDTO,
    *,
    fallback: AutoFactoryControlRunRequest | None,
) -> AutoFactoryControlRunRequest:
    if order.source_root and order.run_mode:
        return AutoFactoryControlRunRequest(
            root_folder=order.source_root,
            batch_code=order.batch_code,
            scan_depth=0 if fallback is None else fallback.scan_depth,
            run_mode=order.run_mode,
        )
    if fallback is not None:
        return fallback
    return AutoFactoryControlRunRequest(
        root_folder="",
        batch_code=order.batch_code,
        scan_depth=0,
        run_mode=AutoFactoryControlViewModel.RUN_MODE_MATERIALIZE_AND_PREVIEWS
        if order.preview_generation_enabled
        else AutoFactoryControlViewModel.RUN_MODE_MATERIALIZE,
    )


def _effective_order_stages(stages: tuple[ProductionOrderStageDTO, ...]) -> tuple[ProductionOrderStageDTO, ...]:
    latest_by_key: dict[tuple[object, ...], ProductionOrderStageDTO] = {}
    for stage in stages:
        latest_by_key[_effective_stage_key(stage)] = stage
    return tuple(sorted(latest_by_key.values(), key=lambda item: (item.sequence_index, item.production_order_stage_id)))


def _effective_stage_key(stage: ProductionOrderStageDTO) -> tuple[object, ...]:
    recipe_code = _stage_detail_value(stage.detail_json, "recipe_code")
    if stage.stage_name == "materialize":
        return (stage.stage_name, stage.production_order_item_id, stage.recipe_id or recipe_code)
    if stage.stage_name in {"preview", "review"}:
        return (stage.stage_name, stage.recipe_id or stage.production_order_item_id)
    return (
        stage.stage_name,
        stage.stage_scope,
        stage.production_order_item_id,
        stage.recipe_id,
        stage.output_id,
        recipe_code,
    )


def _stage_detail_value(detail_json: str | None, key: str) -> object | None:
    if not detail_json:
        return None
    try:
        payload = json.loads(detail_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload.get(key)
