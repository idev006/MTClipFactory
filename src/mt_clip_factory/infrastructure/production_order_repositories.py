from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mt_clip_factory.domain.enums import OrchestrationStatus
from mt_clip_factory.domain.production_orders import (
    ProductionOrderEvent,
    ProductionOrder,
    ProductionOrderItem,
    ProductionOrderStage,
    ProductionOrderSummary,
)
from mt_clip_factory.infrastructure.models import (
    ProductionOrderEventModel,
    ProductionOrderItemModel,
    ProductionOrderModel,
    ProductionOrderStageModel,
)


class SqlAlchemyProductionOrderRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, order: ProductionOrder) -> ProductionOrder:
        model = ProductionOrderModel(
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
            lease_acquired_at=order.lease_acquired_at,
            lease_heartbeat_at=order.lease_heartbeat_at,
            lease_expires_at=order.lease_expires_at,
            blocking_reason=order.blocking_reason,
            created_at=order.created_at,
            started_at=order.started_at,
            finished_at=order.finished_at,
        )
        self._session.add(model)
        self._session.flush()
        order.id = model.id
        return order

    def get_by_id(self, production_order_id: int) -> ProductionOrder | None:
        model = self._session.get(ProductionOrderModel, production_order_id)
        return None if model is None else _to_order(model)

    def get_by_code(self, order_code: str) -> ProductionOrder | None:
        statement = select(ProductionOrderModel).where(ProductionOrderModel.order_code == order_code)
        model = self._session.execute(statement).scalar_one_or_none()
        return None if model is None else _to_order(model)

    def update(self, order: ProductionOrder) -> ProductionOrder:
        if order.id is None:
            raise ValueError("Production order id is required for update.")
        model = self._session.get(ProductionOrderModel, order.id)
        if model is None:
            raise ValueError(f"Unknown production order id: {order.id}")
        model.status = order.status.value
        model.requested_by = order.requested_by
        model.preview_generation_enabled = order.preview_generation_enabled
        model.run_mode = order.run_mode
        model.source_root = order.source_root
        model.lease_owner = order.lease_owner
        model.lease_acquired_at = order.lease_acquired_at
        model.lease_heartbeat_at = order.lease_heartbeat_at
        model.lease_expires_at = order.lease_expires_at
        model.blocking_reason = order.blocking_reason
        model.started_at = order.started_at
        model.finished_at = order.finished_at
        self._session.flush()
        return order

    def list_summaries(self, *, status: str | None = None) -> Sequence[ProductionOrderSummary]:
        statement = (
            select(
                ProductionOrderModel.id,
                ProductionOrderModel.order_code,
                ProductionOrderModel.batch_code,
                ProductionOrderModel.source_mode,
                ProductionOrderModel.requested_by,
                ProductionOrderModel.status,
                ProductionOrderModel.created_at,
                ProductionOrderModel.started_at,
                ProductionOrderModel.finished_at,
                func.count(ProductionOrderItemModel.id).label("item_count"),
            )
            .outerjoin(ProductionOrderItemModel, ProductionOrderItemModel.production_order_id == ProductionOrderModel.id)
            .group_by(
                ProductionOrderModel.id,
                ProductionOrderModel.order_code,
                ProductionOrderModel.batch_code,
                ProductionOrderModel.source_mode,
                ProductionOrderModel.requested_by,
                ProductionOrderModel.status,
                ProductionOrderModel.created_at,
                ProductionOrderModel.started_at,
                ProductionOrderModel.finished_at,
            )
            .order_by(ProductionOrderModel.created_at.desc(), ProductionOrderModel.id.desc())
        )
        if status is not None:
            statement = statement.where(ProductionOrderModel.status == status)
        rows = self._session.execute(statement).all()
        return [
            ProductionOrderSummary(
                production_order_id=row.id,
                order_code=row.order_code,
                batch_code=row.batch_code,
                source_mode=row.source_mode,
                requested_by=row.requested_by,
                status=OrchestrationStatus(row.status),
                created_at=row.created_at,
                started_at=row.started_at,
                finished_at=row.finished_at,
                item_count=row.item_count,
            )
            for row in rows
        ]

    def add_item(self, item: ProductionOrderItem) -> ProductionOrderItem:
        model = ProductionOrderItemModel(
            production_order_id=item.production_order_id,
            product_id=item.product_id,
            product_code_snapshot=item.product_code_snapshot,
            requested_output_count=item.requested_output_count,
            target_platform=item.target_platform,
            target_ratio=item.target_ratio,
            uniqueness_scope=item.uniqueness_scope,
            duration_mode=item.duration_mode,
            fixed_duration_sec=item.fixed_duration_sec,
            min_duration_sec=item.min_duration_sec,
            max_duration_sec=item.max_duration_sec,
        )
        self._session.add(model)
        self._session.flush()
        item.id = model.id
        return item

    def list_items(self, production_order_id: int) -> Sequence[ProductionOrderItem]:
        statement = (
            select(ProductionOrderItemModel)
            .where(ProductionOrderItemModel.production_order_id == production_order_id)
            .order_by(ProductionOrderItemModel.id.asc())
        )
        rows = self._session.execute(statement).scalars().all()
        return [_to_item(row) for row in rows]


class SqlAlchemyProductionOrderStageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, stage: ProductionOrderStage) -> ProductionOrderStage:
        model = ProductionOrderStageModel(
            production_order_id=stage.production_order_id,
            production_order_item_id=stage.production_order_item_id,
            stage_name=stage.stage_name,
            stage_scope=stage.stage_scope,
            status=stage.status.value,
            sequence_index=stage.sequence_index,
            job_id=stage.job_id,
            recipe_id=stage.recipe_id,
            output_id=stage.output_id,
            failure_class=stage.failure_class,
            detail_json=stage.detail_json,
            created_at=stage.created_at,
            updated_at=stage.updated_at,
        )
        self._session.add(model)
        self._session.flush()
        stage.id = model.id
        return stage

    def update(self, stage: ProductionOrderStage) -> ProductionOrderStage:
        if stage.id is None:
            raise ValueError("Production order stage id is required for update.")
        model = self._session.get(ProductionOrderStageModel, stage.id)
        if model is None:
            raise ValueError(f"Unknown production order stage id: {stage.id}")
        model.status = stage.status.value
        model.job_id = stage.job_id
        model.recipe_id = stage.recipe_id
        model.output_id = stage.output_id
        model.failure_class = stage.failure_class
        model.detail_json = stage.detail_json
        model.updated_at = stage.updated_at
        self._session.flush()
        return stage

    def list_by_order(
        self,
        production_order_id: int,
        *,
        stage_name: str | None = None,
    ) -> Sequence[ProductionOrderStage]:
        statement = (
            select(ProductionOrderStageModel)
            .where(ProductionOrderStageModel.production_order_id == production_order_id)
            .order_by(ProductionOrderStageModel.sequence_index.asc(), ProductionOrderStageModel.id.asc())
        )
        if stage_name is not None:
            statement = statement.where(ProductionOrderStageModel.stage_name == stage_name)
        rows = self._session.execute(statement).scalars().all()
        return [_to_stage(row) for row in rows]


class SqlAlchemyProductionOrderEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, event: ProductionOrderEvent) -> ProductionOrderEvent:
        model = ProductionOrderEventModel(
            production_order_id=event.production_order_id,
            production_order_item_id=event.production_order_item_id,
            sequence_index=event.sequence_index,
            event_type=event.event_type,
            status=event.status.value,
            message=event.message,
            stage_name=event.stage_name,
            worker_id=event.worker_id,
            detail_json=event.detail_json,
            created_at=event.created_at,
        )
        self._session.add(model)
        self._session.flush()
        event.id = model.id
        return event

    def list_by_order(self, production_order_id: int) -> Sequence[ProductionOrderEvent]:
        statement = (
            select(ProductionOrderEventModel)
            .where(ProductionOrderEventModel.production_order_id == production_order_id)
            .order_by(ProductionOrderEventModel.sequence_index.asc(), ProductionOrderEventModel.id.asc())
        )
        rows = self._session.execute(statement).scalars().all()
        return [_to_event(row) for row in rows]


def _to_order(model: ProductionOrderModel) -> ProductionOrder:
    return ProductionOrder(
        id=model.id,
        order_code=model.order_code,
        batch_code=model.batch_code,
        source_mode=model.source_mode,
        requested_by=model.requested_by,
        strict_fulfillment=model.strict_fulfillment,
        preview_generation_enabled=model.preview_generation_enabled,
        run_mode=model.run_mode,
        source_root=model.source_root,
        status=OrchestrationStatus(model.status),
        lease_owner=model.lease_owner,
        lease_acquired_at=model.lease_acquired_at,
        lease_heartbeat_at=model.lease_heartbeat_at,
        lease_expires_at=model.lease_expires_at,
        blocking_reason=model.blocking_reason,
        created_at=model.created_at,
        started_at=model.started_at,
        finished_at=model.finished_at,
    )


def _to_item(model: ProductionOrderItemModel) -> ProductionOrderItem:
    return ProductionOrderItem(
        id=model.id,
        production_order_id=model.production_order_id,
        product_id=model.product_id,
        product_code_snapshot=model.product_code_snapshot,
        requested_output_count=model.requested_output_count,
        target_platform=model.target_platform,
        target_ratio=model.target_ratio,
        uniqueness_scope=model.uniqueness_scope,
        duration_mode=model.duration_mode,
        fixed_duration_sec=model.fixed_duration_sec,
        min_duration_sec=model.min_duration_sec,
        max_duration_sec=model.max_duration_sec,
    )


def _to_stage(model: ProductionOrderStageModel) -> ProductionOrderStage:
    return ProductionOrderStage(
        id=model.id,
        production_order_id=model.production_order_id,
        production_order_item_id=model.production_order_item_id,
        stage_name=model.stage_name,
        stage_scope=model.stage_scope,
        status=OrchestrationStatus(model.status),
        sequence_index=model.sequence_index,
        job_id=model.job_id,
        recipe_id=model.recipe_id,
        output_id=model.output_id,
        failure_class=model.failure_class,
        detail_json=model.detail_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_event(model: ProductionOrderEventModel) -> ProductionOrderEvent:
    return ProductionOrderEvent(
        id=model.id,
        production_order_id=model.production_order_id,
        production_order_item_id=model.production_order_item_id,
        sequence_index=model.sequence_index,
        event_type=model.event_type,
        status=OrchestrationStatus(model.status),
        message=model.message,
        stage_name=model.stage_name,
        worker_id=model.worker_id,
        detail_json=model.detail_json,
        created_at=model.created_at,
    )
