from __future__ import annotations

import json
from dataclasses import dataclass

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

ORDER_RISK_FILTER_ALL = "all"
ORDER_RISK_FILTER_HIGH_ONLY = "high_only"
ORDER_RISK_FILTER_MEDIUM_AND_HIGH = "medium_and_high"
ORDER_RISK_FILTER_LOW_AND_HIGHER = "low_and_higher"
ORDER_RISK_FILTER_UNAVAILABLE_ONLY = "unavailable_only"

ORDER_PRODUCT_SORT_PRODUCT_CODE = "product_code"
ORDER_PRODUCT_SORT_RISK_DESC = "risk_desc"
ORDER_PRODUCT_SORT_STATUS_THEN_RISK = "status_then_risk"

ORDER_STAGE_SORT_SEQUENCE = "sequence"
ORDER_STAGE_SORT_RISK_DESC = "risk_desc"
ORDER_STAGE_SORT_RISK_ASC = "risk_asc"

_RISK_LEVEL_HIGH = "High"
_RISK_LEVEL_MEDIUM = "Medium"
_RISK_LEVEL_LOW = "Low"
_RISK_LEVEL_UNAVAILABLE = "Unavailable"


@dataclass(slots=True, frozen=True)
class OrderProductRiskRow:
    product_code: str
    requested_outputs: int
    last_stage: str
    status: str
    risk_level: str
    risk_score: float | None


@dataclass(slots=True, frozen=True)
class OrderStageRiskRow:
    sequence_index: int
    stage_name: str
    stage_scope: str
    status: str
    production_order_item_id: int | None
    recipe_id: int | None
    job_id: int | None
    failure_class: str
    risk_level: str
    risk_score: float | None
    risk_reasons: str


def format_product_request_summary(request) -> str:
    summary = (
        f"- {request.product_code}: requested={request.requested_output_count}, "
        f"platform={request.target_platform or 'default'}, ratio={request.target_ratio or 'default'}, "
        f"duration_mode={request.duration_mode}, creative_preset_mode={request.creative_preset_mode}"
    )
    if request.creative_preset_codes:
        summary = f"{summary}, preset_codes={', '.join(request.creative_preset_codes)}"
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


