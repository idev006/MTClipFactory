from __future__ import annotations

from pathlib import Path

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.config import default_config
from mt_clip_factory.control_center.dto import DashboardJobDTO, PathRootsDTO, SystemSettingsDTO
from mt_clip_factory.control_center.services import DashboardService, SystemSettingsService
from mt_clip_factory.factory.dto import PreviewJobSummaryDTO
from mt_clip_factory.library.artifact_dto import ArtifactJobSummaryDTO
from mt_clip_factory.library.dto import RegisterAssetCommand
from mt_clip_factory.library.readiness import AssetReadinessEvaluator
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.storage import LocalAssetStorage
from mt_clip_factory.library.tag_dto import CreateTagCommand
from mt_clip_factory.library.tag_services import TagManagementService
from mt_clip_factory.library.contracts import AnalyzedMediaMetadata


class FakeMetadataAnalyzer:
    def analyze(self, file_path: Path) -> AnalyzedMediaMetadata:
        return AnalyzedMediaMetadata(
            duration_sec=1.0,
            width=1920,
            height=1080,
            fps=30.0,
            ratio="16:9",
            file_size_mb=round(file_path.stat().st_size / (1024 * 1024), 4),
            codec="h264",
            has_audio=True,
        )


class FakeArtifactGenerationService:
    def __init__(
        self,
        queued_count: int = 0,
        failed_count: int = 0,
        *,
        failed_failure_streaks: list[int] | None = None,
    ) -> None:
        failed_failure_streaks = failed_failure_streaks or []
        self._queued_jobs = [
            ArtifactJobSummaryDTO(
                job_id=index + 1,
                job_code=f"queued_{index + 1}",
                job_type="generate_thumbnail",
                status="queued",
                asset_id=1,
                progress=0.0,
            )
            for index in range(queued_count)
        ]
        self._failed_jobs = [
            ArtifactJobSummaryDTO(
                job_id=queued_count + index + 1,
                job_code=f"failed_{index + 1}",
                job_type="generate_proxy",
                status="failed",
                asset_id=1,
                progress=0.0,
                error_message="job failed",
                consecutive_failure_count=(
                    failed_failure_streaks[index] if index < len(failed_failure_streaks) else 1
                ),
            )
            for index in range(failed_count)
        ]

    def list_jobs(self, *, status: str | None = None) -> list[ArtifactJobSummaryDTO]:
        if status == "queued":
            return list(self._queued_jobs)
        if status == "failed":
            return list(self._failed_jobs)
        return [*self._queued_jobs, *self._failed_jobs]

    def run_job(self, job_id: int) -> None:
        for index, job in enumerate(self._queued_jobs):
            if job.job_id != job_id:
                continue
            self._queued_jobs.pop(index)
            return
        raise ValueError(str(job_id))

    def retry_job(self, job_id: int) -> None:
        for index, job in enumerate(self._failed_jobs):
            if job.job_id != job_id:
                continue
            self._failed_jobs.pop(index)
            return
        raise ValueError(str(job_id))


