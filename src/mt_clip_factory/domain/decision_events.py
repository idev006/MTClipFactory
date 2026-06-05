from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from mt_clip_factory.domain.entities import utc_now


@dataclass(slots=True)
class DecisionEvent:
    recipe_id: int
    event_type: str
    actor: str
    output_id: int | None = None
    reason: str | None = None
    output_code: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    id: int | None = None
