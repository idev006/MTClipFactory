from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
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
    ACTION_BUTTON_MIN_HEIGHT = 38

    def __init__(self, view_model: AutoFactoryControlViewModel) -> None:
        super().__init__()
        self._view_model = view_model
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
        self._refresh_status()
        self._refresh_feedback()
        self._refresh_run_mode_hint()
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
        self.batch_code_input.setPlaceholderText("optional override; default uses the folder name")
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
        self.overview_splitter.addWidget(self._build_run_summary_group())
        self.overview_splitter.addWidget(self._build_selected_product_group())
        self.overview_splitter.setChildrenCollapsible(False)
        self.overview_splitter.setStretchFactor(0, 2)
        self.overview_splitter.setStretchFactor(1, 3)
        self.overview_splitter.setSizes([180, 360])

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
        self.open_product_folder_button.clicked.connect(self._open_selected_product_folder)
        self.open_contracts_button.clicked.connect(self._open_selected_contracts_folder)
        self.open_runs_button.clicked.connect(self._open_selected_runs_folder)
        self.copy_summary_button.clicked.connect(self._copy_selected_product_summary)
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
        self._refresh_selected_product_action_state()
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
        self.order_stages_table = QTableWidget(0, 8)
        self._configure_table(
            self.order_stages_table,
            ["Seq", "Stage", "Scope", "Status", "Item", "Recipe", "Job", "Failure"],
            stretch_columns=(1, 7),
            interactive_widths={4: 90, 5: 90, 6: 90},
        )
        layout.addWidget(self.order_summary_text)
        layout.addWidget(self.order_stages_table)
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

    def _refresh_run_mode_hint(self) -> None:
        run_mode = str(self.run_mode_combo.currentData())
        self.run_mode_hint_label.setText(_build_run_mode_hint(run_mode))

    def _refresh_run_report(self) -> None:
        run_report = self._view_model.run_report
        if run_report is None:
            if self._view_model.preflight_report is None:
                self.run_summary_text.clear()
                self.selected_product_text.setPlainText(self.SELECTED_PRODUCT_PLACEHOLDER)
                self._refresh_selected_product_action_state()
                self.results_tabs.setCurrentWidget(self.overview_splitter)
            self.product_reports_table.setRowCount(0)
            self.asset_actions_table.setRowCount(0)
            return

        self.preflight_products_table.setRowCount(0)
        self.preflight_issues_table.setRowCount(0)
        self.results_tabs.setCurrentWidget(self.intake_splitter)

        request_lines = [
            _format_product_request_summary(request)
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
                self._refresh_selected_product_action_state()
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
            self.order_stages_table.setRowCount(0)
            return

        self.results_tabs.setCurrentWidget(self.order_stage_group)
        self.order_summary_text.setPlainText(
            "\n".join(
                [
                    f"Order ID: {selected_order.production_order_id}",
                    f"Order Code: {selected_order.order_code}",
                    f"Batch Code: {selected_order.batch_code}",
                    f"Source Mode: {selected_order.source_mode}",
                    f"Status: {selected_order.status}",
                    f"Strict Fulfillment: {selected_order.strict_fulfillment}",
                    f"Created At: {selected_order.created_at}",
                    f"Started At: {selected_order.started_at or 'not started'}",
                    f"Finished At: {selected_order.finished_at or 'not finished'}",
                ]
            )
        )
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

    def _browse_for_root_folder(self) -> None:
        selected_dir = QFileDialog.getExistingDirectory(self, "Select Auto Factory Root Folder")
        if selected_dir:
            self.root_folder_input.setText(selected_dir)

    def _run_batch_root(self) -> None:
        try:
            self._view_model.run_batch_root(
                root_folder=self.root_folder_input.text(),
                batch_code=self.batch_code_input.text() or None,
                scan_depth=self.scan_depth_input.value(),
                run_mode=str(self.run_mode_combo.currentData()),
            )
        except Exception as exc:
            QMessageBox.warning(self, "Auto Factory", str(exc))

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
            self._refresh_selected_product_action_state()
            return
        row_index = _selected_row_index(self.preflight_products_table)
        if row_index is None or row_index >= len(preflight_report.product_reports):
            self._refresh_selected_product_action_state()
            return
        product_report = preflight_report.product_reports[row_index]
        self.selected_product_text.setPlainText(_build_preflight_product_detail_text(product_report))
        self._refresh_selected_product_action_state()

    def _refresh_selected_run_product_details(self) -> None:
        run_report = self._view_model.run_report
        if run_report is None:
            self._refresh_selected_product_action_state()
            return
        row_index = _selected_row_index(self.product_reports_table)
        if row_index is None or row_index >= len(run_report.product_reports):
            self._refresh_selected_product_action_state()
            return
        product_report = run_report.product_reports[row_index]
        request = next(
            (item for item in run_report.order.product_requests if item.product_code == product_report.product_code),
            None,
        )
        product_actions = [action for action in run_report.asset_actions if action.product_code == product_report.product_code]
        self.selected_product_text.setPlainText(
            _build_run_product_detail_text(
                batch_code=run_report.batch_code,
                scan_depth=run_report.scan_depth,
                product_report=product_report,
                request=request,
                product_actions=product_actions,
            )
        )
        self._refresh_selected_product_action_state()

    def _open_selected_product_folder(self) -> None:
        product_dir = self._selected_product_dir()
        if product_dir is None:
            QMessageBox.information(self, "Auto Factory", "Select one product row first.")
            return
        self._open_local_path(product_dir, description="product folder")

    def _open_selected_contracts_folder(self) -> None:
        product_dir = self._selected_product_dir()
        if product_dir is None:
            QMessageBox.information(self, "Auto Factory", "Select one product row first.")
            return
        contracts_dir = product_dir / "contracts"
        self._open_local_path(contracts_dir if contracts_dir.exists() else product_dir, description="contracts folder")

    def _open_selected_runs_folder(self) -> None:
        product_dir = self._selected_product_dir()
        if product_dir is None:
            QMessageBox.information(self, "Auto Factory", "Select one product row first.")
            return
        batch_code = self._selected_batch_code()
        preferred_path = product_dir / "runs" / batch_code if batch_code else product_dir / "runs"
        fallback_path = product_dir / "runs"
        if preferred_path.exists():
            self._open_local_path(preferred_path, description="runs folder")
            return
        if fallback_path.exists():
            self._open_local_path(fallback_path, description="runs folder")
            return
        QMessageBox.information(
            self,
            "Auto Factory",
            f"Runs folder does not exist yet.\nExpected path: {preferred_path}",
        )

    def _copy_selected_product_summary(self) -> None:
        summary = self.selected_product_text.toPlainText().strip()
        if not summary or summary == self.SELECTED_PRODUCT_PLACEHOLDER:
            QMessageBox.information(self, "Auto Factory", "There is no selected product summary to copy yet.")
            return
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(summary)
        self._set_feedback_message("Selected product summary copied to clipboard.")

    def _selected_product_dir(self) -> Path | None:
        preflight_report = self._view_model.preflight_report
        if preflight_report is not None and hasattr(self, "preflight_products_table"):
            row_index = _selected_row_index(self.preflight_products_table)
            if row_index is not None and row_index < len(preflight_report.product_reports):
                return Path(preflight_report.product_reports[row_index].product_dir)

        run_report = self._view_model.run_report
        if run_report is not None and hasattr(self, "product_reports_table"):
            row_index = _selected_row_index(self.product_reports_table)
            if row_index is not None and row_index < len(run_report.product_reports):
                product_dir = run_report.product_reports[row_index].product_dir
                if product_dir:
                    return Path(product_dir)
        return None

    def _selected_batch_code(self) -> str | None:
        run_report = self._view_model.run_report
        if run_report is None or not hasattr(self, "product_reports_table"):
            return None
        row_index = _selected_row_index(self.product_reports_table)
        if row_index is None or row_index >= len(run_report.product_reports):
            return None
        return run_report.batch_code

    def _refresh_selected_product_action_state(self) -> None:
        has_product_path = self._selected_product_dir() is not None
        has_summary = bool(self.selected_product_text.toPlainText().strip()) and (
            self.selected_product_text.toPlainText() != self.SELECTED_PRODUCT_PLACEHOLDER
        )
        self.open_product_folder_button.setEnabled(has_product_path)
        self.open_contracts_button.setEnabled(has_product_path)
        self.open_runs_button.setEnabled(has_product_path)
        self.copy_summary_button.setEnabled(has_summary)

    def _open_local_path(self, path: Path, *, description: str) -> None:
        if not path.exists():
            QMessageBox.information(self, "Auto Factory", f"Cannot open {description} because it does not exist:\n{path}")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            QMessageBox.warning(self, "Auto Factory", f"Unable to open {description}:\n{path}")

    def _set_feedback_message(self, message: str) -> None:
        set_feedback = getattr(self._view_model, "_set_feedback", None)
        if callable(set_feedback):
            set_feedback(message)
            return
        if hasattr(self._view_model, "feedback"):
            self._view_model.feedback = message
            feedback_changed = getattr(self._view_model, "feedback_changed", None)
            if feedback_changed is not None:
                feedback_changed.emit()
        self._refresh_feedback()


def _format_product_request_summary(request) -> str:
    summary = (
        f"- {request.product_code}: requested={request.requested_output_count}, "
        f"platform={request.target_platform or 'default'}, ratio={request.target_ratio or 'default'}, "
        f"duration_mode={request.duration_mode}"
    )
    tag_filter_parts: list[str] = []
    if request.foreground_required_tag_labels:
        tag_filter_parts.append(f"foreground={', '.join(request.foreground_required_tag_labels)}")
    if request.background_required_tag_labels:
        tag_filter_parts.append(f"background={', '.join(request.background_required_tag_labels)}")
    if request.music_required_tag_labels:
        tag_filter_parts.append(f"music={', '.join(request.music_required_tag_labels)}")
    if request.voice_required_tag_labels:
        tag_filter_parts.append(f"voice={', '.join(request.voice_required_tag_labels)}")
    if not tag_filter_parts:
        return summary
    return f"{summary} | tag_filters: {'; '.join(tag_filter_parts)}"


def _build_run_mode_hint(run_mode: str) -> str:
    hints = {
        AutoFactoryControlViewModel.RUN_MODE_AUDIT_ONLY: (
            "Audit reads product-folder contracts, tags, and asset readiness without creating products or orders. "
            "Use this first when checking whether pipeline/tag/caption inputs are safe."
        ),
        AutoFactoryControlViewModel.RUN_MODE_INTAKE_ONLY: (
            "Intake registers deterministic assets and writes product-local run evidence without creating a production order. "
            "Use this when you want the library synced before preview/render work."
        ),
        AutoFactoryControlViewModel.RUN_MODE_MATERIALIZE: (
            "Materialize runs intake first, then creates one persisted production order and materializes recipe work."
        ),
        AutoFactoryControlViewModel.RUN_MODE_MATERIALIZE_AND_PREVIEWS: (
            "Build Previews runs the full intake -> production-order -> preview path and writes operator-auditable run artifacts "
            "under each product's runs/<batch_code> layout."
        ),
    }
    base = hints.get(run_mode, "")
    return (
        "Run Mode Guide: "
        f"{base} Product-local snapshots, manifests, and journal evidence are designed to stay traceable under "
        "runs/<batch_code> whenever the source product folder is known."
    )


def _selected_row_index(table: QTableWidget) -> int | None:
    selected_items = table.selectedItems()
    if not selected_items:
        return None
    return selected_items[0].row()


def _select_first_row(table: QTableWidget) -> None:
    if table.rowCount() > 0 and not table.selectedItems():
        table.selectRow(0)


def _build_preflight_product_detail_text(product_report) -> str:
    lines = [
        f"Product Folder: {product_report.product_dir}",
        f"Layout: {product_report.layout_mode}",
        f"Status: {product_report.status}",
        f"Ready For Automation: {'yes' if product_report.ready_for_automation else 'no'}",
        f"Ingestible Assets: {product_report.ingestible_asset_count}",
    ]

    product_config = product_report.product_config
    if product_config is not None:
        lines.extend(
            [
                "",
                "Product Contract:",
                f"- Product Code: {product_config.product_code}",
                f"- Product Name: {product_config.product_name}",
                f"- Category: {product_config.category or '-'}",
                f"- Brand: {product_config.brand_name or '-'}",
                f"- Default Platform: {product_config.default_platform or '-'}",
            ]
        )

    pipeline_config = product_report.pipeline_config
    if pipeline_config is not None:
        lines.extend(
            [
                "",
                "Pipeline Contract:",
                f"- Requested Outputs: {pipeline_config.requested_output_count}",
                f"- Platform: {pipeline_config.target_platform or '-'}",
                f"- Ratio: {pipeline_config.target_ratio or '-'}",
                f"- Uniqueness Scope: {pipeline_config.uniqueness_scope}",
                f"- Duration Mode: {pipeline_config.duration_mode}",
                f"- Fixed Duration Sec: {_format_optional_number(pipeline_config.fixed_duration_sec)}",
                f"- Min/Max Duration Sec: {pipeline_config.min_duration_sec} / {pipeline_config.max_duration_sec}",
                f"- Selection Tags: {_format_selection_tag_summary(pipeline_config)}",
            ]
        )

    caption_contract = product_report.caption_contract
    if caption_contract is not None:
        lines.extend(
            [
                "",
                "Caption Contract:",
                f"- Selection Mode: {caption_contract.selection_mode or '-'}",
                f"- Seed Scope: {caption_contract.seed_scope or '-'}",
                f"- Segment Pools: {', '.join(caption_contract.segment_pool_names) or '-'}",
                f"- Main Pool Entries: {caption_contract.main_pool_entry_count}",
                f"- Sub Pool Entries: {caption_contract.sub_pool_entry_count}",
                f"- Main Preset / Font: {_join_optional(caption_contract.main_style_preset, caption_contract.main_font_family)}",
                f"- Sub Preset / Font: {_join_optional(caption_contract.sub_style_preset, caption_contract.sub_font_family)}",
            ]
        )

    lines.extend(["", "Asset Folders:"])
    for asset_audit in product_report.asset_folders:
        lines.append(
            "- "
            f"{asset_audit.folder_name} ({asset_audit.asset_type}) | files={asset_audit.ingestible_file_count} "
            f"| tagged={asset_audit.tagged_file_count} | global_tags={asset_audit.global_tag_count} "
            f"| file_tag_entries={asset_audit.file_tag_entry_count} | tags.toml={'yes' if asset_audit.tag_file_present else 'no'} "
            f"| required={', '.join(asset_audit.required_tag_labels) or '-'} "
            f"| matching_required={asset_audit.matching_required_file_count}"
        )

    if product_report.issues:
        lines.extend(["", "Issues:"])
        for issue in product_report.issues:
            location = f" @ {issue.location}" if issue.location else ""
            lines.append(f"- [{issue.severity}] {issue.code}: {issue.message}{location}")

    return "\n".join(lines)


def _build_run_product_detail_text(
    *,
    batch_code: str,
    scan_depth: int,
    product_report,
    request,
    product_actions: list,
) -> str:
    lines = [
        f"Batch Code: {batch_code}",
        f"Scan Depth: {scan_depth}",
        f"Product Code: {product_report.product_code}",
        f"Product ID: {product_report.product_id}",
        f"Created Product: {'yes' if product_report.created_product else 'no'}",
        f"Registered Assets: {product_report.registered_asset_count}",
        f"Skipped Existing Assets: {product_report.skipped_existing_asset_count}",
    ]

    if request is not None:
        lines.extend(
            [
                "",
                "Resolved Runtime Request:",
                f"- Requested Outputs: {request.requested_output_count}",
                f"- Platform: {request.target_platform or '-'}",
                f"- Ratio: {request.target_ratio or '-'}",
                f"- Uniqueness Scope: {request.uniqueness_scope}",
                f"- Duration Mode: {request.duration_mode}",
                f"- Fixed Duration Sec: {_format_optional_number(request.fixed_duration_sec)}",
                f"- Min/Max Duration Sec: {request.min_duration_sec} / {request.max_duration_sec}",
                f"- Selection Tags: {_format_selection_tag_summary(request)}",
            ]
        )

    lines.extend(
        [
            "",
            "Asset Intake Actions:",
        ]
    )
    if not product_actions:
        lines.append("- none")
    else:
        for action in product_actions:
            lines.append(f"- {action.action}: {action.asset_type} -> {action.asset_code} ({action.source_file})")

    lines.extend(
        [
            "",
            "Artifact Note:",
            "- Product-local order snapshots and journal events are written under runs/<batch_code> when the product folder is known.",
        ]
    )
    return "\n".join(lines)


def _format_selection_tag_summary(config) -> str:
    parts: list[str] = []
    for label, values in (
        ("foreground", tuple(getattr(config, "foreground_required_tag_labels", ()))),
        ("background", tuple(getattr(config, "background_required_tag_labels", ()))),
        ("music", tuple(getattr(config, "music_required_tag_labels", ()))),
        ("voice", tuple(getattr(config, "voice_required_tag_labels", ()))),
    ):
        if values:
            parts.append(f"{label}={', '.join(values)}")
    return "; ".join(parts) if parts else "-"


def _format_optional_number(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:g}"


def _join_optional(left: str | None, right: str | None) -> str:
    if left and right:
        return f"{left} / {right}"
    return left or right or "-"
