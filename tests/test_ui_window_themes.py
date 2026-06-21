from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication, QAbstractItemView, QComboBox, QHeaderView, QScrollArea, QSplitter, QTabWidget

from mt_clip_factory.control_center.dto import SystemSettingsDTO
from mt_clip_factory.factory.auto_factory_dto import AutoFactoryBatchOrderDTO, AutoFactoryProductRequestDTO
from mt_clip_factory.factory.auto_factory_folder_dto import (
    AutoFactoryFolderAssetActionDTO,
    AutoFactoryFolderAssetFolderAuditDTO,
    AutoFactoryFolderCaptionContractAuditDTO,
    AutoFactoryFolderContractAuditDTO,
    AutoFactoryFolderPipelineConfigDTO,
    AutoFactoryFolderPreflightIssueDTO,
    AutoFactoryFolderPreflightReportDTO,
    AutoFactoryFolderPreflightProductReportDTO,
    AutoFactoryFolderProductConfigDTO,
    AutoFactoryFolderProductReportDTO,
    AutoFactoryFolderRunReportDTO,
)
from mt_clip_factory.factory.dto import CompositionPlanDTO, DecisionEventDTO, OutputSummaryDTO, RecipeItemDTO, TimelineSegmentDTO
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
from mt_clip_factory.ui.control_center.dashboard_window import DashboardWindow
from mt_clip_factory.ui.factory.auto_factory_control_window import AutoFactoryControlWindow
from mt_clip_factory.ui.factory.recipe_builder_window import RecipeBuilderWindow
from mt_clip_factory.ui.library.asset_library_window import AssetLibraryWindow
from mt_clip_factory.ui.library.product_library_window import ProductLibraryWindow
from mt_clip_factory.ui.library.tag_dictionary_window import TagDictionaryWindow


@pytest.fixture()
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class FakeDashboardViewModel(QObject):
    summary_changed = Signal()
    status_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.status = "ready"
        self.summary = None

    def load(self) -> None:
        self.status_changed.emit()

    def recover_queued_jobs(self) -> None:
        self.status = "recovering"
        self.status_changed.emit()

    def retry_failed_jobs(self) -> None:
        self.status = "retrying"
        self.status_changed.emit()


class FakeProductLibraryViewModel(QObject):
    products_changed = Signal()
    feedback_changed = Signal()
    status_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.products = []
        self.feedback = ""
        self.status = "ready"

    def load(self) -> None:
        self.products_changed.emit()
        self.feedback_changed.emit()
        self.status_changed.emit()


class FakeAssetLibraryViewModel(QObject):
    products_changed = Signal()
    assets_changed = Signal()
    feedback_changed = Signal()
    status_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.products = []
        self.assets = []
        self.feedback = ""
        self.status = "ready"

    def load(self) -> None:
        self.products_changed.emit()
        self.assets_changed.emit()
        self.feedback_changed.emit()
        self.status_changed.emit()

    def apply_filters(self, *, product_id, asset_type, status) -> None:  # noqa: ANN001
        self.load()


class FakeTagDictionaryViewModel(QObject):
    tags_changed = Signal()
    assets_changed = Signal()
    selected_asset_changed = Signal()
    feedback_changed = Signal()
    status_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.tags = []
        self.assets = []
        self.selected_asset = None
        self.selected_assets = []
        self.selected_asset_count = 0
        self.feedback = ""
        self.status = "ready"
        self.tag_group_suggestions = []
        self.tag_filter_group_options = []
        self.asset_filter_product_options = []
        self.asset_filter_type_options = []

    def load(self) -> None:
        self.tags_changed.emit()
        self.assets_changed.emit()
        self.selected_asset_changed.emit()
        self.feedback_changed.emit()
        self.status_changed.emit()

    def apply_asset_filters(self, *, product_code=None, status=None, asset_type=None, search_text=None) -> None:  # noqa: ANN001
        self.assets_changed.emit()
        self.selected_asset_changed.emit()
        self.feedback_changed.emit()

    def apply_tag_filters(self, *, tag_group=None, search_text=None) -> None:  # noqa: ANN001
        self.tags_changed.emit()
        self.feedback_changed.emit()

    def select_asset(self, asset_id: int | None) -> None:
        self.selected_asset_changed.emit()

    def select_assets(self, asset_ids: list[int]) -> None:
        self.selected_asset_changed.emit()

    def assign_tag_to_selected_asset(self, *, tag_id: int) -> None:
        self.feedback = f"assigned {tag_id}"
        self.feedback_changed.emit()

    def assign_tag_to_selected_assets(self, *, tag_id: int) -> None:
        self.feedback = f"assigned {tag_id}"
        self.feedback_changed.emit()

    def create_tag_and_assign_to_selected_asset(self, *, tag_name: str, tag_group: str, description: str | None = None) -> int:
        self.feedback = f"created and attached {tag_group}:{tag_name}"
        self.feedback_changed.emit()
        return 1

    def create_tag_and_assign_to_selected_assets(self, *, tag_name: str, tag_group: str, description: str | None = None) -> int:
        self.feedback = f"created and attached {tag_group}:{tag_name}"
        self.feedback_changed.emit()
        return 1


