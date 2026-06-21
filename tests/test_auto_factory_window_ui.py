from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from mt_clip_factory.factory.auto_factory_dto import AutoFactoryBatchOrderDTO, AutoFactoryProductRequestDTO
from mt_clip_factory.factory.auto_factory_folder_dto import (
    AutoFactoryFolderAssetActionDTO,
    AutoFactoryFolderAssetFolderAuditDTO,
    AutoFactoryFolderCaptionContractAuditDTO,
    AutoFactoryFolderContractAuditDTO,
    AutoFactoryFolderPipelineConfigDTO,
    AutoFactoryFolderPreflightReportDTO,
    AutoFactoryFolderPreflightProductReportDTO,
    AutoFactoryFolderProductConfigDTO,
    AutoFactoryFolderProductReportDTO,
    AutoFactoryFolderRunReportDTO,
)
from mt_clip_factory.factory.production_order_dto import (
    ProductionOrderDetailsDTO,
    ProductionOrderEventDTO,
    ProductionOrderItemDTO,
    ProductionOrderStageDTO,
)
from mt_clip_factory.presentation.factory.auto_factory_control import (
    AutoFactoryControlProgressSnapshot,
    AutoFactoryControlRunRequest,
)
from mt_clip_factory.ui.factory.auto_factory_control_window import AutoFactoryControlWindow


@pytest.fixture()
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class FakeAutoFactoryControlViewModel(QObject):
    recent_orders_changed = Signal()
    run_report_changed = Signal()
    preflight_report_changed = Signal()
    selected_order_changed = Signal()
    feedback_changed = Signal()
    status_changed = Signal()
    progress_changed = Signal()
    run_active_changed = Signal()

    RUN_MODE_AUDIT_ONLY = "audit_only"
    RUN_MODE_INTAKE_ONLY = "intake_only"
    RUN_MODE_MATERIALIZE = "materialize"
    RUN_MODE_MATERIALIZE_AND_PREVIEWS = "materialize_and_build_previews"

    def __init__(self, *, run_report=None, preflight_report=None, selected_order=None) -> None:  # noqa: ANN001
        super().__init__()
        self.recent_orders = []
        self.run_report = run_report
        self.preflight_report = preflight_report
        self.selected_order = selected_order
        self.feedback = ""
        self.status = "ready"
        self.progress_snapshot = AutoFactoryControlProgressSnapshot.idle()
        self.run_active = False
        self.monitored_order_id = None

    def load(self) -> None:
        self.recent_orders_changed.emit()
        self.run_report_changed.emit()
        self.preflight_report_changed.emit()
        self.selected_order_changed.emit()
        self.feedback_changed.emit()
        self.status_changed.emit()
        self.progress_changed.emit()
        self.run_active_changed.emit()

    def prepare_run_request(self, *, root_folder: str, batch_code=None, scan_depth=1, run_mode=RUN_MODE_INTAKE_ONLY):  # noqa: ANN001
        return AutoFactoryControlRunRequest(
            root_folder=root_folder,
            batch_code=batch_code,
            scan_depth=scan_depth,
            run_mode=run_mode,
        )

    def mark_run_started(self, request: AutoFactoryControlRunRequest) -> None:
        self.run_active = True
        self.progress_snapshot = AutoFactoryControlProgressSnapshot(
            run_state="running",
            phase="running_intake",
            run_mode=request.run_mode,
            root_folder=request.root_folder,
            batch_code=request.batch_code,
            monitored_order_id=None,
            monitored_order_code=None,
            order_status=None,
            current_stage="running_intake",
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
            last_event="started",
            blocking_reason=None,
            started_at=None,
            finished_at=None,
            command_note="monitoring",
        )
        self.progress_changed.emit()
        self.run_active_changed.emit()

    def update_progress_snapshot(self, snapshot) -> None:  # noqa: ANN001
        self.progress_snapshot = snapshot
        self.monitored_order_id = snapshot.monitored_order_id
        self.progress_changed.emit()

    def apply_execution_result(self, result) -> None:  # noqa: ANN001
        del result
        self.run_active = False
        self.run_active_changed.emit()

    def handle_run_failure(self, error_message: str) -> None:
        self.feedback = error_message
        self.feedback_changed.emit()
        self.run_active = False
        self.run_active_changed.emit()

    def execute_run_request(self, request, *, progress_callback=None):  # noqa: ANN001
        if progress_callback is not None:
            progress_callback(self.progress_snapshot)
        return object()

    def refresh_progress(self) -> None:
        self.progress_changed.emit()

    def select_order(self, production_order_id: int | None) -> None:
        self.monitored_order_id = production_order_id
        self.selected_order_changed.emit()

    def request_pause(self) -> None:
        self.feedback = "pause pending"
        self.feedback_changed.emit()

    def request_stop(self) -> None:
        self.feedback = "stop pending"
        self.feedback_changed.emit()

    def get_resume_order_id(self) -> int:
        return 1

    def mark_resume_started(self, production_order_id: int) -> None:
        self.monitored_order_id = production_order_id
        self.run_active = True
        self.run_active_changed.emit()

    def execute_resume_order(self, production_order_id: int):  # noqa: ANN001
        del production_order_id
        return object()


