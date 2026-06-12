from __future__ import annotations

import json
from pathlib import Path

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

from mt_clip_factory.presentation.factory.recipe_builder import RecipeBuilderViewModel
from mt_clip_factory.ui.theme import apply_theme


class RecipeBuilderWindow(QMainWindow):
    THEME_NAME = "app_window"

    def __init__(self, view_model: RecipeBuilderViewModel) -> None:
        super().__init__()
        self._view_model = view_model
        self.setWindowTitle("MTClipFactory - Video Assembly Factory")
        self.resize(1280, 760)
        apply_theme(self, self.THEME_NAME)

        central = QWidget(self)
        layout = QGridLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(16)
        layout.addWidget(self._build_recipe_group(), 0, 0)
        layout.addWidget(self._build_recipe_table_group(), 0, 1)
        layout.addWidget(self._build_asset_group(), 1, 0)
        layout.addWidget(self._build_recipe_items_group(), 1, 1)
        layout.addWidget(self._build_outputs_group(), 2, 0, 1, 2)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
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
        self.decision_actor_input = QLineEdit()
        self.decision_reason_input = QLineEdit()
        self.role_input.setPlaceholderText("hero, hook, broll, cta")
        self.decision_actor_input.setPlaceholderText("operator, editor, qa")
        self.decision_reason_input.setPlaceholderText("optional decision note")
        form_layout.addRow("Recipe Code", self.recipe_code_input)
        form_layout.addRow("Target Platform", self.platform_input)
        form_layout.addRow("Target Ratio", self.ratio_input)
        form_layout.addRow("Attach Role", self.role_input)
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
        self.recipe_table = QTableWidget(0, 11)
        self.recipe_table.setHorizontalHeaderLabels(
            ["ID", "Product", "Code", "Platform", "Ratio", "Status", "Decision By", "Decision At", "Items", "Score", "Dup Risk"]
        )
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

    def _build_outputs_group(self) -> QGroupBox:
        group = QGroupBox("Recipe Outputs")
        layout = QVBoxLayout(group)
        self.outputs_table = QTableWidget(0, 10)
        self.outputs_table.setHorizontalHeaderLabels(
            ["Output ID", "Kind", "Code", "Approved", "Approved By", "Approved At", "Created", "Job Code", "Source", "Path"]
        )
        self.outputs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.outputs_table.setSelectionMode(QTableWidget.SingleSelection)
        self.outputs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.outputs_table.horizontalHeader().setStretchLastSection(True)
        self.outputs_table.itemSelectionChanged.connect(self._refresh_selected_output_details)
        self.output_details_text = QTextEdit()
        self.output_details_text.setReadOnly(True)
        self.decision_history_table = QTableWidget(0, 5)
        self.decision_history_table.setHorizontalHeaderLabels(["At", "Event", "Actor", "Target", "Reason"])
        self.decision_history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.decision_history_table.setSelectionMode(QTableWidget.SingleSelection)
        self.decision_history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.decision_history_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.outputs_table)
        layout.addWidget(self.output_details_text)
        layout.addWidget(QLabel("Decision History"))
        layout.addWidget(self.decision_history_table)
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

    def _refresh_outputs_table(self) -> None:
        self.outputs_table.setRowCount(len(self._view_model.outputs))
        for row_index, output in enumerate(self._view_model.outputs):
            values = [
                str(output.output_id),
                output.output_kind,
                output.output_code,
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
                _build_output_detail_lines(output, self._view_model.composition_plan)
            )
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


