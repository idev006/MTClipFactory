from __future__ import annotations

from dataclasses import dataclass

from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.library.services import AssetIntakeService


@dataclass(slots=True, frozen=True)
class ResourceLibraryModule:
    product_service: ProductApplicationService
    asset_intake_service: AssetIntakeService
