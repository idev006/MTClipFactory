from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from mt_clip_factory.domain.entities import utc_now


@dataclass(slots=True)
class Output:
    recipe_id: int
    output_code: str
    file_path: str
    platform: str | None = None
    ratio: str | None = None
    duration_sec: float | None = None
    quality_score: float | None = None
    duplicate_risk: float | None = None
    approved: bool = False
    created_at: datetime = field(default_factory=utc_now)
    id: int | None = None

