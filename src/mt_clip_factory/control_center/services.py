from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import tomllib
from typing import TYPE_CHECKING

from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.config import AppConfig
from mt_clip_factory.control_center.dto import DashboardSummaryDTO, SystemSettingsDTO
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.tag_services import TagManagementService

if TYPE_CHECKING:
    from mt_clip_factory.library.artifact_services import ArtifactGenerationService


class SystemSettingsService:
    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path

    def load(self) -> SystemSettingsDTO:
        data = self._read_raw()
        ffmpeg = data.get("ffmpeg", {})
        system = data.get("system", {})
        ffmpeg_root = str(ffmpeg.get("root", ""))
        ffprobe_path = str(ffmpeg.get("ffprobe", ""))
        ffmpeg_path = str(ffmpeg.get("ffmpeg", ""))

        if ffmpeg_root and not ffprobe_path:
            ffprobe_path = str(Path(ffmpeg_root) / "bin" / "ffprobe.exe")
        if ffmpeg_root and not ffmpeg_path:
            ffmpeg_path = str(Path(ffmpeg_root) / "bin" / "ffmpeg.exe")

        return SystemSettingsDTO(
            ffmpeg_root=ffmpeg_root,
            ffprobe_path=ffprobe_path,
            ffmpeg_path=ffmpeg_path,
            cpu_limit_percent=int(system.get("cpu_limit_percent", 0)),
            ram_limit_percent=int(system.get("ram_limit_percent", 0)),
            disk_free_gb_min=int(system.get("disk_free_gb_min", 0)),
            max_preview_workers=int(system.get("max_preview_workers", 0)),
            max_final_workers=int(system.get("max_final_workers", 0)),
            auto_refresh_seconds=int(system.get("auto_refresh_seconds", 0)),
        )

    def save(self, settings: SystemSettingsDTO) -> None:
        content = "\n".join(
            [
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
        tag_management_service: TagManagementService,
        system_settings_service: SystemSettingsService,
    ) -> None:
        self._config = config
        self._product_service = product_service
        self._asset_intake_service = asset_intake_service
        self._artifact_generation_service = artifact_generation_service
        self._tag_management_service = tag_management_service
        self._system_settings_service = system_settings_service

    def build_summary(self) -> DashboardSummaryDTO:
        settings = self._system_settings_service.load()
        products = self._product_service.list_products()
        assets = self._asset_intake_service.list_assets()
        recipe_count = sum(product.recipe_count for product in products)
        output_count = sum(product.output_count for product in products)
        queued_jobs = self._artifact_generation_service.list_jobs(status="queued")
        failed_jobs = self._artifact_generation_service.list_jobs(status="failed")
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
            tag_count=len(tags),
            queued_job_count=len(queued_jobs),
            failed_job_count=len(failed_jobs),
            ffprobe_available=ffprobe_path.exists(),
            ffmpeg_available=ffmpeg_path.exists(),
            workspace_root=str(self._config.paths.workspace_root),
            database_path=str(self._config.paths.database_path),
            media_root=str(self._config.paths.media_root),
            ffprobe_path=settings.ffprobe_path,
            ffmpeg_path=settings.ffmpeg_path,
            cpu_limit_percent=settings.cpu_limit_percent,
            ram_limit_percent=settings.ram_limit_percent,
            disk_free_gb_min=settings.disk_free_gb_min,
            max_preview_workers=settings.max_preview_workers,
            max_final_workers=settings.max_final_workers,
            auto_refresh_seconds=settings.auto_refresh_seconds,
        )


def _escape_toml(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