class FakeRecipeBuilderViewModel(QObject):
    products_changed = Signal()
    assets_changed = Signal()
    recipes_changed = Signal()
    recipe_items_changed = Signal()
    outputs_changed = Signal()
    decision_events_changed = Signal()
    feedback_changed = Signal()
    status_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.products = []
        self.assets = []
        self.recipes = []
        self.recipe_items = []
        self.outputs = []
        self.decision_events = []
        self.composition_plan = None
        self.feedback = ""
        self.status = "ready"

    def load(self) -> None:
        self.products_changed.emit()
        self.assets_changed.emit()
        self.recipes_changed.emit()
        self.recipe_items_changed.emit()
        self.outputs_changed.emit()
        self.decision_events_changed.emit()
        self.feedback_changed.emit()
        self.status_changed.emit()

    def select_recipe(self, recipe_id: int | None) -> None:
        return

    def find_output(self, output_id: int) -> OutputSummaryDTO | None:
        for output in self.outputs:
            if output.output_id == output_id:
                return output
        return None


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


def test_primary_windows_apply_app_theme(qapp: QApplication) -> None:
    dashboard_window = DashboardWindow(
        FakeDashboardViewModel(),
        open_products=lambda: None,
        open_assets=lambda: None,
        open_recipes=lambda: None,
        open_auto_factory=lambda: None,
        open_tags=lambda: None,
        open_settings=lambda: None,
    )
    product_window = ProductLibraryWindow(FakeProductLibraryViewModel())
    asset_window = AssetLibraryWindow(FakeAssetLibraryViewModel())
    tag_window = TagDictionaryWindow(FakeTagDictionaryViewModel())
    auto_factory_window = AutoFactoryControlWindow(FakeAutoFactoryControlViewModel())
    recipe_window = RecipeBuilderWindow(FakeRecipeBuilderViewModel())

    for window in (dashboard_window, product_window, asset_window, tag_window, auto_factory_window, recipe_window):
        assert "QMainWindow" in window.styleSheet()
        assert "QPushButton" in window.styleSheet()
        window.close()


def test_tag_dictionary_window_uses_guided_filter_controls(qapp: QApplication) -> None:
    tag_window = TagDictionaryWindow(FakeTagDictionaryViewModel())

    assert isinstance(tag_window.tag_group_input, QComboBox)
    assert tag_window.tag_group_input.isEditable() is True
    assert isinstance(tag_window.tag_filter_group_combo, QComboBox)
    assert isinstance(tag_window.asset_filter_product_combo, QComboBox)
    assert isinstance(tag_window.asset_filter_status_combo, QComboBox)
    assert isinstance(tag_window.asset_filter_type_combo, QComboBox)
    assert tag_window.asset_search_input.placeholderText().startswith("search asset code")
    assert tag_window.tag_filter_search_input.placeholderText().startswith("search group:name")
    assert "Automation can consume normalized tag labels" in tag_window.automation_hint_label.text()
    assert tag_window.apply_filters_button.text() == "Apply Filters"
    assert tag_window.clear_filters_button.text() == "Clear Filters"
    assert tag_window.create_and_attach_button.text() == "Create And Attach To Selected Assets"
    assert tag_window.assign_tag_button.text() == "Attach Selected Tag To Selected Assets"
    assert tag_window.asset_table.selectionMode() == QAbstractItemView.ExtendedSelection
    tag_window.close()


