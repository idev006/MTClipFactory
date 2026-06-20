from __future__ import annotations

import json
import threading
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from mt_clip_factory.domain.entities import utc_now
from mt_clip_factory.domain.enums import OrchestrationStatus
from mt_clip_factory.domain.production_orders import (
    ProductionOrder,
    ProductionOrderEvent,
    ProductionOrderItem,
    ProductionOrderStage,
)
from mt_clip_factory.domain.services import UnitOfWork
from mt_clip_factory.factory.auto_factory import AutoFactoryBatchService, AutoFactoryCapacityError, AutoFactoryPlanningError
from mt_clip_factory.factory.auto_factory_dto import (
    AutoFactoryBatchOrderDTO,
    AutoFactoryProductRequestDTO,
    MaterializedBatchRecipeDTO,
)
from mt_clip_factory.factory.production_order_dto import (
    ProductionOrderDetailsDTO,
    ProductionOrderEventDTO,
    ProductionOrderItemDTO,
    ProductionOrderStageDTO,
    ProductionOrderSummaryDTO,
)

_LEASE_TIMEOUT_SECONDS = 60
_HEARTBEAT_INTERVAL_SECONDS = 5
_FINAL_ORDER_STATUSES = {
    OrchestrationStatus.SUCCEEDED,
    OrchestrationStatus.FAILED_RETRYABLE,
    OrchestrationStatus.FAILED_TERMINAL,
    OrchestrationStatus.REVIEW_REQUIRED,
    OrchestrationStatus.CANCELLED,
}
_ACTIVE_ORDER_STATUSES = {
    OrchestrationStatus.LEASED,
    OrchestrationStatus.PROCESSING,
    OrchestrationStatus.PAUSE_REQUESTED,
    OrchestrationStatus.STOP_REQUESTED,
    OrchestrationStatus.RESUME_REQUESTED,
}
_RUNNABLE_ORDER_STATUSES = {
    OrchestrationStatus.QUEUED,
    OrchestrationStatus.PAUSED,
    OrchestrationStatus.STOPPED,
    OrchestrationStatus.FAILED_RETRYABLE,
    OrchestrationStatus.REVIEW_REQUIRED,
    OrchestrationStatus.BLOCKED,
    OrchestrationStatus.RESUME_REQUESTED,
}


class ProductionOrderNotFoundError(ValueError):
    """Raised when a production order cannot be found."""


class ProductionOrderAlreadyExistsError(ValueError):
    """Raised when an order code is duplicated."""


class ProductionOrderRunStateError(ValueError):
    """Raised when an order cannot be run from its current state."""


