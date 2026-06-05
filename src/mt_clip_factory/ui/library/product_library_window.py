from __future__ import annotations

from collections.abc import Callable

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

from mt_clip_factory.application.dto import CreateProductCommand, UpdateProductCommand
from mt_clip_factory.presentation.library.product_library import ProductLibraryViewModel


class ProductLibraryWindow(QMainWindow):
    def __init__(
        self,
        view_model: ProductLibraryViewModel,
        open_asset_intake: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self._view_model = view_model
        self._open_asset_intake = open_asset_intake
        self._selected_product_id: int | None = None
        self.setWindowTitle("MTClipFactory - Resource Library Management")
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

        self._view_model.products_changed.connect(self._refresh_table)
        self._view_model.feedback_changed.connect(self._refresh_feedback)
        self._view_model.status_changed.connect(self._refresh_feedback)

        self._refresh_feedback()
        self._view_model.load()

    def _build_form_group(self) -> QGroupBox:
        group = QGroupBox("Product Setup")
        outer_layout = QVBoxLayout(group)
        form_layout = QFormLayout()

        self.code_input = QLineEdit()
        self.name_input = QLineEdit()
        self.category_input = QLineEdit()
        self.brand_input = QLineEdit()
        self.platform_input = QLineEdit()
        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(120)

        form_layout.addRow("Product Code", self.code_input)
        form_layout.addRow("Product Name", self.name_input)
        form_layout.addRow("Category", self.category_input)
        form_layout.addRow("Brand", self.brand_input)
        form_layout.addRow("Default Platform", self.platform_input)
        form_layout.addRow("Description", self.description_input)
        outer_layout.addLayout(form_layout)

        button_row = QHBoxLayout()
        self.new_button = QPushButton("Clear")
        self.create_button = QPushButton("Create")
        self.update_button = QPushButton("Update")
        self.delete_button = QPushButton("Delete")
        self.refresh_button = QPushButton("Refresh")
        self.asset_button = QPushButton("Asset Intake")

        self.new_button.clicked.connect(self._clear_form)
        self.create_button.clicked.connect(self._create_product)
        self.update_button.clicked.connect(self._update_product)
        self.delete_button.clicked.connect(self._delete_product)
        self.refresh_button.clicked.connect(self._view_model.load)
        self.asset_button.clicked.connect(self._handle_open_asset_intake)

        for button in (
            self.new_button,
            self.create_button,
            self.update_button,
            self.delete_button,
            self.refresh_button,
            self.asset_button,
        ):
            button_row.addWidget(button)

        outer_layout.addLayout(button_row)
        self.feedback_label = QLabel()
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        outer_layout.addWidget(self.feedback_label)
        outer_layout.addStretch(1)
        return group

    def _build_table_group(self) -> QGroupBox:
        group = QGroupBox("Products")
        layout = QVBoxLayout(group)
        self.product_table = QTableWidget(0, 8)
        self.product_table.setHorizontalHeaderLabels(
            ["ID", "Code", "Name", "Category", "Brand", "Platform", "Assets", "Outputs"]
        )
        self.product_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.product_table.setSelectionMode(QTableWidget.SingleSelection)
        self.product_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.product_table.itemSelectionChanged.connect(self._load_selected_product)
        self.product_table.setColumnHidden(0, True)
        self.product_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.product_table)
        return group

    def _refresh_feedback(self) -> None:
        feedback = self._view_model.feedback
        status = self._view_model.status
        self.feedback_label.setText(f"Status: {status}\n{feedback}".strip())

    def _refresh_table(self) -> None:
        products = self._view_model.products
        self.product_table.setRowCount(len(products))
        for row_index, product in enumerate(products):
            values = [
                str(product.product_id),
                product.product_code,
                product.product_name,
                product.category or "",
                product.brand_name or "",
                product.default_platform or "",
                str(product.asset_count),
                str(product.output_count),
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                self.product_table.setItem(row_index, column_index, item)

    def _build_create_command(self) -> CreateProductCommand:
        return CreateProductCommand(
            product_code=self.code_input.text(),
            product_name=self.name_input.text(),
            category=self.category_input.text(),
            brand_name=self.brand_input.text(),
            description=self.description_input.toPlainText(),
            default_platform=self.platform_input.text(),
        )

    def _build_update_command(self) -> UpdateProductCommand:
        if self._selected_product_id is None:
            raise ValueError("Select a product before updating.")
        return UpdateProductCommand(
            product_id=self._selected_product_id,
            product_code=self.code_input.text(),
            product_name=self.name_input.text(),
            category=self.category_input.text(),
            brand_name=self.brand_input.text(),
            description=self.description_input.toPlainText(),
            default_platform=self.platform_input.text(),
        )

    def _create_product(self) -> None:
        try:
            self._view_model.create_product(self._build_create_command())
        except ValueError as exc:
            QMessageBox.warning(self, "Create Product", str(exc))
            return
        self._clear_form()

    def _update_product(self) -> None:
        try:
            self._view_model.update_product(self._build_update_command())
        except ValueError as exc:
            QMessageBox.warning(self, "Update Product", str(exc))
            return

    def _delete_product(self) -> None:
        if self._selected_product_id is None:
            QMessageBox.warning(self, "Delete Product", "Select a product before deleting.")
            return
        confirmed = QMessageBox.question(
            self,
            "Delete Product",
            "Delete the selected product? This only works when the product has no assets.",
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return
        try:
            self._view_model.delete_product(self._selected_product_id)
        except ValueError as exc:
            QMessageBox.warning(self, "Delete Product", str(exc))
            return
        self._clear_form()

    def _load_selected_product(self) -> None:
        selected_items = self.product_table.selectedItems()
        if not selected_items:
            return
        row = selected_items[0].row()
        product_id_item = self.product_table.item(row, 0)
        if product_id_item is None:
            return

        product_id = int(product_id_item.text())
        details = self._view_model.get_product(product_id)
        self._selected_product_id = details.product_id
        self.code_input.setText(details.product_code)
        self.name_input.setText(details.product_name)
        self.category_input.setText(details.category or "")
        self.brand_input.setText(details.brand_name or "")
        self.platform_input.setText(details.default_platform or "")
        self.description_input.setPlainText(details.description or "")

    def _clear_form(self) -> None:
        self._selected_product_id = None
        self.code_input.clear()
        self.name_input.clear()
        self.category_input.clear()
        self.brand_input.clear()
        self.platform_input.clear()
        self.description_input.clear()
        self.product_table.clearSelection()

    def _handle_open_asset_intake(self) -> None:
        if self._open_asset_intake is not None:
            self._open_asset_intake()
