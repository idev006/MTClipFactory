from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime

from mt_clip_factory.domain.entities import utc_now
from mt_clip_factory.domain.enums import OrchestrationStatus
from mt_clip_factory.domain.production_orders import ProductionOrder, ProductionOrderItem, ProductionOrderStage
from mt_clip_factory.domain.services import UnitOfWork
from mt_clip_factory.factory.auto_factory import AutoFactoryBatchService, AutoFactoryCapacityError, AutoFactoryPlanningError
from mt_clip_factory.factory.auto_factory_dto import AutoFactoryBatchOrderDTO, AutoFactoryProductRequestDTO
from mt_clip_factory.factory.production_order_dto import (
    ProductionOrderDetailsDTO,
    ProductionOrderItemDTO,
    ProductionOrderStageDTO,
    ProductionOrderSummaryDTO,
)


class ProductionOrderNotFoundError(ValueError):
    """Raised when a production order cannot be found."""


class ProductionOrderAlreadyExistsError(ValueError):
    """Raised when an order code is duplicated."""


class ProductionOrderRunStateError(ValueError):
    """Raised when an order cannot be run from its current state."""


class ProductionOrderService:
    def __init__(
        self,
        *,
        unit_of_work_factory: Callable[[], UnitOfWork],
        auto_factory_service: AutoFactoryBatchService,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._auto_factory_service = auto_factory_service

    def create_order(
        self,
        order: AutoFactoryBatchOrderDTO,
        *,
        source_mode: str,
        order_code: str | None = None,
        requested_by: str | None = None,
    ) -> int:
        resolved_order_code = _normalize_order_code(order_code or order.batch_code)
        if not resolved_order_code:
            raise ValueError("Order code is required.")
        source = _normalize_required_text(source_mode, field_name="source_mode")
        requested_by_value = _normalize_optional_text(requested_by)

        with self._unit_of_work_factory() as uow:
            if uow.production_orders.get_by_code(resolved_order_code) is not None:
                raise ProductionOrderAlreadyExistsError(resolved_order_code)

            products_by_code = {product.product_code: product for product in uow.products.list_summaries()}
            created = uow.production_orders.add(
                ProductionOrder(
                    order_code=resolved_order_code,
                    batch_code=order.batch_code,
                    source_mode=source,
                    requested_by=requested_by_value,
                    strict_fulfillment=order.strict_fulfillment,
                )
            )
            if created.id is None:
                raise RuntimeError("Production order identifier was not assigned.")

            for product_request in order.product_requests:
                product = products_by_code.get(product_request.product_code)
                if product is None:
                    raise ProductionOrderNotFoundError(
                        f"Unknown product code for production order persistence: {product_request.product_code}"
                    )
                uow.production_orders.add_item(
                    ProductionOrderItem(
                        production_order_id=created.id,
                        product_id=product.product_id,
                        product_code_snapshot=product.product_code,
                        requested_output_count=product_request.requested_output_count,
                        target_platform=product_request.target_platform,
                        target_ratio=product_request.target_ratio,
                        uniqueness_scope=product_request.uniqueness_scope,
                        duration_mode=product_request.duration_mode,
                        fixed_duration_sec=product_request.fixed_duration_sec,
                        min_duration_sec=product_request.min_duration_sec,
                        max_duration_sec=product_request.max_duration_sec,
                    )
                )

            uow.commit()
            return created.id

    def create_and_run_order(
        self,
        order: AutoFactoryBatchOrderDTO,
        *,
        source_mode: str,
        order_code: str | None = None,
        requested_by: str | None = None,
        build_previews: bool = True,
    ) -> ProductionOrderDetailsDTO:
        order_id = self.create_order(
            order,
            source_mode=source_mode,
            order_code=order_code,
            requested_by=requested_by,
        )
        return self.run_order(order_id, build_previews=build_previews)

    def run_order(self, production_order_id: int, *, build_previews: bool = True) -> ProductionOrderDetailsDTO:
        order, items = self._load_order_bundle(production_order_id)
        if order.status != OrchestrationStatus.QUEUED:
            raise ProductionOrderRunStateError(
                f"Production order {order.order_code} cannot run from state {order.status.value}."
            )

        order.status = OrchestrationStatus.PROCESSING
        order.started_at = utc_now()
        self._save_order(order)

        batch_order = AutoFactoryBatchOrderDTO(
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
        item_by_product_code = {item.product_code_snapshot: item for item in items}

        try:
            materialization = self._auto_factory_service.materialize_batch(batch_order)
        except AutoFactoryCapacityError as exc:
            self._record_stage(
                production_order_id=production_order_id,
                stage_name="materialize",
                stage_scope="order",
                status=OrchestrationStatus.FAILED_TERMINAL,
                sequence_index=self._next_sequence_index(production_order_id),
                failure_class="planning_capacity_shortfall",
                detail={"error": str(exc)},
            )
            self._finish_order(production_order_id, status=OrchestrationStatus.FAILED_TERMINAL)
            return self.get_order(production_order_id)
        except AutoFactoryPlanningError as exc:
            self._record_stage(
                production_order_id=production_order_id,
                stage_name="materialize",
                stage_scope="order",
                status=OrchestrationStatus.FAILED_TERMINAL,
                sequence_index=self._next_sequence_index(production_order_id),
                failure_class="planning_error",
                detail={"error": str(exc)},
            )
            self._finish_order(production_order_id, status=OrchestrationStatus.FAILED_TERMINAL)
            return self.get_order(production_order_id)
        except Exception as exc:
            self._record_stage(
                production_order_id=production_order_id,
                stage_name="materialize",
                stage_scope="order",
                status=OrchestrationStatus.FAILED_RETRYABLE,
                sequence_index=self._next_sequence_index(production_order_id),
                failure_class="materialization_runtime_failure",
                detail={"error": str(exc)},
            )
            self._finish_order(production_order_id, status=OrchestrationStatus.FAILED_RETRYABLE)
            return self.get_order(production_order_id)

        for created_recipe in materialization.created_recipes:
            item = item_by_product_code[created_recipe.product_code]
            self._record_stage(
                production_order_id=production_order_id,
                production_order_item_id=item.id,
                stage_name="materialize",
                stage_scope="recipe",
                status=OrchestrationStatus.SUCCEEDED,
                sequence_index=self._next_sequence_index(production_order_id),
                recipe_id=created_recipe.recipe_id,
                detail={
                    "recipe_code": created_recipe.recipe_code,
                    "assignment_count": created_recipe.assignment_count,
                },
            )

        if build_previews:
            preview_production = self._auto_factory_service.build_previews_for_materialized_batch(materialization)
            for preview_result in preview_production.recipe_results:
                item = item_by_product_code[preview_result.product_code]
                preview_status = (
                    OrchestrationStatus.SUCCEEDED
                    if preview_result.job_status == "done"
                    else OrchestrationStatus.FAILED_RETRYABLE
                )
                self._record_stage(
                    production_order_id=production_order_id,
                    production_order_item_id=item.id,
                    stage_name="preview",
                    stage_scope="recipe",
                    status=preview_status,
                    sequence_index=self._next_sequence_index(production_order_id),
                    job_id=preview_result.preview_job_id,
                    recipe_id=preview_result.recipe_id,
                    output_id=preview_result.output_id,
                    failure_class=None if preview_status == OrchestrationStatus.SUCCEEDED else "preview_render_failure",
                    detail={
                        "recipe_code": preview_result.recipe_code,
                        "job_status": preview_result.job_status,
                        "output_code": preview_result.output_code,
                        "output_path": preview_result.output_path,
                        "error_message": preview_result.error_message,
                    },
                )
                if preview_status == OrchestrationStatus.SUCCEEDED:
                    review_status = (
                        OrchestrationStatus.REVIEW_REQUIRED
                        if preview_result.review_required
                        else OrchestrationStatus.SUCCEEDED
                    )
                    self._record_stage(
                        production_order_id=production_order_id,
                        production_order_item_id=item.id,
                        stage_name="review",
                        stage_scope="recipe",
                        status=review_status,
                        sequence_index=self._next_sequence_index(production_order_id),
                        recipe_id=preview_result.recipe_id,
                        output_id=preview_result.output_id,
                        detail={
                            "recipe_code": preview_result.recipe_code,
                            "recipe_status": preview_result.recipe_status,
                            "output_code": preview_result.output_code,
                        },
                    )

        final_status = self._resolve_order_status(production_order_id)
        self._finish_order(production_order_id, status=final_status)
        return self.get_order(production_order_id)

    def get_order(self, production_order_id: int) -> ProductionOrderDetailsDTO:
        order, items = self._load_order_bundle(production_order_id)
        with self._unit_of_work_factory() as uow:
            stages = tuple(uow.production_order_stages.list_by_order(production_order_id))
        return ProductionOrderDetailsDTO(
            production_order_id=order.id or 0,
            order_code=order.order_code,
            batch_code=order.batch_code,
            source_mode=order.source_mode,
            requested_by=order.requested_by,
            strict_fulfillment=order.strict_fulfillment,
            status=order.status.value,
            created_at=_format_timestamp(order.created_at),
            started_at=_format_optional_timestamp(order.started_at),
            finished_at=_format_optional_timestamp(order.finished_at),
            items=tuple(
                ProductionOrderItemDTO(
                    production_order_item_id=item.id or 0,
                    product_id=item.product_id,
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
            stages=tuple(
                ProductionOrderStageDTO(
                    production_order_stage_id=stage.id or 0,
                    stage_name=stage.stage_name,
                    stage_scope=stage.stage_scope,
                    status=stage.status.value,
                    sequence_index=stage.sequence_index,
                    production_order_item_id=stage.production_order_item_id,
                    job_id=stage.job_id,
                    recipe_id=stage.recipe_id,
                    output_id=stage.output_id,
                    failure_class=stage.failure_class,
                    detail_json=stage.detail_json,
                    created_at=_format_timestamp(stage.created_at),
                    updated_at=_format_timestamp(stage.updated_at),
                )
                for stage in stages
            ),
        )

    def list_orders(self, *, status: str | None = None) -> list[ProductionOrderSummaryDTO]:
        with self._unit_of_work_factory() as uow:
            return [
                ProductionOrderSummaryDTO(
                    production_order_id=summary.production_order_id,
                    order_code=summary.order_code,
                    batch_code=summary.batch_code,
                    source_mode=summary.source_mode,
                    requested_by=summary.requested_by,
                    status=summary.status.value,
                    item_count=summary.item_count,
                    created_at=_format_timestamp(summary.created_at),
                    started_at=_format_optional_timestamp(summary.started_at),
                    finished_at=_format_optional_timestamp(summary.finished_at),
                )
                for summary in uow.production_orders.list_summaries(status=status)
            ]

    def _load_order_bundle(self, production_order_id: int) -> tuple[ProductionOrder, tuple[ProductionOrderItem, ...]]:
        with self._unit_of_work_factory() as uow:
            order = uow.production_orders.get_by_id(production_order_id)
            if order is None or order.id is None:
                raise ProductionOrderNotFoundError(str(production_order_id))
            items = tuple(uow.production_orders.list_items(production_order_id))
            return order, items

    def _save_order(self, order: ProductionOrder) -> None:
        with self._unit_of_work_factory() as uow:
            uow.production_orders.update(order)
            uow.commit()

    def _finish_order(self, production_order_id: int, *, status: OrchestrationStatus) -> None:
        with self._unit_of_work_factory() as uow:
            order = uow.production_orders.get_by_id(production_order_id)
            if order is None or order.id is None:
                raise ProductionOrderNotFoundError(str(production_order_id))
            order.status = status
            order.finished_at = utc_now()
            if order.started_at is None:
                order.started_at = order.finished_at
            uow.production_orders.update(order)
            uow.commit()

    def _next_sequence_index(self, production_order_id: int) -> int:
        with self._unit_of_work_factory() as uow:
            stages = tuple(uow.production_order_stages.list_by_order(production_order_id))
            return len(stages) + 1

    def _record_stage(
        self,
        *,
        production_order_id: int,
        stage_name: str,
        stage_scope: str,
        status: OrchestrationStatus,
        sequence_index: int,
        production_order_item_id: int | None = None,
        job_id: int | None = None,
        recipe_id: int | None = None,
        output_id: int | None = None,
        failure_class: str | None = None,
        detail: dict | None = None,
    ) -> None:
        now = utc_now()
        with self._unit_of_work_factory() as uow:
            uow.production_order_stages.add(
                ProductionOrderStage(
                    production_order_id=production_order_id,
                    production_order_item_id=production_order_item_id,
                    stage_name=stage_name,
                    stage_scope=stage_scope,
                    status=status,
                    sequence_index=sequence_index,
                    job_id=job_id,
                    recipe_id=recipe_id,
                    output_id=output_id,
                    failure_class=failure_class,
                    detail_json=None if detail is None else json.dumps(detail, sort_keys=True),
                    created_at=now,
                    updated_at=now,
                )
            )
            uow.commit()

    def _resolve_order_status(self, production_order_id: int) -> OrchestrationStatus:
        with self._unit_of_work_factory() as uow:
            statuses = [stage.status for stage in uow.production_order_stages.list_by_order(production_order_id)]
        if any(status == OrchestrationStatus.FAILED_TERMINAL for status in statuses):
            return OrchestrationStatus.FAILED_TERMINAL
        if any(status == OrchestrationStatus.FAILED_RETRYABLE for status in statuses):
            return OrchestrationStatus.FAILED_RETRYABLE
        if any(status == OrchestrationStatus.REVIEW_REQUIRED for status in statuses):
            return OrchestrationStatus.REVIEW_REQUIRED
        return OrchestrationStatus.SUCCEEDED


def _format_timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _format_optional_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _format_timestamp(value)


def _normalize_order_code(value: str) -> str:
    normalized = "".join(character if character.isalnum() else "_" for character in value.strip().lower())
    return normalized.strip("_")


def _normalize_required_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required.")
    return normalized


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
