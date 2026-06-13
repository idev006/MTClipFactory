from __future__ import annotations

from collections.abc import Callable

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
from mt_clip_factory.ui.theme import apply_theme


class AssetLibraryWindow(QMainWindow):
    THEME_NAME = "app_window"

    def __init__(
        self,
        view_model: AssetLibraryViewModel,
        open_tag_dictionary: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self._view_model = view_model
        self._open_tag_dictionary = open_tag_dictionary
        self.setWindowTitle("MTClipFactory - Asset Intake")
        self.resize(1100, 700)
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

        filter_layout = QFormLayout()
        self.filter_product_combo = QComboBox()
        self.filter_asset_type_combo = QComboBox()
        self.filter_status_combo = QComboBox()
        self.filter_asset_type_combo.addItem("All", None)
        for asset_type in AssetType:
            self.filter_asset_type_combo.addItem(asset_type.value, asset_type.value)
        self.filter_status_combo.addItem("All", None)
        for status in ("ready", "needs_review", "analyzed", "retired", "purged"):
            self.filter_status_combo.addItem(status, status)
        filter_layout.addRow("Filter Product", self.filter_product_combo)
        filter_layout.addRow("Filter Type", self.filter_asset_type_combo)
        filter_layout.addRow("Filter Status", self.filter_status_combo)
        outer_layout.addLayout(filter_layout)

        maintenance_row = QHBoxLayout()
        action_row = QHBoxLayout()
        self.register_button = QPushButton("Register")
        self.update_button = QPushButton("Update Selected")
        self.delete_button = QPushButton("Delete Selected")
        self.references_button = QPushButton("Show References")
        self.retire_button = QPushButton("Retire Selected")
        self.purge_button = QPushButton("Purge Media")
        self.thumbnail_button = QPushButton("Generate Thumbnail")
        self.proxy_button = QPushButton("Generate Proxy")
        self.tags_button = QPushButton("Tag Dictionary")
        self.apply_filters_button = QPushButton("Apply Filters")
        self.refresh_button = QPushButton("Refresh")
        self.register_button.clicked.connect(self._register_asset)
        self.update_button.clicked.connect(self._update_asset)
        self.delete_button.clicked.connect(self._delete_asset)
        self.references_button.clicked.connect(self._show_references)
        self.retire_button.clicked.connect(self._retire_asset)
        self.purge_button.clicked.connect(self._purge_asset_media)
        self.thumbnail_button.clicked.connect(self._generate_thumbnail)
        self.proxy_button.clicked.connect(self._generate_proxy)
        self.tags_button.clicked.connect(self._handle_open_tag_dictionary)
        self.apply_filters_button.clicked.connect(self._apply_filters)
        self.refresh_button.clicked.connect(self._view_model.load)
        maintenance_row.addWidget(self.register_button)
        maintenance_row.addWidget(self.update_button)
        maintenance_row.addWidget(self.delete_button)
        maintenance_row.addWidget(self.references_button)
        maintenance_row.addWidget(self.retire_button)
        maintenance_row.addWidget(self.purge_button)
        action_row.addWidget(self.thumbnail_button)
        action_row.addWidget(self.proxy_button)
        action_row.addWidget(self.tags_button)
        action_row.addWidget(self.apply_filters_button)
        action_row.addWidget(self.refresh_button)
        outer_layout.addLayout(maintenance_row)
        outer_layout.addLayout(action_row)

        self.feedback_label = QLabel()
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        outer_layout.addWidget(self.feedback_label)
        outer_layout.addStretch(1)
        return group

    def _build_table_group(self) -> QGroupBox:
        group = QGroupBox("Registered Assets")
        layout = QVBoxLayout(group)
        self.asset_table = QTableWidget(0, 11)
        self.asset_table.setHorizontalHeaderLabels(
            ["ID", "Product", "Code", "Type", "File Name", "Status", "Ratio", "Size MB", "Tags", "Thumbnail", "Proxy"]
        )
        self.asset_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.asset_table.setSelectionMode(QTableWidget.SingleSelection)
        self.asset_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.asset_table.horizontalHeader().setStretchLastSection(True)
        self.asset_table.itemSelectionChanged.connect(self._handle_asset_selection)
        layout.addWidget(self.asset_table)
        return group

    def _refresh_feedback(self) -> None:
        self.feedback_label.setText(f"Status: {self._view_model.status}\n{self._view_model.feedback}".strip())

    def _refresh_product_combo(self) -> None:
        selected_product_id = self.product_combo.currentData()
        selected_filter_product_id = self.filter_product_combo.currentData()
        self.product_combo.blockSignals(True)
        self.filter_product_combo.blockSignals(True)
        self.product_combo.clear()
        self.filter_product_combo.clear()
        self.filter_product_combo.addItem("All", None)
        for product in self._view_model.products:
            label = f"{product.product_code} | {product.product_name}"
            self.product_combo.addItem(label, product.product_id)
            self.filter_product_combo.addItem(label, product.product_id)
        if selected_product_id is not None:
            index = self.product_combo.findData(selected_product_id)
            if index >= 0:
                self.product_combo.setCurrentIndex(index)
        if selected_filter_product_id is not None:
            filter_index = self.filter_product_combo.findData(selected_filter_product_id)
            if filter_index >= 0:
                self.filter_product_combo.setCurrentIndex(filter_index)
        self.product_combo.blockSignals(False)
        self.filter_product_combo.blockSignals(False)

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
                ", ".join(asset.tag_labels),
                "Yes" if asset.thumbnail_path else "No",
                "Yes" if asset.proxy_path else "No",
            ]
            for column_index, value in enumerate(values):
                self.asset_table.setItem(row_index, column_index, QTableWidgetItem(value))

    def _selected_asset_summary(self):
        selected_items = self.asset_table.selectedItems()
        if not selected_items:
            return None
        row_index = selected_items[0].row()
        if row_index < 0 or row_index >= len(self._view_model.assets):
            return None
        return self._view_model.assets[row_index]

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

    def _update_asset(self) -> None:
        asset_id = self._selected_asset_id()
        if asset_id is None:
            QMessageBox.warning(self, "Update Asset", "Select an asset first.")
            return
        try:
            self._view_model.update_asset(asset_id=asset_id, asset_code=self.asset_code_input.text())
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Update Asset", str(exc))
            return
        self.source_path_input.clear()

    def _delete_asset(self) -> None:
        asset = self._selected_asset_summary()
        if asset is None:
            QMessageBox.warning(self, "Delete Asset", "Select an asset first.")
            return
        confirmation = QMessageBox.question(
            self,
            "Delete Asset",
            f"Delete asset {asset.asset_code}? This cannot be undone.",
        )
        if confirmation != QMessageBox.Yes:
            return
        try:
            self._view_model.delete_asset(asset.asset_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Delete Asset", str(exc))
            return
        self.asset_code_input.clear()
        self.source_path_input.clear()

    def _show_references(self) -> None:
        asset = self._selected_asset_summary()
        if asset is None:
            QMessageBox.warning(self, "Show References", "Select an asset first.")
            return
        try:
            report = self._view_model.describe_asset_references(asset.asset_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Show References", str(exc))
            return
        QMessageBox.information(self, "Asset References", self._format_reference_report(report))

    def _retire_asset(self) -> None:
        asset = self._selected_asset_summary()
        if asset is None:
            QMessageBox.warning(self, "Retire Asset", "Select an asset first.")
            return
        confirmation = QMessageBox.question(
            self,
            "Retire Asset",
            (
                f"Retire asset {asset.asset_code}?\n\n"
                "This keeps history intact but prevents future active use."
            ),
        )
        if confirmation != QMessageBox.Yes:
            return
        try:
            self._view_model.retire_asset(asset.asset_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Retire Asset", str(exc))
            return
        self.asset_code_input.clear()
        self.source_path_input.clear()

    def _purge_asset_media(self) -> None:
        asset = self._selected_asset_summary()
        if asset is None:
            QMessageBox.warning(self, "Purge Media", "Select an asset first.")
            return
        confirmation = QMessageBox.question(
            self,
            "Purge Media",
            (
                f"Purge media files for asset {asset.asset_code}?\n\n"
                "This deletes the stored files from disk but keeps the record for history. "
                "Rebuilding old outputs will require a replacement asset."
            ),
        )
        if confirmation != QMessageBox.Yes:
            return
        try:
            report = self._view_model.purge_asset_media(asset.asset_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Purge Media", str(exc))
            return
        reclaimed_mb = report.reclaimed_bytes / (1024 * 1024)
        QMessageBox.information(
            self,
            "Purge Media",
            (
                f"Purged {report.purged_file_count} files for asset {report.asset_code}.\n"
                f"Reclaimed approximately {reclaimed_mb:.2f} MB."
            ),
        )

    def _handle_open_tag_dictionary(self) -> None:
        if self._open_tag_dictionary is not None:
            self._open_tag_dictionary()

    def _apply_filters(self) -> None:
        self._view_model.apply_filters(
            product_id=self.filter_product_combo.currentData(),
            asset_type=self.filter_asset_type_combo.currentData(),
            status=self.filter_status_combo.currentData(),
        )

    def _selected_asset_id(self) -> int | None:
        selected_items = self.asset_table.selectedItems()
        if not selected_items:
            return None
        return int(self.asset_table.item(selected_items[0].row(), 0).text())

    def _handle_asset_selection(self) -> None:
        asset = self._selected_asset_summary()
        if asset is None:
            return
        product_index = self.product_combo.findData(asset.product_id)
        if product_index >= 0:
            self.product_combo.setCurrentIndex(product_index)
        asset_type_index = self.asset_type_combo.findData(asset.asset_type)
        if asset_type_index >= 0:
            self.asset_type_combo.setCurrentIndex(asset_type_index)
        self.asset_code_input.setText(asset.asset_code)
        self.source_path_input.clear()

    def _generate_thumbnail(self) -> None:
        asset_id = self._selected_asset_id()
        if asset_id is None:
            QMessageBox.warning(self, "Generate Thumbnail", "Select an asset first.")
            return
        try:
            self._view_model.generate_thumbnail(asset_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Generate Thumbnail", str(exc))

    def _generate_proxy(self) -> None:
        asset_id = self._selected_asset_id()
        if asset_id is None:
            QMessageBox.warning(self, "Generate Proxy", "Select an asset first.")
            return
        try:
            self._view_model.generate_proxy(asset_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Generate Proxy", str(exc))

    @staticmethod
    def _format_reference_report(report) -> str:
        lines = [
            f"Asset #{report.asset_id}: {report.asset_code}",
            f"Current status: {report.asset_status}",
            "",
            "Recipe references:",
        ]
        if report.recipe_references:
            for reference in report.recipe_references:
                lines.append(
                    f"- Recipe #{reference.recipe_id} | {reference.recipe_code} | "
                    f"status={reference.recipe_status} | outputs={reference.output_count}"
                )
        else:
            lines.append("- none")

        lines.extend(["", "Job references:"])
        if report.job_references:
            for reference in report.job_references:
                lines.append(
                    f"- Job #{reference.job_id} | {reference.job_code} | "
                    f"type={reference.job_type} | status={reference.job_status}"
                )
        else:
            lines.append("- none")

        lines.extend(
            [
                "",
                f"Delete allowed: {'yes' if report.can_delete else 'no'}",
                f"Purge allowed now: {'yes' if report.can_purge_media else 'no'}",
            ]
        )
        return "\n".join(lines)
