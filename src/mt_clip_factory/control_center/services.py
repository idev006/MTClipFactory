from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
import tomllib
from typing import TYPE_CHECKING

from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.config import AppConfig
from mt_clip_factory.control_center.dto import (
    DashboardJobDTO,
    DashboardSummaryDTO,
    PathRootStatusDTO,
    PathRootsDTO,
    RecoveryRunSummaryDTO,
    SystemSettingsDTO,
)
from mt_clip_factory.domain.enums import RecipeStatus
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.tag_services import TagManagementService

if TYPE_CHECKING:
    from mt_clip_factory.factory.services import VideoAssemblyFactoryService
    from mt_clip_factory.library.artifact_services import ArtifactGenerationService


class SystemSettingsService:
    def __init__(self, config_path: Path, *, runtime_path_roots: PathRootsDTO | None = None) -> None:
        self._config_path = config_path
        self._runtime_path_roots = runtime_path_roots

    def load(self) -> SystemSettingsDTO:
        data = self._read_raw()
        workspace_root = self._config_path.parent
        paths = data.get("paths", {})
        ffmpeg = data.get("ffmpeg", {})
        system = data.get("system", {})
        audio = data.get("audio", {})
        review = data.get("review", {})
        database_path = _resolve_runtime_path(workspace_root, str(paths.get("database_path", "ad_kitchen.db")))
        media_root = _resolve_runtime_path(workspace_root, str(paths.get("media_root", "media_library")))
        docs_root = _resolve_runtime_path(workspace_root, str(paths.get("docs_root", "doc")))
        outputs_root = _resolve_runtime_path(workspace_root, str(paths.get("outputs_root", "outputs")))
        preview_root = _resolve_runtime_path(workspace_root, str(paths.get("preview_root", Path(outputs_root) / "preview")))
        ffmpeg_root = str(ffmpeg.get("root", ""))
        ffprobe_path = str(ffmpeg.get("ffprobe", ""))
        ffmpeg_path = str(ffmpeg.get("ffmpeg", ""))

        if ffmpeg_root and not ffprobe_path:
            ffprobe_path = str(Path(ffmpeg_root) / "bin" / "ffprobe.exe")
        if ffmpeg_root and not ffmpeg_path:
            ffmpeg_path = str(Path(ffmpeg_root) / "bin" / "ffmpeg.exe")

        return SystemSettingsDTO(
            database_path=database_path,
            media_root=media_root,
            docs_root=docs_root,
            outputs_root=outputs_root,
            preview_root=preview_root,
            ffmpeg_root=ffmpeg_root,
            ffprobe_path=ffprobe_path,
            ffmpeg_path=ffmpeg_path,
            cpu_limit_percent=int(system.get("cpu_limit_percent", 0)),
            ram_limit_percent=int(system.get("ram_limit_percent", 0)),
            disk_free_gb_min=int(system.get("disk_free_gb_min", 0)),
            max_preview_workers=int(system.get("max_preview_workers", 0)),
            max_final_workers=int(system.get("max_final_workers", 0)),
            auto_refresh_seconds=int(system.get("auto_refresh_seconds", 0)),
            auto_recover_queued_jobs=_coerce_bool(system.get("auto_recover_queued_jobs", False)),
            max_recovery_jobs_per_run=int(system.get("max_recovery_jobs_per_run", 25)),
            failed_job_escalation_threshold=int(system.get("failed_job_escalation_threshold", 2)),
            voice_loop_enabled=_coerce_bool(audio.get("voice_loop_enabled", False)),
            background_music_loop_enabled=_coerce_bool(audio.get("background_music_loop_enabled", True)),
            music_duck_enabled=_coerce_bool(audio.get("music_duck_enabled", True)),
            music_duck_mode=str(audio.get("music_duck_mode", "sidechain_compressor")),
            music_duck_db=int(audio.get("music_duck_db", -15)),
            music_duck_attack_ms=int(audio.get("music_duck_attack_ms", 250)),
            music_duck_release_ms=int(audio.get("music_duck_release_ms", 500)),
            music_duck_threshold_db=int(audio.get("music_duck_threshold_db", -24)),
            music_duck_ratio=float(audio.get("music_duck_ratio", 8.0)),
            review_duration_mismatch_sec=int(review.get("duration_mismatch_sec", 1)),
            review_max_looped_segments=int(review.get("max_looped_segments", 2)),
            review_min_distinct_visual_assets=int(review.get("min_distinct_visual_assets", 2)),
            review_max_consecutive_same_visual_segments=int(review.get("max_consecutive_same_visual_segments", 3)),
        )

    def save(self, settings: SystemSettingsDTO) -> None:
        content = "\n".join(
            [
                "[paths]",
                f'database_path = "{_escape_toml(settings.database_path)}"',
                f'media_root = "{_escape_toml(settings.media_root)}"',
                f'docs_root = "{_escape_toml(settings.docs_root)}"',
                f'outputs_root = "{_escape_toml(settings.outputs_root)}"',
                f'preview_root = "{_escape_toml(settings.preview_root)}"',
                "",
                "[ffmpeg]",
                f'root = "{_escape_toml(settings.ffmpeg_root)}"',
                f'ffprobe = "{_escape_toml(settings.ffprobe_path)}"',
                f'ffmpeg = "{_escape_toml(settings.ffmpeg_path)}"',
                "",
                "[system]",
                f"cpu_limit_percent = {settings.cpu_limit_percent}",
                f"ram_limit_percent = {settings.ram_limit_percent}",
                f"disk_free_gb_min = {settings.disk_free_gb_min}",
                f"max_preview_workers = {settings.max_preview_workers}",
                f"max_final_workers = {settings.max_final_workers}",
                f"auto_refresh_seconds = {settings.auto_refresh_seconds}",
                f"auto_recover_queued_jobs = {_format_toml_bool(settings.auto_recover_queued_jobs)}",
                f"max_recovery_jobs_per_run = {settings.max_recovery_jobs_per_run}",
                f"failed_job_escalation_threshold = {settings.failed_job_escalation_threshold}",
                "",
                "[audio]",
                f"voice_loop_enabled = {_format_toml_bool(settings.voice_loop_enabled)}",
                f"background_music_loop_enabled = {_format_toml_bool(settings.background_music_loop_enabled)}",
                f"music_duck_enabled = {_format_toml_bool(settings.music_duck_enabled)}",
                f'music_duck_mode = "{_escape_toml(settings.music_duck_mode)}"',
                f"music_duck_db = {settings.music_duck_db}",
                f"music_duck_attack_ms = {settings.music_duck_attack_ms}",
                f"music_duck_release_ms = {settings.music_duck_release_ms}",
                f"music_duck_threshold_db = {settings.music_duck_threshold_db}",
                f"music_duck_ratio = {settings.music_duck_ratio}",
                "",
                "[review]",
                f"duration_mismatch_sec = {settings.review_duration_mismatch_sec}",
                f"max_looped_segments = {settings.review_max_looped_segments}",
                f"min_distinct_visual_assets = {settings.review_min_distinct_visual_assets}",
                f"max_consecutive_same_visual_segments = {settings.review_max_consecutive_same_visual_segments}",
                "",
            ]
        )
        self._config_path.write_text(content, encoding="utf-8")

    def update(self, **kwargs) -> SystemSettingsDTO:
        current = asdict(self.load())
        current.update(kwargs)
        updated = SystemSettingsDTO(**current)
        self.save(updated)
        return updated

    def path_root_status(self, *, configured_settings: SystemSettingsDTO | None = None) -> PathRootStatusDTO:
        settings = configured_settings or self.load()
        configured_paths = _path_roots_from_settings(settings)
        runtime_paths = self._runtime_path_roots or configured_paths
        changed_path_roots = tuple(
            path_name
            for path_name in (
                "database_path",
                "media_root",
                "docs_root",
                "outputs_root",
                "preview_root",
            )
            if getattr(runtime_paths, path_name) != getattr(configured_paths, path_name)
        )
        return PathRootStatusDTO(
            runtime_paths=runtime_paths,
            configured_paths=configured_paths,
            changed_path_roots=changed_path_roots,
            restart_required=bool(changed_path_roots),
            reload_policy="restart_required",
        )

    def _read_raw(self) -> dict:
        if not self._config_path.exists():
            return {}
        with self._config_path.open("rb") as file_handle:
            return tomllib.load(file_handle)


