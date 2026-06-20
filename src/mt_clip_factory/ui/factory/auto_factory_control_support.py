from __future__ import annotations

import json


def format_product_request_summary(request) -> str:
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
        f"Lease Heartbeat: {snapshot.lease_heartbeat_at or '-'}",
        f"Lease Expires: {snapshot.lease_expires_at or '-'}",
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
            f"Lease Heartbeat: {order.lease_heartbeat_at or '-'}",
            f"Lease Expires: {order.lease_expires_at or '-'}",
            f"Blocking Reason: {order.blocking_reason or '-'}",
            f"Strict Fulfillment: {order.strict_fulfillment}",
            f"Created At: {order.created_at}",
            f"Started At: {order.started_at or 'not started'}",
            f"Finished At: {order.finished_at or 'not finished'}",
        ]
    )


def build_order_product_rows(order) -> list[tuple[str, str, str, str]]:
    latest_stage_by_item_id: dict[int, object] = {}
    for stage in _effective_order_stages(order.stages):
        if stage.production_order_item_id is None:
            continue
        latest_stage_by_item_id[stage.production_order_item_id] = stage

    rows: list[tuple[str, str, str, str]] = []
    for item in order.items:
        latest_stage = latest_stage_by_item_id.get(item.production_order_item_id)
        rows.append(
            (
                item.product_code,
                str(item.requested_output_count),
                "-" if latest_stage is None else latest_stage.stage_name,
                "queued" if latest_stage is None else latest_stage.status,
            )
        )
    return rows


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
