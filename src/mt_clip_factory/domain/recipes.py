from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from mt_clip_factory.domain.entities import utc_now
from mt_clip_factory.domain.enums import RecipeStatus


@dataclass(slots=True)
class Recipe:
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
    recipe_score: float = 0.0
    duplicate_risk: float = 0.0
    status: RecipeStatus = RecipeStatus.CANDIDATE
    decision_actor: str | None = None
    decision_at: datetime | None = None
    decision_reason: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    id: int | None = None


@dataclass(slots=True)
class RecipeItem:
    recipe_id: int
    asset_id: int
    role: str
    asset_code: str | None = None
    asset_type: str | None = None
    id: int | None = None


@dataclass(slots=True, frozen=True)
class RecipeSummary:
    recipe_id: int
    product_id: int
    product_code: str
    recipe_code: str
    target_platform: str | None
    target_ratio: str | None
    status: RecipeStatus
    decision_actor: str | None
    decision_at: datetime | None
    item_count: int
    recipe_score: float = 0.0
    duplicate_risk: float = 0.0
