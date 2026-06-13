from __future__ import annotations

from pathlib import Path

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.config import default_config
from mt_clip_factory.control_center.dto import PathRootsDTO, SystemSettingsDTO
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
from mt_clip_factory.presentation.control_center.dashboard import DashboardViewModel
from mt_clip_factory.presentation.control_center.settings import SettingsViewModel


class FakeMetadataAnalyzer:
    def analyze(self, file_path: Path) -> AnalyzedMediaMetadata:
        return AnalyzedMediaMetadata(
            duration_sec=1.0,
            width=1920,
            height=1080,
            fps=30.0,
            ratio="16:9",
            file_size_mb=0.001,
            codec="h264",
            has_audio=True,
        )


class FakeArtifactGenerationService:
    def __init__(self, queued_count: int = 0, failed_count: int = 0) -> None:
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
    def __init__(self) -> None:
        self._recipes = [
            {"recipe_id": 3, "status": "needs_review"},
            {"recipe_id": 4, "status": "approved"},
        ]
        self._jobs = [
            PreviewJobSummaryDTO(
                job_id=5,
                job_code="preview_05",
                recipe_id=3,
                job_type="render_recipe_preview",
                status="queued",
                progress=0.0,
                output_path=None,
            ),
            PreviewJobSummaryDTO(
                job_id=6,
                job_code="final_06",
                recipe_id=4,
                job_type="render_recipe_final",
                status="processing",
                progress=0.6,
                output_path=None,
            ),
            PreviewJobSummaryDTO(
                job_id=7,
                job_code="preview_07",
                recipe_id=2,
                job_type="render_recipe_preview",
                status="failed",
                progress=0.0,
                output_path=None,
                error_message="preview failed",
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
                output_path="F:/workspace/outputs/preview/5.mp4",
            )
            return
        raise ValueError(str(job_id))

    def run_final_render_job(self, job_id: int) -> None:
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
                output_path="F:/workspace/outputs/preview/retried.mp4",
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


def test_settings_view_model_loads_and_saves(tmp_path) -> None:
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
                "[visual]",
                'key_profile = "auto"',
                'key_color = "#00FF00"',
                "",
                "[audio]",
                "voice_loop_enabled = false",
                "background_music_loop_enabled = true",
                "music_duck_enabled = true",
                'music_duck_mode = "sidechain_compressor"',
                "music_duck_db = -15",
                "music_duck_attack_ms = 250",
                "music_duck_release_ms = 500",
                "music_duck_threshold_db = -24",
                "music_duck_ratio = 8.0",
                "voice_mix_gain_db = 0",
                "music_mix_gain_db = -4",
                "",
            ]
        ),
        encoding="utf-8",
    )
    service = SystemSettingsService(
        config_path,
        runtime_path_roots=PathRootsDTO(
            database_path=str(tmp_path / "ad_kitchen.db"),
            media_root=str(tmp_path / "media_library"),
            docs_root=str(tmp_path / "doc"),
            outputs_root=str(tmp_path / "outputs"),
            preview_root=str(tmp_path / "outputs" / "preview"),
        ),
    )
    view_model = SettingsViewModel(service)

    view_model.load()
    assert view_model.status == "ready"
    assert view_model.settings is not None

    view_model.save(
        SystemSettingsDTO(
            database_path=str(tmp_path / "db.sqlite"),
            media_root=str(tmp_path / "media"),
            docs_root=str(tmp_path / "doc"),
            outputs_root=str(tmp_path / "outputs"),
            preview_root=str(tmp_path / "outputs" / "preview"),
            ffmpeg_root=r"F:\ffmpeg",
            ffprobe_path=r"F:\ffmpeg\bin\ffprobe.exe",
            ffmpeg_path=r"F:\ffmpeg\bin\ffmpeg.exe",
            cpu_limit_percent=91,
            ram_limit_percent=81,
            disk_free_gb_min=25,
            max_preview_workers=2,
            max_final_workers=1,
            auto_refresh_seconds=6,
            auto_recover_queued_jobs=True,
            max_recovery_jobs_per_run=12,
            failed_job_escalation_threshold=3,
            voice_loop_enabled=False,
            background_music_loop_enabled=True,
            music_duck_enabled=True,
            visual_key_profile="custom",
            visual_key_color="#2255FF",
            music_duck_mode="windowed_volume_duck",
            music_duck_db=-18,
            music_duck_attack_ms=180,
            music_duck_release_ms=420,
            music_duck_threshold_db=-20,
            music_duck_ratio=5.5,
            voice_mix_gain_db=2,
            music_mix_gain_db=-6,
        )
    )

    assert view_model.status == "ready"
    assert view_model.settings is not None
    assert view_model.settings.outputs_root.endswith("outputs")
    assert view_model.settings.cpu_limit_percent == 91
    assert view_model.settings.auto_recover_queued_jobs is True
    assert view_model.settings.max_recovery_jobs_per_run == 12
    assert view_model.settings.failed_job_escalation_threshold == 3
    assert view_model.settings.visual_key_profile == "custom"
    assert view_model.settings.visual_key_color == "#2255FF"
    assert view_model.settings.music_duck_mode == "windowed_volume_duck"
    assert view_model.settings.music_duck_db == -18
    assert view_model.settings.music_duck_threshold_db == -20
    assert view_model.settings.music_duck_ratio == 5.5
    assert view_model.settings.voice_mix_gain_db == 2
    assert view_model.settings.music_mix_gain_db == -6
    assert view_model.settings.review_duration_mismatch_sec == 1
    assert "restart-driven" in view_model.feedback
    assert "Restart required for path roots" in view_model.feedback