def test_auto_factory_window_exposes_guided_run_controls(qapp: QApplication) -> None:
    auto_factory_window = AutoFactoryControlWindow(FakeAutoFactoryControlViewModel())

    assert isinstance(auto_factory_window.run_mode_combo, QComboBox)
    assert isinstance(auto_factory_window.results_tabs, QTabWidget)
    assert isinstance(auto_factory_window.workspace_splitter, QSplitter)
    assert isinstance(auto_factory_window.page_splitter, QSplitter)
    assert auto_factory_window.workspace_splitter.orientation() == Qt.Horizontal
    assert auto_factory_window.page_splitter.orientation() == Qt.Vertical
    assert [auto_factory_window.results_tabs.tabText(index) for index in range(auto_factory_window.results_tabs.count())] == [
        "Overview",
        "Audit",
        "Intake",
        "Orders",
    ]
    assert auto_factory_window.run_mode_combo.itemText(0) == "Audit Only"
    assert auto_factory_window.run_mode_combo.itemText(1) == "Intake Only"
    assert auto_factory_window.run_mode_combo.itemText(3) == "Intake + Materialize + Build Previews"
    assert auto_factory_window.scan_depth_input.minimum() == 0
    assert auto_factory_window.browse_button.text() == "Browse..."
    assert auto_factory_window.run_button.text() == "Run Auto Factory"
    assert "blank auto-generates a unique code" in auto_factory_window.batch_code_input.placeholderText()
    assert auto_factory_window.refresh_orders_button.text() == "Refresh Orders"
    assert auto_factory_window.refresh_progress_button.text() == "Refresh Progress"
    assert auto_factory_window.pause_button.text() == "Pause Run"
    assert auto_factory_window.stop_button.text() == "Stop Run"
    assert auto_factory_window.resume_button.text() == "Resume Run"
    assert auto_factory_window.run_mode_hint_label.text().startswith("Run Mode Guide:")
    assert "runs/<batch_code>" in auto_factory_window.run_mode_hint_label.text()
    assert auto_factory_window.progress_text.isReadOnly() is True
    assert "No active run." in auto_factory_window.progress_text.toPlainText()
    assert auto_factory_window.preflight_products_table.columnCount() == 5
    assert auto_factory_window.preflight_issues_table.columnCount() == 5
    assert auto_factory_window.order_product_progress_table.columnCount() == 5
    assert auto_factory_window.order_stages_table.columnCount() == 10
    assert auto_factory_window.selected_product_text.isReadOnly() is True
    assert auto_factory_window.selected_product_text.minimumHeight() == auto_factory_window.SELECTED_PRODUCT_MIN_HEIGHT - 90
    assert auto_factory_window.recent_orders_table.minimumHeight() == auto_factory_window.RECENT_ORDERS_MIN_HEIGHT - 50
    assert auto_factory_window.open_product_folder_button.text() == "Open Product Folder"
    assert auto_factory_window.open_contracts_button.text() == "Open Contracts"
    assert auto_factory_window.open_runs_button.text() == "Open Runs Folder"
    assert auto_factory_window.copy_summary_button.text() == "Copy Summary"
    assert auto_factory_window.open_product_folder_button.isEnabled() is False
    assert auto_factory_window.preflight_products_table.horizontalHeader().sectionResizeMode(0) == QHeaderView.Stretch
    assert auto_factory_window.preflight_issues_table.horizontalHeader().sectionResizeMode(4) == QHeaderView.Stretch
    assert auto_factory_window.asset_actions_table.horizontalHeader().sectionResizeMode(4) == QHeaderView.Stretch
    assert auto_factory_window.refresh_progress_button.isEnabled() is False
    auto_factory_window.close()


def test_auto_factory_window_switches_tabs_by_runtime_context(qapp: QApplication) -> None:
    auto_factory_window = AutoFactoryControlWindow(FakeAutoFactoryControlViewModel())

    assert auto_factory_window.results_tabs.currentWidget() is auto_factory_window.overview_splitter

    auto_factory_window._view_model.preflight_report = AutoFactoryFolderPreflightReportDTO(
        root_folder="F:\\batch_root",
        scan_depth=1,
        discovered_product_dirs=("F:\\batch_root\\tea",),
        status="ready",
        error_count=0,
        warning_count=0,
        product_reports=(),
    )
    auto_factory_window._refresh_preflight_report()
    assert auto_factory_window.results_tabs.currentWidget() is auto_factory_window.audit_splitter

    auto_factory_window._view_model.preflight_report = None
    auto_factory_window._view_model.run_report = AutoFactoryFolderRunReportDTO(
        batch_code="launch_batch",
        scan_depth=1,
        order=AutoFactoryBatchOrderDTO(
            batch_code="launch_batch",
            product_requests=(
                AutoFactoryProductRequestDTO(
                    product_code="tea",
                    requested_output_count=1,
                    target_platform="tiktok",
                    target_ratio="9:16",
                ),
            ),
        ),
        discovered_product_dirs=("F:\\batch_root\\tea",),
        product_reports=(),
        asset_actions=(),
    )
    auto_factory_window._refresh_run_report()
    assert auto_factory_window.results_tabs.currentWidget() is auto_factory_window.intake_splitter
    auto_factory_window.close()


