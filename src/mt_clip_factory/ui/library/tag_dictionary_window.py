from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
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
        layout.addWidget(self._build_form_group(), 0, 0)
        layout.addWidget(self._build_table_group(), 0, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 2)
        self.setCentralWidget(central)

        self._view_model.tags_changed.connect(self._refresh_tags)
        self._view_model.assets_changed.connect(self._refresh_assets)
        self._view_model.feedback_changed.connect(self._refresh_feedback)
        self._view_model.status_changed.connect(self._refresh_feedback)
        self._refresh_feedback()
        self._view_model.load()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._view_model.load()

    def _build_form_group(self) -> QGroupBox:
        group = QGroupBox("Create Tag / Assign Tag")
        layout = QVBoxLayout(group)
        form_layout = QFormLayout()

        self.tag_name_input = QLineEdit()
        self.tag_group_input = QLineEdit()
        self.tag_description_input = QTextEdit()
        self.tag_description_input.setFixedHeight(90)

        form_layout.addRow("Tag Name", self.tag_name_input)
        form_layout.addRow("Tag Group", self.tag_group_input)
        form_layout.addRow("Description", self.tag_description_input)
        layout.addLayout(form_layout)

        button_row = QHBoxLayout()
        self.create_tag_button = QPushButton("Create Tag")
        self.assign_tag_button = QPushButton("Assign Selected Tag")
        self.refresh_button = QPushButton("Refresh")

        self.create_tag_button.clicked.connect(self._create_tag)
        self.assign_tag_button.clicked.connect(self._assign_tag)
        self.refresh_button.clicked.connect(self._view_model.load)

        button_row.addWidget(self.create_tag_button)
        button_row.addWidget(self.assign_tag_button)
        button_row.addWidget(self.refresh_button)
        layout.addLayout(button_row)

        self.feedback_label = QLabel()
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.feedback_label)
        layout.addStretch(1)
        return group

    def _build_table_group(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        tag_group = QGroupBox("Tags")
        tag_layout = QVBoxLayout(tag_group)
        self.tag_table = QTableWidget(0, 4)
        self.tag_table.setHorizontalHeaderLabels(["ID", "Group", "Name", "Description"])
        self.tag_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.tag_table.setSelectionMode(QTableWidget.SingleSelection)
        self.tag_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tag_table.horizontalHeader().setStretchLastSection(True)
        tag_layout.addWidget(self.tag_table)

        asset_group = QGroupBox("Assets")
        asset_layout = QVBoxLayout(asset_group)
        self.asset_table = QTableWidget(0, 5)
        self.asset_table.setHorizontalHeaderLabels(["ID", "Product", "Code", "Type", "Status"])
        self.asset_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.asset_table.setSelectionMode(QTableWidget.SingleSelection)
        self.asset_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.asset_table.horizontalHeader().setStretchLastSection(True)
        asset_layout.addWidget(self.asset_table)

        layout.addWidget(tag_group)
        layout.addWidget(asset_group)
        return container

    def _refresh_feedback(self) -> None:
        self.feedback_label.setText(f"Status: {self._view_model.status}\n{self._view_model.feedback}".strip())

    def _refresh_tags(self) -> None:
        tags = self._view_model.tags
        self.tag_table.setRowCount(len(tags))
        for row_index, tag in enumerate(tags):
            values = [str(tag.tag_id), tag.tag_group, tag.tag_name, tag.description or ""]
            for column_index, value in enumerate(values):
                self.tag_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _refresh_assets(self) -> None:
        assets = self._view_model.assets
        self.asset_table.setRowCount(len(assets))
        for row_index, asset in enumerate(assets):
            values = [str(asset.asset_id), asset.product_code, asset.asset_code, asset.asset_type, asset.status]
            for column_index, value in enumerate(values):
                self.asset_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _create_tag(self) -> None:
        try:
            self._view_model.create_tag(
                tag_name=self.tag_name_input.text(),
                tag_group=self.tag_group_input.text(),
                description=self.tag_description_input.toPlainText(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Create Tag", str(exc))
            return

        self.tag_name_input.clear()
        self.tag_group_input.clear()
        self.tag_description_input.clear()

    def _assign_tag(self) -> None:
        selected_tag = self.tag_table.selectedItems()
        selected_asset = self.asset_table.selectedItems()
        if not selected_tag or not selected_asset:
            QMessageBox.warning(self, "Assign Tag", "Select one tag and one asset before assigning.")
            return

        tag_id = int(selected_tag[0].tableWidget().item(selected_tag[0].row(), 0).text())
        asset_id = int(selected_asset[0].tableWidget().item(selected_asset[0].row(), 0).text())
        try:
            self._view_model.assign_tag_to_asset(asset_id=asset_id, tag_id=tag_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Assign Tag", str(exc))
