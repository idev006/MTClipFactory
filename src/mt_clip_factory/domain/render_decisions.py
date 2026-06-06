from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from mt_clip_factory.domain.entities import utc_now


@dataclass(slots=True)
class RenderDecision:
    recipe_id: int
    decision_type: str
    action: str
    composition_plan_id: int | None = None
    asset_role: str | None = None
    details_json: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    id: int | None = None
