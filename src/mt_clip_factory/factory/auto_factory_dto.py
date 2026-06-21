from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class AutoFactoryProductRequestDTO:
    product_code: str
    requested_output_count: int
    target_platform: str | None = None
    target_ratio: str | None = None
    uniqueness_scope: str = "batch"
    duration_mode: str = "voice_with_bounds"
    fixed_duration_sec: float | None = None
    min_duration_sec: float = 12.0
    max_duration_sec: float = 30.0
    foreground_required_tag_labels: tuple[str, ...] = ()
    background_required_tag_labels: tuple[str, ...] = ()
    music_required_tag_labels: tuple[str, ...] = ()
    voice_required_tag_labels: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class AutoFactoryBatchOrderDTO:
    batch_code: str
    product_requests: tuple[AutoFactoryProductRequestDTO, ...]
    strict_fulfillment: bool = True


@dataclass(slots=True, frozen=True)
class PlannedBatchAssetAssignmentDTO:
    asset_id: int
    asset_code: str
    asset_type: str
    role: str


@dataclass(slots=True, frozen=True)
class PlannedBatchRecipeDTO:
    product_id: int
    product_code: str
    recipe_code: str
    request_index: int
    target_platform: str | None
    target_ratio: str | None
    duration_sec: float | None
    duration_source: str
    fingerprint: str
    fingerprint_hash: str
    assignments: tuple[PlannedBatchAssetAssignmentDTO, ...]
    near_duplicate_score: float = 0.0
    near_duplicate_reasons: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class ProductBatchPlanSummaryDTO:
    product_id: int
    product_code: str
    requested_output_count: int
    planner_feasible_unique_count: int
    planned_output_count: int
    can_fulfill_exactly: bool
    shortfall_count: int
    limiting_reason: str | None = None


@dataclass(slots=True, frozen=True)
class AutoFactoryBatchPlanDTO:
    batch_code: str
    summaries: tuple[ProductBatchPlanSummaryDTO, ...]
    planned_recipes: tuple[PlannedBatchRecipeDTO, ...]


@dataclass(slots=True, frozen=True)
class MaterializedBatchRecipeDTO:
    recipe_id: int
    product_id: int
    product_code: str
    recipe_code: str
    assignment_count: int


@dataclass(slots=True, frozen=True)
class AutoFactoryBatchMaterializationDTO:
    batch_code: str
    created_recipes: tuple[MaterializedBatchRecipeDTO, ...]


@dataclass(slots=True, frozen=True)
class AutoFactoryPreviewRecipeResultDTO:
    recipe_id: int
    product_id: int
    product_code: str
    recipe_code: str
    preview_job_id: int
    job_status: str
    recipe_status: str
    review_required: bool
    output_id: int | None = None
    output_code: str | None = None
    output_path: str | None = None
    error_message: str | None = None


@dataclass(slots=True, frozen=True)
class AutoFactoryBatchPreviewProductionDTO:
    batch_code: str
    recipe_results: tuple[AutoFactoryPreviewRecipeResultDTO, ...]
    succeeded_recipe_count: int
    failed_recipe_count: int


@dataclass(slots=True, frozen=True)
class AutoFactoryBatchExecutionDTO:
    batch_code: str
    materialization: AutoFactoryBatchMaterializationDTO
    preview_production: AutoFactoryBatchPreviewProductionDTO
