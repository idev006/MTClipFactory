from __future__ import annotations

from PySide6.QtCore import QThread, QTimer, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mt_clip_factory.presentation.factory.auto_factory_control import AutoFactoryControlViewModel
from mt_clip_factory.ui.factory.auto_factory_control_actions import (
    copy_selected_product_summary,
    open_selected_contracts_folder,
    open_selected_product_folder,
    open_selected_runs_folder,
    refresh_selected_product_action_state,
    set_feedback_message,
)
from mt_clip_factory.ui.factory.auto_factory_control_support import (
    build_order_product_rows,
    build_order_summary_text,
    build_preflight_product_detail_text,
    build_progress_summary_text,
    build_run_mode_hint,
    build_run_product_detail_text,
    format_product_request_summary,
)
from mt_clip_factory.ui.factory.auto_factory_run_worker import AutoFactoryRunWorker
from mt_clip_factory.ui.theme import apply_theme


class AutoFactoryControlWindow(QMainWindow):
    THEME_NAME = "app_window"
    SELECTED_PRODUCT_PLACEHOLDER = "Select an audit or intake product row to inspect its contract/runtime details."
    CONTROLS_PANEL_MIN_WIDTH = 420
    RUN_SUMMARY_MIN_HEIGHT = 150
    SELECTED_PRODUCT_MIN_HEIGHT = 260
    DATA_TABLE_MIN_HEIGHT = 220
    ORDER_STAGES_MIN_HEIGHT = 280
    RECENT_ORDERS_MIN_HEIGHT = 220
    RUN_PROGRESS_MIN_HEIGHT = 220
    ACTION_BUTTON_MIN_HEIGHT = 38

    def __init__(self, view_model: AutoFactoryControlViewModel) -> None:
        super().__init__()
        self._view_model = view_model
        self._run_thread: QThread | None = None
        self._run_worker: AutoFactoryRunWorker | None = None
        self.setWindowTitle("MTClipFactory - Auto Factory")
        self.resize(1440, 860)
        self.setMinimumSize(1320, 820)
        apply_theme(self, self.THEME_NAME)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        controls_group = self._build_controls_group()
        controls_group.setMinimumWidth(self.CONTROLS_PANEL_MIN_WIDTH)
        self.results_tabs = self._build_results_area()
        self.workspace_splitter = QSplitter(Qt.Horizontal)
        self.workspace_splitter.addWidget(controls_group)
        self.workspace_splitter.addWidget(self.results_tabs)
        self.workspace_splitter.setChildrenCollapsible(False)
        self.workspace_splitter.setStretchFactor(0, 1)
        self.workspace_splitter.setStretchFactor(1, 3)
        self.workspace_splitter.setSizes([440, 980])

        recent_orders_group = self._build_recent_orders_group()
        recent_orders_group.setMinimumHeight(self.RECENT_ORDERS_MIN_HEIGHT)
        self.page_splitter = QSplitter(Qt.Vertical)
        self.page_splitter.addWidget(self.workspace_splitter)
        self.page_splitter.addWidget(recent_orders_group)
        self.page_splitter.setChildrenCollapsible(False)
        self.page_splitter.setStretchFactor(0, 4)
        self.page_splitter.setStretchFactor(1, 1)
        self.page_splitter.setSizes([620, 240])
        layout.addWidget(self.page_splitter)
        self.setCentralWidget(central)

        self._view_model.recent_orders_changed.connect(self._refresh_recent_orders)
        self._view_model.run_report_changed.connect(self._refresh_run_report)
        self._view_model.preflight_report_changed.connect(self._refresh_preflight_report)
        self._view_model.selected_order_changed.connect(self._refresh_selected_order)
        self._view_model.status_changed.connect(self._refresh_status)
        self._view_model.feedback_changed.connect(self._refresh_feedback)
        self._view_model.progress_changed.connect(self._refresh_progress)
        self._view_model.run_active_changed.connect(self._refresh_run_controls)
        self.monitor_timer = QTimer(self)
        self.monitor_timer.setInterval(1000)
        self.monitor_timer.timeout.connect(self._poll_progress)
        self._refresh_status()
        self._refresh_feedback()
        self._refresh_run_mode_hint()
        self._refresh_progress()
        self._refresh_run_controls()
        self._view_model.load()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._view_model.load()

    def _build_controls_group(self) -> QGroupBox:
        group = QGroupBox("Run Controls")
        layout = QVBoxLayout(group)
        form_layout = QFormLayout()

        root_row = QWidget()
        root_layout = QHBoxLayout(root_row)
        root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_folder_input = QLineEdit()
        self.root_folder_input.setPlaceholderText("select one batch root folder")
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._browse_for_root_folder)
        root_layout.addWidget(self.root_folder_input, 1)
        root_layout.addWidget(self.browse_button)

        self.batch_code_input = QLineEdit()
        self.batch_code_input.setPlaceholderText(
            "optional override; blank auto-generates a unique code from the folder name"
        )
        self.scan_depth_input = QSpinBox()
        self.scan_depth_input.setMinimum(0)
        self.scan_depth_input.setMaximum(32)
        self.scan_depth_input.setValue(1)
        self.run_mode_combo = QComboBox()
        self.run_mode_combo.addItem("Audit Only", self._view_model.RUN_MODE_AUDIT_ONLY)
        self.run_mode_combo.addItem("Intake Only", self._view_model.RUN_MODE_INTAKE_ONLY)
        self.run_mode_combo.addItem("Intake + Materialize", self._view_model.RUN_MODE_MATERIALIZE)
        self.run_mode_combo.addItem(
            "Intake + Materialize + Build Previews",
            self._view_model.RUN_MODE_MATERIALIZE_AND_PREVIEWS,
        )
        self.run_mode_combo.currentIndexChanged.connect(self._refresh_run_mode_hint)

        form_layout.addRow("Root Folder", root_row)
        form_layout.addRow("Batch Code", self.batch_code_input)
        form_layout.addRow("Scan Depth", self.scan_depth_input)
        form_layout.addRow("Run Mode", self.run_mode_combo)
        layout.addLayout(form_layout)

        self.run_mode_hint_label = QLabel()
        self.run_mode_hint_label.setWordWrap(True)
        self.run_mode_hint_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.run_mode_hint_label)

        button_row = QHBoxLayout()
        self.run_button = QPushButton("Run Auto Factory")
        self.refresh_orders_button = QPushButton("Refresh Orders")
        self.run_button.clicked.connect(self._run_batch_root)
        self.refresh_orders_button.clicked.connect(self._view_model.load)
        button_row.addWidget(self.run_button)
        button_row.addWidget(self.refresh_orders_button)
        layout.addLayout(button_row)

        progress_button_row = QHBoxLayout()
        self.refresh_progress_button = QPushButton("Refresh Progress")
        self.pause_button = QPushButton("Pause Run")
        self.stop_button = QPushButton("Stop Run")
        self.resume_button = QPushButton("Resume Run")
        self.refresh_progress_button.clicked.connect(self._refresh_progress_snapshot)
        self.pause_button.clicked.connect(self._request_pause)
        self.stop_button.clicked.connect(self._request_stop)
        self.resume_button.clicked.connect(self._request_resume)
        progress_button_row.addWidget(self.refresh_progress_button)
        progress_button_row.addWidget(self.pause_button)
        progress_button_row.addWidget(self.stop_button)
        progress_button_row.addWidget(self.resume_button)
        layout.addLayout(progress_button_row)

        self.operator_controls_label = QLabel()
        self.operator_controls_label.setWordWrap(True)
        self.operator_controls_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.operator_controls_label)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.feedback_label = QLabel()
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.status_label)
        layout.addWidget(self.feedback_label)
        layout.addStretch(1)
        return group

    def _build_results_area(self) -> QTabWidget:
        tabs = QTabWidget()

        self.overview_splitter = QSplitter(Qt.Vertical)
        self.overview_splitter.addWidget(self._build_run_progress_group())
        self.overview_splitter.addWidget(self._build_run_summary_group())
        self.overview_splitter.addWidget(self._build_selected_product_group())
        self.overview_splitter.setChildrenCollapsible(False)
        self.overview_splitter.setStretchFactor(0, 3)
        self.overview_splitter.setStretchFactor(1, 2)
        self.overview_splitter.setStretchFactor(2, 3)
        self.overview_splitter.setSizes([240, 180, 320])

        self.audit_splitter = QSplitter(Qt.Vertical)
        self.audit_splitter.addWidget(self._build_preflight_products_group())
        self.audit_splitter.addWidget(self._build_preflight_issues_group())
        self.audit_splitter.setChildrenCollapsible(False)
        self.audit_splitter.setStretchFactor(0, 3)
        self.audit_splitter.setStretchFactor(1, 2)
        self.audit_splitter.setSizes([300, 240])

        self.intake_splitter = QSplitter(Qt.Vertical)
        self.intake_splitter.addWidget(self._build_product_reports_group())
        self.intake_splitter.addWidget(self._build_asset_actions_group())
        self.intake_splitter.setChildrenCollapsible(False)
        self.intake_splitter.setStretchFactor(0, 2)
        self.intake_splitter.setStretchFactor(1, 3)
        self.intake_splitter.setSizes([220, 320])

        self.order_stage_group = self._build_order_stages_group()

        tabs.addTab(self.overview_splitter, "Overview")
        tabs.addTab(self.audit_splitter, "Audit")
        tabs.addTab(self.intake_splitter, "Intake")
        tabs.addTab(self.order_stage_group, "Orders")
        return tabs

    def _build_run_progress_group(self) -> QGroupBox:
        group = QGroupBox("Run Progress")
        group.setMinimumHeight(self.RUN_PROGRESS_MIN_HEIGHT)
        layout = QVBoxLayout(group)
        self.progress_text = QTextEdit()
        self.progress_text.setReadOnly(True)
        self.progress_text.setMinimumHeight(self.RUN_PROGRESS_MIN_HEIGHT - 40)
        layout.addWidget(self.progress_text)
        return group

    def _build_run_summary_group(self) -> QGroupBox:
        group = QGroupBox("Latest Run Summary")
        group.setMinimumHeight(self.RUN_SUMMARY_MIN_HEIGHT)
        layout = QVBoxLayout(group)
        self.run_summary_text = QTextEdit()
        self.run_summary_text.setReadOnly(True)
        self.run_summary_text.setMinimumHeight(self.RUN_SUMMARY_MIN_HEIGHT - 40)
        layout.addWidget(self.run_summary_text)
        return group

    def _build_product_reports_group(self) -> QGroupBox:
        group = QGroupBox("Intake Product Reports")
        group.setMinimumHeight(self.DATA_TABLE_MIN_HEIGHT)
        layout = QVBoxLayout(group)
        self.product_reports_table = QTableWidget(0, 5)
        self._configure_table(
            self.product_reports_table,
            ["Product ID", "Product Code", "Created", "Registered Assets", "Skipped Existing"],
            stretch_columns=(1,),
        )
        self.product_reports_table.itemSelectionChanged.connect(self._refresh_selected_run_product_details)
        layout.addWidget(self.product_reports_table)
        return group

    def _build_asset_actions_group(self) -> QGroupBox:
        group = QGroupBox("Intake Asset Actions")
        group.setMinimumHeight(self.DATA_TABLE_MIN_HEIGHT)
        layout = QVBoxLayout(group)
        self.asset_actions_table = QTableWidget(0, 5)
        self._configure_table(
            self.asset_actions_table,
            ["Product", "Type", "Asset Code", "Action", "Source File"],
            stretch_columns=(4,),
            interactive_widths={2: 180, 3: 150},
        )
        layout.addWidget(self.asset_actions_table)
        return group

    def _build_preflight_products_group(self) -> QGroupBox:
        group = QGroupBox("Audit Product Summary")
        group.setMinimumHeight(self.DATA_TABLE_MIN_HEIGHT)
        layout = QVBoxLayout(group)
        self.preflight_products_table = QTableWidget(0, 5)
        self._configure_table(
            self.preflight_products_table,
            ["Product Code", "Layout", "Status", "Requested Outputs", "Assets"],
            stretch_columns=(0,),
        )
        self.preflight_products_table.itemSelectionChanged.connect(self._refresh_selected_preflight_product_details)
        layout.addWidget(self.preflight_products_table)
        return group

    def _build_selected_product_group(self) -> QGroupBox:
        group = QGroupBox("Selected Product Contract And Runtime Summary")
        group.setMinimumHeight(self.SELECTED_PRODUCT_MIN_HEIGHT)
        layout = QVBoxLayout(group)
        action_grid = QGridLayout()
        self.open_product_folder_button = QPushButton("Open Product Folder")
        self.open_contracts_button = QPushButton("Open Contracts")
        self.open_runs_button = QPushButton("Open Runs Folder")
        self.copy_summary_button = QPushButton("Copy Summary")
        self.open_product_folder_button.clicked.connect(lambda: open_selected_product_folder(self))
        self.open_contracts_button.clicked.connect(lambda: open_selected_contracts_folder(self))
        self.open_runs_button.clicked.connect(lambda: open_selected_runs_folder(self))
        self.copy_summary_button.clicked.connect(lambda: copy_selected_product_summary(self))
        for button in (
            self.open_product_folder_button,
            self.open_contracts_button,
            self.open_runs_button,
            self.copy_summary_button,
        ):
            button.setMinimumHeight(self.ACTION_BUTTON_MIN_HEIGHT)
        action_grid.addWidget(self.open_product_folder_button, 0, 0)
        action_grid.addWidget(self.open_contracts_button, 0, 1)
        action_grid.addWidget(self.open_runs_button, 1, 0)
        action_grid.addWidget(self.copy_summary_button, 1, 1)
        action_grid.setColumnStretch(0, 1)
        action_grid.setColumnStretch(1, 1)
        layout.addLayout(action_grid)
        self.selected_product_text = QTextEdit()
        self.selected_product_text.setReadOnly(True)
        self.selected_product_text.setMinimumHeight(self.SELECTED_PRODUCT_MIN_HEIGHT - 90)
        self.selected_product_text.setPlainText(self.SELECTED_PRODUCT_PLACEHOLDER)
        layout.addWidget(self.selected_product_text)
        refresh_selected_product_action_state(self)
        return group

    def _build_preflight_issues_group(self) -> QGroupBox:
        group = QGroupBox("Audit Issues")
        group.setMinimumHeight(self.DATA_TABLE_MIN_HEIGHT)
        layout = QVBoxLayout(group)
        self.preflight_issues_table = QTableWidget(0, 5)
        self._configure_table(
            self.preflight_issues_table,
            ["Severity", "Code", "Product", "Location", "Message"],
            stretch_columns=(4,),
            interactive_widths={3: 240},
        )
        layout.addWidget(self.preflight_issues_table)
        return group

    def _build_order_stages_group(self) -> QGroupBox:
        group = QGroupBox("Selected Production Order Stages")
        group.setMinimumHeight(self.ORDER_STAGES_MIN_HEIGHT)
        layout = QVBoxLayout(group)
        self.order_summary_text = QTextEdit()
        self.order_summary_text.setReadOnly(True)
        self.order_summary_text.setMinimumHeight(110)
        self.order_product_progress_table = QTableWidget(0, 4)
        self._configure_table(
            self.order_product_progress_table,
            ["Product Code", "Requested Outputs", "Last Stage", "Status"],
            stretch_columns=(0, 2, 3),
        )
        self.order_stages_table = QTableWidget(0, 8)
        self._configure_table(
            self.order_stages_table,
            ["Seq", "Stage", "Scope", "Status", "Item", "Recipe", "Job", "Failure"],
            stretch_columns=(1, 7),
            interactive_widths={4: 90, 5: 90, 6: 90},
        )
        self.order_events_table = QTableWidget(0, 5)
        self._configure_table(
            self.order_events_table,
            ["Seq", "Event", "Status", "Stage", "Message"],
            stretch_columns=(4,),
            interactive_widths={4: 360},
        )
        layout.addWidget(self.order_summary_text)
        layout.addWidget(self.order_product_progress_table)
        layout.addWidget(self.order_stages_table)
        layout.addWidget(self.order_events_table)
        return group

    def _build_recent_orders_group(self) -> QGroupBox:
        group = QGroupBox("Recent Production Orders")
        group.setMinimumHeight(self.RECENT_ORDERS_MIN_HEIGHT)
        layout = QVBoxLayout(group)
        self.recent_orders_table = QTableWidget(0, 8)
        self._configure_table(
            self.recent_orders_table,
            ["ID", "Order Code", "Batch Code", "Status", "Items", "Source", "Started", "Finished"],
            stretch_columns=(1, 2, 5),
        )
        self.recent_orders_table.setMinimumHeight(self.RECENT_ORDERS_MIN_HEIGHT - 50)
        self.recent_orders_table.itemSelectionChanged.connect(self._select_recent_order)
        layout.addWidget(self.recent_orders_table)
        return group

    def _configure_table(
        self,
        table: QTableWidget,
        headers: list[str],
        *,
        stretch_columns: tuple[int, ...] = (),
        interactive_widths: dict[int, int] | None = None,
    ) -> None:
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setWordWrap(False)
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(72)
        for column_index in range(len(headers)):
            header.setSectionResizeMode(column_index, QHeaderView.ResizeToContents)
        for column_index, width in (interactive_widths or {}).items():
            header.setSectionResizeMode(column_index, QHeaderView.Interactive)
            table.setColumnWidth(column_index, width)
        for column_index in stretch_columns:
            header.setSectionResizeMode(column_index, QHeaderView.Stretch)

    def _refresh_status(self) -> None:
        self.status_label.setText(f"Status: {self._view_model.status}")

    def _refresh_feedback(self) -> None:
        self.feedback_label.setText(self._view_model.feedback)

    def _refresh_progress(self) -> None:
        self.progress_text.setPlainText(build_progress_summary_text(self._view_model.progress_snapshot))
        self.operator_controls_label.setText(self._view_model.progress_snapshot.command_note)

    def _refresh_run_controls(self) -> None:
        run_active = self._view_model.run_active
        has_order_context = self._view_model.monitored_order_id is not None or self._view_model.selected_order is not None
        order_status = None if self._view_model.selected_order is None else self._view_model.selected_order.status
        active_worker_count = self._view_model.progress_snapshot.active_worker_count
        self.run_button.setEnabled(not run_active)
        self.browse_button.setEnabled(not run_active)
        self.batch_code_input.setEnabled(not run_active)
        self.scan_depth_input.setEnabled(not run_active)
        self.run_mode_combo.setEnabled(not run_active)
        self.refresh_orders_button.setEnabled(not run_active)
        self.refresh_progress_button.setEnabled(has_order_context or run_active)
        self.pause_button.setEnabled(has_order_context and order_status in {"leased", "processing", "resume_requested"})
        self.stop_button.setEnabled(
            has_order_context and order_status in {"leased", "processing", "pause_requested", "paused", "resume_requested"}
        )
        self.resume_button.setEnabled(
            has_order_context
            and not run_active
            and (
                order_status in {"paused", "stopped", "failed_retryable", "review_required", "blocked"}
                or (order_status in {"processing", "pause_requested", "stop_requested"} and active_worker_count == 0)
            )
        )

    def _refresh_run_mode_hint(self) -> None:
        run_mode = str(self.run_mode_combo.currentData())
        self.run_mode_hint_label.setText(build_run_mode_hint(run_mode, run_modes=self._view_model))

    def _refresh_run_report(self) -> None:
        run_report = self._view_model.run_report
        if run_report is None:
            if self._view_model.preflight_report is None:
                self.run_summary_text.clear()
                self.selected_product_text.setPlainText(self.SELECTED_PRODUCT_PLACEHOLDER)
                refresh_selected_product_action_state(self)
                self.results_tabs.setCurrentWidget(self.overview_splitter)
            self.product_reports_table.setRowCount(0)
            self.asset_actions_table.setRowCount(0)
            return

        self.preflight_products_table.setRowCount(0)
        self.preflight_issues_table.setRowCount(0)
        self.results_tabs.setCurrentWidget(self.intake_splitter)

        request_lines = [
            format_product_request_summary(request)
            for request in run_report.order.product_requests
        ]
        self.run_summary_text.setPlainText(
            "\n".join(
                [
                    f"Batch Code: {run_report.batch_code}",
                    f"Scan Depth: {run_report.scan_depth}",
                    f"Discovered Product Folders: {len(run_report.discovered_product_dirs)}",
                    "Folders:",
                    *[f"- {path}" for path in run_report.discovered_product_dirs],
                    "",
                    "Requested Products:",
                    *request_lines,
                ]
            )
        )

        self.product_reports_table.setRowCount(len(run_report.product_reports))
        for row_index, product_report in enumerate(run_report.product_reports):
            values = [
                str(product_report.product_id),
                product_report.product_code,
                "yes" if product_report.created_product else "no",
                str(product_report.registered_asset_count),
                str(product_report.skipped_existing_asset_count),
            ]
            for column_index, value in enumerate(values):
                self.product_reports_table.setItem(row_index, column_index, QTableWidgetItem(value))
        _select_first_row(self.product_reports_table)

        self.asset_actions_table.setRowCount(len(run_report.asset_actions))
        for row_index, action in enumerate(run_report.asset_actions):
            values = [
                action.product_code,
                action.asset_type,
                action.asset_code,
                action.action,
                action.source_file,
            ]
            for column_index, value in enumerate(values):
                self.asset_actions_table.setItem(row_index, column_index, QTableWidgetItem(value))
        self._refresh_selected_run_product_details()

    def _refresh_preflight_report(self) -> None:
        preflight_report = self._view_model.preflight_report
        if preflight_report is None:
            if self._view_model.run_report is None:
                self.run_summary_text.clear()
                self.selected_product_text.setPlainText(self.SELECTED_PRODUCT_PLACEHOLDER)
                refresh_selected_product_action_state(self)
                self.results_tabs.setCurrentWidget(self.overview_splitter)
            self.preflight_products_table.setRowCount(0)
            self.preflight_issues_table.setRowCount(0)
            return

        self.product_reports_table.setRowCount(0)
        self.asset_actions_table.setRowCount(0)
        self.order_summary_text.setPlainText("No production order selected.")
        self.order_stages_table.setRowCount(0)
        self.results_tabs.setCurrentWidget(self.audit_splitter)
        self.run_summary_text.setPlainText(
            "\n".join(
                [
                    f"Audit Status: {preflight_report.status}",
                    f"Scan Depth: {preflight_report.scan_depth}",
                    f"Discovered Product Folders: {len(preflight_report.discovered_product_dirs)}",
                    f"Errors: {preflight_report.error_count}",
                    f"Warnings: {preflight_report.warning_count}",
                    "Folders:",
                    *[f"- {path}" for path in preflight_report.discovered_product_dirs],
                ]
            )
        )

        self.preflight_products_table.setRowCount(len(preflight_report.product_reports))
        issue_rows: list[tuple[str, str, str, str, str]] = []
        for row_index, product_report in enumerate(preflight_report.product_reports):
            values = [
                product_report.product_code or "<unknown>",
                product_report.layout_mode,
                product_report.status,
                "" if product_report.requested_output_count is None else str(product_report.requested_output_count),
                str(product_report.ingestible_asset_count),
            ]
            for column_index, value in enumerate(values):
                self.preflight_products_table.setItem(row_index, column_index, QTableWidgetItem(value))
            for issue in product_report.issues:
                issue_rows.append(
                    (
                        issue.severity,
                        issue.code,
                        product_report.product_code or "<unknown>",
                        issue.location or "",
                        issue.message,
                    )
                )

        self.preflight_issues_table.setRowCount(len(issue_rows))
        for row_index, values in enumerate(issue_rows):
            for column_index, value in enumerate(values):
                self.preflight_issues_table.setItem(row_index, column_index, QTableWidgetItem(value))
        _select_first_row(self.preflight_products_table)
        self._refresh_selected_preflight_product_details()

    def _refresh_selected_order(self) -> None:
        selected_order = self._view_model.selected_order
        if selected_order is None:
            self.order_summary_text.setPlainText("No production order selected.")
            self.order_product_progress_table.setRowCount(0)
            self.order_stages_table.setRowCount(0)
            self.order_events_table.setRowCount(0)
            self._refresh_run_controls()
            return

        self.results_tabs.setCurrentWidget(self.order_stage_group)
        self.order_summary_text.setPlainText(build_order_summary_text(selected_order))
        product_rows = build_order_product_rows(selected_order)
        self.order_product_progress_table.setRowCount(len(product_rows))
        for row_index, values in enumerate(product_rows):
            for column_index, value in enumerate(values):
                self.order_product_progress_table.setItem(row_index, column_index, QTableWidgetItem(value))
        self.order_stages_table.setRowCount(len(selected_order.stages))
        for row_index, stage in enumerate(selected_order.stages):
            values = [
                str(stage.sequence_index),
                stage.stage_name,
                stage.stage_scope,
                stage.status,
                str(stage.production_order_item_id or ""),
                str(stage.recipe_id or ""),
                str(stage.job_id or ""),
                stage.failure_class or "",
            ]
            for column_index, value in enumerate(values):
                self.order_stages_table.setItem(row_index, column_index, QTableWidgetItem(value))
        self.order_events_table.setRowCount(len(selected_order.events))
        for row_index, event in enumerate(selected_order.events):
            values = [
                str(event.sequence_index),
                event.event_type,
                event.status,
                event.stage_name or "",
                event.message,
            ]
            for column_index, value in enumerate(values):
                self.order_events_table.setItem(row_index, column_index, QTableWidgetItem(value))
        self._refresh_run_controls()

    def _refresh_recent_orders(self) -> None:
        orders = self._view_model.recent_orders
        current_order_id = self._view_model.selected_order.production_order_id if self._view_model.selected_order else None
        self.recent_orders_table.blockSignals(True)
        self.recent_orders_table.setRowCount(len(orders))
        for row_index, order in enumerate(orders):
            values = [
                str(order.production_order_id),
                order.order_code,
                order.batch_code,
                order.status,
                str(order.item_count),
                order.source_mode,
                order.started_at or "",
                order.finished_at or "",
            ]
            for column_index, value in enumerate(values):
                self.recent_orders_table.setItem(row_index, column_index, QTableWidgetItem(value))
            if current_order_id is not None and order.production_order_id == current_order_id:
                self.recent_orders_table.selectRow(row_index)
        self.recent_orders_table.blockSignals(False)
        self._refresh_run_controls()

    def _browse_for_root_folder(self) -> None:
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Auto Factory Root Folder")
        if selected_dir:
            self.root_folder_input.setText(selected_dir)

    def _run_batch_root(self) -> None:
        try:
            request = self._view_model.prepare_run_request(
                root_folder=self.root_folder_input.text(),
                batch_code=self.batch_code_input.text() or None,
                scan_depth=self.scan_depth_input.value(),
                run_mode=str(self.run_mode_combo.currentData()),
            )
        except Exception as exc:
            QMessageBox.warning(self, "Auto Factory", str(exc))
            return
        self._start_run_worker(request)

    def _start_run_worker(self, request) -> None:
        if self._run_thread is not None:
            QMessageBox.information(self, "Auto Factory", "A run is already in progress.")
            return
        self._view_model.mark_run_started(request)
        self.monitor_timer.start()
        self._run_thread = QThread(self)
        self._run_worker = AutoFactoryRunWorker(
            self._view_model,
            mode=AutoFactoryRunWorker.MODE_RUN_REQUEST,
            request=request,
        )
        self._run_worker.moveToThread(self._run_thread)
        self._run_thread.started.connect(self._run_worker.run)
        self._run_worker.progress_changed.connect(self._view_model.update_progress_snapshot)
        self._run_worker.completed.connect(self._handle_run_completed)
        self._run_worker.failed.connect(self._handle_run_failed)
        self._run_worker.finished.connect(self._finish_run_worker)
        self._run_worker.finished.connect(self._run_thread.quit)
        self._run_thread.finished.connect(self._cleanup_run_thread)
        self._run_thread.finished.connect(self._run_thread.deleteLater)
        self._run_thread.start()

    def _start_resume_worker(self, production_order_id: int) -> None:
        if self._run_thread is not None:
            QMessageBox.information(self, "Auto Factory", "A run is already in progress.")
            return
        self._view_model.mark_resume_started(production_order_id)
        self.monitor_timer.start()
        self._run_thread = QThread(self)
        self._run_worker = AutoFactoryRunWorker(
            self._view_model,
            mode=AutoFactoryRunWorker.MODE_RESUME_ORDER,
            production_order_id=production_order_id,
        )
        self._run_worker.moveToThread(self._run_thread)
        self._run_thread.started.connect(self._run_worker.run)
        self._run_worker.progress_changed.connect(self._view_model.update_progress_snapshot)
        self._run_worker.completed.connect(self._handle_run_completed)
        self._run_worker.failed.connect(self._handle_run_failed)
        self._run_worker.finished.connect(self._finish_run_worker)
        self._run_worker.finished.connect(self._run_thread.quit)
        self._run_thread.finished.connect(self._cleanup_run_thread)
        self._run_thread.finished.connect(self._run_thread.deleteLater)
        self._run_thread.start()

    def _handle_run_completed(self, result) -> None:
        self._view_model.apply_execution_result(result)
        if self._view_model.monitored_order_id is not None:
            self._view_model.refresh_progress()

    def _handle_run_failed(self, error_message: str) -> None:
        self._view_model.handle_run_failure(error_message)
        QMessageBox.warning(self, "Auto Factory", error_message)

    def _finish_run_worker(self) -> None:
        if self._run_worker is not None:
            self._run_worker.deleteLater()
        self._run_worker = None
        if not self._view_model.run_active:
            self.monitor_timer.stop()
        self._refresh_run_controls()

    def _cleanup_run_thread(self) -> None:
        self._run_thread = None
        self._refresh_run_controls()

    def _refresh_progress_snapshot(self) -> None:
        try:
            self._view_model.refresh_progress()
        except Exception as exc:
            QMessageBox.warning(self, "Auto Factory", str(exc))

    def _poll_progress(self) -> None:
        if not self._view_model.run_active and self._view_model.monitored_order_id is None:
            self.monitor_timer.stop()
            return
        try:
            self._view_model.refresh_progress()
        except Exception as exc:
            self.monitor_timer.stop()
            set_feedback_message(self, str(exc))

    def _request_pause(self) -> None:
        try:
            self._view_model.request_pause()
        except Exception as exc:
            QMessageBox.warning(self, "Auto Factory", str(exc))

    def _request_stop(self) -> None:
        try:
            self._view_model.request_stop()
        except Exception as exc:
            QMessageBox.warning(self, "Auto Factory", str(exc))

    def _request_resume(self) -> None:
        try:
            production_order_id = self._view_model.get_resume_order_id()
        except Exception as exc:
            QMessageBox.warning(self, "Auto Factory", str(exc))
            return
        self._start_resume_worker(production_order_id)

    def _select_recent_order(self) -> None:
        selected_items = self.recent_orders_table.selectedItems()
        if not selected_items:
            return
        order_id_item = self.recent_orders_table.item(selected_items[0].row(), 0)
        if order_id_item is None:
            return
        try:
            self._view_model.select_order(int(order_id_item.text()))
        except Exception as exc:
            QMessageBox.warning(self, "Load Production Order", str(exc))

    def _refresh_selected_preflight_product_details(self) -> None:
        preflight_report = self._view_model.preflight_report
        if preflight_report is None:
            refresh_selected_product_action_state(self)
            return
        row_index = _selected_row_index(self.preflight_products_table)
        if row_index is None or row_index >= len(preflight_report.product_reports):
            refresh_selected_product_action_state(self)
            return
        product_report = preflight_report.product_reports[row_index]
        self.selected_product_text.setPlainText(build_preflight_product_detail_text(product_report))
        refresh_selected_product_action_state(self)

    def _refresh_selected_run_product_details(self) -> None:
        run_report = self._view_model.run_report
        if run_report is None:
            refresh_selected_product_action_state(self)
            return
        row_index = _selected_row_index(self.product_reports_table)
        if row_index is None or row_index >= len(run_report.product_reports):
            refresh_selected_product_action_state(self)
            return
        product_report = run_report.product_reports[row_index]
        request = next(
            (item for item in run_report.order.product_requests if item.product_code == product_report.product_code),
            None,
        )
        product_actions = [action for action in run_report.asset_actions if action.product_code == product_report.product_code]
        self.selected_product_text.setPlainText(
            build_run_product_detail_text(
                batch_code=run_report.batch_code,
                scan_depth=run_report.scan_depth,
                product_report=product_report,
                request=request,
                product_actions=product_actions,
            )
        )
        refresh_selected_product_action_state(self)

def _selected_row_index(table: QTableWidget) -> int | None:
    selected_items = table.selectedItems()
    if not selected_items:
        return None
    return selected_items[0].row()


def _select_first_row(table: QTableWidget) -> None:
    if table.rowCount() > 0 and not table.selectedItems():
        table.selectRow(0)
