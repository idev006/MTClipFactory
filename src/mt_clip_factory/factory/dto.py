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
class OutputSummaryDTO:
    output_id: int
    recipe_id: int
    recipe_code: str
    output_code: str
    file_path: str
    platform: str | None
    ratio: str | None
    approved: bool
