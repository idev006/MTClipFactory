from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from mt_clip_factory.domain.entities import utc_now
from mt_clip_factory.domain.enums import JobStatus


@dataclass(slots=True)
class Job:
    job_code: str
    job_type: str
    recipe_id: int | None = None
    asset_id: int | None = None
    status: JobStatus = JobStatus.PENDING
    priority: int = 5
    progress: float = 0.0
    worker_id: str | None = None
    input_json: str | None = None
    output_json: str | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    id: int | None = None


@dataclass(slots=True, frozen=True)
class JobSummary:
    job_id: int
    job_code: str
    job_type: str
    status: JobStatus
    asset_id: int | None
    recipe_id: int | None
    progress: float
    error_message: str | None = None
