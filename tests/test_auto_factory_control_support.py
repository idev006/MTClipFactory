from __future__ import annotations

from mt_clip_factory.factory.production_order_dto import (
    ProductionOrderDetailsDTO,
    ProductionOrderEventDTO,
    ProductionOrderItemDTO,
    ProductionOrderStageDTO,
)
from mt_clip_factory.ui.factory.auto_factory_control_support import (
    build_order_product_rows,
    build_order_stage_rows,
    build_order_summary_text,
)


def _selected_order() -> ProductionOrderDetailsDTO:
    return ProductionOrderDetailsDTO(
        production_order_id=16,
        order_code="tea_order_016",
        batch_code="tea_batch_016",
        source_mode="folder_control_surface",
        requested_by=None,
        strict_fulfillment=True,
        preview_generation_enabled=True,
        run_mode="materialize_and_build_previews",
        source_root="F:\\batch_root",
        status="succeeded",
        lease_owner=None,
        lease_acquired_at=None,
        lease_heartbeat_at=None,
        lease_expires_at=None,
        blocking_reason=None,
        created_at="2026-06-26 10:00:00",
        started_at="2026-06-26 10:00:01",
        finished_at="2026-06-26 10:00:09",
        items=(
            ProductionOrderItemDTO(
                production_order_item_id=5,
                product_id=1,
                product_code="tea",
                requested_output_count=1,
                target_platform="tiktok",
                target_ratio="9:16",
                uniqueness_scope="batch",
                duration_mode="voice_with_bounds",
                fixed_duration_sec=None,
                min_duration_sec=12.0,
                max_duration_sec=30.0,
            ),
        ),
        stages=(
            ProductionOrderStageDTO(
                production_order_stage_id=11,
                stage_name="materialize",
                stage_scope="recipe",
                status="succeeded",
                sequence_index=1,
                production_order_item_id=5,
                job_id=None,
                recipe_id=101,
                output_id=None,
                failure_class=None,
                detail_json='{"recipe_code":"tea_batch_001","near_duplicate_score":0.275,"near_duplicate_reasons":["voice_asset_overused"]}',
                created_at="2026-06-26 10:00:02",
                updated_at="2026-06-26 10:00:02",
            ),
            ProductionOrderStageDTO(
                production_order_stage_id=12,
                stage_name="preview",
                stage_scope="recipe",
                status="succeeded",
                sequence_index=2,
                production_order_item_id=5,
                job_id=91,
                recipe_id=101,
                output_id=201,
                failure_class=None,
                detail_json=(
                    '{"recipe_code":"tea_batch_001","output_code":"preview_001","clip_formula_hash":"abc123def4567890",'
                    '"history_scope":"auto_factory_preview","duplicate_risk":1.0,'
                    '"review_signal_codes":["historical_render_duplicate"]}'
                ),
                created_at="2026-06-26 10:00:04",
                updated_at="2026-06-26 10:00:04",
            ),
            ProductionOrderStageDTO(
                production_order_stage_id=13,
                stage_name="review",
                stage_scope="recipe",
                status="review_required",
                sequence_index=3,
                production_order_item_id=5,
                job_id=None,
                recipe_id=101,
                output_id=201,
                failure_class=None,
                detail_json=(
                    '{"recipe_code":"tea_batch_001","recipe_status":"needs_review","clip_formula_hash":"abc123def4567890",'
                    '"history_scope":"auto_factory_preview","duplicate_risk":1.0,'
                    '"review_signal_codes":["historical_render_duplicate"]}'
                ),
                created_at="2026-06-26 10:00:05",
                updated_at="2026-06-26 10:00:05",
            ),
        ),
        events=(
            ProductionOrderEventDTO(
                production_order_event_id=20,
                sequence_index=1,
                event_type="run_completed",
                status="succeeded",
                message="Completed production order tea_order_016 with status succeeded.",
                production_order_item_id=None,
                stage_name=None,
                worker_id=None,
                detail_json=None,
                created_at="2026-06-26 10:00:09",
            ),
        ),
    )


def test_order_summary_and_rows_surface_render_history_truth() -> None:
    order = _selected_order()

    summary = build_order_summary_text(order)
    product_rows = build_order_product_rows(order)
    stage_rows = build_order_stage_rows(order)

    assert "Risk Focus: High" in summary
    assert "Planner Risk: max=0.275, recipes=1" in summary
    assert "Render-History Risk: max=1.000, stages=2" in summary
    assert "History Scopes: auto_factory_preview" in summary
    assert "Review Signals: historical_render_duplicate" in summary
    assert "Clip Formula Hashes: abc123def456" in summary
    assert product_rows[0].risk_level == "High"
    assert product_rows[0].risk_score == 1.0
    assert stage_rows[1].risk_level == "High"
    assert stage_rows[1].risk_score == 1.0
    assert "historical_render_duplicate" in stage_rows[1].risk_reasons
    assert "history_scope:auto_factory_preview" in stage_rows[1].risk_reasons
    assert "clip_formula_hash:abc123def456" in stage_rows[1].risk_reasons
