from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from mt_clip_factory.domain.entities import utc_now


@dataclass(slots=True, frozen=True)
class CompositionLayerAssignment:
    layer_name: str
    asset_ids: tuple[int, ...]
    asset_codes: tuple[str, ...]


@dataclass(slots=True)
class CompositionPlan:
    recipe_id: int
    duration_source: str
    target_duration_sec: float | None = None
    resolved_duration_sec: float | None = None
    layer_assignments: tuple[CompositionLayerAssignment, ...] = ()
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    id: int | None = None
