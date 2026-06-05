from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ArtifactJobSummaryDTO:
    job_id: int
    job_code: str
    job_type: str
    status: str
    asset_id: int | None
    progress: float
    error_message: str | None = None