def test_asset_library_window_exposes_lifecycle_maintenance_controls(qapp: QApplication) -> None:
    asset_window = AssetLibraryWindow(FakeAssetLibraryViewModel())

    assert asset_window.references_button.text() == "Show References"
    assert asset_window.retire_button.text() == "Retire Selected"
    assert asset_window.purge_button.text() == "Purge Media"
    assert asset_window.replace_button.text() == "Replace In Recipes..."
    assert [asset_window.filter_status_combo.itemText(index) for index in range(asset_window.filter_status_combo.count())] == [
        "All",
        "ready",
        "needs_review",
        "analyzed",
        "retired",
        "purged",
    ]
    asset_window.close()


def test_recipe_builder_window_explains_ready_assets_and_keeps_asset_panel_usable(qapp: QApplication) -> None:
    recipe_window = RecipeBuilderWindow(FakeRecipeBuilderViewModel())

    assert isinstance(recipe_window.scroll_area, QScrollArea)
    assert recipe_window.scroll_area.widgetResizable() is True
    assert recipe_window.scroll_area.widget() is recipe_window.content_widget
    assert isinstance(recipe_window.workspace_splitter, QSplitter)
    assert recipe_window.workspace_splitter.count() == 3
    assert isinstance(recipe_window.inventory_splitter, QSplitter)
    assert isinstance(recipe_window.review_splitter, QSplitter)
    assert recipe_window.workflow_label.text().startswith("Workflow:")
    assert isinstance(recipe_window.role_input, QComboBox)
    assert recipe_window.role_input.isEditable() is True
    assert recipe_window.role_input.currentText() == ""
    assert [recipe_window.role_input.itemText(index) for index in range(recipe_window.role_input.count())] == list(
        RecipeBuilderWindow.DEFAULT_ATTACH_ROLES
    )
    assert recipe_window.role_hint_label.text().startswith("Role guidance:")
    assert recipe_window.assets_hint_label.text().startswith("Only assets that are already in status 'ready'")
    assert recipe_window.product_picker.verticalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert recipe_window.recipe_table.verticalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert recipe_window.assets_table.verticalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert recipe_window.recipe_items_table.verticalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert recipe_window.outputs_table.verticalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert recipe_window.decision_history_table.verticalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert recipe_window.assets_table.minimumHeight() == RecipeBuilderWindow.ASSETS_TABLE_MIN_HEIGHT
    assert recipe_window.recipe_items_table.minimumHeight() == RecipeBuilderWindow.RECIPE_ITEMS_TABLE_MIN_HEIGHT
    assert recipe_window.recipe_table.minimumHeight() == RecipeBuilderWindow.RECIPE_TABLE_MIN_HEIGHT
    recipe_window.close()


def test_recipe_builder_window_uses_resizable_workspace_columns(qapp: QApplication) -> None:
    recipe_window = RecipeBuilderWindow(FakeRecipeBuilderViewModel())

    assert recipe_window.workspace_splitter.orientation() == Qt.Horizontal
    assert recipe_window.inventory_splitter.orientation() == Qt.Vertical
    assert recipe_window.review_splitter.orientation() == Qt.Vertical
    assert recipe_window.workspace_splitter.widget(0) is recipe_window.scroll_area
    assert recipe_window.inventory_splitter.count() == 2
    assert recipe_window.review_splitter.count() == 2
    recipe_window.close()