class _OrderHeartbeat:
    def __init__(self, service: ProductionOrderService, *, production_order_id: int, worker_id: str) -> None:
        self._service = service
        self._production_order_id = production_order_id
        self._worker_id = worker_id
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name=f"production-order-heartbeat-{production_order_id}",
            daemon=True,
        )

    def __enter__(self) -> _OrderHeartbeat:
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._stop_event.set()
        self._thread.join(timeout=_HEARTBEAT_INTERVAL_SECONDS)

    def _run(self) -> None:
        while not self._stop_event.wait(_HEARTBEAT_INTERVAL_SECONDS):
            self._service._heartbeat_order(self._production_order_id, self._worker_id)


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
        build_previews: bool = True,
        run_mode: str | None = None,
        source_root: str | None = None,
    ) -> int:
        resolved_order_code = _normalize_order_code(order_code or order.batch_code)
        if not resolved_order_code:
            raise ValueError("Order code is required.")
        source = _normalize_required_text(source_mode, field_name="source_mode")
        requested_by_value = _normalize_optional_text(requested_by)
        run_mode_value = _normalize_optional_text(run_mode)
        source_root_value = _normalize_optional_text(source_root)

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
                    preview_generation_enabled=build_previews,
                    run_mode=run_mode_value,
                    source_root=source_root_value,
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
            self._append_event_in_uow(
                uow,
                production_order_id=created.id,
                event_type="order_created",
                status=OrchestrationStatus.QUEUED,
                message=f"Created production order {created.order_code}.",
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
        run_mode: str | None = None,
        source_root: str | None = None,
    ) -> ProductionOrderDetailsDTO:
        order_id = self.create_order(
            order,
            source_mode=source_mode,
            order_code=order_code,
            requested_by=requested_by,
            build_previews=build_previews,
            run_mode=run_mode,
            source_root=source_root,
        )
        return self.run_order(order_id, build_previews=build_previews)

    def run_order(self, production_order_id: int, *, build_previews: bool | None = None) -> ProductionOrderDetailsDTO:
        worker_id = self._new_worker_id()
        claimed_order, recovered_stale_lease, previous_status = self._claim_order_lease(
            production_order_id,
            worker_id=worker_id,
            build_previews=build_previews,
        )
        if recovered_stale_lease:
            self._append_event(
                production_order_id=production_order_id,
                event_type="stale_lease_recovered",
                status=OrchestrationStatus.RESUME_REQUESTED,
                message=f"Recovered stale lease for production order {claimed_order.order_code}.",
                worker_id=worker_id,
            )
        self._append_event(
            production_order_id=production_order_id,
            event_type="run_started" if previous_status == OrchestrationStatus.QUEUED else "resume_requested",
            status=OrchestrationStatus.PROCESSING,
            message=(
                f"Started production order {claimed_order.order_code}."
                if previous_status == OrchestrationStatus.QUEUED
                else f"Resumed production order {claimed_order.order_code}."
            ),
            worker_id=worker_id,
        )

        with _OrderHeartbeat(self, production_order_id=production_order_id, worker_id=worker_id):
            return self._execute_order_run(production_order_id, worker_id=worker_id)

    def request_pause(self, production_order_id: int) -> ProductionOrderDetailsDTO:
        with self._unit_of_work_factory() as uow:
            order = self._require_order(uow, production_order_id)
            if order.status == OrchestrationStatus.PAUSED:
                return self.get_order(production_order_id)
            if order.status not in {OrchestrationStatus.LEASED, OrchestrationStatus.PROCESSING, OrchestrationStatus.RESUME_REQUESTED}:
                raise ProductionOrderRunStateError(
                    f"Production order {order.order_code} cannot pause from state {order.status.value}."
                )
            if self._lease_is_stale(order):
                raise ProductionOrderRunStateError(
                    f"Production order {order.order_code} has a stale lease. Use Resume Run to recover it."
                )
            order.status = OrchestrationStatus.PAUSE_REQUESTED
            uow.production_orders.update(order)
            self._append_event_in_uow(
                uow,
                production_order_id=production_order_id,
                event_type="pause_requested",
                status=OrchestrationStatus.PAUSE_REQUESTED,
                message=f"Pause requested for production order {order.order_code}.",
                worker_id=order.lease_owner,
            )
            uow.commit()
        return self.get_order(production_order_id)

    def request_stop(self, production_order_id: int) -> ProductionOrderDetailsDTO:
        with self._unit_of_work_factory() as uow:
            order = self._require_order(uow, production_order_id)
            if order.status == OrchestrationStatus.STOPPED:
                return self.get_order(production_order_id)
            if order.status == OrchestrationStatus.PAUSED:
                self._clear_lease(order)
                order.status = OrchestrationStatus.STOPPED
                order.finished_at = utc_now()
                uow.production_orders.update(order)
                self._append_event_in_uow(
                    uow,
                    production_order_id=production_order_id,
                    event_type="stopped",
                    status=OrchestrationStatus.STOPPED,
                    message=f"Stopped production order {order.order_code}.",
                )
                uow.commit()
                return self.get_order(production_order_id)
            if order.status not in {
                OrchestrationStatus.LEASED,
                OrchestrationStatus.PROCESSING,
                OrchestrationStatus.PAUSE_REQUESTED,
                OrchestrationStatus.RESUME_REQUESTED,
            }:
                raise ProductionOrderRunStateError(
                    f"Production order {order.order_code} cannot stop from state {order.status.value}."
                )
            order.status = OrchestrationStatus.STOP_REQUESTED
            uow.production_orders.update(order)
            self._append_event_in_uow(
                uow,
                production_order_id=production_order_id,
                event_type="stop_requested",
                status=OrchestrationStatus.STOP_REQUESTED,
                message=f"Stop requested for production order {order.order_code}.",
                worker_id=order.lease_owner,
            )
            uow.commit()
        return self.get_order(production_order_id)

    def resume_order(self, production_order_id: int) -> ProductionOrderDetailsDTO:
        return self.run_order(production_order_id)

    def get_order(self, production_order_id: int) -> ProductionOrderDetailsDTO:
        order, items = self._load_order_bundle(production_order_id)
        with self._unit_of_work_factory() as uow:
            stages = tuple(uow.production_order_stages.list_by_order(production_order_id))
            events = tuple(uow.production_order_events.list_by_order(production_order_id))
        return ProductionOrderDetailsDTO(
            production_order_id=order.id or 0,
            order_code=order.order_code,
            batch_code=order.batch_code,
            source_mode=order.source_mode,
            requested_by=order.requested_by,
            strict_fulfillment=order.strict_fulfillment,
            preview_generation_enabled=order.preview_generation_enabled,
            run_mode=order.run_mode,
            source_root=order.source_root,
            status=order.status.value,
            lease_owner=order.lease_owner,
            lease_acquired_at=_format_optional_timestamp(order.lease_acquired_at),
            lease_heartbeat_at=_format_optional_timestamp(order.lease_heartbeat_at),
            lease_expires_at=_format_optional_timestamp(order.lease_expires_at),
            blocking_reason=order.blocking_reason,
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
            events=tuple(
                ProductionOrderEventDTO(
                    production_order_event_id=event.id or 0,
                    sequence_index=event.sequence_index,
                    event_type=event.event_type,
                    status=event.status.value,
                    message=event.message,
                    production_order_item_id=event.production_order_item_id,
                    stage_name=event.stage_name,
                    worker_id=event.worker_id,
                    detail_json=event.detail_json,
                    created_at=_format_timestamp(event.created_at),
                )
                for event in events
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

    def _execute_order_run(self, production_order_id: int, *, worker_id: str) -> ProductionOrderDetailsDTO:
        order, items = self._load_order_bundle(production_order_id)
        batch_order = _build_batch_order(order, items)
        item_by_product_code = {item.product_code_snapshot: item for item in items}
        stages = self._list_stages(production_order_id)

        try:
            plan = self._auto_factory_service.plan_batch(batch_order)
            if order.strict_fulfillment:
                shortfalls = [summary for summary in plan.summaries if not summary.can_fulfill_exactly]
                if shortfalls:
                    details = ", ".join(
                        f"{summary.product_code}: requested={summary.requested_output_count}, feasible={summary.planner_feasible_unique_count}"
                        for summary in shortfalls
                    )
                    raise AutoFactoryCapacityError(
                        f"Batch cannot be fulfilled exactly under current planner policy: {details}"
                    )
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
            return self._finalize_order(
                production_order_id,
                worker_id=worker_id,
                status=OrchestrationStatus.FAILED_TERMINAL,
                message=f"Production order blocked by planner capacity: {exc}",
                blocking_reason=str(exc),
            )
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
            return self._finalize_order(
                production_order_id,
                worker_id=worker_id,
                status=OrchestrationStatus.FAILED_TERMINAL,
                message=f"Production order blocked by planning error: {exc}",
                blocking_reason=str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            self._record_stage(
                production_order_id=production_order_id,
                stage_name="materialize",
                stage_scope="order",
                status=OrchestrationStatus.FAILED_RETRYABLE,
                sequence_index=self._next_sequence_index(production_order_id),
                failure_class="materialization_runtime_failure",
                detail={"error": str(exc)},
            )
            return self._finalize_order(
                production_order_id,
                worker_id=worker_id,
                status=OrchestrationStatus.FAILED_RETRYABLE,
                message=f"Production order runtime failure during planning: {exc}",
                blocking_reason=str(exc),
            )

        materialized_recipes: list[MaterializedBatchRecipeDTO] = []
        for planned_recipe in plan.planned_recipes:
            checkpoint_state = self._consume_control_checkpoint(production_order_id, worker_id=worker_id)
            if checkpoint_state is not None:
                return self.get_order(production_order_id)

            item = item_by_product_code[planned_recipe.product_code]
            existing_materialized = _find_materialized_recipe(
                stages,
                production_order_item_id=item.id or 0,
                recipe_code=planned_recipe.recipe_code,
                product_id=planned_recipe.product_id,
                product_code=planned_recipe.product_code,
            )
            if existing_materialized is not None:
                materialized_recipes.append(existing_materialized)
                continue

            self._append_event(
                production_order_id=production_order_id,
                production_order_item_id=item.id,
                stage_name="materialize",
                event_type="stage_started",
                status=OrchestrationStatus.PROCESSING,
                message=f"Materializing {planned_recipe.recipe_code}.",
                worker_id=worker_id,
                detail={"recipe_code": planned_recipe.recipe_code},
            )
            try:
                created_recipe = self._auto_factory_service.materialize_planned_recipe(planned_recipe)
            except Exception as exc:  # noqa: BLE001
                self._record_stage(
                    production_order_id=production_order_id,
                    production_order_item_id=item.id,
                    stage_name="materialize",
                    stage_scope="recipe",
                    status=OrchestrationStatus.FAILED_RETRYABLE,
                    sequence_index=self._next_sequence_index(production_order_id),
                    failure_class="materialization_runtime_failure",
                    detail={"error": str(exc), "recipe_code": planned_recipe.recipe_code},
                )
                return self._finalize_order(
                    production_order_id,
                    worker_id=worker_id,
                    status=OrchestrationStatus.FAILED_RETRYABLE,
                    message=f"Materialization failed for {planned_recipe.recipe_code}: {exc}",
                    blocking_reason=str(exc),
                    production_order_item_id=item.id,
                    stage_name="materialize",
                )

            materialized_recipes.append(created_recipe)
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
            self._append_event(
                production_order_id=production_order_id,
                production_order_item_id=item.id,
                stage_name="materialize",
                event_type="stage_completed",
                status=OrchestrationStatus.SUCCEEDED,
                message=f"Materialized {created_recipe.recipe_code}.",
                worker_id=worker_id,
                detail={"recipe_code": created_recipe.recipe_code},
            )
            stages = self._list_stages(production_order_id)

        if not order.preview_generation_enabled:
            return self._complete_order_from_stages(production_order_id, worker_id=worker_id)

        for created_recipe in materialized_recipes:
            checkpoint_state = self._consume_control_checkpoint(production_order_id, worker_id=worker_id)
            if checkpoint_state is not None:
                return self.get_order(production_order_id)

            if _has_successful_stage(stages, stage_name="preview", recipe_id=created_recipe.recipe_id):
                continue

            item = item_by_product_code[created_recipe.product_code]
            self._append_event(
                production_order_id=production_order_id,
                production_order_item_id=item.id,
                stage_name="preview",
                event_type="stage_started",
                status=OrchestrationStatus.PROCESSING,
                message=f"Rendering preview for {created_recipe.recipe_code}.",
                worker_id=worker_id,
                detail={"recipe_code": created_recipe.recipe_code},
            )
            preview_result = self._auto_factory_service.build_preview_for_materialized_recipe(
                created_recipe,
                batch_code=order.batch_code,
                source_mode=order.source_mode,
            )
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
                self._append_event(
                    production_order_id=production_order_id,
                    production_order_item_id=item.id,
                    stage_name="preview",
                    event_type="stage_completed",
                    status=OrchestrationStatus.SUCCEEDED,
                    message=f"Rendered preview for {created_recipe.recipe_code}.",
                    worker_id=worker_id,
                    detail={"recipe_code": created_recipe.recipe_code},
                )
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
                self._append_event(
                    production_order_id=production_order_id,
                    production_order_item_id=item.id,
                    stage_name="review",
                    event_type="stage_completed",
                    status=review_status,
                    message=(
                        f"Preview for {created_recipe.recipe_code} requires review."
                        if review_status == OrchestrationStatus.REVIEW_REQUIRED
                        else f"Preview for {created_recipe.recipe_code} cleared review."
                    ),
                    worker_id=worker_id,
                    detail={"recipe_code": created_recipe.recipe_code},
                )
            else:
                self._append_event(
                    production_order_id=production_order_id,
                    production_order_item_id=item.id,
                    stage_name="preview",
                    event_type="stage_failed",
                    status=OrchestrationStatus.FAILED_RETRYABLE,
                    message=f"Preview failed for {created_recipe.recipe_code}: {preview_result.error_message or 'unknown error'}",
                    worker_id=worker_id,
                    detail={"recipe_code": created_recipe.recipe_code},
                )
            stages = self._list_stages(production_order_id)

        return self._complete_order_from_stages(production_order_id, worker_id=worker_id)

    def _claim_order_lease(
        self,
        production_order_id: int,
        *,
        worker_id: str,
        build_previews: bool | None,
    ) -> tuple[ProductionOrder, bool, OrchestrationStatus]:
        now = utc_now()
        with self._unit_of_work_factory() as uow:
            order = self._require_order(uow, production_order_id)
            previous_status = order.status
            recovered_stale_lease = False
            if build_previews is not None:
                order.preview_generation_enabled = build_previews
            if order.status not in _RUNNABLE_ORDER_STATUSES and not (
                order.status in _ACTIVE_ORDER_STATUSES and self._lease_is_stale(order)
            ):
                raise ProductionOrderRunStateError(
                    f"Production order {order.order_code} cannot run from state {order.status.value}."
                )
            if self._lease_is_active(order) and order.lease_owner != worker_id:
                raise ProductionOrderRunStateError(
                    f"Production order {order.order_code} is already leased by another worker."
                )
            if order.lease_owner is not None and self._lease_is_stale(order):
                recovered_stale_lease = True
            order.status = OrchestrationStatus.PROCESSING
            order.started_at = order.started_at or now
            order.finished_at = None
            order.blocking_reason = None
            order.lease_owner = worker_id
            order.lease_acquired_at = now
            order.lease_heartbeat_at = now
            order.lease_expires_at = now + timedelta(seconds=_LEASE_TIMEOUT_SECONDS)
            uow.production_orders.update(order)
            uow.commit()
            return order, recovered_stale_lease, previous_status

    def _heartbeat_order(self, production_order_id: int, worker_id: str) -> None:
        now = utc_now()
        with self._unit_of_work_factory() as uow:
            order = uow.production_orders.get_by_id(production_order_id)
            if order is None or order.id is None:
                return
            if order.lease_owner != worker_id or order.status not in _ACTIVE_ORDER_STATUSES | {OrchestrationStatus.PROCESSING}:
                return
            order.lease_heartbeat_at = now
            order.lease_expires_at = now + timedelta(seconds=_LEASE_TIMEOUT_SECONDS)
            uow.production_orders.update(order)
            uow.commit()

    def _consume_control_checkpoint(
        self,
        production_order_id: int,
        *,
        worker_id: str,
    ) -> OrchestrationStatus | None:
        with self._unit_of_work_factory() as uow:
            order = self._require_order(uow, production_order_id)
            if order.lease_owner != worker_id:
                return None
            if order.status == OrchestrationStatus.PAUSE_REQUESTED:
                self._clear_lease(order)
                order.status = OrchestrationStatus.PAUSED
                uow.production_orders.update(order)
                self._append_event_in_uow(
                    uow,
                    production_order_id=production_order_id,
                    event_type="paused",
                    status=OrchestrationStatus.PAUSED,
                    message=f"Paused production order {order.order_code} at a safe checkpoint.",
                )
                uow.commit()
                return OrchestrationStatus.PAUSED
            if order.status == OrchestrationStatus.STOP_REQUESTED:
                self._clear_lease(order)
                order.status = OrchestrationStatus.STOPPED
                order.finished_at = utc_now()
                uow.production_orders.update(order)
                self._append_event_in_uow(
                    uow,
                    production_order_id=production_order_id,
                    event_type="stopped",
                    status=OrchestrationStatus.STOPPED,
                    message=f"Stopped production order {order.order_code} at a safe checkpoint.",
                )
                uow.commit()
                return OrchestrationStatus.STOPPED
        return None

    def _complete_order_from_stages(self, production_order_id: int, *, worker_id: str) -> ProductionOrderDetailsDTO:
        final_status = self._resolve_order_status(production_order_id)
        message = f"Completed production order {self.get_order(production_order_id).order_code} with status {final_status.value}."
        return self._finalize_order(
            production_order_id,
            worker_id=worker_id,
            status=final_status,
            message=message,
            blocking_reason=None if final_status == OrchestrationStatus.SUCCEEDED else _resolve_blocking_reason(self._list_stages(production_order_id), final_status),
        )

    def _finalize_order(
        self,
        production_order_id: int,
        *,
        worker_id: str,
        status: OrchestrationStatus,
        message: str,
        blocking_reason: str | None,
        production_order_item_id: int | None = None,
        stage_name: str | None = None,
    ) -> ProductionOrderDetailsDTO:
        with self._unit_of_work_factory() as uow:
            order = self._require_order(uow, production_order_id)
            self._clear_lease(order)
            order.status = status
            order.blocking_reason = blocking_reason
            if status in _FINAL_ORDER_STATUSES or status == OrchestrationStatus.STOPPED:
                order.finished_at = utc_now()
            uow.production_orders.update(order)
            self._append_event_in_uow(
                uow,
                production_order_id=production_order_id,
                production_order_item_id=production_order_item_id,
                stage_name=stage_name,
                event_type="run_completed" if status in {OrchestrationStatus.SUCCEEDED, OrchestrationStatus.REVIEW_REQUIRED} else "run_blocked",
                status=status,
                message=message,
                worker_id=worker_id,
            )
            uow.commit()
        return self.get_order(production_order_id)

    def _load_order_bundle(self, production_order_id: int) -> tuple[ProductionOrder, tuple[ProductionOrderItem, ...]]:
        with self._unit_of_work_factory() as uow:
            order = self._require_order(uow, production_order_id)
            items = tuple(uow.production_orders.list_items(production_order_id))
            return order, items

    def _list_stages(self, production_order_id: int) -> tuple[ProductionOrderStage, ...]:
        with self._unit_of_work_factory() as uow:
            return tuple(uow.production_order_stages.list_by_order(production_order_id))

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
        effective_stages = _effective_stages(self._list_stages(production_order_id))
        statuses = [stage.status for stage in effective_stages]
        if any(status == OrchestrationStatus.FAILED_TERMINAL for status in statuses):
            return OrchestrationStatus.FAILED_TERMINAL
        if any(status == OrchestrationStatus.FAILED_RETRYABLE for status in statuses):
            return OrchestrationStatus.FAILED_RETRYABLE
        if any(status == OrchestrationStatus.REVIEW_REQUIRED for status in statuses):
            return OrchestrationStatus.REVIEW_REQUIRED
        return OrchestrationStatus.SUCCEEDED

    def _append_event(
        self,
        *,
        production_order_id: int,
        event_type: str,
        status: OrchestrationStatus,
        message: str,
        production_order_item_id: int | None = None,
        stage_name: str | None = None,
        worker_id: str | None = None,
        detail: dict | None = None,
    ) -> None:
        with self._unit_of_work_factory() as uow:
            self._append_event_in_uow(
                uow,
                production_order_id=production_order_id,
                production_order_item_id=production_order_item_id,
                event_type=event_type,
                status=status,
                message=message,
                stage_name=stage_name,
                worker_id=worker_id,
                detail=detail,
            )
            uow.commit()

    def _append_event_in_uow(
        self,
        uow: UnitOfWork,
        *,
        production_order_id: int,
        event_type: str,
        status: OrchestrationStatus,
        message: str,
        production_order_item_id: int | None = None,
        stage_name: str | None = None,
        worker_id: str | None = None,
        detail: dict | None = None,
    ) -> None:
        sequence_index = len(tuple(uow.production_order_events.list_by_order(production_order_id))) + 1
        uow.production_order_events.add(
            ProductionOrderEvent(
                production_order_id=production_order_id,
                production_order_item_id=production_order_item_id,
                sequence_index=sequence_index,
                event_type=event_type,
                status=status,
                message=message,
                stage_name=stage_name,
                worker_id=worker_id,
                detail_json=None if detail is None else json.dumps(detail, sort_keys=True),
            )
        )

    def _next_sequence_index(self, production_order_id: int) -> int:
        return len(self._list_stages(production_order_id)) + 1

    def _require_order(self, uow: UnitOfWork, production_order_id: int) -> ProductionOrder:
        order = uow.production_orders.get_by_id(production_order_id)
        if order is None or order.id is None:
            raise ProductionOrderNotFoundError(str(production_order_id))
        return order

    def _new_worker_id(self) -> str:
        return f"local_auto_factory_{uuid4().hex[:12]}"

    def _lease_is_active(self, order: ProductionOrder) -> bool:
        return order.lease_owner is not None and not self._lease_is_stale(order)

    def _lease_is_stale(self, order: ProductionOrder) -> bool:
        if order.lease_owner is None or order.lease_expires_at is None:
            return False
        return order.lease_expires_at <= utc_now()

    def _clear_lease(self, order: ProductionOrder) -> None:
        order.lease_owner = None
        order.lease_acquired_at = None
        order.lease_heartbeat_at = None
        order.lease_expires_at = None


def _build_batch_order(
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


def _effective_stage_key(stage: ProductionOrderStage) -> tuple[object, ...]:
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


def _effective_stages(stages: Sequence[ProductionOrderStage]) -> tuple[ProductionOrderStage, ...]:
    latest_by_key: dict[tuple[object, ...], ProductionOrderStage] = {}
    for stage in stages:
        latest_by_key[_effective_stage_key(stage)] = stage
    return tuple(sorted(latest_by_key.values(), key=lambda item: (item.sequence_index, item.id or 0)))


def _find_materialized_recipe(
    stages: Sequence[ProductionOrderStage],
    *,
    production_order_item_id: int,
    recipe_code: str,
    product_id: int,
    product_code: str,
) -> MaterializedBatchRecipeDTO | None:
    for stage in _effective_stages(stages):
        if stage.stage_name != "materialize" or stage.status != OrchestrationStatus.SUCCEEDED:
            continue
        if stage.production_order_item_id != production_order_item_id:
            continue
        if _stage_detail_value(stage.detail_json, "recipe_code") != recipe_code or stage.recipe_id is None:
            continue
        assignment_count = int(_stage_detail_value(stage.detail_json, "assignment_count") or 0)
        return MaterializedBatchRecipeDTO(
            recipe_id=stage.recipe_id,
            product_id=product_id,
            product_code=product_code,
            recipe_code=recipe_code,
            assignment_count=assignment_count,
        )
    return None


def _has_successful_stage(
    stages: Sequence[ProductionOrderStage],
    *,
    stage_name: str,
    recipe_id: int,
) -> bool:
    for stage in _effective_stages(stages):
        if stage.stage_name == stage_name and stage.recipe_id == recipe_id and stage.status == OrchestrationStatus.SUCCEEDED:
            return True
    return False


def _resolve_blocking_reason(
    stages: Sequence[ProductionOrderStage],
    fallback_status: OrchestrationStatus,
) -> str | None:
    for stage in reversed(_effective_stages(stages)):
        if stage.failure_class:
            return stage.failure_class
        error_message = _stage_detail_value(stage.detail_json, "error_message") or _stage_detail_value(stage.detail_json, "error")
        if isinstance(error_message, str) and error_message.strip():
            return error_message
    return None if fallback_status == OrchestrationStatus.SUCCEEDED else fallback_status.value


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
