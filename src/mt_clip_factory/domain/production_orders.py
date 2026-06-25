from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from mt_clip_factory.domain.entities import utc_now
from mt_clip_factory.domain.enums import OrchestrationStatus


@dataclass(slots=True)
class ProductionOrder:
    order_code: str
    batch_code: str
    source_mode: str
    requested_by: str | None = None
    strict_fulfillment: bool = True
    preview_generation_enabled: bool = True
    run_mode: str | None = None
    source_root: str | None = None
    status: OrchestrationStatus = OrchestrationStatus.QUEUED
    lease_owner: str | None = None
    lease_acquired_at: datetime | None = None
    lease_heartbeat_at: datetime | None = None
    lease_expires_at: datetime | None = None
    blocking_reason: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    id: int | None = None


@dataclass(slots=True)
class ProductionOrderItem:
    production_order_id: int
    product_id: int
    product_code_snapshot: str
    requested_output_count: int
    target_platform: str | None = None
    target_ratio: str | None = None
    uniqueness_scope: str = "batch"
    duration_mode: str = "voice_with_bounds"
    fixed_duration_sec: float | None = None
    min_duration_sec: float = 12.0
    max_duration_sec: float = 30.0
    id: int | None = None


@dataclass(slots=True)
class ProductionOrderStage:
    production_order_id: int
    stage_name: str
    stage_scope: str
    status: OrchestrationStatus
    sequence_index: int
    production_order_item_id: int | None = None
    job_id: int | None = None
    recipe_id: int | None = None
    output_id: int | None = None
    failure_class: str | None = None
    detail_json: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    id: int | None = None


@dataclass(slots=True)
class ProductionOrderEvent:
    production_order_id: int
    sequence_index: int
    event_type: str
    status: OrchestrationStatus
    message: str
    production_order_item_id: int | None = None
    stage_name: str | None = None
    worker_id: str | None = None
    detail_json: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    id: int | None = None


@dataclass(slots=True, frozen=True)
class ProductionOrderSummary:
    production_order_id: int
    order_code: str
    batch_code: str
    source_mode: str
    requested_by: str | None
    status: OrchestrationStatus
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    item_count: int
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
