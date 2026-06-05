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


@dataclass(slots=True, frozen=True)
class DashboardSummaryDTO:
    product_count: int
    asset_count: int
    recipe_count: int
    output_count: int
    ready_asset_count: int
    needs_review_asset_count: int
    tag_count: int
    queued_job_count: int
    failed_job_count: int
    ffprobe_available: bool
    ffmpeg_available: bool
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
