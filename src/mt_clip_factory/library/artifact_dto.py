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
    recovery_attempt_count: int = 0
    consecutive_failure_count: int = 0
    last_recovery_attempt_at: str | None = None
    last_failure_at: str | None = None