def test_auto_factory_window_can_open_selected_preflight_product_paths_and_copy_summary(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    product_dir = tmp_path / "TeaProduct"
    contracts_dir = product_dir / "contracts"
    runs_dir = product_dir / "runs"
    contracts_dir.mkdir(parents=True)
    runs_dir.mkdir(parents=True)

    view_model = FakeAutoFactoryControlViewModel(
        preflight_report=AutoFactoryFolderPreflightReportDTO(
            root_folder=str(tmp_path),
            scan_depth=1,
            discovered_product_dirs=(str(product_dir),),
            status="ready",
            error_count=0,
            warning_count=0,
            product_reports=(
                AutoFactoryFolderPreflightProductReportDTO(
                    product_dir=str(product_dir),
                    layout_mode="v2",
                    status="ready",
                    product_code="tea",
                    product_name="Tea Product",
                    requested_output_count=2,
                    ready_for_automation=True,
                    contracts=(
                        AutoFactoryFolderContractAuditDTO(
                            contract_name="product.toml",
                            resolved_path=str(contracts_dir / "product.toml"),
                            layout_mode="v2",
                            required=True,
                            present=True,
                        ),
                    ),
                    asset_folders=(
                        AutoFactoryFolderAssetFolderAuditDTO(
                            folder_name="foreground",
                            asset_type="foreground_video",
                            resolved_path=str(product_dir / "assets" / "foreground"),
                            layout_mode="v2",
                            ingestible_file_count=1,
                            ingestible_files=("hook.mp4",),
                            tag_file_present=True,
                            global_tag_count=1,
                            file_tag_entry_count=1,
                            tagged_file_count=1,
                            matching_required_file_count=1,
                        ),
                    ),
                    issues=(),
                    ingestible_asset_count=1,
                    product_config=AutoFactoryFolderProductConfigDTO(
                        product_code="tea",
                        product_name="Tea Product",
                        default_platform="tiktok",
                    ),
                    pipeline_config=AutoFactoryFolderPipelineConfigDTO(
                        requested_output_count=2,
                        target_platform="tiktok",
                        target_ratio="9:16",
                        foreground_required_tag_labels=("message:hook",),
                    ),
                    caption_contract=AutoFactoryFolderCaptionContractAuditDTO(
                        selection_mode="random_with_seed",
                        seed_scope="batch",
                        segment_pool_names=("hook",),
                        main_pool_entry_count=1,
                        sub_pool_entry_count=1,
                        main_style_preset="sale_blast",
                        sub_style_preset="dark_lower_third",
                        main_font_family="TH Baijam",
                        sub_font_family="TH Chakra Petch",
                    ),
                ),
            ),
        )
    )
    auto_factory_window = AutoFactoryControlWindow(view_model)

    opened_paths: list[str] = []
    monkeypatch.setattr(
        "mt_clip_factory.ui.factory.auto_factory_control_actions.QDesktopServices.openUrl",
        lambda url: opened_paths.append(url.toLocalFile()) or True,
    )

    assert auto_factory_window.open_product_folder_button.isEnabled() is True
    assert auto_factory_window.open_runs_button.isEnabled() is True
    auto_factory_window.open_product_folder_button.click()
    auto_factory_window.open_contracts_button.click()
    auto_factory_window.open_runs_button.click()
    auto_factory_window.copy_summary_button.click()

    assert [Path(path) for path in opened_paths] == [product_dir, contracts_dir, runs_dir]
    assert "Product Folder:" in qapp.clipboard().text()
    assert "copied to clipboard" in auto_factory_window.feedback_label.text().lower()
    auto_factory_window.close()


def test_auto_factory_window_shows_persisted_duplicate_risk_in_orders_tab(qapp: QApplication) -> None:
    selected_order = ProductionOrderDetailsDTO(
        production_order_id=8,
        order_code="tea_order_008",
        batch_code="tea_batch",
        source_mode="folder_control_surface",
        requested_by=None,
        strict_fulfillment=True,
        preview_generation_enabled=True,
        run_mode="materialize_and_build_previews",
        source_root="F:\\batch_root",
        status="succeeded",
        lease_owner=None,
        lease_acquired_at=None,
        lease_heartbeat_at=None,
        lease_expires_at=None,
        blocking_reason=None,
        created_at="2026-06-21 11:00:00",
        started_at="2026-06-21 11:00:01",
        finished_at="2026-06-21 11:00:05",
        items=(
            ProductionOrderItemDTO(
                production_order_item_id=5,
                product_id=1,
                product_code="tea",
                requested_output_count=1,
                target_platform="tiktok",
                target_ratio="9:16",
                uniqueness_scope="batch",
                duration_mode="voice_with_bounds",
                fixed_duration_sec=None,
                min_duration_sec=12.0,
                max_duration_sec=30.0,
            ),
        ),
        stages=(
            ProductionOrderStageDTO(
                production_order_stage_id=11,
                stage_name="materialize",
                stage_scope="recipe",
                status="succeeded",
                sequence_index=1,
                production_order_item_id=5,
                job_id=None,
                recipe_id=101,
                output_id=None,
                failure_class=None,
                detail_json='{"recipe_code":"tea_batch_001","near_duplicate_score":0.275,"near_duplicate_reasons":["voice_asset_overused"]}',
                created_at="2026-06-21 11:00:02",
                updated_at="2026-06-21 11:00:02",
            ),
        ),
        events=(
            ProductionOrderEventDTO(
                production_order_event_id=21,
                sequence_index=1,
                event_type="run_completed",
                status="succeeded",
                message="Completed production order tea_order_008 with status succeeded.",
                production_order_item_id=None,
                stage_name=None,
                worker_id=None,
                detail_json=None,
                created_at="2026-06-21 11:00:05",
            ),
        ),
    )
    auto_factory_window = AutoFactoryControlWindow(
        FakeAutoFactoryControlViewModel(selected_order=selected_order)
    )

    auto_factory_window._refresh_selected_order()

    assert "Duplicate-Risk Summary:" in auto_factory_window.order_summary_text.toPlainText()
    assert "0.275" in auto_factory_window.order_summary_text.toPlainText()
    assert auto_factory_window.order_product_progress_table.item(0, 4).text() == "0.275"
    assert auto_factory_window.order_stages_table.item(0, 8).text() == "0.275"
    assert auto_factory_window.order_stages_table.item(0, 9).text() == "voice_asset_overused"
    auto_factory_window.close()


def test_auto_factory_window_opens_batch_specific_runs_folder_for_intake_rows(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    product_dir = tmp_path / "TeaProduct"
    batch_runs_dir = product_dir / "runs" / "launch_batch"
    batch_runs_dir.mkdir(parents=True)

    view_model = FakeAutoFactoryControlViewModel(
        run_report=AutoFactoryFolderRunReportDTO(
            batch_code="launch_batch",
            scan_depth=1,
            order=AutoFactoryBatchOrderDTO(
                batch_code="launch_batch",
                product_requests=(
                    AutoFactoryProductRequestDTO(
                        product_code="tea",
                        requested_output_count=2,
                        target_platform="tiktok",
                        target_ratio="9:16",
                    ),
                ),
            ),
            discovered_product_dirs=(str(product_dir),),
            product_reports=(
                AutoFactoryFolderProductReportDTO(
                    product_id=1,
                    product_code="tea",
                    created_product=False,
                    registered_asset_count=2,
                    skipped_existing_asset_count=1,
                    product_dir=str(product_dir),
                ),
            ),
            asset_actions=(
                AutoFactoryFolderAssetActionDTO(
                    product_code="tea",
                    asset_type="foreground_video",
                    asset_code="tea_fg_hook",
                    source_file=str(product_dir / "assets" / "foreground" / "hook.mp4"),
                    action="registered",
                ),
            ),
        )
    )
    auto_factory_window = AutoFactoryControlWindow(view_model)

    opened_paths: list[str] = []
    monkeypatch.setattr(
        "mt_clip_factory.ui.factory.auto_factory_control_actions.QDesktopServices.openUrl",
        lambda url: opened_paths.append(url.toLocalFile()) or True,
    )

    auto_factory_window.open_runs_button.click()

    assert [Path(path) for path in opened_paths] == [batch_runs_dir]
    auto_factory_window.close()