def _build_output_detail_lines(output, composition_plan) -> list[str]:
    lines = [
        f"Output ID: {output.output_id}",
        f"Recipe: {output.recipe_code} (#{output.recipe_id})",
        f"Kind: {output.output_kind}",
        f"Approved: {output.approved}",
        f"Approved By: {output.approved_by or '-'}",
        f"Approved At: {output.approved_at or '-'}",
        f"Approval Reason: {output.approval_reason or '-'}",
        f"Created At: {output.created_at}",
        f"Platform: {output.platform or '-'}",
        f"Ratio: {output.ratio or '-'}",
        f"Render Job Code: {output.rendering_job_code or '-'}",
        f"Manifest Path: {output.manifest_path or '-'}",
        f"Source Output ID: {output.source_output_id or '-'}",
        f"Source Output Code: {output.source_output_code or '-'}",
        f"Source Output Path: {output.source_output_path or '-'}",
        f"Quality Score: {output.quality_score if output.quality_score is not None else '-'}",
        f"Duplicate Risk: {output.duplicate_risk if output.duplicate_risk is not None else '-'}",
        f"File Path: {output.file_path}",
    ]
    if composition_plan is None:
        return lines
    lines.extend(
        [
            "",
            f"Composition Plan ID: {composition_plan.plan_id}",
            f"Duration Source: {composition_plan.duration_source}",
            f"Resolved Duration: {composition_plan.resolved_duration_sec or '-'}",
            f"Timeline Segments: {len(composition_plan.segments)}",
            f"Render Decisions: {len(composition_plan.decisions)}",
        ]
    )
    for segment in composition_plan.segments:
        lines.append(
            f"- Segment {segment.sequence_index}: {segment.segment_type} "
            f"{segment.start_sec:.3f}-{segment.end_sec:.3f}s | audio={segment.audio_policy or '-'}"
        )
    for decision in composition_plan.decisions[:6]:
        lines.append(
            f"- Decision: {decision.decision_type} -> {decision.action}"
            f"{f' | role={decision.asset_role}' if decision.asset_role else ''}"
        )
    if len(composition_plan.decisions) > 6:
        lines.append(f"- More Decisions: {len(composition_plan.decisions) - 6}")
    lines.extend(_build_manifest_review_lines(output.manifest_path))
    lines.extend(_build_manifest_audio_lines(output.manifest_path))
    return lines


def _build_manifest_review_lines(manifest_path: str | None) -> list[str]:
    payload = _read_manifest_payload(manifest_path)
    review_gate = payload.get("review_gate")
    if not isinstance(review_gate, dict):
        return []
    lines = [
        "",
        "Review Gate:",
        f"- Required: {review_gate.get('required', '-')}",
        f"- Duplicate Risk: {review_gate.get('duplicate_risk', '-')}",
        f"- Quality Score: {review_gate.get('quality_score', '-')}",
        f"- Summary: {review_gate.get('summary', '-')}",
    ]
    signals = review_gate.get("signals")
    if isinstance(signals, list):
        for signal in signals:
            if not isinstance(signal, dict):
                continue
            lines.append(
                f"- Signal: {signal.get('code', '-')} | value={signal.get('metric_value', '-')} | threshold={signal.get('threshold', '-')}"
            )
    metrics = review_gate.get("metrics")
    if isinstance(metrics, dict):
        for metric_name, metric_value in sorted(metrics.items()):
            lines.append(f"- Metric: {metric_name}={metric_value}")
    return lines


def _build_manifest_audio_lines(manifest_path: str | None) -> list[str]:
    payload = _read_manifest_payload(manifest_path)
    audio_mix = payload.get("audio_mix")
    if not isinstance(audio_mix, dict):
        return []
    lines = [
        "",
        "Runtime Audio Mix:",
        f"- Mode: {audio_mix.get('mode', '-')}",
        f"- Audio Present: {audio_mix.get('audio_present', '-')}",
        f"- Voice Loop Applied: {audio_mix.get('voice_loop_applied', '-')}",
    ]
    mix_balance = audio_mix.get("mix_balance")
    if isinstance(mix_balance, dict):
        lines.append(f"- Mix Strategy: {mix_balance.get('strategy', '-')}")
        lines.append(f"- Voice Mix Gain (dB): {mix_balance.get('voice_mix_gain_db', '-')}")
        lines.append(f"- Music Mix Gain (dB): {mix_balance.get('music_mix_gain_db', '-')}")
    ducking = audio_mix.get("ducking")
    if isinstance(ducking, dict):
        lines.append(f"- Duck Applied: {ducking.get('applied', '-')}")
        lines.append(f"- Duck Mode: {ducking.get('mode', ducking.get('reason', '-'))}")
        if ducking.get("duck_db") is not None:
            lines.append(f"- Duck Gain (dB): {ducking.get('duck_db')}")
        if ducking.get("threshold_db") is not None:
            lines.append(f"- Duck Threshold (dB): {ducking.get('threshold_db')}")
        if ducking.get("ratio") is not None:
            lines.append(f"- Duck Ratio: {ducking.get('ratio')}")
    voice_tracks = audio_mix.get("voice_tracks")
    music_tracks = audio_mix.get("music_tracks")
    if isinstance(voice_tracks, list):
        lines.append(f"- Voice Track Count: {len(voice_tracks)}")
    if isinstance(music_tracks, list):
        lines.append(f"- Music Track Count: {len(music_tracks)}")
    return lines


def _read_manifest_payload(manifest_path: str | None) -> dict:
    if not manifest_path:
        return {}
    manifest_file = Path(manifest_path)
    if not manifest_file.exists():
        return {}
    try:
        payload = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}