class FakeVideoAssemblyFactoryService:
    def __init__(self, *, failed_failure_streak: int = 1) -> None:
        self._recipes = [
            {"recipe_id": 5, "status": "needs_review"},
            {"recipe_id": 3, "status": "approved"},
        ]
        self._jobs = [
            PreviewJobSummaryDTO(
                job_id=11,
                job_code="preview_11",
                recipe_id=5,
                job_type="render_recipe_preview",
                status="queued",
                progress=0.0,
                output_path=None,
            ),
            PreviewJobSummaryDTO(
                job_id=10,
                job_code="final_10",
                recipe_id=3,
                job_type="render_recipe_final",
                status="processing",
                progress=0.4,
                output_path=None,
            ),
            PreviewJobSummaryDTO(
                job_id=9,
                job_code="preview_09",
                recipe_id=2,
                job_type="render_recipe_preview",
                status="done",
                progress=1.0,
                output_path="F:/workspace/outputs/preview/honey.mp4",
            ),
            PreviewJobSummaryDTO(
                job_id=8,
                job_code="final_08",
                recipe_id=1,
                job_type="render_recipe_final",
                status="failed",
                progress=0.0,
                output_path=None,
                error_message="render failed",
                consecutive_failure_count=failed_failure_streak,
            ),
        ]

    def list_jobs(self, *, status: str | None = None) -> list[PreviewJobSummaryDTO]:
        if status is None:
            return list(self._jobs)
        return [job for job in self._jobs if job.status == status]

    def list_recipes(self, *, product_id: int | None = None, status: str | None = None):
        if status is None:
            return list(self._recipes)
        return [recipe for recipe in self._recipes if recipe["status"] == status]

    def list_preview_jobs(self, *, status: str | None = None) -> list[PreviewJobSummaryDTO]:
        jobs = [job for job in self._jobs if job.job_type == "render_recipe_preview"]
        if status is None:
            return jobs
        return [job for job in jobs if job.status == status]

    def list_final_render_jobs(self, *, status: str | None = None) -> list[PreviewJobSummaryDTO]:
        jobs = [job for job in self._jobs if job.job_type == "render_recipe_final"]
        if status is None:
            return jobs
        return [job for job in jobs if job.status == status]

    def run_preview_job(self, job_id: int) -> None:
        self._complete_job(job_id, "render_recipe_preview")

    def run_final_render_job(self, job_id: int) -> None:
        self._complete_job(job_id, "render_recipe_final")

    def _complete_job(self, job_id: int, expected_type: str) -> None:
        for index, job in enumerate(self._jobs):
            if job.job_id != job_id:
                continue
            if job.job_type != expected_type:
                raise ValueError(job.job_type)
            self._jobs[index] = PreviewJobSummaryDTO(
                job_id=job.job_id,
                job_code=job.job_code,
                recipe_id=job.recipe_id,
                job_type=job.job_type,
                status="done",
                progress=1.0,
                output_path=job.output_path or "F:/workspace/outputs/preview/recovered.mp4",
            )
            return
        raise ValueError(str(job_id))

    def retry_job(self, job_id: int) -> None:
        for index, job in enumerate(self._jobs):
            if job.job_id != job_id:
                continue
            self._jobs[index] = PreviewJobSummaryDTO(
                job_id=job.job_id,
                job_code=job.job_code,
                recipe_id=job.recipe_id,
                job_type=job.job_type,
                status="done",
                progress=1.0,
                output_path=job.output_path or "F:/workspace/outputs/final/retried.mp4",
            )
            return
        raise ValueError(str(job_id))


def _build_asset_service(unit_of_work_factory, media_root: Path) -> AssetIntakeService:
    return AssetIntakeService(
        unit_of_work_factory=unit_of_work_factory,
        asset_storage=LocalAssetStorage(media_root),
        metadata_analyzer=FakeMetadataAnalyzer(),
        readiness_evaluator=AssetReadinessEvaluator(),
    )


def _runtime_path_roots_from_config(config) -> PathRootsDTO:
    return PathRootsDTO(
        database_path=str(config.paths.database_path),
        media_root=str(config.paths.media_root),
        docs_root=str(config.paths.docs_root),
        outputs_root=str(config.paths.outputs_root),
        preview_root=str(config.paths.preview_root),
    )