class DashboardService:
    def __init__(
        self,
        config: AppConfig,
        product_service: ProductApplicationService,
        asset_intake_service: AssetIntakeService,
        artifact_generation_service: ArtifactGenerationService,
        video_assembly_factory_service: VideoAssemblyFactoryService,
        tag_management_service: TagManagementService,
        system_settings_service: SystemSettingsService,
    ) -> None:
        self._config = config
        self._product_service = product_service
        self._asset_intake_service = asset_intake_service
        self._artifact_generation_service = artifact_generation_service
        self._video_assembly_factory_service = video_assembly_factory_service
        self._tag_management_service = tag_management_service
        self._system_settings_service = system_settings_service
        self._last_recovery_summary: RecoveryRunSummaryDTO | None = None

    def build_summary(self) -> DashboardSummaryDTO:
        settings = self._system_settings_service.load()
        path_root_status = self._system_settings_service.path_root_status(configured_settings=settings)
        products = self._product_service.list_products()
        assets = self._asset_intake_service.list_assets()
        recipe_count = sum(product.recipe_count for product in products)
        output_count = sum(product.output_count for product in products)
        dashboard_jobs = self._build_dashboard_jobs(
            failed_job_escalation_threshold=settings.failed_job_escalation_threshold
        )
        review_recipes = self._video_assembly_factory_service.list_recipes(status=RecipeStatus.NEEDS_REVIEW.value)
        tags = self._tag_management_service.list_tags()
        ready_asset_count = sum(1 for asset in assets if asset.status == "ready")
        needs_review_asset_count = sum(1 for asset in assets if asset.status == "needs_review")
        ffprobe_path = Path(settings.ffprobe_path)
        ffmpeg_path = Path(settings.ffmpeg_path)
        return DashboardSummaryDTO(
            product_count=len(products),
            asset_count=len(assets),
            recipe_count=recipe_count,
            output_count=output_count,
            ready_asset_count=ready_asset_count,
            needs_review_asset_count=needs_review_asset_count,
            needs_review_recipe_count=len(review_recipes),
            tag_count=len(tags),
            total_job_count=len(dashboard_jobs),
            active_job_count=sum(1 for job in dashboard_jobs if job.status in {"queued", "processing"}),
            queued_job_count=sum(1 for job in dashboard_jobs if job.status == "queued"),
            processing_job_count=sum(1 for job in dashboard_jobs if job.status == "processing"),
            failed_job_count=sum(1 for job in dashboard_jobs if job.status == "failed"),
            escalated_job_count=sum(1 for job in dashboard_jobs if job.recovery_escalated),
            generated_at=_utc_timestamp(),
            ffprobe_available=ffprobe_path.exists(),
            ffmpeg_available=ffmpeg_path.exists(),
            recent_jobs=tuple(dashboard_jobs[:8]),
            last_recovery_summary=self._last_recovery_summary,
            workspace_root=str(self._config.paths.workspace_root),
            runtime_database_path=path_root_status.runtime_paths.database_path,
            runtime_media_root=path_root_status.runtime_paths.media_root,
            runtime_docs_root=path_root_status.runtime_paths.docs_root,
            runtime_outputs_root=path_root_status.runtime_paths.outputs_root,
            runtime_preview_root=path_root_status.runtime_paths.preview_root,
            database_path=path_root_status.configured_paths.database_path,
            media_root=path_root_status.configured_paths.media_root,
            docs_root=path_root_status.configured_paths.docs_root,
            outputs_root=path_root_status.configured_paths.outputs_root,
            preview_root=path_root_status.configured_paths.preview_root,
            changed_path_roots=path_root_status.changed_path_roots,
            path_restart_required=path_root_status.restart_required,
            path_reload_policy=path_root_status.reload_policy,
            ffprobe_path=settings.ffprobe_path,
            ffmpeg_path=settings.ffmpeg_path,
            cpu_limit_percent=settings.cpu_limit_percent,
            ram_limit_percent=settings.ram_limit_percent,
            disk_free_gb_min=settings.disk_free_gb_min,
            max_preview_workers=settings.max_preview_workers,
            max_final_workers=settings.max_final_workers,
            auto_refresh_seconds=settings.auto_refresh_seconds,
            auto_recover_queued_jobs=settings.auto_recover_queued_jobs,
            max_recovery_jobs_per_run=settings.max_recovery_jobs_per_run,
            failed_job_escalation_threshold=settings.failed_job_escalation_threshold,
            voice_loop_enabled=settings.voice_loop_enabled,
            background_music_loop_enabled=settings.background_music_loop_enabled,
            music_duck_enabled=settings.music_duck_enabled,
            music_duck_mode=settings.music_duck_mode,
            music_duck_db=settings.music_duck_db,
            music_duck_attack_ms=settings.music_duck_attack_ms,
            music_duck_release_ms=settings.music_duck_release_ms,
            music_duck_threshold_db=settings.music_duck_threshold_db,
            music_duck_ratio=settings.music_duck_ratio,
            review_duration_mismatch_sec=settings.review_duration_mismatch_sec,
            review_max_looped_segments=settings.review_max_looped_segments,
            review_min_distinct_visual_assets=settings.review_min_distinct_visual_assets,
            review_max_consecutive_same_visual_segments=settings.review_max_consecutive_same_visual_segments,
            operator_playbook_lines=_build_operator_playbook_lines(dashboard_jobs),
        )

    def _build_dashboard_jobs(self, *, failed_job_escalation_threshold: int) -> list[DashboardJobDTO]:
        artifact_jobs = [
            DashboardJobDTO(
                job_id=job.job_id,
                job_code=job.job_code,
                job_type=job.job_type,
                job_source="library",
                status=job.status,
                progress=job.progress,
                subject_reference=_subject_reference("asset", job.asset_id),
                error_message=job.error_message,
                recovery_attempt_count=job.recovery_attempt_count,
                consecutive_failure_count=job.consecutive_failure_count,
                last_recovery_attempt_at=job.last_recovery_attempt_at,
                last_failure_at=job.last_failure_at,
                recovery_escalated=_is_recovery_escalated(
                    status=job.status,
                    consecutive_failure_count=job.consecutive_failure_count,
                    threshold=failed_job_escalation_threshold,
                ),
                operator_playbook=_operator_playbook_for_job(
                    job_source="library",
                    job_type=job.job_type,
                    error_message=job.error_message,
                ),
            )
            for job in self._artifact_generation_service.list_jobs()
        ]
        factory_jobs = [
            DashboardJobDTO(
                job_id=job.job_id,
                job_code=job.job_code,
                job_type=job.job_type,
                job_source="factory",
                status=job.status,
                progress=job.progress,
                subject_reference=_subject_reference("recipe", job.recipe_id),
                output_path=job.output_path,
                error_message=job.error_message,
                recovery_attempt_count=job.recovery_attempt_count,
                consecutive_failure_count=job.consecutive_failure_count,
                last_recovery_attempt_at=job.last_recovery_attempt_at,
                last_failure_at=job.last_failure_at,
                recovery_escalated=_is_recovery_escalated(
                    status=job.status,
                    consecutive_failure_count=job.consecutive_failure_count,
                    threshold=failed_job_escalation_threshold,
                ),
                operator_playbook=_operator_playbook_for_job(
                    job_source="factory",
                    job_type=job.job_type,
                    error_message=job.error_message,
                ),
            )
            for job in self._video_assembly_factory_service.list_jobs()
        ]
        return sorted([*artifact_jobs, *factory_jobs], key=lambda job: job.job_id, reverse=True)

    def recover_queued_jobs(self, *, trigger: str = "manual") -> RecoveryRunSummaryDTO:
        return self._run_job_recovery(trigger=trigger, job_selection="queued")

    def retry_failed_jobs(self, *, trigger: str = "manual") -> RecoveryRunSummaryDTO:
        return self._run_job_recovery(trigger=trigger, job_selection="failed")

    def _run_job_recovery(self, *, trigger: str, job_selection: str) -> RecoveryRunSummaryDTO:
        settings = self._system_settings_service.load()
        started_at = _utc_timestamp()
        selected_jobs = self._selected_recovery_jobs(
            job_selection=job_selection,
            failed_job_escalation_threshold=settings.failed_job_escalation_threshold,
        )
        attempted_jobs = (
            selected_jobs
            if settings.max_recovery_jobs_per_run <= 0
            else selected_jobs[: settings.max_recovery_jobs_per_run]
        )
        deferred_jobs = selected_jobs[len(attempted_jobs) :]
        recovered_job_codes: list[str] = []
        failed_job_codes: list[str] = []
        escalated_job_codes = [
            str(job["job_code"])
            for job in selected_jobs
            if bool(job.get("recovery_escalated"))
        ]

        for job in attempted_jobs:
            try:
                job["runner"](job["job_id"])
                recovered_job_codes.append(str(job["job_code"]))
            except Exception:  # noqa: BLE001
                failed_job_codes.append(str(job["job_code"]))

        summary = RecoveryRunSummaryDTO(
            trigger=trigger,
            job_selection=job_selection,
            started_at=started_at,
            finished_at=_utc_timestamp(),
            matched_job_count=len(selected_jobs),
            queued_job_count=len(selected_jobs) if job_selection == "queued" else 0,
            attempted_job_count=len(attempted_jobs),
            deferred_job_count=len(deferred_jobs),
            succeeded_job_count=len(recovered_job_codes),
            failed_job_count=len(failed_job_codes),
            escalated_job_count=len(escalated_job_codes),
            recovered_job_codes=tuple(recovered_job_codes),
            failed_job_codes=tuple(failed_job_codes),
            deferred_job_codes=tuple(str(job["job_code"]) for job in deferred_jobs),
            escalated_job_codes=tuple(escalated_job_codes),
        )
        self._last_recovery_summary = summary
        return summary

    def should_auto_recover_queued_jobs(self) -> bool:
        return self._system_settings_service.load().auto_recover_queued_jobs

    def _selected_recovery_jobs(
        self,
        *,
        job_selection: str,
        failed_job_escalation_threshold: int,
    ) -> list[dict[str, object]]:
        if job_selection == "queued":
            return self._queued_recovery_jobs()
        if job_selection == "failed":
            return self._failed_retry_jobs(
                failed_job_escalation_threshold=failed_job_escalation_threshold
            )
        raise ValueError(f"Unsupported recovery selection: {job_selection}")

    def _queued_recovery_jobs(self) -> list[dict[str, object]]:
        jobs: list[dict[str, object]] = []
        jobs.extend(
            {
                "job_id": job.job_id,
                "job_code": job.job_code,
                "runner": self._artifact_generation_service.run_job,
                "recovery_escalated": False,
                "consecutive_failure_count": job.consecutive_failure_count,
            }
            for job in self._artifact_generation_service.list_jobs(status="queued")
        )
        jobs.extend(
            {
                "job_id": job.job_id,
                "job_code": job.job_code,
                "runner": self._video_assembly_factory_service.run_preview_job,
                "recovery_escalated": False,
                "consecutive_failure_count": job.consecutive_failure_count,
            }
            for job in self._video_assembly_factory_service.list_preview_jobs(status="queued")
        )
        jobs.extend(
            {
                "job_id": job.job_id,
                "job_code": job.job_code,
                "runner": self._video_assembly_factory_service.run_final_render_job,
                "recovery_escalated": False,
                "consecutive_failure_count": job.consecutive_failure_count,
            }
            for job in self._video_assembly_factory_service.list_final_render_jobs(status="queued")
        )
        return jobs

    def _failed_retry_jobs(self, *, failed_job_escalation_threshold: int) -> list[dict[str, object]]:
        jobs: list[dict[str, object]] = []
        jobs.extend(
            {
                "job_id": job.job_id,
                "job_code": job.job_code,
                "runner": self._artifact_generation_service.retry_job,
                "recovery_escalated": _is_recovery_escalated(
                    status=job.status,
                    consecutive_failure_count=job.consecutive_failure_count,
                    threshold=failed_job_escalation_threshold,
                ),
                "consecutive_failure_count": job.consecutive_failure_count,
            }
            for job in self._artifact_generation_service.list_jobs(status="failed")
        )
        jobs.extend(
            {
                "job_id": job.job_id,
                "job_code": job.job_code,
                "runner": self._video_assembly_factory_service.retry_job,
                "recovery_escalated": _is_recovery_escalated(
                    status=job.status,
                    consecutive_failure_count=job.consecutive_failure_count,
                    threshold=failed_job_escalation_threshold,
                ),
                "consecutive_failure_count": job.consecutive_failure_count,
            }
            for job in self._video_assembly_factory_service.list_jobs(status="failed")
        )
        return sorted(
            jobs,
            key=lambda job: (
                bool(job["recovery_escalated"]),
                int(job["consecutive_failure_count"]),
                -int(job["job_id"]),
            ),
        )


