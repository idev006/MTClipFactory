from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CreateRecipeCommand:
    product_id: int
    recipe_code: str
    target_platform: str | None = None
    target_ratio: str | None = None
    duration_sec: float | None = None
    mood: str | None = None
    script_angle: str | None = None
    target_audience: str | None = None
    hook_text: str | None = None
    cta_text: str | None = None


@dataclass(slots=True, frozen=True)
class AssignAssetToRecipeCommand:
    recipe_id: int
    asset_id: int
    role: str


@dataclass(slots=True, frozen=True)
class RecipeItemDTO:
    recipe_item_id: int
    asset_id: int
    asset_code: str | None
    asset_type: str | None
    role: str


@dataclass(slots=True, frozen=True)
class RecipeSummaryDTO:
    recipe_id: int
    product_id: int
    product_code: str
    recipe_code: str
    target_platform: str | None
    target_ratio: str | None
    status: str
    decision_actor: str | None
    decision_at: str | None
    item_count: int


@dataclass(slots=True, frozen=True)
class RecipeDetailsDTO:
    recipe_id: int
    product_id: int
    recipe_code: str
    target_platform: str | None
    target_ratio: str | None
    duration_sec: float | None
    mood: str | None
    script_angle: str | None
    target_audience: str | None
    hook_text: str | None
    cta_text: str | None
    status: str
    decision_actor: str | None
    decision_at: str | None
    decision_reason: str | None
    items: tuple[RecipeItemDTO, ...]


@dataclass(slots=True, frozen=True)
class PreviewJobSummaryDTO:
    job_id: int
    job_code: str
    recipe_id: int | None
    job_type: str
    status: str
    progress: float
    output_path: str | None
    error_message: str | None = None


@dataclass(slots=True, frozen=True)
class DecisionEventDTO:
    event_id: int
    recipe_id: int
    event_type: str
    actor: str
    created_at: str
    output_id: int | None = None
    output_code: str | None = None
    reason: str | None = None


@dataclass(slots=True, frozen=True)
class CompositionLayerDTO:
    layer_name: str
    asset_ids: tuple[int, ...]
    asset_codes: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class RenderDecisionDTO:
    decision_id: int
    decision_type: str
    action: str
    created_at: str
    asset_role: str | None = None
    details_json: str | None = None


@dataclass(slots=True, frozen=True)
class CompositionPlanDTO:
    plan_id: int
    recipe_id: int
    duration_source: str
    target_duration_sec: float | None
    resolved_duration_sec: float | None
    updated_at: str
    layers: tuple[CompositionLayerDTO, ...]
    decisions: tuple[RenderDecisionDTO, ...]


@dataclass(slots=True, frozen=True)
class OutputSummaryDTO:
    output_id: int
    recipe_id: int
    recipe_code: str
    output_code: str
    file_path: str
    platform: str | None
    ratio: str | None
    approved: bool
    created_at: str
    approved_by: str | None
    approved_at: str | None
    approval_reason: str | None
    output_kind: str
    rendering_job_code: str | None
    manifest_path: str | None = None
    source_output_id: int | None = None
    source_output_code: str | None = None
    source_output_path: str | None = None
