from __future__ import annotations

import logging
import threading
from datetime import timedelta
from typing import TYPE_CHECKING

from sqlalchemy.exc import OperationalError

from mt_clip_factory.domain.entities import utc_now
from mt_clip_factory.domain.enums import OrchestrationStatus

from mt_clip_factory.factory.production_order_detail_support import resolve_blocking_reason

if TYPE_CHECKING:
    from mt_clip_factory.domain.production_orders import ProductionOrder
    from mt_clip_factory.factory.production_order_dto import ProductionOrderDetailsDTO
    from mt_clip_factory.factory.production_order_service import ProductionOrderService

_LEASE_TIMEOUT_SECONDS = 60
_HEARTBEAT_INTERVAL_SECONDS = 5
_SQLITE_LOCK_MARKERS = ("database is locked", "database table is locked")
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
_LOGGER = logging.getLogger(__name__)


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
            try:
                heartbeat_order(self._service, self._production_order_id, self._worker_id)
            except Exception:  # noqa: BLE001
                _LOGGER.exception(
                    "Unexpected heartbeat failure for production order %s.",
                    self._production_order_id,
                )


def claim_order_lease(
    service: ProductionOrderService,
    production_order_id: int,
    *,
    worker_id: str,
    build_previews: bool | None,
    run_state_error_cls: type[Exception],
) -> tuple[ProductionOrder, bool, OrchestrationStatus]:
    now = utc_now()
    with service._unit_of_work_factory() as uow:  # noqa: SLF001
        order = service._require_order(uow, production_order_id)  # noqa: SLF001
        previous_status = order.status
        recovered_stale_lease = False
        if build_previews is not None:
            order.preview_generation_enabled = build_previews
        if order.status not in _RUNNABLE_ORDER_STATUSES and not (
            order.status in _ACTIVE_ORDER_STATUSES and service._lease_is_stale(order)  # noqa: SLF001
        ):
            raise run_state_error_cls(
                f"Production order {order.order_code} cannot run from state {order.status.value}."
            )
        if service._lease_is_active(order) and order.lease_owner != worker_id:  # noqa: SLF001
            raise run_state_error_cls(
                f"Production order {order.order_code} is already leased by another worker."
            )
        if order.lease_owner is not None and service._lease_is_stale(order):  # noqa: SLF001
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


def heartbeat_order(service: ProductionOrderService, production_order_id: int, worker_id: str) -> bool:
    now = utc_now()
    try:
        with service._unit_of_work_factory() as uow:  # noqa: SLF001
            order = uow.production_orders.get_by_id(production_order_id)
            if order is None or order.id is None:
                return False
            if order.lease_owner != worker_id or order.status not in _ACTIVE_ORDER_STATUSES | {OrchestrationStatus.PROCESSING}:
                return False
            order.lease_heartbeat_at = now
            order.lease_expires_at = now + timedelta(seconds=_LEASE_TIMEOUT_SECONDS)
            uow.production_orders.update(order)
            uow.commit()
            return True
    except OperationalError as exc:
        if _is_transient_sqlite_lock_error(exc):
            _LOGGER.warning(
                "Skipped one heartbeat for production order %s because SQLite was temporarily locked.",
                production_order_id,
            )
            return False
        raise


def consume_control_checkpoint(
    service: ProductionOrderService,
    production_order_id: int,
    *,
    worker_id: str,
) -> OrchestrationStatus | None:
    with service._unit_of_work_factory() as uow:  # noqa: SLF001
        order = service._require_order(uow, production_order_id)  # noqa: SLF001
        if order.lease_owner != worker_id:
            return None
        if order.status == OrchestrationStatus.PAUSE_REQUESTED:
            service._clear_lease(order)  # noqa: SLF001
            order.status = OrchestrationStatus.PAUSED
            uow.production_orders.update(order)
            service._append_event_in_uow(  # noqa: SLF001
                uow,
                production_order_id=production_order_id,
                event_type="paused",
                status=OrchestrationStatus.PAUSED,
                message=f"Paused production order {order.order_code} at a safe checkpoint.",
            )
            uow.commit()
            return OrchestrationStatus.PAUSED
        if order.status == OrchestrationStatus.STOP_REQUESTED:
            service._clear_lease(order)  # noqa: SLF001
            order.status = OrchestrationStatus.STOPPED
            order.finished_at = utc_now()
            uow.production_orders.update(order)
            service._append_event_in_uow(  # noqa: SLF001
                uow,
                production_order_id=production_order_id,
                event_type="stopped",
                status=OrchestrationStatus.STOPPED,
                message=f"Stopped production order {order.order_code} at a safe checkpoint.",
            )
            uow.commit()
            return OrchestrationStatus.STOPPED
    return None


def complete_order_from_stages(
    service: ProductionOrderService,
    production_order_id: int,
    *,
    worker_id: str,
) -> ProductionOrderDetailsDTO:
    final_status = service._resolve_order_status(production_order_id)  # noqa: SLF001
    message = f"Completed production order {service.get_order(production_order_id).order_code} with status {final_status.value}."
    return finalize_order(
        service,
        production_order_id,
        worker_id=worker_id,
        status=final_status,
        message=message,
        blocking_reason=None
        if final_status == OrchestrationStatus.SUCCEEDED
        else resolve_blocking_reason(service._list_stages(production_order_id), final_status),  # noqa: SLF001
    )


def finalize_order(
    service: ProductionOrderService,
    production_order_id: int,
    *,
    worker_id: str,
    status: OrchestrationStatus,
    message: str,
    blocking_reason: str | None,
    production_order_item_id: int | None = None,
    stage_name: str | None = None,
) -> ProductionOrderDetailsDTO:
    with service._unit_of_work_factory() as uow:  # noqa: SLF001
        order = service._require_order(uow, production_order_id)  # noqa: SLF001
        service._clear_lease(order)  # noqa: SLF001
        order.status = status
        order.blocking_reason = blocking_reason
        if status in _FINAL_ORDER_STATUSES or status == OrchestrationStatus.STOPPED:
            order.finished_at = utc_now()
        uow.production_orders.update(order)
        service._append_event_in_uow(  # noqa: SLF001
            uow,
            production_order_id=production_order_id,
            production_order_item_id=production_order_item_id,
            stage_name=stage_name,
            event_type="run_completed"
            if status in {OrchestrationStatus.SUCCEEDED, OrchestrationStatus.REVIEW_REQUIRED}
            else "run_blocked",
            status=status,
            message=message,
            worker_id=worker_id,
        )
        uow.commit()
    return service.get_order(production_order_id)


def _is_transient_sqlite_lock_error(exc: OperationalError) -> bool:
    error_text = str(exc).lower()
    return any(marker in error_text for marker in _SQLITE_LOCK_MARKERS)
