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
    QVBoxLayout,
    QWidget,
)

from mt_clip_factory.presentation.factory.recipe_builder import RecipeBuilderViewModel


class RecipeBuilderWindow(QMainWindow):
    def __init__(self, view_model: RecipeBuilderViewModel) -> None:
        super().__init__()
        self._view_model = view_model
        self.setWindowTitle("MTClipFactory - Video Assembly Factory")
        self.resize(1280, 760)

        central = QWidget(self)
        layout = QGridLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(16)
        layout.addWidget(self._build_recipe_group(), 0, 0)
        layout.addWidget(self._build_recipe_table_group(), 0, 1)
        layout.addWidget(self._build_asset_group(), 1, 0)
        layout.addWidget(self._build_recipe_items_group(), 1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        self.setCentralWidget(central)

        self._view_model.products_changed.connect(self._refresh_product_combo)
        self._view_model.assets_changed.connect(self._refresh_assets_table)
        self._view_model.recipes_changed.connect(self._refresh_recipes_table)
        self._view_model.recipe_items_changed.connect(self._refresh_recipe_items_table)
        self._view_model.feedback_changed.connect(self._refresh_feedback)
        self._view_model.status_changed.connect(self._refresh_feedback)
        self._refresh_feedback()
        self._view_model.load()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._view_model.load()

    def _build_recipe_group(self) -> QGroupBox:
        group = QGroupBox("Create Recipe")
        layout = QVBoxLayout(group)
        form_layout = QFormLayout()
        self.product_combo = QLineEdit()
        self.product_combo.setReadOnly(True)
        self.product_picker = QTableWidget(0, 2)
        self.product_picker.setHorizontalHeaderLabels(["ID", "Product"])
        self.product_picker.setSelectionBehavior(QTableWidget.SelectRows)
        self.product_picker.setSelectionMode(QTableWidget.SingleSelection)
        self.product_picker.setEditTriggers(QTableWidget.NoEditTriggers)
        self.product_picker.horizontalHeader().setStretchLastSection(True)
        self.recipe_code_input = QLineEdit()
        self.platform_input = QLineEdit()
        self.ratio_input = QLineEdit()
        self.role_input = QLineEdit()
        self.role_input.setPlaceholderText("hero, hook, broll, cta")
        form_layout.addRow("Recipe Code", self.recipe_code_input)
        form_layout.addRow("Target Platform", self.platform_input)
        form_layout.addRow("Target Ratio", self.ratio_input)
        form_layout.addRow("Attach Role", self.role_input)
        layout.addWidget(self.product_picker)
        layout.addLayout(form_layout)

        button_row = QHBoxLayout()
        create_button = QPushButton("Create Recipe")
        attach_button = QPushButton("Attach Selected Asset")
        preview_button = QPushButton("Build Preview")
        refresh_button = QPushButton("Refresh")
        create_button.clicked.connect(self._create_recipe)
        attach_button.clicked.connect(self._attach_asset)
        preview_button.clicked.connect(self._build_preview)
        refresh_button.clicked.connect(self._view_model.load)
        button_row.addWidget(create_button)
        button_row.addWidget(attach_button)
        button_row.addWidget(preview_button)
        button_row.addWidget(refresh_button)
        layout.addLayout(button_row)

        self.feedback_label = QLabel()
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.feedback_label)
        return group

    def _build_recipe_table_group(self) -> QGroupBox:
        group = QGroupBox("Recipes")
        layout = QVBoxLayout(group)
        self.recipe_table = QTableWidget(0, 6)
        self.recipe_table.setHorizontalHeaderLabels(["ID", "Product", "Code", "Platform", "Ratio", "Items"])
        self.recipe_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.recipe_table.setSelectionMode(QTableWidget.SingleSelection)
        self.recipe_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.recipe_table.horizontalHeader().setStretchLastSection(True)
        self.recipe_table.itemSelectionChanged.connect(self._handle_recipe_selection)
        layout.addWidget(self.recipe_table)
        return group

    def _build_asset_group(self) -> QGroupBox:
        group = QGroupBox("Ready Assets")
        layout = QVBoxLayout(group)
        self.assets_table = QTableWidget(0, 5)
        self.assets_table.setHorizontalHeaderLabels(["ID", "Product", "Code", "Type", "Status"])
        self.assets_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.assets_table.setSelectionMode(QTableWidget.SingleSelection)
        self.assets_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.assets_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.assets_table)
        return group

    def _build_recipe_items_group(self) -> QGroupBox:
        group = QGroupBox("Recipe Items")
        layout = QVBoxLayout(group)
        self.recipe_items_table = QTableWidget(0, 4)
        self.recipe_items_table.setHorizontalHeaderLabels(["Item ID", "Asset ID", "Asset Code", "Role"])
        self.recipe_items_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.recipe_items_table.setSelectionMode(QTableWidget.SingleSelection)
        self.recipe_items_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.recipe_items_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.recipe_items_table)
        return group

    def _refresh_feedback(self) -> None:
        self.feedback_label.setText(f"Status: {self._view_model.status}\n{self._view_model.feedback}".strip())

    def _refresh_product_combo(self) -> None:
        self.product_picker.setRowCount(len(self._view_model.products))
        for row_index, product in enumerate(self._view_model.products):
            self.product_picker.setItem(row_index, 0, QTableWidgetItem(str(product.product_id)))
            self.product_picker.setItem(
                row_index,
                1,
                QTableWidgetItem(f"{product.product_code} | {product.product_name}"),
            )

    def _refresh_recipes_table(self) -> None:
        self.recipe_table.setRowCount(len(self._view_model.recipes))
        for row_index, recipe in enumerate(self._view_model.recipes):
            values = [
                str(recipe.recipe_id),
                recipe.product_code,
                recipe.recipe_code,
                recipe.target_platform or "",
                recipe.target_ratio or "",
                str(recipe.item_count),
            ]
            for column_index, value in enumerate(values):
                self.recipe_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _refresh_assets_table(self) -> None:
        self.assets_table.setRowCount(len(self._view_model.assets))
        for row_index, asset in enumerate(self._view_model.assets):
            values = [
                str(asset.asset_id),
                asset.product_code,
                asset.asset_code,
                asset.asset_type,
                asset.status,
            ]
            for column_index, value in enumerate(values):
                self.assets_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _refresh_recipe_items_table(self) -> None:
        self.recipe_items_table.setRowCount(len(self._view_model.recipe_items))
        for row_index, item in enumerate(self._view_model.recipe_items):
            values = [
                str(item.recipe_item_id),
                str(item.asset_id),
                item.asset_code or "",
                item.role,
            ]
            for column_index, value in enumerate(values):
                self.recipe_items_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _selected_product_id(self) -> int | None:
        selected_items = self.product_picker.selectedItems()
        if not selected_items:
            return None
        return int(self.product_picker.item(selected_items[0].row(), 0).text())

    def _selected_recipe_id(self) -> int | None:
        selected_items = self.recipe_table.selectedItems()
        if not selected_items:
            return None
        return int(self.recipe_table.item(selected_items[0].row(), 0).text())

    def _selected_asset_id(self) -> int | None:
        selected_items = self.assets_table.selectedItems()
        if not selected_items:
            return None
        return int(self.assets_table.item(selected_items[0].row(), 0).text())

    def _create_recipe(self) -> None:
        product_id = self._selected_product_id()
        if product_id is None:
            QMessageBox.warning(self, "Create Recipe", "Select a product first.")
            return
        try:
            self._view_model.create_recipe(
                product_id=product_id,
                recipe_code=self.recipe_code_input.text(),
                target_platform=self.platform_input.text() or None,
                target_ratio=self.ratio_input.text() or None,
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Create Recipe", str(exc))
            return

        self.recipe_code_input.clear()
        self.platform_input.clear()
        self.ratio_input.clear()

    def _attach_asset(self) -> None:
        recipe_id = self._selected_recipe_id()
        asset_id = self._selected_asset_id()
        if recipe_id is None or asset_id is None:
            QMessageBox.warning(self, "Attach Asset", "Select both a recipe and an asset first.")
            return
        try:
            self._view_model.assign_asset_to_recipe(
                recipe_id=recipe_id,
                asset_id=asset_id,
                role=self.role_input.text(),
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Attach Asset", str(exc))

    def _build_preview(self) -> None:
        recipe_id = self._selected_recipe_id()
        if recipe_id is None:
            QMessageBox.warning(self, "Build Preview", "Select a recipe first.")
            return
        try:
            self._view_model.queue_preview(recipe_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Build Preview", str(exc))

    def _handle_recipe_selection(self) -> None:
        self._view_model.select_recipe(self._selected_recipe_id())