def test_recipe_builder_window_filters_role_suggestions_by_selected_asset_type(qapp: QApplication) -> None:
    recipe_window = RecipeBuilderWindow(FakeRecipeBuilderViewModel())

    recipe_window._set_role_suggestions("voiceover", auto_select=True)
    assert [recipe_window.role_input.itemText(index) for index in range(recipe_window.role_input.count())] == ["voice"]
    assert recipe_window.role_input.currentText() == "voice"
    assert "voiceover assets" in recipe_window.role_hint_label.text().lower()

    recipe_window._set_role_suggestions("background_music", auto_select=True)
    assert [recipe_window.role_input.itemText(index) for index in range(recipe_window.role_input.count())] == ["music"]
    assert recipe_window.role_input.currentText() == "music"

    recipe_window._set_role_suggestions("foreground_video", auto_select=True)
    assert [recipe_window.role_input.itemText(index) for index in range(recipe_window.role_input.count())] == [
        "hook",
        "problem",
        "benefit",
        "proof",
        "cta",
        "hero",
        "broll",
    ]
    assert recipe_window.role_input.currentText() == "hook"

    recipe_window.role_input.setCurrentText("custom_visual_role")
    recipe_window._set_role_suggestions("background_video")
    assert recipe_window.role_input.currentText() == "custom_visual_role"
    assert recipe_window.role_input.itemText(recipe_window.role_input.count() - 1) == "custom_visual_role"
    recipe_window.close()


def test_recipe_builder_window_prioritizes_next_segment_role_for_visual_assets(qapp: QApplication) -> None:
    recipe_window = RecipeBuilderWindow(FakeRecipeBuilderViewModel())
    recipe_window._view_model.recipe_items = [
        RecipeItemDTO(recipe_item_id=1, asset_id=101, asset_code="hook_clip", asset_type="foreground_video", role="hook")
    ]
    recipe_window._view_model.composition_plan = CompositionPlanDTO(
        plan_id=1,
        recipe_id=1,
        duration_source="voiceover_total_duration",
        target_duration_sec=18.0,
        resolved_duration_sec=18.0,
        updated_at="2026-06-12 10:00:00",
        layers=(),
        decisions=(),
        segments=(
            TimelineSegmentDTO(1, "hook", 1, 0.0, 3.6, 3.6),
            TimelineSegmentDTO(2, "problem", 2, 3.6, 7.2, 3.6),
            TimelineSegmentDTO(3, "benefit", 3, 7.2, 13.5, 6.3),
            TimelineSegmentDTO(4, "cta", 4, 13.5, 18.0, 4.5),
        ),
    )

    recipe_window._set_role_suggestions("background_video", auto_select=True)

    assert [recipe_window.role_input.itemText(index) for index in range(4)] == [
        "problem",
        "benefit",
        "cta",
        "hook",
    ]
    assert recipe_window.role_input.currentText() == "problem"
    assert "`hook -> problem -> benefit -> cta`" in recipe_window.role_hint_label.text()
    assert "Attached roles so far: hook." in recipe_window.role_hint_label.text()
    recipe_window.close()


def test_recipe_builder_window_surfaces_replacement_aftercare_guidance(qapp: QApplication) -> None:
    recipe_window = RecipeBuilderWindow(FakeRecipeBuilderViewModel())
    recipe_window._view_model.outputs = [
        OutputSummaryDTO(
            output_id=1,
            recipe_id=1,
            recipe_code="honey_launch",
            output_code="preview_old",
            file_path="outputs/preview_old.mp4",
            platform="tiktok",
            ratio="9:16",
            approved=True,
            created_at="2026-06-13 10:00:00",
            approved_by="qa_lead",
            approved_at="2026-06-13 10:05:00",
            approval_reason="old approval",
            output_kind="preview",
            rendering_job_code="preview_job_old",
        ),
        OutputSummaryDTO(
            output_id=2,
            recipe_id=1,
            recipe_code="honey_launch",
            output_code="preview_new",
            file_path="outputs/preview_new.mp4",
            platform="tiktok",
            ratio="9:16",
            approved=False,
            created_at="2026-06-13 12:00:00",
            approved_by=None,
            approved_at=None,
            approval_reason=None,
            output_kind="preview",
            rendering_job_code="preview_job_new",
        ),
    ]
    recipe_window._view_model.decision_events = [
        DecisionEventDTO(
            event_id=1,
            recipe_id=1,
            event_type="recipe_assets_replaced",
            actor="asset_replacement_workflow",
            created_at="2026-06-13 11:00:00",
            reason="Replaced hero asset with corrected asset.",
        )
    ]

    recipe_window._refresh_outputs_table()

    assert "Approve that rebuilt output" in recipe_window.aftercare_label.text()
    assert recipe_window.outputs_table.item(0, 3).text() == "Historical only"
    assert recipe_window.outputs_table.item(1, 3).text() == "Post-replacement"
    recipe_window.outputs_table.selectRow(0)
    recipe_window._refresh_selected_output_details()
    assert "Aftercare State: Historical only" in recipe_window.output_details_text.toPlainText()
    recipe_window.close()
