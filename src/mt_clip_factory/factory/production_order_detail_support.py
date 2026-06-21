from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from mt_clip_factory.domain.enums import OrchestrationStatus
from mt_clip_factory.domain.production_orders import ProductionOrder, ProductionOrderItem, ProductionOrderStage
from mt_clip_factory.factory.auto_factory_dto import (
    AutoFactoryBatchOrderDTO,
    AutoFactoryProductRequestDTO,
    MaterializedBatchRecipeDTO,
    PlannedBatchRecipeDTO,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


def build_batch_order(
    order: ProductionOrder,
    items: Sequence[ProductionOrderItem],
) -> AutoFactoryBatchOrderDTO:
    return AutoFactoryBatchOrderDTO(
        batch_code=order.batch_code,
        product_requests=tuple(
            AutoFactoryProductRequestDTO(
                product_code=item.product_code_snapshot,
                requested_output_count=item.requested_output_count,
                target_platform=item.target_platform,
                target_ratio=item.target_ratio,
                uniqueness_scope=item.uniqueness_scope,
                duration_mode=item.duration_mode,
                fixed_duration_sec=item.fixed_duration_sec,
                min_duration_sec=item.min_duration_sec,
                max_duration_sec=item.max_duration_sec,
            )
            for item in items
        ),
        strict_fulfillment=order.strict_fulfillment,
    )


def effective_stage_key(stage: ProductionOrderStage) -> tuple[object, ...]:
    recipe_code = stage_detail_value(stage.detail_json, "recipe_code")
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


def effective_stages(stages: Sequence[ProductionOrderStage]) -> tuple[ProductionOrderStage, ...]:
    latest_by_key: dict[tuple[object, ...], ProductionOrderStage] = {}
    for stage in stages:
        latest_by_key[effective_stage_key(stage)] = stage
    return tuple(sorted(latest_by_key.values(), key=lambda item: (item.sequence_index, item.id or 0)))


def find_materialized_recipe(
    stages: Sequence[ProductionOrderStage],
    *,
    production_order_item_id: int,
    recipe_code: str,
    product_id: int,
    product_code: str,
) -> MaterializedBatchRecipeDTO | None:
    for stage in effective_stages(stages):
        if stage.stage_name != "materialize" or stage.status != OrchestrationStatus.SUCCEEDED:
            continue
        if stage.production_order_item_id != production_order_item_id:
            continue
        if stage_detail_value(stage.detail_json, "recipe_code") != recipe_code or stage.recipe_id is None:
            continue
        assignment_count = int(stage_detail_value(stage.detail_json, "assignment_count") or 0)
        return MaterializedBatchRecipeDTO(
            recipe_id=stage.recipe_id,
            product_id=product_id,
            product_code=product_code,
            recipe_code=recipe_code,
            assignment_count=assignment_count,
        )
    return None


def has_successful_stage(
    stages: Sequence[ProductionOrderStage],
    *,
    stage_name: str,
    recipe_id: int,
) -> bool:
    for stage in effective_stages(stages):
        if stage.stage_name == stage_name and stage.recipe_id == recipe_id and stage.status == OrchestrationStatus.SUCCEEDED:
            return True
    return False


def resolve_blocking_reason(
    stages: Sequence[ProductionOrderStage],
    fallback_status: OrchestrationStatus,
) -> str | None:
    for stage in reversed(effective_stages(stages)):
        if stage.failure_class:
            return stage.failure_class
        error_message = stage_detail_value(stage.detail_json, "error_message") or stage_detail_value(stage.detail_json, "error")
        if isinstance(error_message, str) and error_message.strip():
            return error_message
    return None if fallback_status == OrchestrationStatus.SUCCEEDED else fallback_status.value


def build_materialize_stage_detail(
    planned_recipe: PlannedBatchRecipeDTO,
    created_recipe: MaterializedBatchRecipeDTO,
) -> dict[str, object]:
    return {
        "recipe_code": created_recipe.recipe_code,
        "assignment_count": created_recipe.assignment_count,
        "near_duplicate_score": planned_recipe.near_duplicate_score,
        "near_duplicate_reasons": list(planned_recipe.near_duplicate_reasons),
        "fingerprint": planned_recipe.fingerprint,
    }


def stage_detail_value(detail_json: str | None, key: str) -> object | None:
    if not detail_json:
        return None
    try:
        payload = json.loads(detail_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload.get(key)


def format_timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def format_optional_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return format_timestamp(value)


def normalize_order_code(value: str) -> str:
    normalized = "".join(character if character.isalnum() else "_" for character in value.strip().lower())
    return normalized.strip("_")


def normalize_required_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required.")
    return normalized


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