def test_dashboard_view_model_loads_summary(unit_of_work_factory, tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    settings_service = SystemSettingsService(workspace_root / "app_config.toml")
    settings_service.save(
        SystemSettingsDTO(
            database_path=str(workspace_root / "ad_kitchen.db"),
            media_root=str(workspace_root / "media_library"),
            docs_root=str(workspace_root / "doc"),
            outputs_root=str(workspace_root / "outputs"),
            preview_root=str(workspace_root / "outputs" / "preview"),
            ffmpeg_root="",
            ffprobe_path="",
            ffmpeg_path="",
            cpu_limit_percent=0,
            ram_limit_percent=0,
            disk_free_gb_min=0,
            max_preview_workers=0,
            max_final_workers=0,
            auto_refresh_seconds=0,
            auto_recover_queued_jobs=False,
            max_recovery_jobs_per_run=25,
            failed_job_escalation_threshold=2,
            voice_loop_enabled=False,
            background_music_loop_enabled=True,
            music_duck_enabled=True,
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
        artifact_generation_service=FakeArtifactGenerationService(queued_count=1, failed_count=1),
        video_assembly_factory_service=FakeVideoAssemblyFactoryService(),
        tag_management_service=tag_service,
        system_settings_service=settings_service,
    )
    view_model = DashboardViewModel(dashboard_service)

    view_model.load()

    assert view_model.status == "ready"
    assert view_model.summary is not None
    assert view_model.summary.product_count == 1
    assert view_model.summary.recipe_count == 0
    assert view_model.summary.output_count == 0
    assert view_model.summary.queued_job_count == 2
    assert view_model.summary.processing_job_count == 1
    assert view_model.summary.failed_job_count == 2
    assert view_model.summary.path_restart_required is False
    assert view_model.summary.music_duck_enabled is True
    assert view_model.summary.music_duck_mode == "sidechain_compressor"
    assert view_model.summary.voice_mix_gain_db == 0
    assert view_model.summary.music_mix_gain_db == -4
    assert view_model.summary.needs_review_recipe_count == 1
    assert view_model.summary.recent_jobs[0].job_code == "preview_07"


def test_dashboard_view_model_recovers_queued_jobs(unit_of_work_factory, tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    settings_service = SystemSettingsService(workspace_root / "app_config.toml")
    settings_service.save(
        SystemSettingsDTO(
            database_path=str(workspace_root / "ad_kitchen.db"),
            media_root=str(workspace_root / "media_library"),
            docs_root=str(workspace_root / "doc"),
            outputs_root=str(workspace_root / "outputs"),
            preview_root=str(workspace_root / "outputs" / "preview"),
            ffmpeg_root="",
            ffprobe_path="",
            ffmpeg_path="",
            cpu_limit_percent=0,
            ram_limit_percent=0,
            disk_free_gb_min=0,
            max_preview_workers=0,
            max_final_workers=0,
            auto_refresh_seconds=0,
            auto_recover_queued_jobs=False,
            max_recovery_jobs_per_run=25,
            failed_job_escalation_threshold=2,
            voice_loop_enabled=False,
            background_music_loop_enabled=True,
            music_duck_enabled=True,
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
        artifact_generation_service=FakeArtifactGenerationService(queued_count=1, failed_count=0),
        video_assembly_factory_service=FakeVideoAssemblyFactoryService(),
        tag_management_service=tag_service,
        system_settings_service=settings_service,
    )
    view_model = DashboardViewModel(dashboard_service)

    view_model.recover_queued_jobs()

    assert view_model.status == "ready"
    assert view_model.summary is not None
    assert view_model.summary.queued_job_count == 0
    assert view_model.summary.last_recovery_summary is not None
    assert view_model.summary.last_recovery_summary.succeeded_job_count == 2


def test_dashboard_view_model_retries_failed_jobs(unit_of_work_factory, tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    settings_service = SystemSettingsService(workspace_root / "app_config.toml")
    settings_service.save(
        SystemSettingsDTO(
            database_path=str(workspace_root / "ad_kitchen.db"),
            media_root=str(workspace_root / "media_library"),
            docs_root=str(workspace_root / "doc"),
            outputs_root=str(workspace_root / "outputs"),
            preview_root=str(workspace_root / "outputs" / "preview"),
            ffmpeg_root="",
            ffprobe_path="",
            ffmpeg_path="",
            cpu_limit_percent=0,
            ram_limit_percent=0,
            disk_free_gb_min=0,
            max_preview_workers=0,
            max_final_workers=0,
            auto_refresh_seconds=0,
            auto_recover_queued_jobs=False,
            max_recovery_jobs_per_run=25,
            failed_job_escalation_threshold=2,
            voice_loop_enabled=False,
            background_music_loop_enabled=True,
            music_duck_enabled=True,
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
        artifact_generation_service=FakeArtifactGenerationService(queued_count=0, failed_count=1),
        video_assembly_factory_service=FakeVideoAssemblyFactoryService(),
        tag_management_service=tag_service,
        system_settings_service=settings_service,
    )
    view_model = DashboardViewModel(dashboard_service)

    view_model.retry_failed_jobs()

    assert view_model.status == "ready"
    assert view_model.summary is not None
    assert view_model.summary.failed_job_count == 0
    assert view_model.summary.last_recovery_summary is not None
    assert view_model.summary.last_recovery_summary.job_selection == "failed"