def build_run_mode_hint(run_mode: str, *, run_modes) -> str:
    hints = {
        run_modes.RUN_MODE_AUDIT_ONLY: (
            "Audit reads product-folder contracts, tags, and asset readiness without creating products or orders. "
            "Use this first when checking whether pipeline/tag/caption inputs are safe."
        ),
        run_modes.RUN_MODE_INTAKE_ONLY: (
            "Intake registers deterministic assets and writes product-local run evidence without creating a production order. "
            "Use this when you want the library synced before preview/render work."
        ),
        run_modes.RUN_MODE_MATERIALIZE: (
            "Materialize runs intake first, then creates one persisted production order and materializes recipe work."
        ),
        run_modes.RUN_MODE_MATERIALIZE_AND_PREVIEWS: (
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


def build_preflight_product_detail_text(product_report) -> str:
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
                f"- Fixed Duration Sec: {format_optional_number(pipeline_config.fixed_duration_sec)}",
                f"- Min/Max Duration Sec: {pipeline_config.min_duration_sec} / {pipeline_config.max_duration_sec}",
                f"- Selection Tags: {format_selection_tag_summary(pipeline_config)}",
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
                f"- Main Preset / Font: {join_optional(caption_contract.main_style_preset, caption_contract.main_font_family)}",
                f"- Sub Preset / Font: {join_optional(caption_contract.sub_style_preset, caption_contract.sub_font_family)}",
            ]
        )

    creative_preset_contract = product_report.creative_preset_contract
    if creative_preset_contract is not None:
        lines.extend(
            [
                "",
                "Creative Preset Contract:",
                f"- Presets: {creative_preset_contract.enabled_preset_count} enabled / {creative_preset_contract.preset_count} total",
                f"- Preset Codes: {', '.join(creative_preset_contract.preset_codes) or '-'}",
                f"- Platforms: {creative_preset_contract.platform_count}",
                f"- Ratios: {creative_preset_contract.ratio_count}",
                f"- Headline Pools: {creative_preset_contract.headline_pool_name_count}",
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


def build_run_product_detail_text(
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
                f"- Fixed Duration Sec: {format_optional_number(request.fixed_duration_sec)}",
                f"- Min/Max Duration Sec: {request.min_duration_sec} / {request.max_duration_sec}",
                f"- Creative Preset Mode: {request.creative_preset_mode}",
                f"- Creative Preset Codes: {', '.join(request.creative_preset_codes) or '-'}",
                f"- Selection Tags: {format_selection_tag_summary(request)}",
            ]
        )

    lines.extend(["", "Asset Intake Actions:"])
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


def build_progress_summary_text(snapshot) -> str:
    lines = [
        f"Run State: {snapshot.run_state}",
        f"Phase: {snapshot.phase}",
        f"Run Mode: {snapshot.run_mode or '-'}",
        f"Root Folder: {snapshot.root_folder or '-'}",
        f"Batch Code: {snapshot.batch_code or '-'}",
        f"Monitored Order ID: {snapshot.monitored_order_id or '-'}",
        f"Monitored Order Code: {snapshot.monitored_order_code or '-'}",
        f"Order Status: {snapshot.order_status or '-'}",
        f"Current Stage: {snapshot.current_stage or '-'}",
        f"Lease Owner: {snapshot.lease_owner or '-'}",
        f"Lease State: {snapshot.lease_state}",
        f"Lease Heartbeat: {snapshot.lease_heartbeat_at or '-'}",
        f"Lease Expires: {snapshot.lease_expires_at or '-'}",
        f"Recovery State: {snapshot.recovery_state}",
        f"Suggested Action: {snapshot.suggested_action}",
        f"Products Requested: {snapshot.total_products}",
        f"Products With Stage Activity: {snapshot.products_with_stage_activity}",
        f"Requested Outputs: {snapshot.total_requested_outputs}",
        f"Materialized Recipes: {snapshot.materialized_recipe_count}",
        f"Previews Completed: {snapshot.preview_completed_count}",
        f"Review Required: {snapshot.review_required_count}",
        f"Recorded Stages: {snapshot.stage_count}",
        f"Active Workers: {snapshot.active_worker_count}",
        f"Started At: {snapshot.started_at or '-'}",
        f"Finished At: {snapshot.finished_at or '-'}",
        f"Last Event: {snapshot.last_event or '-'}",
    ]
    if snapshot.blocking_reason:
        lines.append(f"Blocking Reason: {snapshot.blocking_reason}")
    lines.extend(["", "Operator Controls:", snapshot.command_note])
    return "\n".join(lines)


def build_order_summary_text(order) -> str:
    planner_risk_scores: list[float] = []
    planner_risk_reasons: list[str] = []
    creative_preset_codes: list[str] = []
    creative_preset_signatures: list[str] = []
    render_risk_scores: list[float] = []
    render_history_scopes: list[str] = []
    render_signal_codes: list[str] = []
    render_clip_formula_hashes: list[str] = []
    for stage in _effective_order_stages(order.stages):
        if stage.stage_name == "materialize" and stage.status == "succeeded":
            stage_score = _stage_near_duplicate_score(stage.detail_json)
            if stage_score is not None:
                planner_risk_scores.append(stage_score)
            planner_risk_reasons.extend(_stage_near_duplicate_reasons(stage.detail_json))
            preset_code = _stage_creative_preset_code(stage.detail_json)
            if preset_code:
                creative_preset_codes.append(preset_code)
            preset_signature = _stage_creative_preset_signature(stage.detail_json)
            if preset_signature:
                creative_preset_signatures.append(preset_signature)
            continue
        if stage.stage_name not in {"preview", "review"}:
            continue
        stage_score = _stage_render_duplicate_score(stage.detail_json)
        if stage_score is not None:
            render_risk_scores.append(stage_score)
        history_scope = _stage_history_scope(stage.detail_json)
        if history_scope:
            render_history_scopes.append(history_scope)
        render_signal_codes.extend(_stage_review_signal_codes(stage.detail_json))
        clip_formula_hash = _stage_clip_formula_hash(stage.detail_json)
        if clip_formula_hash:
            render_clip_formula_hashes.append(clip_formula_hash)
    max_planner_risk_score = None if not planner_risk_scores else max(planner_risk_scores)
    max_render_risk_score = None if not render_risk_scores else max(render_risk_scores)
    combined_risk_candidates = [score for score in (max_planner_risk_score, max_render_risk_score) if score is not None]
    combined_risk_score = None if not combined_risk_candidates else max(combined_risk_candidates)
    planner_risk_summary = "-" if max_planner_risk_score is None else f"max={max_planner_risk_score:.3f}, recipes={len(planner_risk_scores)}"
    render_risk_summary = "-" if max_render_risk_score is None else f"max={max_render_risk_score:.3f}, stages={len(render_risk_scores)}"
    planner_reasons_summary = ", ".join(dict.fromkeys(planner_risk_reasons)) if planner_risk_reasons else "-"
    creative_preset_summary = ", ".join(dict.fromkeys(creative_preset_codes)) if creative_preset_codes else "-"
    creative_signature_summary = ", ".join(dict.fromkeys(creative_preset_signatures)) if creative_preset_signatures else "-"
    history_scope_summary = ", ".join(dict.fromkeys(render_history_scopes)) if render_history_scopes else "-"
    render_signal_summary = ", ".join(dict.fromkeys(render_signal_codes)) if render_signal_codes else "-"
    clip_formula_summary = _summarize_clip_formula_hashes(render_clip_formula_hashes)
    risk_focus = _risk_level_label(combined_risk_score)
    return "\n".join(
        [
            f"Order ID: {order.production_order_id}",
            f"Order Code: {order.order_code}",
            f"Batch Code: {order.batch_code}",
            f"Source Mode: {order.source_mode}",
            f"Run Mode: {order.run_mode or '-'}",
            f"Source Root: {order.source_root or '-'}",
            f"Build Previews: {'yes' if order.preview_generation_enabled else 'no'}",
            f"Status: {order.status}",
            f"Lease Owner: {order.lease_owner or '-'}",
            f"Lease State: {order.lease_state}",
            f"Lease Heartbeat: {order.lease_heartbeat_at or '-'}",
            f"Lease Expires: {order.lease_expires_at or '-'}",
            f"Recovery State: {order.recovery_state}",
            f"Suggested Action: {order.suggested_action}",
            f"Blocking Reason: {order.blocking_reason or '-'}",
            f"Strict Fulfillment: {order.strict_fulfillment}",
            f"Created At: {order.created_at}",
            f"Started At: {order.started_at or 'not started'}",
            f"Finished At: {order.finished_at or 'not finished'}",
            "",
            "Duplicate-Risk Summary:",
            f"- Risk Focus: {risk_focus}",
            f"- Creative Presets: {creative_preset_summary}",
            f"- Creative Signatures: {creative_signature_summary}",
            f"- Planner Risk: {planner_risk_summary}",
            f"- Planner Reasons: {planner_reasons_summary}",
            f"- Render-History Risk: {render_risk_summary}",
            f"- History Scopes: {history_scope_summary}",
            f"- Review Signals: {render_signal_summary}",
            f"- Clip Formula Hashes: {clip_formula_summary}",
            "- Risk Legend: High >= 0.600 | Medium >= 0.250 | Low < 0.250 | Unavailable = no persisted evidence.",
            "- Interpretation: planner and render-history evidence only, not a platform verdict.",
        ]
    )


def build_order_product_rows(order) -> list[OrderProductRiskRow]:
    latest_stage_by_item_id: dict[int, object] = {}
    risk_scores_by_item_id: dict[int, list[float]] = {}
    for stage in _effective_order_stages(order.stages):
        if stage.production_order_item_id is None:
            continue
        latest_stage_by_item_id[stage.production_order_item_id] = stage
        stage_score = _stage_display_risk_score(stage)
        if stage_score is None:
            continue
        risk_scores_by_item_id.setdefault(stage.production_order_item_id, []).append(stage_score)

    rows: list[OrderProductRiskRow] = []
    for item in order.items:
        latest_stage = latest_stage_by_item_id.get(item.production_order_item_id)
        stage_scores = risk_scores_by_item_id.get(item.production_order_item_id, [])
        risk_score = None if not stage_scores else max(stage_scores)
        rows.append(
            OrderProductRiskRow(
                product_code=item.product_code,
                requested_outputs=item.requested_output_count,
                last_stage="-" if latest_stage is None else latest_stage.stage_name,
                status="queued" if latest_stage is None else latest_stage.status,
                risk_level=_risk_level_label(risk_score),
                risk_score=risk_score,
            )
        )
    return rows


def build_order_stage_rows(order) -> list[OrderStageRiskRow]:
    rows: list[OrderStageRiskRow] = []
    for stage in order.stages:
        risk_score = _stage_display_risk_score(stage)
        risk_reasons = ", ".join(_stage_display_risk_reasons(stage))
        rows.append(
            OrderStageRiskRow(
                sequence_index=stage.sequence_index,
                stage_name=stage.stage_name,
                stage_scope=stage.stage_scope,
                status=stage.status,
                production_order_item_id=stage.production_order_item_id,
                recipe_id=stage.recipe_id,
                job_id=stage.job_id,
                failure_class=stage.failure_class or "",
                risk_level=_risk_level_label(risk_score),
                risk_score=risk_score,
                risk_reasons=risk_reasons,
            )
        )
    return rows


def refresh_selected_preflight_product_details(window) -> None:  # noqa: ANN001
    preflight_report = window._view_model.preflight_report
    if preflight_report is None:
        from mt_clip_factory.ui.factory.auto_factory_control_actions import refresh_selected_product_action_state

        refresh_selected_product_action_state(window)
        return
    row_index = selected_row_index(window.preflight_products_table)
    if row_index is None or row_index >= len(preflight_report.product_reports):
        from mt_clip_factory.ui.factory.auto_factory_control_actions import refresh_selected_product_action_state

        refresh_selected_product_action_state(window)
        return
    product_report = preflight_report.product_reports[row_index]
    window.selected_product_text.setPlainText(build_preflight_product_detail_text(product_report))
    from mt_clip_factory.ui.factory.auto_factory_control_actions import refresh_selected_product_action_state

    refresh_selected_product_action_state(window)


def refresh_selected_run_product_details(window) -> None:  # noqa: ANN001
    run_report = window._view_model.run_report
    if run_report is None:
        from mt_clip_factory.ui.factory.auto_factory_control_actions import refresh_selected_product_action_state

        refresh_selected_product_action_state(window)
        return
    row_index = selected_row_index(window.product_reports_table)
    if row_index is None or row_index >= len(run_report.product_reports):
        from mt_clip_factory.ui.factory.auto_factory_control_actions import refresh_selected_product_action_state

        refresh_selected_product_action_state(window)
        return
    product_report = run_report.product_reports[row_index]
    request = next(
        (item for item in run_report.order.product_requests if item.product_code == product_report.product_code),
        None,
    )
    product_actions = [action for action in run_report.asset_actions if action.product_code == product_report.product_code]
    window.selected_product_text.setPlainText(
        build_run_product_detail_text(
            batch_code=run_report.batch_code,
            scan_depth=run_report.scan_depth,
            product_report=product_report,
            request=request,
            product_actions=product_actions,
        )
    )
    from mt_clip_factory.ui.factory.auto_factory_control_actions import refresh_selected_product_action_state

    refresh_selected_product_action_state(window)


def refresh_selected_order(window) -> None:  # noqa: ANN001
    selected_order = window._view_model.selected_order
    if selected_order is None:
        window.order_summary_text.setPlainText("No production order selected.")
        window.order_product_progress_table.setRowCount(0)
        window.order_stages_table.setRowCount(0)
        window.order_events_table.setRowCount(0)
        window._refresh_run_controls()
        return

    window.results_tabs.setCurrentWidget(window.order_stage_group)
    window.order_summary_text.setPlainText(build_order_summary_text(selected_order))
    risk_filter = str(window.order_risk_filter_combo.currentData())
    product_sort = str(window.order_product_sort_combo.currentData())
    stage_sort = str(window.order_stage_sort_combo.currentData())
    product_rows = sort_order_product_rows(
        filter_order_product_rows(build_order_product_rows(selected_order), risk_filter=risk_filter),
        sort_mode=product_sort,
    )
    window.order_product_progress_table.setRowCount(len(product_rows))
    for row_index, row in enumerate(product_rows):
        values = [
            row.product_code,
            str(row.requested_outputs),
            row.last_stage,
            row.status,
            row.risk_level,
            _format_risk_score(row.risk_score),
        ]
        for column_index, value in enumerate(values):
            item = QTableWidgetItem(value)
            _apply_risk_item_emphasis(item, row.risk_level)
            window.order_product_progress_table.setItem(row_index, column_index, item)
    stage_rows = sort_order_stage_rows(
        filter_order_stage_rows(build_order_stage_rows(selected_order), risk_filter=risk_filter),
        sort_mode=stage_sort,
    )
    window.order_stages_table.setRowCount(len(stage_rows))
    for row_index, row in enumerate(stage_rows):
        values = [
            str(row.sequence_index),
            row.stage_name,
            row.stage_scope,
            row.status,
            str(row.production_order_item_id or ""),
            str(row.recipe_id or ""),
            str(row.job_id or ""),
            row.failure_class,
            row.risk_level,
            _format_risk_score(row.risk_score),
            row.risk_reasons,
        ]
        for column_index, value in enumerate(values):
            item = QTableWidgetItem(value)
            _apply_risk_item_emphasis(item, row.risk_level)
            window.order_stages_table.setItem(row_index, column_index, item)
    window.order_events_table.setRowCount(len(selected_order.events))
    for row_index, event in enumerate(selected_order.events):
        values = [
            str(event.sequence_index),
            event.event_type,
            event.status,
            event.stage_name or "",
            event.message,
        ]
        for column_index, value in enumerate(values):
            window.order_events_table.setItem(row_index, column_index, QTableWidgetItem(value))
    window._refresh_run_controls()


def refresh_recent_orders(window) -> None:  # noqa: ANN001
    orders = window._view_model.recent_orders
    current_order_id = window._view_model.selected_order.production_order_id if window._view_model.selected_order else None
    window.recent_orders_table.blockSignals(True)
    window.recent_orders_table.setRowCount(len(orders))
    for row_index, order in enumerate(orders):
        values = [
            str(order.production_order_id),
            order.order_code,
            order.batch_code,
            order.status,
            order.recovery_state,
            order.suggested_action,
            order.risk_level,
            _format_risk_score(order.max_duplicate_truth_score),
            str(order.item_count),
            order.source_mode,
            order.started_at or "",
            order.finished_at or "",
        ]
        for column_index, value in enumerate(values):
            item = QTableWidgetItem(value)
            _apply_risk_item_emphasis(item, order.risk_level)
            window.recent_orders_table.setItem(row_index, column_index, item)
        if current_order_id is not None and order.production_order_id == current_order_id:
            window.recent_orders_table.selectRow(row_index)
    window.recent_orders_table.blockSignals(False)
    window._refresh_run_controls()


def selected_row_index(table: QTableWidget) -> int | None:
    selected_items = table.selectedItems()
    if not selected_items:
        return None
    return selected_items[0].row()


def select_first_row(table: QTableWidget) -> None:
    if table.rowCount() > 0 and not table.selectedItems():
        table.selectRow(0)


def _effective_order_stages(stages: tuple[object, ...]) -> tuple[object, ...]:
    latest_by_key: dict[tuple[object, ...], object] = {}
    for stage in stages:
        latest_by_key[_effective_stage_key(stage)] = stage
    return tuple(sorted(latest_by_key.values(), key=lambda item: (item.sequence_index, item.production_order_stage_id)))


def _effective_stage_key(stage) -> tuple[object, ...]:  # noqa: ANN001
    recipe_code = _stage_detail_value(stage.detail_json, "recipe_code")
    if stage.stage_name == "materialize":
        return (stage.stage_name, stage.production_order_item_id, stage.recipe_id or recipe_code)
    if stage.stage_name in {"preview", "review"}:
        return (stage.stage_name, stage.recipe_id or stage.production_order_item_id)
    return (
        stage.stage_name,
        stage.stage_scope,
        stage.production_order_item_id,
        stage.recipe_id,
        stage.output_id,
        recipe_code,
    )


def _stage_detail_value(detail_json: str | None, key: str) -> object | None:
    if not detail_json:
        return None
    try:
        payload = json.loads(detail_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload.get(key)


def _stage_near_duplicate_score(detail_json: str | None) -> float | None:
    value = _stage_detail_value(detail_json, "near_duplicate_score")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stage_near_duplicate_reasons(detail_json: str | None) -> tuple[str, ...]:
    value = _stage_detail_value(detail_json, "near_duplicate_reasons")
    if not isinstance(value, list):
        return ()
    return tuple(reason for reason in value if isinstance(reason, str) and reason.strip())


def _stage_render_duplicate_score(detail_json: str | None) -> float | None:
    value = _stage_detail_value(detail_json, "duplicate_risk")
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stage_creative_preset_code(detail_json: str | None) -> str | None:
    value = _stage_detail_value(detail_json, "creative_preset_code")
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _stage_creative_preset_signature(detail_json: str | None) -> str | None:
    value = _stage_detail_value(detail_json, "creative_preset_signature")
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _stage_history_scope(detail_json: str | None) -> str | None:
    value = _stage_detail_value(detail_json, "history_scope")
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _stage_clip_formula_hash(detail_json: str | None) -> str | None:
    value = _stage_detail_value(detail_json, "clip_formula_hash")
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _stage_review_signal_codes(detail_json: str | None) -> tuple[str, ...]:
    value = _stage_detail_value(detail_json, "review_signal_codes")
    if not isinstance(value, list):
        return ()
    return tuple(code.strip() for code in value if isinstance(code, str) and code.strip())


def _stage_display_risk_score(stage) -> float | None:  # noqa: ANN001
    return _stage_near_duplicate_score(stage.detail_json) if stage.stage_name == "materialize" else _stage_render_duplicate_score(stage.detail_json)


def _stage_display_risk_reasons(stage) -> tuple[str, ...]:  # noqa: ANN001
    parts: list[str] = []
    if stage.stage_name == "materialize":
        parts.extend(_stage_near_duplicate_reasons(stage.detail_json))
    signal_codes = _stage_review_signal_codes(stage.detail_json)
    if signal_codes:
        parts.extend(signal_codes)
    history_scope = _stage_history_scope(stage.detail_json)
    if history_scope is not None:
        parts.append(f"history_scope:{history_scope}")
    clip_formula_hash = _stage_clip_formula_hash(stage.detail_json)
    if clip_formula_hash is not None:
        parts.append(f"clip_formula_hash:{clip_formula_hash[:12]}")
    render_duplicate_score = _stage_render_duplicate_score(stage.detail_json)
    if (
        stage.stage_name in {"preview", "review"}
        and render_duplicate_score is not None
        and render_duplicate_score > 0.0
        and not signal_codes
    ):
        parts.append("render_duplicate_risk")
    return tuple(dict.fromkeys(parts))


def _summarize_clip_formula_hashes(values: list[str]) -> str:
    if not values:
        return "-"
    unique_values = list(dict.fromkeys(values))
    preview = ", ".join(value[:12] for value in unique_values[:3])
    if len(unique_values) > 3:
        return f"{preview} (+{len(unique_values) - 3} more)"
    return preview


def filter_order_product_rows(
    rows: list[OrderProductRiskRow],
    *,
    risk_filter: str,
) -> list[OrderProductRiskRow]:
    return [row for row in rows if _matches_risk_filter(row.risk_level, risk_filter)]


def sort_order_product_rows(
    rows: list[OrderProductRiskRow],
    *,
    sort_mode: str,
) -> list[OrderProductRiskRow]:
    if sort_mode == ORDER_PRODUCT_SORT_RISK_DESC:
        return sorted(
            rows,
            key=lambda row: (
                -_risk_level_priority(row.risk_level),
                float("-inf") if row.risk_score is None else -row.risk_score,
                row.product_code,
            ),
        )
    if sort_mode == ORDER_PRODUCT_SORT_STATUS_THEN_RISK:
        return sorted(
            rows,
            key=lambda row: (row.status, -_risk_level_priority(row.risk_level), -(row.risk_score or 0.0), row.product_code),
        )
    return sorted(rows, key=lambda row: row.product_code)


def filter_order_stage_rows(
    rows: list[OrderStageRiskRow],
    *,
    risk_filter: str,
) -> list[OrderStageRiskRow]:
    return [row for row in rows if _matches_risk_filter(row.risk_level, risk_filter)]


def sort_order_stage_rows(
    rows: list[OrderStageRiskRow],
    *,
    sort_mode: str,
) -> list[OrderStageRiskRow]:
    if sort_mode == ORDER_STAGE_SORT_RISK_DESC:
        return sorted(
            rows,
            key=lambda row: (
                -_risk_level_priority(row.risk_level),
                float("-inf") if row.risk_score is None else -row.risk_score,
                row.sequence_index,
            ),
        )
    if sort_mode == ORDER_STAGE_SORT_RISK_ASC:
        return sorted(
            rows,
            key=lambda row: (
                _risk_level_priority(row.risk_level),
                float("inf") if row.risk_score is None else row.risk_score,
                row.sequence_index,
            ),
        )
    return sorted(rows, key=lambda row: row.sequence_index)


def format_selection_tag_summary(config) -> str:
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


def format_optional_number(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:g}"


def join_optional(left: str | None, right: str | None) -> str:
    if left and right:
        return f"{left} / {right}"
    return left or right or "-"


def _risk_level_label(score: float | None) -> str:
    if score is None:
        return _RISK_LEVEL_UNAVAILABLE
    if score >= 0.6:
        return _RISK_LEVEL_HIGH
    if score >= 0.25:
        return _RISK_LEVEL_MEDIUM
    return _RISK_LEVEL_LOW


def _risk_level_priority(level: str) -> int:
    return {
        _RISK_LEVEL_HIGH: 3,
        _RISK_LEVEL_MEDIUM: 2,
        _RISK_LEVEL_LOW: 1,
        _RISK_LEVEL_UNAVAILABLE: 0,
    }.get(level, 0)


def _matches_risk_filter(level: str, risk_filter: str) -> bool:
    if risk_filter == ORDER_RISK_FILTER_HIGH_ONLY:
        return level == _RISK_LEVEL_HIGH
    if risk_filter == ORDER_RISK_FILTER_MEDIUM_AND_HIGH:
        return level in {_RISK_LEVEL_HIGH, _RISK_LEVEL_MEDIUM}
    if risk_filter == ORDER_RISK_FILTER_LOW_AND_HIGHER:
        return level in {_RISK_LEVEL_HIGH, _RISK_LEVEL_MEDIUM, _RISK_LEVEL_LOW}
    if risk_filter == ORDER_RISK_FILTER_UNAVAILABLE_ONLY:
        return level == _RISK_LEVEL_UNAVAILABLE
    return True


def _format_risk_score(score: float | None) -> str:
    return "-" if score is None else f"{score:.3f}"


def _apply_risk_item_emphasis(item: QTableWidgetItem, level: str) -> None:
    if level == _RISK_LEVEL_HIGH:
        item.setBackground(QColor("#f7d6d9"))
    elif level == _RISK_LEVEL_MEDIUM:
        item.setBackground(QColor("#f7ead1"))
    elif level == _RISK_LEVEL_LOW:
        item.setBackground(QColor("#e2f1df"))
    else:
        item.setBackground(QColor("#eef1f5"))
