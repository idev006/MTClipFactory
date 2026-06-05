from __future__ import annotations

from pathlib import Path

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.config import default_config
from mt_clip_factory.control_center.dto import SystemSettingsDTO
from mt_clip_factory.control_center.services import DashboardService, SystemSettingsService
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


def _build_asset_service(unit_of_work_factory, media_root: Path) -> AssetIntakeService:
    return AssetIntakeService(
        unit_of_work_factory=unit_of_work_factory,
        asset_storage=LocalAssetStorage(media_root),
        metadata_analyzer=FakeMetadataAnalyzer(),
        readiness_evaluator=AssetReadinessEvaluator(),
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
                "",
            ]
        ),
        encoding="utf-8",
    )
    service = SystemSettingsService(config_path)
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
        )
    )

    assert view_model.status == "ready"
    assert view_model.settings is not None
    assert view_model.settings.outputs_root.endswith("outputs")
    assert view_model.settings.cpu_limit_percent == 91


def test_dashboard_view_model_loads_summary(unit_of_work_factory, tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    config = default_config(workspace_root)
    settings_service = SystemSettingsService(config.paths.app_config_path)
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library")
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
    assert view_model.summary.queued_job_count == 1
    assert view_model.summary.failed_job_count == 1
