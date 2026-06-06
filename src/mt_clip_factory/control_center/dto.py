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
    failed_job_escalation_threshold: int
    voice_loop_enabled: bool
    background_music_loop_enabled: bool
    music_duck_enabled: bool
    music_duck_mode: str = "sidechain_compressor"
    music_duck_db: int = -15
    music_duck_attack_ms: int = 250
    music_duck_release_ms: int = 500
    music_duck_threshold_db: int = -24
    music_duck_ratio: float = 8.0
    voice_mix_gain_db: int = 0
    music_mix_gain_db: int = -4
    review_duration_mismatch_sec: int = 1
    review_max_looped_segments: int = 2
    review_min_distinct_visual_assets: int = 2
    review_max_consecutive_same_visual_segments: int = 3


@dataclass(slots=True, frozen=True)
class PathRootsDTO:
    database_path: str
    media_root: str
    docs_root: str
    outputs_root: str
    preview_root: str


@dataclass(slots=True, frozen=True)
class PathRootStatusDTO:
    runtime_paths: PathRootsDTO
    configured_paths: PathRootsDTO
    changed_path_roots: tuple[str, ...]
    restart_required: bool
    reload_policy: str


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
    recovery_attempt_count: int = 0
    consecutive_failure_count: int = 0
    last_recovery_attempt_at: str | None = None
    last_failure_at: str | None = None
    recovery_escalated: bool = False
    operator_playbook: str | None = None


@dataclass(slots=True, frozen=True)
class RecoveryRunSummaryDTO:
    trigger: str
    job_selection: str
    started_at: str
    finished_at: str
    matched_job_count: int
    queued_job_count: int
    attempted_job_count: int
    deferred_job_count: int
    succeeded_job_count: int
    failed_job_count: int
    escalated_job_count: int
    recovered_job_codes: tuple[str, ...]
    failed_job_codes: tuple[str, ...]
    deferred_job_codes: tuple[str, ...]
    escalated_job_codes: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class DashboardSummaryDTO:
    product_count: int
    asset_count: int
    recipe_count: int
    output_count: int
    ready_asset_count: int
    needs_review_asset_count: int
    needs_review_recipe_count: int
    tag_count: int
    total_job_count: int
    active_job_count: int
    queued_job_count: int
    processing_job_count: int
    failed_job_count: int
    escalated_job_count: int
    generated_at: str
    ffprobe_available: bool
    ffmpeg_available: bool
    recent_jobs: tuple[DashboardJobDTO, ...]
    last_recovery_summary: RecoveryRunSummaryDTO | None
    workspace_root: str
    runtime_database_path: str
    runtime_media_root: str
    runtime_docs_root: str
    runtime_outputs_root: str
    runtime_preview_root: str
    database_path: str
    media_root: str
    docs_root: str
    outputs_root: str
    preview_root: str
    changed_path_roots: tuple[str, ...]
    path_restart_required: bool
    path_reload_policy: str
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
    failed_job_escalation_threshold: int
    voice_loop_enabled: bool
    background_music_loop_enabled: bool
    music_duck_enabled: bool
    music_duck_mode: str
    music_duck_db: int
    music_duck_attack_ms: int
    music_duck_release_ms: int
    music_duck_threshold_db: int
    music_duck_ratio: float
    voice_mix_gain_db: int
    music_mix_gain_db: int
    review_duration_mismatch_sec: int
    review_max_looped_segments: int
    review_min_distinct_visual_assets: int
    review_max_consecutive_same_visual_segments: int
    operator_playbook_lines: tuple[str, ...]
