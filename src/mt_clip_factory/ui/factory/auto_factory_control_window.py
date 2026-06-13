from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
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

    def __init__(self, view_model: AutoFactoryControlViewModel) -> None:
        super().__init__()
        self._view_model = view_model
        self.setWindowTitle("MTClipFactory - Auto Factory")
        self.resize(1440, 860)
        apply_theme(self, self.THEME_NAME)

        central = QWidget(self)
        layout = QGridLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(16)
        layout.addWidget(self._build_controls_group(), 0, 0)
        layout.addWidget(self._build_results_area(), 0, 1)
        layout.addWidget(self._build_recent_orders_group(), 1, 0, 1, 2)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)
        layout.setRowStretch(0, 3)
        layout.setRowStretch(1, 2)
        self.setCentralWidget(central)

        self._view_model.recent_orders_changed.connect(self._refresh_recent_orders)
        self._view_model.run_report_changed.connect(self._refresh_run_report)
        self._view_model.selected_order_changed.connect(self._refresh_selected_order)
        self._view_model.status_changed.connect(self._refresh_status)
        self._view_model.feedback_changed.connect(self._refresh_feedback)
        self._refresh_status()
        self._refresh_feedback()
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
        self.run_mode_combo.addItem("Intake Only", self._view_model.RUN_MODE_INTAKE_ONLY)
        self.run_mode_combo.addItem("Intake + Materialize", self._view_model.RUN_MODE_MATERIALIZE)
        self.run_mode_combo.addItem(
            "Intake + Materialize + Build Previews",
            self._view_model.RUN_MODE_MATERIALIZE_AND_PREVIEWS,
        )

        form_layout.addRow("Root Folder", root_row)
        form_layout.addRow("Batch Code", self.batch_code_input)
        form_layout.addRow("Scan Depth", self.scan_depth_input)
        form_layout.addRow("Run Mode", self.run_mode_combo)
        layout.addLayout(form_layout)

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

    def _build_results_area(self) -> QWidget:
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self._build_run_summary_group())
        splitter.addWidget(self._build_product_reports_group())
        splitter.addWidget(self._build_asset_actions_group())
        splitter.addWidget(self._build_order_stages_group())
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 2)
        splitter.setStretchFactor(3, 3)
        self.results_splitter = splitter
        return splitter

    def _build_run_summary_group(self) -> QGroupBox:
        group = QGroupBox("Latest Run Summary")
        layout = QVBoxLayout(group)
        self.run_summary_text = QTextEdit()
        self.run_summary_text.setReadOnly(True)
        layout.addWidget(self.run_summary_text)
        return group

    def _build_product_reports_group(self) -> QGroupBox:
        group = QGroupBox("Product Reports")
        layout = QVBoxLayout(group)
        self.product_reports_table = QTableWidget(0, 5)
        self.product_reports_table.setHorizontalHeaderLabels(
            ["Product ID", "Product Code", "Created", "Registered Assets", "Skipped Existing"]
        )
        self.product_reports_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.product_reports_table.setSelectionMode(QTableWidget.SingleSelection)
        self.product_reports_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.product_reports_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.product_reports_table)
        return group

    def _build_asset_actions_group(self) -> QGroupBox:
        group = QGroupBox("Asset Intake Actions")
        layout = QVBoxLayout(group)
        self.asset_actions_table = QTableWidget(0, 5)
        self.asset_actions_table.setHorizontalHeaderLabels(
            ["Product", "Type", "Asset Code", "Action", "Source File"]
        )
        self.asset_actions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.asset_actions_table.setSelectionMode(QTableWidget.SingleSelection)
        self.asset_actions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.asset_actions_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.asset_actions_table)
        return group

    def _build_order_stages_group(self) -> QGroupBox:
        group = QGroupBox("Selected Production Order Stages")
        layout = QVBoxLayout(group)
        self.order_summary_text = QTextEdit()
        self.order_summary_text.setReadOnly(True)
        self.order_stages_table = QTableWidget(0, 8)
        self.order_stages_table.setHorizontalHeaderLabels(
            ["Seq", "Stage", "Scope", "Status", "Item", "Recipe", "Job", "Failure"]
        )
        self.order_stages_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.order_stages_table.setSelectionMode(QTableWidget.SingleSelection)
        self.order_stages_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.order_stages_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.order_summary_text)
        layout.addWidget(self.order_stages_table)
        return group

    def _build_recent_orders_group(self) -> QGroupBox:
        group = QGroupBox("Recent Production Orders")
        layout = QVBoxLayout(group)
        self.recent_orders_table = QTableWidget(0, 8)
        self.recent_orders_table.setHorizontalHeaderLabels(
            ["ID", "Order Code", "Batch Code", "Status", "Items", "Source", "Started", "Finished"]
        )
        self.recent_orders_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.recent_orders_table.setSelectionMode(QTableWidget.SingleSelection)
        self.recent_orders_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.recent_orders_table.horizontalHeader().setStretchLastSection(True)
        self.recent_orders_table.itemSelectionChanged.connect(self._select_recent_order)
        layout.addWidget(self.recent_orders_table)
        return group

    def _refresh_status(self) -> None:
        self.status_label.setText(f"Status: {self._view_model.status}")

    def _refresh_feedback(self) -> None:
        self.feedback_label.setText(self._view_model.feedback)

    def _refresh_run_report(self) -> None:
        run_report = self._view_model.run_report
        if run_report is None:
            self.run_summary_text.clear()
            self.product_reports_table.setRowCount(0)
            self.asset_actions_table.setRowCount(0)
            return

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

    def _refresh_selected_order(self) -> None:
        selected_order = self._view_model.selected_order
        if selected_order is None:
            self.order_summary_text.setPlainText("No production order selected.")
            self.order_stages_table.setRowCount(0)
            return

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
