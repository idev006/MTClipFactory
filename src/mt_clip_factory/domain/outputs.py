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
    approved_by: str | None = None
    approved_at: datetime | None = None
    approval_reason: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    id: int | None = None


@dataclass(slots=True, frozen=True)
class OutputSummary:
    output_id: int
    recipe_id: int
    recipe_code: str
    output_code: str
    file_path: str
    platform: str | None
    ratio: str | None
    approved: bool
    approved_by: str | None
    approved_at: datetime | None
    approval_reason: str | None
    created_at: datetime
    quality_score: float | None = None
    duplicate_risk: float | None = None
