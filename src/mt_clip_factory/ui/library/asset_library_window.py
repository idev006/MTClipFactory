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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mt_clip_factory.domain.enums import AssetType
from mt_clip_factory.presentation.library.asset_library import AssetLibraryViewModel


class AssetLibraryWindow(QMainWindow):
    def __init__(self, view_model: AssetLibraryViewModel) -> None:
        super().__init__()
        self._view_model = view_model
        self.setWindowTitle("MTClipFactory - Asset Intake")
        self.resize(1100, 700)

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

        self._view_model.products_changed.connect(self._refresh_product_combo)
        self._view_model.assets_changed.connect(self._refresh_table)
        self._view_model.feedback_changed.connect(self._refresh_feedback)
        self._view_model.status_changed.connect(self._refresh_feedback)
        self._refresh_feedback()
        self._view_model.load()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._view_model.load()

    def _build_form_group(self) -> QGroupBox:
        group = QGroupBox("Asset Intake")
        outer_layout = QVBoxLayout(group)
        form_layout = QFormLayout()

        self.product_combo = QComboBox()
        self.asset_type_combo = QComboBox()
        for asset_type in AssetType:
            self.asset_type_combo.addItem(asset_type.value, asset_type.value)

        self.asset_code_input = QLineEdit()
        self.source_path_input = QLineEdit()
        self.source_path_input.setPlaceholderText("Select a source file to ingest")
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse_file)

        source_row = QHBoxLayout()
        source_row.addWidget(self.source_path_input)
        source_row.addWidget(browse_button)

        form_layout.addRow("Product", self.product_combo)
        form_layout.addRow("Asset Type", self.asset_type_combo)
        form_layout.addRow("Asset Code", self.asset_code_input)
        form_layout.addRow("Source File", source_row)
        outer_layout.addLayout(form_layout)

        button_row = QHBoxLayout()
        self.register_button = QPushButton("Register")
        self.refresh_button = QPushButton("Refresh")
        self.register_button.clicked.connect(self._register_asset)
        self.refresh_button.clicked.connect(self._view_model.load)
        button_row.addWidget(self.register_button)
        button_row.addWidget(self.refresh_button)
        outer_layout.addLayout(button_row)

        self.feedback_label = QLabel()
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        outer_layout.addWidget(self.feedback_label)
        outer_layout.addStretch(1)
        return group

    def _build_table_group(self) -> QGroupBox:
        group = QGroupBox("Registered Assets")
        layout = QVBoxLayout(group)
        self.asset_table = QTableWidget(0, 8)
        self.asset_table.setHorizontalHeaderLabels(
            ["ID", "Product", "Code", "Type", "File Name", "Status", "Ratio", "Size MB"]
        )
        self.asset_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.asset_table.setSelectionMode(QTableWidget.SingleSelection)
        self.asset_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.asset_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.asset_table)
        return group

    def _refresh_feedback(self) -> None:
        self.feedback_label.setText(f"Status: {self._view_model.status}\n{self._view_model.feedback}".strip())

    def _refresh_product_combo(self) -> None:
        selected_product_id = self.product_combo.currentData()
        self.product_combo.blockSignals(True)
        self.product_combo.clear()
        for product in self._view_model.products:
            label = f"{product.product_code} | {product.product_name}"
            self.product_combo.addItem(label, product.product_id)
        if selected_product_id is not None:
            index = self.product_combo.findData(selected_product_id)
            if index >= 0:
                self.product_combo.setCurrentIndex(index)
        self.product_combo.blockSignals(False)

    def _refresh_table(self) -> None:
        assets = self._view_model.assets
        self.asset_table.setRowCount(len(assets))
        for row_index, asset in enumerate(assets):
            values = [
                str(asset.asset_id),
                asset.product_code,
                asset.asset_code,
                asset.asset_type,
                asset.file_name,
                asset.status,
                asset.ratio or "",
                "" if asset.file_size_mb is None else f"{asset.file_size_mb:.4f}",
            ]
            for column_index, value in enumerate(values):
                self.asset_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _browse_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Asset File")
        if file_path:
            self.source_path_input.setText(file_path)

    def _register_asset(self) -> None:
        product_id = self.product_combo.currentData()
        if product_id is None:
            QMessageBox.warning(self, "Register Asset", "Create a product before registering assets.")
            return
        try:
            self._view_model.register_asset(
                product_id=int(product_id),
                asset_type=str(self.asset_type_combo.currentData()),
                source_file_path=self.source_path_input.text(),
                asset_code=self.asset_code_input.text() or None,
            )
        except (FileNotFoundError, ValueError) as exc:
            QMessageBox.warning(self, "Register Asset", str(exc))
            return

        self.asset_code_input.clear()
        self.source_path_input.clear()

