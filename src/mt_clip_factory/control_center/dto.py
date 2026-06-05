from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SystemSettingsDTO:
    database_path: str
    media_root: str
    docs_root: str
    outputs_root: str
    preview_root: str
    ffmpeg_root: str
    ffprobe_path: str
    ffmpeg_path: str
    cpu_limit_percent: int
    ram_limit_percent: int
    disk_free_gb_min: int
    max_preview_workers: int
    max_final_workers: int
    auto_refresh_seconds: int
    auto_recover_queued_jobs: bool
    max_recovery_jobs_per_run: int


@dataclass(slots=True, frozen=True)
class DashboardJobDTO:
    job_id: int
    job_code: str
    job_type: str
    job_source: str
    status: str
    progress: float
    subject_reference: str
    output_path: str | None = None
    error_message: str | None = None


@dataclass(slots=True, frozen=True)
class RecoveryRunSummaryDTO:
    trigger: str
    job_selection: str
    started_at: str
    finished_at: str
    matched_job_count: int
    queued_job_count: int
    attempted_job_count: int
    succeeded_job_count: int
    failed_job_count: int
    recovered_job_codes: tuple[str, ...]
    failed_job_codes: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class DashboardSummaryDTO:
    product_count: int
    asset_count: int
    recipe_count: int
    output_count: int
    ready_asset_count: int
    needs_review_asset_count: int
    tag_count: int
    total_job_count: int
    active_job_count: int
    queued_job_count: int
    processing_job_count: int
    failed_job_count: int
    generated_at: str
    ffprobe_available: bool
    ffmpeg_available: bool
    recent_jobs: tuple[DashboardJobDTO, ...]
    last_recovery_summary: RecoveryRunSummaryDTO | None
    workspace_root: str
    database_path: str
    media_root: str
    docs_root: str
    outputs_root: str
    preview_root: str
    ffprobe_path: str
    ffmpeg_path: str
    cpu_limit_percent: int
    ram_limit_percent: int
    disk_free_gb_min: int
    max_preview_workers: int
    max_final_workers: int
    auto_refresh_seconds: int
    auto_recover_queued_jobs: bool
    max_recovery_jobs_per_run: int