def _escape_toml(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _format_toml_bool(value: bool) -> str:
    return "true" if value else "false"


def _resolve_runtime_path(workspace_root: Path, raw_value: str) -> str:
    path = Path(raw_value)
    if path.is_absolute():
        return str(path)
    return str(workspace_root / path)


def _subject_reference(kind: str, subject_id: int | None) -> str:
    return f"{kind}#{subject_id}" if subject_id is not None else f"{kind}#-"


def _path_roots_from_settings(settings: SystemSettingsDTO) -> PathRootsDTO:
    return PathRootsDTO(
        database_path=settings.database_path,
        media_root=settings.media_root,
        docs_root=settings.docs_root,
        outputs_root=settings.outputs_root,
        preview_root=settings.preview_root,
    )


def _is_recovery_escalated(*, status: str, consecutive_failure_count: int, threshold: int) -> bool:
    return status == "failed" and threshold > 0 and consecutive_failure_count >= threshold


def _operator_playbook_for_job(*, job_source: str, job_type: str, error_message: str | None) -> str | None:
    if error_message is None:
        return None
    normalized = error_message.lower()
    if "ffmpeg" in normalized or "ffprobe" in normalized or "not found" in normalized:
        return "Verify FFmpeg or source-path configuration before retrying this job."
    if "no items" in normalized or "no renderable video assets" in normalized:
        return "Add or repair the recipe's required media inputs before retrying this render."
    if "approve" in normalized:
        return "Complete the required approval step before retrying final delivery."
    if job_source == "library":
        return "Inspect the asset source file, metadata readiness, and writable cache paths before retrying."
    if job_type == "render_recipe_final":
        return "Confirm approved preview lineage, output roots, and render prerequisites before retrying."
    if job_type == "render_recipe_preview":
        return "Inspect recipe composition inputs, preview manifests, and source media paths before retrying."
    return "Inspect the persisted job inputs, dependencies, and writable output paths before retrying."


def _build_operator_playbook_lines(jobs: list[DashboardJobDTO]) -> tuple[str, ...]:
    lines: list[str] = []
    seen: set[str] = set()
    for job in jobs:
        if job.status != "failed" or job.operator_playbook is None:
            continue
        prefix = "Escalated" if job.recovery_escalated else "Failed"
        line = f"{prefix} {job.job_code}: {job.operator_playbook}"
        if line in seen:
            continue
        seen.add(line)
        lines.append(line)
    return tuple(lines[:5])


def _utc_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
