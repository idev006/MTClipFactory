from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QAbstractItemView,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mt_clip_factory.presentation.library.tag_dictionary import TagDictionaryViewModel
from mt_clip_factory.ui.theme import apply_theme


class TagDictionaryWindow(QMainWindow):
    THEME_NAME = "app_window"

    def __init__(self, view_model: TagDictionaryViewModel) -> None:
        super().__init__()
        self._view_model = view_model
        self.setWindowTitle("MTClipFactory - Tag Dictionary")
        self.resize(1200, 720)
        apply_theme(self, self.THEME_NAME)

        central = QWidget(self)
        layout = QGridLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(16)
        layout.addWidget(self._build_left_group(), 0, 0)
        layout.addWidget(self._build_center_group(), 0, 1)
        layout.addWidget(self._build_right_group(), 0, 2)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)
        layout.setColumnStretch(2, 1)
        self.setCentralWidget(central)

        self._view_model.tags_changed.connect(self._refresh_tags)
        self._view_model.assets_changed.connect(self._refresh_assets)
        self._view_model.selected_asset_changed.connect(self._refresh_selected_asset)
        self._view_model.feedback_changed.connect(self._refresh_feedback)
        self._view_model.status_changed.connect(self._refresh_feedback)
        self._refresh_feedback()
        self._view_model.load()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._view_model.load()

    def _build_left_group(self) -> QGroupBox:
        group = QGroupBox("Create Tag / Available Tags")
        layout = QVBoxLayout(group)
        form_layout = QFormLayout()

        self.tag_name_input = QLineEdit()
        self.tag_name_input.setPlaceholderText("for example: warm, premium, testimonial")
        self.tag_group_input = QComboBox()
        self.tag_group_input.setEditable(True)
        self.tag_group_input.setInsertPolicy(QComboBox.NoInsert)
        self.tag_description_input = QTextEdit()
        self.tag_description_input.setFixedHeight(90)

        form_layout.addRow("Tag Name", self.tag_name_input)
        form_layout.addRow("Tag Group", self.tag_group_input)
        form_layout.addRow("Description", self.tag_description_input)
        layout.addLayout(form_layout)

        tag_filter_group = QGroupBox("Tag Filters")
        tag_filter_layout = QFormLayout(tag_filter_group)
        self.tag_filter_group_combo = QComboBox()
        self.tag_filter_search_input = QLineEdit()
        self.tag_filter_search_input.setPlaceholderText("search group:name or description")
        tag_filter_layout.addRow("Group", self.tag_filter_group_combo)
        tag_filter_layout.addRow("Search", self.tag_filter_search_input)
        layout.addWidget(tag_filter_group)

        button_row = QHBoxLayout()
        self.create_tag_button = QPushButton("Create Tag")
        self.create_and_attach_button = QPushButton("Create And Attach To Selected Assets")
        self.apply_tag_filters_button = QPushButton("Apply Tag Filters")
        self.clear_tag_filters_button = QPushButton("Clear Tag Filters")
        self.refresh_button = QPushButton("Refresh")

        self.create_tag_button.clicked.connect(self._create_tag)
        self.create_and_attach_button.clicked.connect(self._create_and_attach_tag)
        self.apply_tag_filters_button.clicked.connect(self._apply_tag_filters)
        self.clear_tag_filters_button.clicked.connect(self._clear_tag_filters)
        self.refresh_button.clicked.connect(self._view_model.load)

        button_row.addWidget(self.create_tag_button)
        button_row.addWidget(self.create_and_attach_button)
        button_row.addWidget(self.apply_tag_filters_button)
        button_row.addWidget(self.clear_tag_filters_button)
        button_row.addWidget(self.refresh_button)
        layout.addLayout(button_row)

        tag_group = QGroupBox("Available Tags")
        tag_layout = QVBoxLayout(tag_group)
        self.tag_table = QTableWidget(0, 4)
        self.tag_table.setHorizontalHeaderLabels(["ID", "Group", "Name", "Description"])
        self.tag_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.tag_table.setSelectionMode(QTableWidget.SingleSelection)
        self.tag_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tag_table.horizontalHeader().setStretchLastSection(True)
        self.tag_table.itemDoubleClicked.connect(lambda _: self._assign_tag_to_selected_asset())
        tag_layout.addWidget(self.tag_table)
        layout.addWidget(tag_group)

        self.feedback_label = QLabel()
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.feedback_label)
        return group

    def _build_center_group(self) -> QGroupBox:
        group = QGroupBox("Asset-First Tagging")
        layout = QVBoxLayout(group)

        filter_group = QGroupBox("Asset Filters")
        filter_layout = QFormLayout(filter_group)
        self.asset_filter_product_combo = QComboBox()
        self.asset_filter_status_combo = QComboBox()
        self.asset_filter_type_combo = QComboBox()
        self.asset_filter_status_combo.addItem("All", None)
        for status in ("ready", "needs_review", "analyzed", "retired", "purged"):
            self.asset_filter_status_combo.addItem(status, status)
        self.asset_search_input = QLineEdit()
        self.asset_search_input.setPlaceholderText("search asset code, file, type, product, or tag")
        filter_layout.addRow("Product", self.asset_filter_product_combo)
        filter_layout.addRow("Status", self.asset_filter_status_combo)
        filter_layout.addRow("Asset Type", self.asset_filter_type_combo)
        filter_layout.addRow("Search", self.asset_search_input)
        layout.addWidget(filter_group)

        self.automation_hint_label = QLabel(
            "Automation can consume normalized tag labels like `mood:warm` or `message:proof` from tagged assets."
        )
        self.automation_hint_label.setWordWrap(True)
        layout.addWidget(self.automation_hint_label)

        button_row = QHBoxLayout()
        self.apply_filters_button = QPushButton("Apply Filters")
        self.clear_filters_button = QPushButton("Clear Filters")
        self.apply_filters_button.clicked.connect(self._apply_filters)
        self.clear_filters_button.clicked.connect(self._clear_filters)
        button_row.addWidget(self.apply_filters_button)
        button_row.addWidget(self.clear_filters_button)
        layout.addLayout(button_row)

        asset_group = QGroupBox("Assets")
        asset_layout = QVBoxLayout(asset_group)
        self.asset_table = QTableWidget(0, 6)
        self.asset_table.setHorizontalHeaderLabels(["ID", "Product", "Code", "Type", "Status", "Tags"])
        self.asset_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.asset_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.asset_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.asset_table.horizontalHeader().setStretchLastSection(True)
        self.asset_table.itemSelectionChanged.connect(self._select_asset_from_table)
        asset_layout.addWidget(self.asset_table)
        layout.addWidget(asset_group)
        return group

    def _build_right_group(self) -> QGroupBox:
        group = QGroupBox("Selected Assets")
        layout = QVBoxLayout(group)
        self.selected_asset_summary_label = QLabel("Select one or more assets to begin asset-first tagging.")
        self.selected_asset_summary_label.setWordWrap(True)
        self.selected_asset_summary_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.selected_asset_summary_label)

        self.selected_assets_count_label = QLabel("Selected Assets: 0")
        self.selected_assets_count_label.setWordWrap(True)
        layout.addWidget(self.selected_assets_count_label)

        self.selected_asset_tags_text = QTextEdit()
        self.selected_asset_tags_text.setReadOnly(True)
        layout.addWidget(self.selected_asset_tags_text)

        self.assign_tag_button = QPushButton("Attach Selected Tag To Selected Assets")
        self.assign_tag_button.clicked.connect(self._assign_tag_to_selected_asset)
        layout.addWidget(self.assign_tag_button)
        layout.addStretch(1)
        return group

    def _refresh_feedback(self) -> None:
        self.feedback_label.setText(f"Status: {self._view_model.status}\n{self._view_model.feedback}".strip())

    def _refresh_tags(self) -> None:
        tags = self._view_model.tags
        current_group = self.tag_group_input.currentText()
        current_filter_group = self.tag_filter_group_combo.currentData()
        self.tag_group_input.blockSignals(True)
        self.tag_filter_group_combo.blockSignals(True)
        self.tag_group_input.clear()
        self.tag_filter_group_combo.clear()
        self.tag_filter_group_combo.addItem("All", None)
        for tag_group in self._view_model.tag_group_suggestions:
            self.tag_group_input.addItem(tag_group, tag_group)
        for tag_group in self._view_model.tag_filter_group_options:
            self.tag_filter_group_combo.addItem(tag_group, tag_group)
        self.tag_group_input.setCurrentText(current_group)
        self.tag_group_input.setCompleter(QCompleter(self._view_model.tag_group_suggestions, self))
        if current_filter_group is not None:
            tag_group_index = self.tag_filter_group_combo.findData(current_filter_group)
            if tag_group_index >= 0:
                self.tag_filter_group_combo.setCurrentIndex(tag_group_index)
        self.tag_group_input.blockSignals(False)
        self.tag_filter_group_combo.blockSignals(False)
        self.tag_table.setRowCount(len(tags))
        for row_index, tag in enumerate(tags):
            values = [str(tag.tag_id), tag.tag_group, tag.tag_name, tag.description or ""]
            for column_index, value in enumerate(values):
                self.tag_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _refresh_assets(self) -> None:
        assets = self._view_model.assets
        current_product = self.asset_filter_product_combo.currentData()
        current_asset_type = self.asset_filter_type_combo.currentData()
        selected_asset = self._view_model.selected_asset
        self.asset_filter_product_combo.blockSignals(True)
        self.asset_filter_type_combo.blockSignals(True)
        self.asset_table.blockSignals(True)
        self.asset_filter_product_combo.clear()
        self.asset_filter_type_combo.clear()
        self.asset_filter_product_combo.addItem("All", None)
        self.asset_filter_type_combo.addItem("All", None)
        for product_code in self._view_model.asset_filter_product_options:
            self.asset_filter_product_combo.addItem(product_code, product_code)
        for asset_type in self._view_model.asset_filter_type_options:
            self.asset_filter_type_combo.addItem(asset_type, asset_type)
        if current_product is not None:
            product_index = self.asset_filter_product_combo.findData(current_product)
            if product_index >= 0:
                self.asset_filter_product_combo.setCurrentIndex(product_index)
        if current_asset_type is not None:
            asset_type_index = self.asset_filter_type_combo.findData(current_asset_type)
            if asset_type_index >= 0:
                self.asset_filter_type_combo.setCurrentIndex(asset_type_index)
        self.asset_filter_product_combo.blockSignals(False)
        self.asset_filter_type_combo.blockSignals(False)
        search_suggestions = sorted(
            {
                asset.asset_code
                for asset in assets
            }
            | {asset.file_name for asset in assets}
            | {asset.product_code for asset in assets}
            | {tag_label for asset in assets for tag_label in asset.tag_labels}
        )
        self.asset_search_input.setCompleter(QCompleter(search_suggestions, self))
        self.asset_table.setRowCount(len(assets))
        for row_index, asset in enumerate(assets):
            values = [
                str(asset.asset_id),
                asset.product_code,
                asset.asset_code,
                asset.asset_type,
                asset.status,
                ", ".join(asset.tag_labels),
            ]
            for column_index, value in enumerate(values):
                self.asset_table.setItem(row_index, column_index, QTableWidgetItem(value))
            if asset.asset_id in {selected.asset_id for selected in self._view_model.selected_assets}:
                self.asset_table.selectRow(row_index)
        self.asset_table.blockSignals(False)

    def _create_tag(self) -> None:
        try:
            self._view_model.create_tag(
                tag_name=self.tag_name_input.text(),
                tag_group=self.tag_group_input.currentText(),
                description=self.tag_description_input.toPlainText(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Create Tag", str(exc))
            return

        self.tag_name_input.clear()
        self.tag_group_input.setCurrentIndex(-1)
        if self.tag_group_input.lineEdit() is not None:
            self.tag_group_input.lineEdit().clear()
        self.tag_description_input.clear()

    def _create_and_attach_tag(self) -> None:
        try:
            self._view_model.create_tag_and_assign_to_selected_asset(
                tag_name=self.tag_name_input.text(),
                tag_group=self.tag_group_input.currentText(),
                description=self.tag_description_input.toPlainText(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Create And Attach Tag", str(exc))
            return

        self.tag_name_input.clear()
        self.tag_description_input.clear()

    def _assign_tag_to_selected_asset(self) -> None:
        selected_tag = self.tag_table.selectedItems()
        if not selected_tag:
            QMessageBox.warning(self, "Assign Tag", "Select one tag before attaching it to the selected asset.")
            return

        tag_id = int(selected_tag[0].tableWidget().item(selected_tag[0].row(), 0).text())
        try:
            self._view_model.assign_tag_to_selected_asset(tag_id=tag_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Assign Tag", str(exc))

    def _apply_filters(self) -> None:
        self._view_model.apply_asset_filters(
            product_code=self.asset_filter_product_combo.currentData(),
            status=self.asset_filter_status_combo.currentData(),
            asset_type=self.asset_filter_type_combo.currentData(),
            search_text=self.asset_search_input.text(),
        )

    def _clear_filters(self) -> None:
        self.asset_filter_product_combo.setCurrentIndex(0)
        self.asset_filter_status_combo.setCurrentIndex(0)
        self.asset_filter_type_combo.setCurrentIndex(0)
        self.asset_search_input.clear()
        self._view_model.apply_asset_filters()

    def _apply_tag_filters(self) -> None:
        self._view_model.apply_tag_filters(
            tag_group=self.tag_filter_group_combo.currentData(),
            search_text=self.tag_filter_search_input.text(),
        )

    def _clear_tag_filters(self) -> None:
        self.tag_filter_group_combo.setCurrentIndex(0)
        self.tag_filter_search_input.clear()
        self._view_model.apply_tag_filters()

    def _select_asset_from_table(self) -> None:
        selected_ranges = self.asset_table.selectionModel().selectedRows()
        if not selected_ranges:
            self._view_model.select_assets([])
            return
        asset_ids: list[int] = []
        for model_index in selected_ranges:
            asset_id_item = self.asset_table.item(model_index.row(), 0)
            if asset_id_item is not None:
                asset_ids.append(int(asset_id_item.text()))
        self._view_model.select_assets(asset_ids)

    def _refresh_selected_asset(self) -> None:
        selected_asset = self._view_model.selected_asset
        if selected_asset is None:
            self.selected_asset_summary_label.setText("Select one or more assets to begin asset-first tagging.")
            self.selected_assets_count_label.setText("Selected Assets: 0")
            self.selected_asset_tags_text.setPlainText("")
            return

        self.selected_assets_count_label.setText(f"Selected Assets: {self._view_model.selected_asset_count}")
        self.selected_asset_summary_label.setText(
            "\n".join(
                [
                    f"Primary Asset: {selected_asset.asset_code}",
                    f"Product: {selected_asset.product_code}",
                    f"Type: {selected_asset.asset_type}",
                    f"Status: {selected_asset.status}",
                ]
            )
        )
        self.selected_asset_tags_text.setPlainText(
            "\n".join(
                [
                    "Current Tags:",
                    *([f"- {tag_label}" for tag_label in selected_asset.tag_labels] or ["- No tags assigned yet."]),
                ]
            )
        )
