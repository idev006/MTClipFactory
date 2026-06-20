from __future__ import annotations

from mt_clip_factory.factory.auto_factory_dto import AutoFactoryBatchOrderDTO, AutoFactoryProductRequestDTO
from mt_clip_factory.factory.auto_factory_folder_dto import (
    AutoFactoryFolderAssetActionDTO,
    AutoFactoryFolderAssetFolderAuditDTO,
    AutoFactoryFolderContractAuditDTO,
    AutoFactoryFolderPreflightIssueDTO,
    AutoFactoryFolderPreflightProductReportDTO,
    AutoFactoryFolderPreflightReportDTO,
    AutoFactoryFolderProductReportDTO,
    AutoFactoryFolderRunReportDTO,
)
from mt_clip_factory.factory.production_order_dto import (
    ProductionOrderDetailsDTO,
    ProductionOrderItemDTO,
    ProductionOrderStageDTO,
    ProductionOrderSummaryDTO,
)
from mt_clip_factory.presentation.factory.auto_factory_control import (
    AutoFactoryControlProgressSnapshot,
    AutoFactoryControlViewModel,
)


class FakeAutoFactoryFolderService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None, int, bool]] = []
        self.audit_calls: list[tuple[str, int]] = []

    def run_batch_root(
        self,
        batch_root,
        *,
        batch_code: str | None = None,
        scan_depth: int = 1,
        materialize: bool = True,
        build_previews: bool = False,
    ) -> AutoFactoryFolderRunReportDTO:
        self.calls.append((str(batch_root), batch_code, scan_depth, materialize))
        return AutoFactoryFolderRunReportDTO(
            batch_code=batch_code or "uat_batch",
            scan_depth=scan_depth,
            order=AutoFactoryBatchOrderDTO(
                batch_code=batch_code or "uat_batch",
                product_requests=(
                    AutoFactoryProductRequestDTO(
                        product_code="tea",
                        requested_output_count=2,
                        target_platform="tiktok",
                        target_ratio="9:16",
                    ),
                ),
            ),
            discovered_product_dirs=(str(batch_root),),
            product_reports=(
                AutoFactoryFolderProductReportDTO(
                    product_id=1,
                    product_code="tea",
                    created_product=False,
                    registered_asset_count=3,
                    skipped_existing_asset_count=1,
                    product_dir=str(batch_root),
                ),
            ),
            asset_actions=(
                AutoFactoryFolderAssetActionDTO(
                    product_code="tea",
                    asset_type="foreground_video",
                    asset_code="tea_fg_hook",
                    source_file=f"{batch_root}\\foreground\\hook.mp4",
                    action="registered",
                ),
            ),
        )

    def audit_batch_root(
        self,
        batch_root,
        *,
        scan_depth: int = 1,
    ) -> AutoFactoryFolderPreflightReportDTO:
        self.audit_calls.append((str(batch_root), scan_depth))
        return AutoFactoryFolderPreflightReportDTO(
            root_folder=str(batch_root),
            scan_depth=scan_depth,
            discovered_product_dirs=(str(batch_root),),
            status="warning",
            error_count=0,
            warning_count=1,
            product_reports=(
                AutoFactoryFolderPreflightProductReportDTO(
                    product_dir=str(batch_root),
                    layout_mode="v2",
                    status="warning",
                    product_code="tea",
                    product_name="Tea Product",
                    requested_output_count=2,
                    ready_for_automation=True,
                    contracts=(
                        AutoFactoryFolderContractAuditDTO(
                            contract_name="product.toml",
                            resolved_path=f"{batch_root}\\contracts\\product.toml",
                            layout_mode="v2",
                            required=True,
                            present=True,
                        ),
                    ),
                    asset_folders=(
                        AutoFactoryFolderAssetFolderAuditDTO(
                            folder_name="music",
                            asset_type="background_music",
                            resolved_path=f"{batch_root}\\assets\\music",
                            layout_mode="v2",
                            ingestible_file_count=0,
                            ingestible_files=(),
                            tag_file_present=True,
                            global_tag_count=1,
                            file_tag_entry_count=0,
                            tagged_file_count=0,
                            issues=(
                                AutoFactoryFolderPreflightIssueDTO(
                                    severity="warning",
                                    code="empty_asset_folder",
                                    message="music folder is empty",
                                    location=f"{batch_root}\\assets\\music",
                                ),
                            ),
                        ),
                    ),
                    issues=(
                        AutoFactoryFolderPreflightIssueDTO(
                            severity="warning",
                            code="empty_asset_folder",
                            message="music folder is empty",
                            location=f"{batch_root}\\assets\\music",
                        ),
                    ),
                    ingestible_asset_count=3,
                ),
            ),
        )


