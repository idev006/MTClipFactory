from __future__ import annotations

from pathlib import Path

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.config import default_config
from mt_clip_factory.control_center.dto import DashboardJobDTO, SystemSettingsDTO
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


class FakeVideoAssemblyFactoryService:
    def __init__(self) -> None:
        self._jobs = [
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
        ]

    def list_jobs(self, *, status: str | None = None) -> list[PreviewJobSummaryDTO]:
        if status is None:
            return list(self._jobs)
        return [job for job in self._jobs if job.status == status]


def _build_asset_service(unit_of_work_factory, media_root: Path) -> AssetIntakeService:
    return AssetIntakeService(
        unit_of_work_factory=unit_of_work_factory,
        asset_storage=LocalAssetStorage(media_root),
        metadata_analyzer=FakeMetadataAnalyzer(),
        readiness_evaluator=AssetReadinessEvaluator(),
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
    )
    service.save(updated)

    loaded = service.load()
    assert loaded.database_path.endswith("db.sqlite")
    assert loaded.ffmpeg_root == r"F:\custom_ffmpeg"
    assert loaded.cpu_limit_percent == 88
    assert config_path.exists()


def test_dashboard_service_aggregates_system_information(unit_of_work_factory, tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    config = default_config(workspace_root)
    settings_service = SystemSettingsService(config.paths.app_config_path)
    settings_service.save(
        SystemSettingsDTO(
            database_path=str(tmp_path / "workspace" / "ad_kitchen.db"),
            media_root=str(tmp_path / "media_library"),
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
        )
    )

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
    assert summary.tag_count == 1
    assert summary.total_job_count == 5
    assert summary.active_job_count == 3
    assert summary.queued_job_count == 2
    assert summary.processing_job_count == 1
    assert summary.failed_job_count == 1
    assert summary.recent_jobs[0] == DashboardJobDTO(
        job_id=10,
        job_code="final_10",
        job_type="render_recipe_final",
        job_source="factory",
        status="processing",
        progress=0.4,
        subject_reference="recipe#3",
        output_path=None,
        error_message=None,
    )
    assert summary.outputs_root.endswith("outputs")
    assert summary.preview_root.endswith("preview")
    assert summary.cpu_limit_percent == 90
