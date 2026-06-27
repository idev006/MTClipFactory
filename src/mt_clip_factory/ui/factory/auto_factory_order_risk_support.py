from __future__ import annotations

from collections import Counter
import json
from dataclasses import dataclass

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


def build_order_summary_text(order) -> str:
    requested_preset_modes = tuple(
        dict.fromkeys(
            item.creative_preset_mode.strip()
            for item in order.items
            if isinstance(item.creative_preset_mode, str) and item.creative_preset_mode.strip()
        )
    )
    requested_preset_codes = tuple(
        dict.fromkeys(
            code.strip()
            for item in order.items
            for code in item.creative_preset_codes
            if isinstance(code, str) and code.strip()
        )
    )
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
    requested_mode_summary = ", ".join(requested_preset_modes) if requested_preset_modes else "-"
    requested_code_summary = ", ".join(requested_preset_codes) if requested_preset_codes else "-"
    creative_preset_summary = ", ".join(dict.fromkeys(creative_preset_codes)) if creative_preset_codes else "-"
    creative_signature_summary = ", ".join(dict.fromkeys(creative_preset_signatures)) if creative_preset_signatures else "-"
    preset_spread_summary = _summarize_preset_spread(creative_preset_codes)
    preset_concentration_summary = _summarize_preset_concentration(creative_preset_codes)
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
            f"- Requested Preset Modes: {requested_mode_summary}",
            f"- Requested Preset Codes: {requested_code_summary}",
            f"- Creative Presets: {creative_preset_summary}",
            f"- Creative Signatures: {creative_signature_summary}",
            f"- Preset Spread: {preset_spread_summary}",
            f"- Preset Concentration: {preset_concentration_summary}",
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


def _effective_order_stages(stages: tuple[object, ...]) -> tuple[object, ...]:
    succeeded_render_stages: dict[tuple[int | None, int | None, str], object] = {}
    terminal_render_stages: set[tuple[int | None, int | None, str]] = set()
    for stage in stages:
        if stage.stage_name not in {"preview", "review"}:
            continue
        key = (stage.production_order_item_id, stage.recipe_id, stage.stage_name)
        if stage.status == "succeeded":
            succeeded_render_stages[key] = stage
            continue
        if stage.status == "review_required":
            terminal_render_stages.add(key)
    filtered: list[object] = []
    for stage in stages:
        if stage.stage_name not in {"preview", "review"}:
            filtered.append(stage)
            continue
        key = (stage.production_order_item_id, stage.recipe_id, stage.stage_name)
        if stage.status == "review_required" and key in succeeded_render_stages:
            continue
        if stage.status == "succeeded" and key in terminal_render_stages:
            filtered.append(stage)
            continue
        filtered.append(stage)
    return tuple(filtered)


def _stage_detail_value(detail_json: str | None, key: str) -> object | None:
    if detail_json is None:
        return None
    try:
        payload = json.loads(detail_json)
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload.get(key)


def _stage_near_duplicate_score(detail_json: str | None) -> float | None:
    value = _stage_detail_value(detail_json, "near_duplicate_score")
    if not isinstance(value, (int, float)):
        return None
    return float(value)


def _stage_near_duplicate_reasons(detail_json: str | None) -> tuple[str, ...]:
    value = _stage_detail_value(detail_json, "near_duplicate_reasons")
    if not isinstance(value, list):
        return ()
    return tuple(reason for reason in value if isinstance(reason, str) and reason.strip())


def _stage_render_duplicate_score(detail_json: str | None) -> float | None:
    value = _stage_detail_value(detail_json, "duplicate_risk")
    if not isinstance(value, (int, float)):
        return None
    return float(value)


def _stage_creative_preset_code(detail_json: str | None) -> str | None:
    value = _stage_detail_value(detail_json, "creative_preset_code")
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _stage_creative_preset_signature(detail_json: str | None) -> str | None:
    value = _stage_detail_value(detail_json, "creative_preset_signature")
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _stage_history_scope(detail_json: str | None) -> str | None:
    value = _stage_detail_value(detail_json, "history_scope")
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _stage_clip_formula_hash(detail_json: str | None) -> str | None:
    value = _stage_detail_value(detail_json, "clip_formula_hash")
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _stage_review_signal_codes(detail_json: str | None) -> tuple[str, ...]:
    value = _stage_detail_value(detail_json, "review_signal_codes")
    if not isinstance(value, list):
        return ()
    return tuple(code for code in value if isinstance(code, str) and code.strip())


def _stage_display_risk_score(stage) -> float | None:  # noqa: ANN001
    return _stage_near_duplicate_score(stage.detail_json) if stage.stage_name == "materialize" else _stage_render_duplicate_score(stage.detail_json)


def _stage_display_risk_reasons(stage) -> tuple[str, ...]:  # noqa: ANN001
    parts: list[str] = []
    if stage.stage_name == "materialize":
        parts.extend(_stage_near_duplicate_reasons(stage.detail_json))
        return tuple(dict.fromkeys(parts))
    history_scope = _stage_history_scope(stage.detail_json)
    clip_formula_hash = _stage_clip_formula_hash(stage.detail_json)
    if history_scope:
        parts.append(f"history_scope:{history_scope}")
    if clip_formula_hash:
        parts.append(f"clip_formula_hash:{clip_formula_hash[:12]}")
    render_duplicate_score = _stage_render_duplicate_score(stage.detail_json)
    if (
        stage.stage_name in {"preview", "review"}
        and render_duplicate_score is not None
        and render_duplicate_score > 0.0
    ):
        parts.append("render_duplicate_risk")
    parts.extend(_stage_review_signal_codes(stage.detail_json))
    return tuple(dict.fromkeys(parts))


def _summarize_preset_spread(values: list[str]) -> str:
    if not values:
        return "-"
    counts = Counter(value for value in values if value)
    if not counts:
        return "-"
    total = sum(counts.values())
    return ", ".join(
        f"{code} x{count} ({(float(count) / float(total)):.0%})"
        for code, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    )


def _summarize_preset_concentration(values: list[str]) -> str:
    if not values:
        return "-"
    counts = Counter(value for value in values if value)
    if not counts:
        return "-"
    total = sum(counts.values())
    max_share = max(counts.values()) / float(total)
    return f"unique={len(counts)}, max_share={max_share:.3f}, recipes={total}"


def _summarize_clip_formula_hashes(values: list[str]) -> str:
    if not values:
        return "-"
    seen: list[str] = []
    for value in values:
        prefix = value[:12]
        if prefix not in seen:
            seen.append(prefix)
    return ", ".join(seen)


def _risk_level_label(score: float | None) -> str:
    if score is None:
        return _RISK_LEVEL_UNAVAILABLE
    if score >= 0.6:
        return _RISK_LEVEL_HIGH
    if score >= 0.25:
        return _RISK_LEVEL_MEDIUM
    return _RISK_LEVEL_LOW