class FakeProductionOrderService:
    def __init__(self) -> None:
        self.create_calls: list[tuple[str, str | None, bool]] = []
        self.create_order_calls: list[tuple[str, str | None]] = []
        self.run_order_calls: list[tuple[int, bool]] = []
        self.get_calls: list[int] = []
        self._details = ProductionOrderDetailsDTO(
            production_order_id=41,
            order_code="uat_batch_20260613_120000_000001",
            batch_code="uat_batch",
            source_mode="folder_control_surface",
            requested_by=None,
            strict_fulfillment=True,
            status="succeeded",
            created_at="2026-06-13 12:00:00",
            started_at="2026-06-13 12:00:01",
            finished_at="2026-06-13 12:00:05",
            items=(
                ProductionOrderItemDTO(
                    production_order_item_id=5,
                    product_id=1,
                    product_code="tea",
                    requested_output_count=2,
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
                    detail_json='{"recipe_code":"tea_r0001"}',
                    created_at="2026-06-13 12:00:02",
                    updated_at="2026-06-13 12:00:02",
                ),
            ),
        )
        self._summaries = [
            ProductionOrderSummaryDTO(
                production_order_id=41,
                order_code=self._details.order_code,
                batch_code=self._details.batch_code,
                source_mode=self._details.source_mode,
                requested_by=None,
                status=self._details.status,
                item_count=1,
                created_at=self._details.created_at,
                started_at=self._details.started_at,
                finished_at=self._details.finished_at,
            )
        ]

    def list_orders(self, *, status: str | None = None) -> list[ProductionOrderSummaryDTO]:
        return list(self._summaries)

    def create_and_run_order(
        self,
        order: AutoFactoryBatchOrderDTO,
        *,
        source_mode: str,
        order_code: str | None = None,
        requested_by: str | None = None,
        build_previews: bool = True,
    ) -> ProductionOrderDetailsDTO:
        self.create_calls.append((order.batch_code, order_code, build_previews))
        return self._details

    def create_order(
        self,
        order: AutoFactoryBatchOrderDTO,
        *,
        source_mode: str,
        order_code: str | None = None,
        requested_by: str | None = None,
    ) -> int:
        self.create_order_calls.append((order.batch_code, order_code))
        return self._details.production_order_id

    def run_order(self, production_order_id: int, *, build_previews: bool = True) -> ProductionOrderDetailsDTO:
        self.run_order_calls.append((production_order_id, build_previews))
        return self._details

    def get_order(self, production_order_id: int) -> ProductionOrderDetailsDTO:
        self.get_calls.append(production_order_id)
        return self._details


def test_auto_factory_control_view_model_runs_intake_only_without_order_creation() -> None:
    folder_service = FakeAutoFactoryFolderService()
    order_service = FakeProductionOrderService()
    view_model = AutoFactoryControlViewModel(folder_service, order_service)

    view_model.run_batch_root(root_folder="F:\\batch_root", scan_depth=2)

    assert view_model.status == "ready"
    assert view_model.run_report is not None
    assert view_model.run_report.scan_depth == 2
    assert view_model.selected_order is None
    assert folder_service.calls == [("F:\\batch_root", None, 2, False)]
    assert order_service.create_calls == []
    assert "Intake completed without creating a production order." in view_model.feedback


