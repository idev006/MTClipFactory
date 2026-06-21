from __future__ import annotations

import sqlite3
from collections.abc import Callable

import pytest
from sqlalchemy.exc import OperationalError

from mt_clip_factory.domain.entities import utc_now
from mt_clip_factory.domain.enums import OrchestrationStatus
from mt_clip_factory.domain.production_orders import ProductionOrder
from mt_clip_factory.factory.production_order_run_support import heartbeat_order


class _FakeProductionOrderRepository:
    def __init__(self, order: ProductionOrder | None, *, update_error: OperationalError | None = None) -> None:
        self._order = order
        self._update_error = update_error
        self.update_calls = 0

    def get_by_id(self, production_order_id: int) -> ProductionOrder | None:
        del production_order_id
        return self._order

    def update(self, order: ProductionOrder) -> ProductionOrder:
        self.update_calls += 1
        if self._update_error is not None:
            raise self._update_error
        self._order = order
        return order


class _FakeUnitOfWork:
    def __init__(self, repository: _FakeProductionOrderRepository) -> None:
        self.production_orders = repository
        self.commit_calls = 0

    def __enter__(self) -> _FakeUnitOfWork:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb

    def commit(self) -> None:
        self.commit_calls += 1


class _FakeService:
    def __init__(self, uow_factory: Callable[[], _FakeUnitOfWork]) -> None:
        self._unit_of_work_factory = uow_factory


def _build_active_order() -> ProductionOrder:
    now = utc_now()
    return ProductionOrder(
        order_code="order_001",
        batch_code="batch_001",
        source_mode="manual_batch",
        status=OrchestrationStatus.PROCESSING,
        lease_owner="worker_a",
        lease_acquired_at=now,
        lease_heartbeat_at=now,
        lease_expires_at=now,
        id=18,
    )


def _build_operational_error(message: str) -> OperationalError:
    return OperationalError(
        "UPDATE production_orders SET lease_heartbeat_at=?, lease_expires_at=? WHERE production_orders.id = ?",
        {},
        sqlite3.OperationalError(message),
    )


def test_heartbeat_order_ignores_transient_sqlite_lock_error() -> None:
    repository = _FakeProductionOrderRepository(
        _build_active_order(),
        update_error=_build_operational_error("database is locked"),
    )
    service = _FakeService(lambda: _FakeUnitOfWork(repository))

    result = heartbeat_order(service, 18, "worker_a")

    assert result is False
    assert repository.update_calls == 1


def test_heartbeat_order_reraises_non_lock_operational_error() -> None:
    repository = _FakeProductionOrderRepository(
        _build_active_order(),
        update_error=_build_operational_error("disk I/O error"),
    )
    service = _FakeService(lambda: _FakeUnitOfWork(repository))

    with pytest.raises(OperationalError):
        heartbeat_order(service, 18, "worker_a")


def test_heartbeat_order_updates_active_leased_order() -> None:
    repository = _FakeProductionOrderRepository(_build_active_order())
    service = _FakeService(lambda: _FakeUnitOfWork(repository))

    result = heartbeat_order(service, 18, "worker_a")

    assert result is True
    assert repository.update_calls == 1
    assert repository.get_by_id(18) is not None
    assert repository.get_by_id(18).lease_heartbeat_at is not None
    assert repository.get_by_id(18).lease_expires_at is not None
