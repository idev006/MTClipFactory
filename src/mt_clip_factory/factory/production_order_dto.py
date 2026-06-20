from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ProductionOrderItemDTO:
    production_order_item_id: int
    product_id: int
    product_code: str
    requested_output_count: int
    target_platform: str | None
    target_ratio: str | None
    uniqueness_scope: str
    duration_mode: str
    fixed_duration_sec: float | None
    min_duration_sec: float
    max_duration_sec: float


@dataclass(slots=True, frozen=True)
class ProductionOrderStageDTO:
    production_order_stage_id: int
    stage_name: str
    stage_scope: str
    status: str
    sequence_index: int
    production_order_item_id: int | None
    job_id: int | None
    recipe_id: int | None
    output_id: int | None
    failure_class: str | None
    detail_json: str | None
    created_at: str
    updated_at: str


@dataclass(slots=True, frozen=True)
class ProductionOrderSummaryDTO:
    production_order_id: int
    order_code: str
    batch_code: str
    source_mode: str
    requested_by: str | None
    status: str
    item_count: int
    created_at: str
    started_at: str | None
    finished_at: str | None


@dataclass(slots=True, frozen=True)
class ProductionOrderEventDTO:
    production_order_event_id: int
    sequence_index: int
    event_type: str
    status: str
    message: str
    production_order_item_id: int | None
    stage_name: str | None
    worker_id: str | None
    detail_json: str | None
    created_at: str


@dataclass(slots=True, frozen=True)
class ProductionOrderDetailsDTO:
    production_order_id: int
    order_code: str
    batch_code: str
    source_mode: str
    requested_by: str | None
    strict_fulfillment: bool
    preview_generation_enabled: bool
    run_mode: str | None
    source_root: str | None
    status: str
    lease_owner: str | None
    lease_acquired_at: str | None
    lease_heartbeat_at: str | None
    lease_expires_at: str | None
    blocking_reason: str | None
    created_at: str
    started_at: str | None
    finished_at: str | None
    items: tuple[ProductionOrderItemDTO, ...]
    stages: tuple[ProductionOrderStageDTO, ...]
    events: tuple[ProductionOrderEventDTO, ...]