def test_auto_factory_control_view_model_runs_audit_only_without_order_creation() -> None:
    folder_service = FakeAutoFactoryFolderService()
    order_service = FakeProductionOrderService()
    view_model = AutoFactoryControlViewModel(folder_service, order_service)

    view_model.run_batch_root(
        root_folder="F:\\batch_root",
        scan_depth=0,
        run_mode=AutoFactoryControlViewModel.RUN_MODE_AUDIT_ONLY,
    )

    assert view_model.status == "ready"
    assert view_model.preflight_report is not None
    assert view_model.preflight_report.status == "warning"
    assert view_model.run_report is None
    assert view_model.selected_order is None
    assert folder_service.audit_calls == [("F:\\batch_root", 0)]
    assert folder_service.calls == []
    assert order_service.create_calls == []
    assert "Audited 1 product folder(s): 0 error(s), 1 warning(s)." in view_model.feedback


def test_auto_factory_control_view_model_runs_materialization_with_preview_mode() -> None:
    folder_service = FakeAutoFactoryFolderService()
    order_service = FakeProductionOrderService()
    view_model = AutoFactoryControlViewModel(folder_service, order_service)

    view_model.run_batch_root(
        root_folder="F:\\batch_root",
        batch_code="campaign_launch",
        scan_depth=1,
        run_mode=AutoFactoryControlViewModel.RUN_MODE_MATERIALIZE_AND_PREVIEWS,
    )

    assert view_model.status == "ready"
    assert view_model.selected_order is not None
    assert view_model.selected_order.production_order_id == 41
    assert len(view_model.recent_orders) == 1
    assert folder_service.calls == [("F:\\batch_root", "campaign_launch", 1, False)]
    assert order_service.create_order_calls[0][0] == "campaign_launch"
    assert order_service.run_order_calls == [(41, True)]
    assert "Production order" in view_model.feedback
    assert "succeeded" in view_model.feedback


def test_auto_factory_control_view_model_can_load_recent_orders_and_select_one() -> None:
    order_service = FakeProductionOrderService()
    view_model = AutoFactoryControlViewModel(FakeAutoFactoryFolderService(), order_service)

    view_model.load()
    view_model.select_order(41)

    assert view_model.status == "ready"
    assert len(view_model.recent_orders) == 1
    assert view_model.selected_order is not None
    assert view_model.selected_order.order_code == "uat_batch_20260613_120000_000001"
    assert order_service.get_calls == [41]


def test_auto_factory_control_view_model_tracks_progress_snapshot_for_completed_order() -> None:
    folder_service = FakeAutoFactoryFolderService()
    order_service = FakeProductionOrderService()
    view_model = AutoFactoryControlViewModel(folder_service, order_service)

    view_model.run_batch_root(
        root_folder="F:\\batch_root",
        batch_code="campaign_launch",
        scan_depth=1,
        run_mode=AutoFactoryControlViewModel.RUN_MODE_MATERIALIZE_AND_PREVIEWS,
    )

    snapshot = view_model.progress_snapshot
    assert isinstance(snapshot, AutoFactoryControlProgressSnapshot)
    assert snapshot.run_state == "ready" or snapshot.run_state == "completed"
    assert snapshot.monitored_order_id == 41
    assert snapshot.monitored_order_code == "uat_batch_20260613_120000_000001"
    assert snapshot.total_products == 1
    assert snapshot.total_requested_outputs == 2
    assert snapshot.materialized_recipe_count == 1
    assert snapshot.stage_count == 1
    assert snapshot.active_worker_count == 0


def test_auto_factory_control_view_model_refreshes_monitored_order_progress() -> None:
    order_service = FakeProductionOrderService()
    view_model = AutoFactoryControlViewModel(FakeAutoFactoryFolderService(), order_service)

    view_model.select_order(41)
    view_model.refresh_progress()

    assert view_model.progress_snapshot.monitored_order_id == 41
    assert view_model.progress_snapshot.order_status == "succeeded"
    assert order_service.get_calls == [41, 41]