def test_system_settings_service_reads_and_writes_toml(tmp_path) -> None:
    config_path = tmp_path / "app_config.toml"
    config_path.write_text(
        "\n".join(
            [
                "[paths]",
                'database_path = "ad_kitchen.db"',
                'media_root = "media_library"',
                'docs_root = "doc"',
                'outputs_root = "outputs"',
                'preview_root = "outputs\\\\preview"',
                "",
                "[ffmpeg]",
                'root = "F:\\\\ffmpeg"',
                'ffprobe = "F:\\\\ffmpeg\\\\bin\\\\ffprobe.exe"',
                'ffmpeg = "F:\\\\ffmpeg\\\\bin\\\\ffmpeg.exe"',
                "",
                "[system]",
                "cpu_limit_percent = 90",
                "ram_limit_percent = 80",
                "disk_free_gb_min = 20",
                "max_preview_workers = 1",
                "max_final_workers = 1",
                "auto_refresh_seconds = 10",
                "auto_recover_queued_jobs = false",
                "max_recovery_jobs_per_run = 25",
                "failed_job_escalation_threshold = 2",
                "",
            ]
        ),
        encoding="utf-8",
    )
    service = SystemSettingsService(config_path)

    defaults = service.load()
    assert defaults.ffprobe_path.endswith("ffprobe.exe")

    updated = SystemSettingsDTO(
        database_path=str(tmp_path / "db.sqlite"),
        media_root=str(tmp_path / "media"),
        docs_root=str(tmp_path / "doc"),
        outputs_root=str(tmp_path / "outputs"),
        preview_root=str(tmp_path / "outputs" / "preview"),
        ffmpeg_root=r"F:\custom_ffmpeg",
        ffprobe_path=r"F:\custom_ffmpeg\bin\ffprobe.exe",
        ffmpeg_path=r"F:\custom_ffmpeg\bin\ffmpeg.exe",
        cpu_limit_percent=88,
        ram_limit_percent=77,
        disk_free_gb_min=15,
        max_preview_workers=2,
        max_final_workers=1,
        auto_refresh_seconds=5,
        preview_output_resolution="1080*1920",
        final_output_resolution="720x1280",
        auto_recover_queued_jobs=True,
        max_recovery_jobs_per_run=12,
        failed_job_escalation_threshold=3,
        voice_loop_enabled=False,
        background_music_loop_enabled=True,
        music_duck_enabled=True,
        music_duck_mode="windowed_volume_duck",
        music_duck_db=-16,
        music_duck_attack_ms=220,
        music_duck_release_ms=480,
        music_duck_threshold_db=-22,
        music_duck_ratio=6.5,
        voice_mix_gain_db=3,
        music_mix_gain_db=-7,
    )
    service.save(updated)

    loaded = service.load()
    assert loaded.database_path.endswith("db.sqlite")
    assert loaded.ffmpeg_root == r"F:\custom_ffmpeg"
    assert loaded.cpu_limit_percent == 88
    assert loaded.preview_output_resolution == "1080x1920"
    assert loaded.final_output_resolution == "720x1280"
    assert loaded.auto_recover_queued_jobs is True
    assert loaded.max_recovery_jobs_per_run == 12
    assert loaded.failed_job_escalation_threshold == 3
    assert loaded.voice_loop_enabled is False
    assert loaded.background_music_loop_enabled is True
    assert loaded.music_duck_enabled is True
    assert loaded.music_duck_mode == "windowed_volume_duck"
    assert loaded.music_duck_db == -16
    assert loaded.music_duck_threshold_db == -22
    assert loaded.music_duck_ratio == 6.5
    assert loaded.voice_mix_gain_db == 3
    assert loaded.music_mix_gain_db == -7
    assert config_path.exists()


