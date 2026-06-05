from __future__ import annotations

from dataclasses import dataclass

from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.tag_services import TagManagementService


@dataclass(slots=True, frozen=True)
class ResourceLibraryModule:
    product_service: ProductApplicationService
    asset_intake_service: AssetIntakeService
    tag_management_service: TagManagementService
