from __future__ import annotations

from dataclasses import dataclass

from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.control_center.services import DashboardService, SystemSettingsService
from mt_clip_factory.factory.services import VideoAssemblyFactoryService
from mt_clip_factory.library.artifact_services import ArtifactGenerationService
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.tag_services import TagManagementService


@dataclass(slots=True, frozen=True)
class ResourceLibraryModule:
    product_service: ProductApplicationService
    asset_intake_service: AssetIntakeService
    artifact_generation_service: ArtifactGenerationService
    video_assembly_factory_service: VideoAssemblyFactoryService
    tag_management_service: TagManagementService
    system_settings_service: SystemSettingsService
    dashboard_service: DashboardService