def test_dashboard_service_aggregates_system_information(unit_of_work_factory, tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    settings_service = SystemSettingsService(workspace_root / "app_config.toml")
    settings_service.save(
        SystemSettingsDTO(
            database_path=str(tmp_path / "workspace" / "ad_kitchen.db"),
            media_root=str(tmp_path / "workspace" / "media_library"),
            docs_root=str(tmp_path / "workspace" / "doc"),
            outputs_root=str(tmp_path / "workspace" / "outputs"),
            preview_root=str(tmp_path / "workspace" / "outputs" / "preview"),
            ffmpeg_root=str(tmp_path / "ffmpeg"),
            ffprobe_path=str(tmp_path / "ffmpeg" / "bin" / "ffprobe.exe"),
            ffmpeg_path=str(tmp_path / "ffmpeg" / "bin" / "ffmpeg.exe"),
            cpu_limit_percent=90,
            ram_limit_percent=80,
            disk_free_gb_min=20,
            max_preview_workers=1,
            max_final_workers=1,
            auto_refresh_seconds=10,
            auto_recover_queued_jobs=True,
            max_recovery_jobs_per_run=3,
            failed_job_escalation_threshold=2,
            voice_loop_enabled=False,
            background_music_loop_enabled=True,
            music_duck_enabled=True,
            music_duck_mode="sidechain_compressor",
            music_duck_db=-15,
            music_duck_attack_ms=250,
            music_duck_release_ms=500,
            music_duck_threshold_db=-24,
            music_duck_ratio=8.0,
            voice_mix_gain_db=1,
            music_mix_gain_db=-5,
        )
    )
    config = default_config(workspace_root)
    settings_service = SystemSettingsService(
        config.paths.app_config_path,
        runtime_path_roots=_runtime_path_roots_from_config(config),
    )

    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    asset_service = _build_asset_service(unit_of_work_factory, workspace_root / "media_library")
    tag_service = TagManagementService(unit_of_work_factory=unit_of_work_factory)

    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    source_file = tmp_path / "hero.mp4"
    source_file.write_bytes(b"video")
    asset_service.register_asset(
        RegisterAssetCommand(
            product_id=product_id,
            asset_type="background_video",
            source_file_path=source_file,
        )
    )
    tag_service.create_tag(CreateTagCommand(tag_name="Warm", tag_group="Mood"))

    dashboard_service = DashboardService(
        config=config,
        product_service=product_service,
        asset_intake_service=asset_service,
        artifact_generation_service=FakeArtifactGenerationService(queued_count=2, failed_count=1),
        video_assembly_factory_service=FakeVideoAssemblyFactoryService(),
        tag_management_service=tag_service,
        system_settings_service=settings_service,
    )
    summary = dashboard_service.build_summary()

    assert summary.product_count == 1
    assert summary.asset_count == 1
    assert summary.recipe_count == 0
    assert summary.output_count == 0
    assert summary.ready_asset_count == 1
    assert summary.needs_review_recipe_count == 1
    assert summary.tag_count == 1
    assert summary.total_job_count == 7
    assert summary.active_job_count == 4
    assert summary.queued_job_count == 3
    assert summary.processing_job_count == 1
    assert summary.failed_job_count == 2
    assert summary.escalated_job_count == 0
    assert summary.auto_recover_queued_jobs is True
    assert summary.preview_output_resolution == ""
    assert summary.final_output_resolution == ""
    assert summary.max_recovery_jobs_per_run == 3
    assert summary.failed_job_escalation_threshold == 2
    assert summary.path_restart_required is False
    assert summary.changed_path_roots == ()
    assert summary.voice_loop_enabled is False
    assert summary.background_music_loop_enabled is True
    assert summary.music_duck_enabled is True
    assert summary.music_duck_mode == "sidechain_compressor"
    assert summary.music_duck_db == -15
    assert summary.music_duck_threshold_db == -24
    assert summary.music_duck_ratio == 8.0
    assert summary.voice_mix_gain_db == 1
    assert summary.music_mix_gain_db == -5
    assert summary.review_duration_mismatch_sec == 1
    assert summary.review_max_looped_segments == 2
    assert summary.recent_jobs[0] == DashboardJobDTO(
        job_id=11,
        job_code="preview_11",
        job_type="render_recipe_preview",
        job_source="factory",
        status="queued",
        progress=0.0,
        subject_reference="recipe#5",
        output_path=None,
        error_message=None,
    )
    assert summary.outputs_root.endswith("outputs")
    assert summary.preview_root.endswith("preview")
    assert summary.runtime_outputs_root.endswith("outputs")
    assert summary.runtime_preview_root.endswith("preview")
    assert summary.cpu_limit_percent == 90


def test_dashboard_service_recovers_queued_jobs_and_records_summary(unit_of_work_factory, tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    settings_service = SystemSettingsService(workspace_root / "app_config.toml")
    settings_service.save(
        SystemSettingsDTO(
            database_path=str(tmp_path / "workspace" / "ad_kitchen.db"),
            media_root=str(tmp_path / "workspace" / "media_library"),
            docs_root=str(tmp_path / "workspace" / "doc"),
            outputs_root=str(tmp_path / "workspace" / "outputs"),
            preview_root=str(tmp_path / "workspace" / "outputs" / "preview"),
            ffmpeg_root=str(tmp_path / "ffmpeg"),
            ffprobe_path=str(tmp_path / "ffmpeg" / "bin" / "ffprobe.exe"),
            ffmpeg_path=str(tmp_path / "ffmpeg" / "bin" / "ffmpeg.exe"),
            cpu_limit_percent=90,
            ram_limit_percent=80,
            disk_free_gb_min=20,
            max_preview_workers=1,
            max_final_workers=1,
            auto_refresh_seconds=10,
            auto_recover_queued_jobs=False,
            max_recovery_jobs_per_run=2,
            failed_job_escalation_threshold=2,
            voice_loop_enabled=False,
            background_music_loop_enabled=True,
            music_duck_enabled=True,
            music_duck_mode="sidechain_compressor",
            music_duck_db=-15,
            music_duck_attack_ms=250,
            music_duck_release_ms=500,
            music_duck_threshold_db=-24,
            music_duck_ratio=8.0,
        )
    )
    config = default_config(workspace_root)
    settings_service = SystemSettingsService(
        config.paths.app_config_path,
        runtime_path_roots=_runtime_path_roots_from_config(config),
    )
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    asset_service = _build_asset_service(unit_of_work_factory, workspace_root / "media_library")
    tag_service = TagManagementService(unit_of_work_factory=unit_of_work_factory)
    dashboard_service = DashboardService(
        config=config,
        product_service=product_service,
        asset_intake_service=asset_service,
        artifact_generation_service=FakeArtifactGenerationService(queued_count=2, failed_count=0),
        video_assembly_factory_service=FakeVideoAssemblyFactoryService(),
        tag_management_service=tag_service,
        system_settings_service=settings_service,
    )

    result = dashboard_service.recover_queued_jobs(trigger="manual")
    summary = dashboard_service.build_summary()

    assert result.trigger == "manual"
    assert result.queued_job_count == 3
    assert result.attempted_job_count == 2
    assert result.deferred_job_count == 1
    assert result.succeeded_job_count == 2
    assert result.failed_job_count == 0
    assert summary.queued_job_count == 1
    assert summary.last_recovery_summary is not None
    assert summary.last_recovery_summary.job_selection == "queued"
    assert summary.last_recovery_summary.attempted_job_count == 2


def test_dashboard_service_retries_failed_jobs_and_records_summary(unit_of_work_factory, tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    settings_service = SystemSettingsService(workspace_root / "app_config.toml")
    settings_service.save(
        SystemSettingsDTO(
            database_path=str(tmp_path / "workspace" / "ad_kitchen.db"),
            media_root=str(tmp_path / "workspace" / "media_library"),
            docs_root=str(tmp_path / "workspace" / "doc"),
            outputs_root=str(tmp_path / "workspace" / "outputs"),
            preview_root=str(tmp_path / "workspace" / "outputs" / "preview"),
            ffmpeg_root=str(tmp_path / "ffmpeg"),
            ffprobe_path=str(tmp_path / "ffmpeg" / "bin" / "ffprobe.exe"),
            ffmpeg_path=str(tmp_path / "ffmpeg" / "bin" / "ffmpeg.exe"),
            cpu_limit_percent=90,
            ram_limit_percent=80,
            disk_free_gb_min=20,
            max_preview_workers=1,
            max_final_workers=1,
            auto_refresh_seconds=10,
            auto_recover_queued_jobs=False,
            max_recovery_jobs_per_run=5,
            failed_job_escalation_threshold=2,
            voice_loop_enabled=False,
            background_music_loop_enabled=True,
            music_duck_enabled=True,
            music_duck_mode="sidechain_compressor",
            music_duck_db=-15,
            music_duck_attack_ms=250,
            music_duck_release_ms=500,
            music_duck_threshold_db=-24,
            music_duck_ratio=8.0,
        )
    )
    config = default_config(workspace_root)
    settings_service = SystemSettingsService(
        config.paths.app_config_path,
        runtime_path_roots=_runtime_path_roots_from_config(config),
    )
    dashboard_service = DashboardService(
        config=config,
        product_service=ProductApplicationService(unit_of_work_factory=unit_of_work_factory),
        asset_intake_service=_build_asset_service(unit_of_work_factory, workspace_root / "media_library"),
        artifact_generation_service=FakeArtifactGenerationService(queued_count=0, failed_count=1),
        video_assembly_factory_service=FakeVideoAssemblyFactoryService(),
        tag_management_service=TagManagementService(unit_of_work_factory=unit_of_work_factory),
        system_settings_service=settings_service,
    )

    result = dashboard_service.retry_failed_jobs(trigger="manual")
    summary = dashboard_service.build_summary()

    assert result.job_selection == "failed"
    assert result.matched_job_count == 2
    assert result.attempted_job_count == 2
    assert result.deferred_job_count == 0
    assert result.succeeded_job_count == 2
    assert result.failed_job_count == 0
    assert result.escalated_job_count == 0
    assert summary.failed_job_count == 0
    assert summary.last_recovery_summary is not None
    assert summary.last_recovery_summary.job_selection == "failed"


def test_dashboard_service_prioritizes_non_escalated_failed_jobs(unit_of_work_factory, tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    settings_service = SystemSettingsService(
        workspace_root / "app_config.toml",
        runtime_path_roots=PathRootsDTO(
            database_path=str(workspace_root / "ad_kitchen.db"),
            media_root=str(workspace_root / "media_library"),
            docs_root=str(workspace_root / "doc"),
            outputs_root=str(workspace_root / "outputs"),
            preview_root=str(workspace_root / "outputs" / "preview"),
        ),
    )
    settings_service.save(
        SystemSettingsDTO(
            database_path=str(tmp_path / "workspace" / "ad_kitchen.db"),
            media_root=str(tmp_path / "workspace" / "media_library_v2"),
            docs_root=str(tmp_path / "workspace" / "doc"),
            outputs_root=str(tmp_path / "workspace" / "outputs"),
            preview_root=str(tmp_path / "workspace" / "outputs" / "preview"),
            ffmpeg_root=str(tmp_path / "ffmpeg"),
            ffprobe_path=str(tmp_path / "ffmpeg" / "bin" / "ffprobe.exe"),
            ffmpeg_path=str(tmp_path / "ffmpeg" / "bin" / "ffmpeg.exe"),
            cpu_limit_percent=90,
            ram_limit_percent=80,
            disk_free_gb_min=20,
            max_preview_workers=1,
            max_final_workers=1,
            auto_refresh_seconds=10,
            auto_recover_queued_jobs=False,
            max_recovery_jobs_per_run=1,
            failed_job_escalation_threshold=2,
            voice_loop_enabled=False,
            background_music_loop_enabled=True,
            music_duck_enabled=True,
            music_duck_mode="sidechain_compressor",
            music_duck_db=-15,
            music_duck_attack_ms=250,
            music_duck_release_ms=500,
            music_duck_threshold_db=-24,
            music_duck_ratio=8.0,
        )
    )
    config = default_config(workspace_root)
    dashboard_service = DashboardService(
        config=config,
        product_service=ProductApplicationService(unit_of_work_factory=unit_of_work_factory),
        asset_intake_service=_build_asset_service(unit_of_work_factory, workspace_root / "media_library"),
        artifact_generation_service=FakeArtifactGenerationService(
            queued_count=0,
            failed_count=1,
            failed_failure_streaks=[1],
        ),
        video_assembly_factory_service=FakeVideoAssemblyFactoryService(failed_failure_streak=3),
        tag_management_service=TagManagementService(unit_of_work_factory=unit_of_work_factory),
        system_settings_service=settings_service,
    )

    before = dashboard_service.build_summary()
    result = dashboard_service.retry_failed_jobs(trigger="manual")
    after = dashboard_service.build_summary()

    assert before.escalated_job_count == 1
    assert before.operator_playbook_lines
    assert before.path_restart_required is True
    assert before.changed_path_roots == ("media_root",)
    assert result.attempted_job_count == 1
    assert result.deferred_job_count == 1
    assert result.escalated_job_count == 1
    assert result.recovered_job_codes == ("failed_1",)
    assert result.deferred_job_codes == ("final_08",)
    assert result.escalated_job_codes == ("final_08",)
    assert after.failed_job_count == 1
    assert after.escalated_job_count == 1


def test_dashboard_service_reports_runtime_and_configured_paths_when_restart_is_pending(unit_of_work_factory, tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    config = default_config(workspace_root)
    settings_service = SystemSettingsService(
        config.paths.app_config_path,
        runtime_path_roots=_runtime_path_roots_from_config(config),
    )
    settings_service.save(
        SystemSettingsDTO(
            database_path=str(workspace_root / "data" / "mtclip.db"),
            media_root=str(workspace_root / "media_library_v2"),
            docs_root=str(workspace_root / "doc_v2"),
            outputs_root=str(workspace_root / "outputs_v2"),
            preview_root=str(workspace_root / "outputs_v2" / "preview"),
            ffmpeg_root=str(tmp_path / "ffmpeg"),
            ffprobe_path=str(tmp_path / "ffmpeg" / "bin" / "ffprobe.exe"),
            ffmpeg_path=str(tmp_path / "ffmpeg" / "bin" / "ffmpeg.exe"),
            cpu_limit_percent=90,
            ram_limit_percent=80,
            disk_free_gb_min=20,
            max_preview_workers=1,
            max_final_workers=1,
            auto_refresh_seconds=10,
            auto_recover_queued_jobs=False,
            max_recovery_jobs_per_run=3,
            failed_job_escalation_threshold=2,
            voice_loop_enabled=False,
            background_music_loop_enabled=True,
            music_duck_enabled=True,
            music_duck_mode="sidechain_compressor",
            music_duck_db=-15,
            music_duck_attack_ms=250,
            music_duck_release_ms=500,
            music_duck_threshold_db=-24,
            music_duck_ratio=8.0,
        )
    )

    dashboard_service = DashboardService(
        config=config,
        product_service=ProductApplicationService(unit_of_work_factory=unit_of_work_factory),
        asset_intake_service=_build_asset_service(unit_of_work_factory, workspace_root / "media_library"),
        artifact_generation_service=FakeArtifactGenerationService(),
        video_assembly_factory_service=FakeVideoAssemblyFactoryService(),
        tag_management_service=TagManagementService(unit_of_work_factory=unit_of_work_factory),
        system_settings_service=settings_service,
    )

    summary = dashboard_service.build_summary()

    assert summary.path_reload_policy == "restart_required"
    assert summary.path_restart_required is True
    assert summary.runtime_database_path.endswith("ad_kitchen.db")
    assert summary.database_path.endswith("mtclip.db")
    assert summary.runtime_outputs_root.endswith("outputs")
    assert summary.outputs_root.endswith("outputs_v2")
    assert summary.changed_path_roots == (
        "database_path",
        "media_root",
        "docs_root",
        "outputs_root",
        "preview_root",
    )
