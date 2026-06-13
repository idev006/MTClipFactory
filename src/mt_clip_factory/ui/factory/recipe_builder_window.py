from __future__ import annotations

from collections import Counter

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from mt_clip_factory.presentation.factory.recipe_builder import RecipeBuilderViewModel
from mt_clip_factory.ui.factory.recipe_builder_aftercare import (
    _build_manifest_audio_lines,
    _build_manifest_review_lines,
    assess_recipe_aftercare,
    build_aftercare_guidance,
    build_output_detail_lines,
    format_output_aftercare_state,
)
from mt_clip_factory.ui.theme import apply_theme


class RecipeBuilderWindow(QMainWindow):
    THEME_NAME = "app_window"
    DEFAULT_ATTACH_ROLES = ("hero", "hook", "problem", "benefit", "proof", "cta", "broll", "background", "voice", "music")
    SEMANTIC_VISUAL_ROLES = ("hook", "problem", "benefit", "proof", "cta")
    ROLE_SUGGESTIONS_BY_ASSET_TYPE = {
        "background_video": ("hook", "problem", "benefit", "proof", "cta", "background", "broll"),
        "foreground_video": ("hero", "hook", "problem", "benefit", "proof", "cta", "broll"),
        "voiceover": ("voice",),
        "background_music": ("music",),
        "sfx": ("sfx",),
        "template": ("template", "text_overlay", "subtitle"),
        "script": ("script",),
    }
    PRODUCT_PICKER_MIN_HEIGHT = 110
    RECIPE_TABLE_MIN_HEIGHT = 240
    ASSETS_TABLE_MIN_HEIGHT = 220
    RECIPE_ITEMS_TABLE_MIN_HEIGHT = 220
    OUTPUTS_TABLE_MIN_HEIGHT = 160
    OUTPUT_DETAILS_MIN_HEIGHT = 120
    DECISION_HISTORY_MIN_HEIGHT = 120

    def __init__(self, view_model: RecipeBuilderViewModel) -> None:
        super().__init__()
        self._view_model = view_model
        self.setWindowTitle("MTClipFactory - Video Assembly Factory")
        self.resize(1280, 760)
        apply_theme(self, self.THEME_NAME)

        central = QWidget(self)
        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(16, 16, 16, 16)

        self.workspace_splitter = QSplitter(Qt.Horizontal, central)
        self.workspace_splitter.setChildrenCollapsible(False)
        self.inventory_splitter = QSplitter(Qt.Vertical, self.workspace_splitter)
        self.inventory_splitter.setChildrenCollapsible(False)
        self.review_splitter = QSplitter(Qt.Vertical, self.workspace_splitter)
        self.review_splitter.setChildrenCollapsible(False)

        self.scroll_area = QScrollArea(self.workspace_splitter)
        self.scroll_area.setWidgetResizable(True)
        self.content_widget = QWidget(self.scroll_area)
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSizeConstraint(QLayout.SetMinimumSize)
        content_layout.addWidget(self._build_recipe_group())
        content_layout.addStretch(1)
        self.scroll_area.setWidget(self.content_widget)

        self.inventory_splitter.addWidget(self._build_asset_group())
        self.inventory_splitter.addWidget(self._build_recipe_items_group())
        self.review_splitter.addWidget(self._build_recipe_table_group())
        self.review_splitter.addWidget(self._build_outputs_group())

        self.workspace_splitter.addWidget(self.scroll_area)
        self.workspace_splitter.addWidget(self.inventory_splitter)
        self.workspace_splitter.addWidget(self.review_splitter)
        self.workspace_splitter.setStretchFactor(0, 2)
        self.workspace_splitter.setStretchFactor(1, 2)
        self.workspace_splitter.setStretchFactor(2, 3)
        self.inventory_splitter.setStretchFactor(0, 3)
        self.inventory_splitter.setStretchFactor(1, 2)
        self.review_splitter.setStretchFactor(0, 2)
        self.review_splitter.setStretchFactor(1, 3)
        self.workspace_splitter.setSizes([420, 420, 620])
        self.inventory_splitter.setSizes([360, 260])
        self.review_splitter.setSizes([280, 420])

        outer_layout.addWidget(self.workspace_splitter)
        self.setCentralWidget(central)

        self._view_model.products_changed.connect(self._refresh_product_combo)
        self._view_model.assets_changed.connect(self._refresh_assets_table)
        self._view_model.recipes_changed.connect(self._refresh_recipes_table)
        self._view_model.recipe_items_changed.connect(self._refresh_recipe_items_table)
        self._view_model.outputs_changed.connect(self._refresh_outputs_table)
        self._view_model.decision_events_changed.connect(self._refresh_decision_history_table)
        self._view_model.feedback_changed.connect(self._refresh_feedback)
        self._view_model.status_changed.connect(self._refresh_feedback)
        self._refresh_feedback()
        self._view_model.load()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._view_model.load()

    def _build_recipe_group(self) -> QGroupBox:
        group = QGroupBox("Recipe Builder")
        layout = QVBoxLayout(group)
        summary_label = QLabel(
            "Use this page to create a recipe, attach ready assets, build preview, review the result, approve it, and build the final output."
        )
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)
        self.workflow_label = QLabel(
            "Workflow: 1) select product  2) create recipe  3) attach ready assets  4) build preview  "
            "5) approve output  6) approve recipe  7) build final"
        )
        self.workflow_label.setWordWrap(True)
        layout.addWidget(self.workflow_label)
        self.aftercare_label = QLabel("Workflow guidance: Select a recipe to see rebuild and approval guidance.")
        self.aftercare_label.setWordWrap(True)
        layout.addWidget(self.aftercare_label)
        form_layout = QFormLayout()
        self.product_combo = QLineEdit()
        self.product_combo.setReadOnly(True)
        self.product_picker = QTableWidget(0, 2)
        self.product_picker.setHorizontalHeaderLabels(["ID", "Product"])
        self._configure_table(self.product_picker, minimum_height=self.PRODUCT_PICKER_MIN_HEIGHT)
        self.recipe_code_input = QLineEdit()
        self.platform_input = QLineEdit()
        self.ratio_input = QLineEdit()
        self.role_input = QComboBox()
        self.role_input.setEditable(True)
        self.role_input.addItems(self.DEFAULT_ATTACH_ROLES)
        self.role_input.setInsertPolicy(QComboBox.NoInsert)
        self.role_input.setCurrentIndex(-1)
        if self.role_input.lineEdit() is not None:
            self.role_input.lineEdit().setPlaceholderText("choose or type role")
        self.decision_actor_input = QLineEdit()
        self.decision_reason_input = QLineEdit()
        self.decision_actor_input.setPlaceholderText("operator, editor, qa")
        self.decision_reason_input.setPlaceholderText("optional decision note")
        self.role_hint_label = QLabel("Role guidance: Select a recipe and asset to get a suggested role.")
        self.role_hint_label.setWordWrap(True)
        form_layout.addRow("Recipe Code", self.recipe_code_input)
        form_layout.addRow("Target Platform", self.platform_input)
        form_layout.addRow("Target Ratio", self.ratio_input)
        form_layout.addRow("Attach Role", self.role_input)
        form_layout.addRow("Role Guidance", self.role_hint_label)
        form_layout.addRow("Decision Actor", self.decision_actor_input)
        form_layout.addRow("Decision Note", self.decision_reason_input)
        layout.addWidget(self.product_picker)
        layout.addLayout(form_layout)

        button_row = QHBoxLayout()
        create_button = QPushButton("Create Recipe")
        attach_button = QPushButton("Attach Selected Asset")
        preview_button = QPushButton("Build Preview")
        approve_output_button = QPushButton("Approve Output")
        approve_recipe_button = QPushButton("Approve Recipe")
        reject_recipe_button = QPushButton("Reject Recipe")
        final_render_button = QPushButton("Build Final")
        refresh_button = QPushButton("Refresh")
        create_button.clicked.connect(self._create_recipe)
        attach_button.clicked.connect(self._attach_asset)
        preview_button.clicked.connect(self._build_preview)
        approve_output_button.clicked.connect(self._approve_output)
        approve_recipe_button.clicked.connect(self._approve_recipe)
        reject_recipe_button.clicked.connect(self._reject_recipe)
        final_render_button.clicked.connect(self._build_final)
        refresh_button.clicked.connect(self._view_model.load)
        button_row.addWidget(create_button)
        button_row.addWidget(attach_button)
        button_row.addWidget(preview_button)
        button_row.addWidget(approve_output_button)
        button_row.addWidget(approve_recipe_button)
        button_row.addWidget(reject_recipe_button)
        button_row.addWidget(final_render_button)
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
        hint_label = QLabel("Select one recipe here to load its items, outputs, and decision history into the review workspace.")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)
        self.recipe_table = QTableWidget(0, 11)
        self.recipe_table.setHorizontalHeaderLabels(
            ["ID", "Product", "Code", "Platform", "Ratio", "Status", "Decision By", "Decision At", "Items", "Score", "Dup Risk"]
        )
        self._configure_table(self.recipe_table, minimum_height=self.RECIPE_TABLE_MIN_HEIGHT)
        self.recipe_table.itemSelectionChanged.connect(self._handle_recipe_selection)
        layout.addWidget(self.recipe_table)
        return group

    def _build_asset_group(self) -> QGroupBox:
        group = QGroupBox("Ready Assets (Status = ready)")
        layout = QVBoxLayout(group)
        self.assets_hint_label = QLabel(
            "Only assets that are already in status 'ready' appear here. If an asset is missing, check the Assets screen and confirm it finished intake/analysis first."
        )
        self.assets_hint_label.setWordWrap(True)
        layout.addWidget(self.assets_hint_label)
        self.assets_table = QTableWidget(0, 5)
        self.assets_table.setHorizontalHeaderLabels(["ID", "Product", "Code", "Type", "Status"])
        self._configure_table(self.assets_table, minimum_height=self.ASSETS_TABLE_MIN_HEIGHT)
        self.assets_table.itemSelectionChanged.connect(self._refresh_role_suggestions_for_selected_asset)
        layout.addWidget(self.assets_table)
        return group

    def _build_recipe_items_group(self) -> QGroupBox:
        group = QGroupBox("Recipe Items")
        layout = QVBoxLayout(group)
        hint_label = QLabel("This is the current ingredient list for the selected recipe, including the role assigned to each attached asset.")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)
        self.recipe_items_table = QTableWidget(0, 4)
        self.recipe_items_table.setHorizontalHeaderLabels(["Item ID", "Asset ID", "Asset Code", "Role"])
        self._configure_table(self.recipe_items_table, minimum_height=self.RECIPE_ITEMS_TABLE_MIN_HEIGHT)
        layout.addWidget(self.recipe_items_table)
        return group

    def _build_outputs_group(self) -> QGroupBox:
        group = QGroupBox("Recipe Outputs")
        layout = QVBoxLayout(group)
        outputs_hint = QLabel(
            "Review preview/final outputs here, inspect render evidence below, and confirm the decision trail before approval."
        )
        outputs_hint.setWordWrap(True)
        layout.addWidget(outputs_hint)
        self.outputs_table = QTableWidget(0, 11)
        self.outputs_table.setHorizontalHeaderLabels(
            ["Output ID", "Kind", "Code", "Aftercare", "Approved", "Approved By", "Approved At", "Created", "Job Code", "Source", "Path"]
        )
        self._configure_table(self.outputs_table, minimum_height=self.OUTPUTS_TABLE_MIN_HEIGHT)
        self.outputs_table.itemSelectionChanged.connect(self._refresh_selected_output_details)
        self.output_details_text = QTextEdit()
        self.output_details_text.setReadOnly(True)
        self.output_details_text.setMinimumHeight(self.OUTPUT_DETAILS_MIN_HEIGHT)
        self.decision_history_table = QTableWidget(0, 5)
        self.decision_history_table.setHorizontalHeaderLabels(["At", "Event", "Actor", "Target", "Reason"])
        self._configure_table(self.decision_history_table, minimum_height=self.DECISION_HISTORY_MIN_HEIGHT)
        layout.addWidget(self.outputs_table)
        layout.addWidget(self.output_details_text)
        layout.addWidget(QLabel("Decision History"))
        layout.addWidget(self.decision_history_table)
        return group

    def _configure_table(self, table: QTableWidget, *, minimum_height: int) -> None:
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        table.setMinimumHeight(minimum_height)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

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
                recipe.status,
                recipe.decision_actor or "",
                recipe.decision_at or "",
                str(recipe.item_count),
                f"{recipe.recipe_score:.3f}",
                f"{recipe.duplicate_risk:.3f}",
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
        self._refresh_role_suggestions_for_selected_asset()

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
        self._refresh_role_suggestions_for_selected_asset()

    def _refresh_outputs_table(self) -> None:
        aftercare = assess_recipe_aftercare(self._view_model.decision_events, self._view_model.outputs)
        self.outputs_table.setRowCount(len(self._view_model.outputs))
        for row_index, output in enumerate(self._view_model.outputs):
            values = [
                str(output.output_id),
                output.output_kind,
                output.output_code,
                format_output_aftercare_state(output, aftercare),
                "Yes" if output.approved else "No",
                output.approved_by or "",
                output.approved_at or "",
                output.created_at,
                output.rendering_job_code or "",
                output.source_output_code or "",
                output.file_path,
            ]
            for column_index, value in enumerate(values):
                self.outputs_table.setItem(row_index, column_index, QTableWidgetItem(value))
        self._refresh_aftercare_guidance()
        self._refresh_selected_output_details()

    def _refresh_decision_history_table(self) -> None:
        self.decision_history_table.setRowCount(len(self._view_model.decision_events))
        for row_index, event in enumerate(self._view_model.decision_events):
            values = [
                event.created_at,
                self._format_event_label(event.event_type),
                event.actor,
                self._format_event_target(event.output_id, event.output_code),
                event.reason or "",
            ]
            for column_index, value in enumerate(values):
                self.decision_history_table.setItem(row_index, column_index, QTableWidgetItem(value))
        self._refresh_aftercare_guidance()

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

    def _selected_output_id(self) -> int | None:
        selected_items = self.outputs_table.selectedItems()
        if not selected_items:
            return None
        return int(self.outputs_table.item(selected_items[0].row(), 0).text())

    def _selected_asset_type(self) -> str | None:
        selected_items = self.assets_table.selectedItems()
        if not selected_items:
            return None
        asset_type_item = self.assets_table.item(selected_items[0].row(), 3)
        if asset_type_item is None:
            return None
        return asset_type_item.text().strip() or None

    def _refresh_role_suggestions_for_selected_asset(self) -> None:
        asset_type = self._selected_asset_type()
        self._set_role_suggestions(asset_type, auto_select=asset_type is not None)

    def _current_recipe_roles(self) -> tuple[str, ...]:
        return tuple(item.role for item in self._view_model.recipe_items)

    def _planned_segment_roles(self) -> tuple[str, ...]:
        composition_plan = self._view_model.composition_plan
        if composition_plan is None or not composition_plan.segments:
            return self.SEMANTIC_VISUAL_ROLES
        return tuple(segment.segment_type for segment in composition_plan.segments)

    def _remaining_planned_visual_roles(self, base_suggestions: tuple[str, ...]) -> tuple[str, ...]:
        planned_roles = tuple(
            role for role in self._planned_segment_roles() if role in self.SEMANTIC_VISUAL_ROLES and role in base_suggestions
        )
        used_counts = Counter(role for role in self._current_recipe_roles() if role in planned_roles)
        remaining_planned = []
        for role in planned_roles:
            if used_counts[role] > 0:
                used_counts[role] -= 1
                continue
            remaining_planned.append(role)
        return tuple(remaining_planned)

    def _ordered_role_suggestions(self, asset_type: str | None) -> tuple[str, ...]:
        base_suggestions = self.ROLE_SUGGESTIONS_BY_ASSET_TYPE.get(asset_type, self.DEFAULT_ATTACH_ROLES)
        if asset_type not in {"background_video", "foreground_video"}:
            return base_suggestions
        planned_roles = tuple(
            role for role in self._planned_segment_roles() if role in self.SEMANTIC_VISUAL_ROLES and role in base_suggestions
        )
        remaining_planned = list(self._remaining_planned_visual_roles(base_suggestions))
        if not remaining_planned:
            extra_roles = [role for role in base_suggestions if role not in planned_roles]
            completed_roles = [role for role in base_suggestions if role in planned_roles]
            return tuple(extra_roles + completed_roles)
        trailing_roles = [role for role in base_suggestions if role not in remaining_planned]
        return tuple(remaining_planned + trailing_roles)

    def _build_role_guidance_text(self, asset_type: str | None, suggestions: tuple[str, ...]) -> str:
        if asset_type is None:
            return "Role guidance: Select a recipe and asset to get a suggested role."
        if not suggestions:
            return f"Role guidance: No role suggestions are available for asset type `{asset_type}`."
        if asset_type == "voiceover":
            return "Role guidance: Voiceover assets should normally be attached as `voice`."
        if asset_type == "background_music":
            return "Role guidance: Background music assets should normally be attached as `music`."
        if asset_type in {"background_video", "foreground_video"}:
            planned_roles = self._planned_segment_roles()
            current_roles = self._current_recipe_roles()
            remaining_segment_roles = list(
                self._remaining_planned_visual_roles(self.ROLE_SUGGESTIONS_BY_ASSET_TYPE.get(asset_type, self.DEFAULT_ATTACH_ROLES))
            )
            if remaining_segment_roles:
                sequence_text = " -> ".join(planned_roles)
                next_role = remaining_segment_roles[0]
                attached_text = ", ".join(current_roles) if current_roles else "none yet"
                return (
                    f"Role guidance: Next suggested visual role is `{next_role}` based on the current segment flow "
                    f"`{sequence_text}`. Attached roles so far: {attached_text}."
                )
            return (
                "Role guidance: Planned segment roles are already covered, so use extra visual roles such as "
                f"`{suggestions[0]}` for additional coverage."
            )
        return f"Role guidance: Suggested role for `{asset_type}` is `{suggestions[0]}`."

    def _set_role_suggestions(self, asset_type: str | None, *, auto_select: bool = False) -> None:
        suggestions = self._ordered_role_suggestions(asset_type)
        current_text = self.role_input.currentText().strip()
        self.role_input.blockSignals(True)
        self.role_input.clear()
        self.role_input.addItems(suggestions)
        self.role_input.setCurrentIndex(-1)
        if auto_select and suggestions:
            self.role_input.setCurrentText(suggestions[0])
        elif current_text:
            if current_text not in suggestions:
                self.role_input.addItem(current_text)
            self.role_input.setCurrentText(current_text)
        self.role_input.blockSignals(False)
        self.role_hint_label.setText(self._build_role_guidance_text(asset_type, suggestions))

    def _refresh_selected_output_details(self) -> None:
        output_id = self._selected_output_id()
        if output_id is None:
            self.output_details_text.setPlainText("Select an output to inspect lineage and render details.")
            return
        output = self._view_model.find_output(output_id)
        if output is None:
            self.output_details_text.setPlainText("Selected output details are unavailable.")
            return
        self.output_details_text.setPlainText(
            "\n".join(
                build_output_detail_lines(output, self._view_model.composition_plan, self._view_model.decision_events)
            )
        )

    def _refresh_aftercare_guidance(self) -> None:
        self.aftercare_label.setText(
            build_aftercare_guidance(assess_recipe_aftercare(self._view_model.decision_events, self._view_model.outputs))
        )

    def _format_event_label(self, event_type: str) -> str:
        return event_type.replace("_", " ").title()

    def _format_event_target(self, output_id: int | None, output_code: str | None) -> str:
        if output_id is None:
            return "Recipe"
        if output_code:
            return f"Output #{output_id} | {output_code}"
        return f"Output #{output_id}"

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
                role=self.role_input.currentText(),
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

    def _approve_output(self) -> None:
        output_id = self._selected_output_id()
        if output_id is None:
            QMessageBox.warning(self, "Approve Output", "Select an output first.")
            return
        try:
            self._view_model.approve_output(
                output_id,
                actor=self.decision_actor_input.text(),
                reason=self.decision_reason_input.text() or None,
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Approve Output", str(exc))

    def _approve_recipe(self) -> None:
        recipe_id = self._selected_recipe_id()
        if recipe_id is None:
            QMessageBox.warning(self, "Approve Recipe", "Select a recipe first.")
            return
        try:
            self._view_model.approve_recipe(
                recipe_id,
                actor=self.decision_actor_input.text(),
                reason=self.decision_reason_input.text() or None,
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Approve Recipe", str(exc))

    def _reject_recipe(self) -> None:
        recipe_id = self._selected_recipe_id()
        if recipe_id is None:
            QMessageBox.warning(self, "Reject Recipe", "Select a recipe first.")
            return
        try:
            self._view_model.reject_recipe(
                recipe_id,
                actor=self.decision_actor_input.text(),
                reason=self.decision_reason_input.text() or None,
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Reject Recipe", str(exc))

    def _build_final(self) -> None:
        recipe_id = self._selected_recipe_id()
        if recipe_id is None:
            QMessageBox.warning(self, "Build Final", "Select a recipe first.")
            return
        try:
            self._view_model.queue_final_render(recipe_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Build Final", str(exc))

    def _handle_recipe_selection(self) -> None:
        self._view_model.select_recipe(self._selected_recipe_id())
        self._refresh_role_suggestions_for_selected_asset()
