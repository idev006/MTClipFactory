from __future__ import annotations

from dataclasses import dataclass

from mt_clip_factory.factory.auto_factory_dto import (
    AutoFactoryBatchMaterializationDTO,
    AutoFactoryBatchOrderDTO,
    AutoFactoryBatchPreviewProductionDTO,
)


@dataclass(slots=True, frozen=True)
class AutoFactoryFolderProductConfigDTO:
    product_code: str
    product_name: str
    category: str | None = None
    brand_name: str | None = None
    description: str | None = None
    default_platform: str | None = None


@dataclass(slots=True, frozen=True)
class AutoFactoryFolderPipelineConfigDTO:
    requested_output_count: int
    target_platform: str | None = None
    target_ratio: str | None = None
    uniqueness_scope: str = "batch"
    duration_mode: str = "voice_with_bounds"
    fixed_duration_sec: float | None = None
    min_duration_sec: float = 12.0
    max_duration_sec: float = 30.0


@dataclass(slots=True, frozen=True)
class AutoFactoryFolderAssetActionDTO:
    product_code: str
    asset_type: str
    asset_code: str
    source_file: str
    action: str


@dataclass(slots=True, frozen=True)
class AutoFactoryFolderProductReportDTO:
    product_id: int
    product_code: str
    created_product: bool
    registered_asset_count: int
    skipped_existing_asset_count: int


@dataclass(slots=True, frozen=True)
class AutoFactoryFolderRunReportDTO:
    batch_code: str
    scan_depth: int
    order: AutoFactoryBatchOrderDTO
    discovered_product_dirs: tuple[str, ...]
    product_reports: tuple[AutoFactoryFolderProductReportDTO, ...]
    asset_actions: tuple[AutoFactoryFolderAssetActionDTO, ...]
    materialization: AutoFactoryBatchMaterializationDTO | None = None
    preview_production: AutoFactoryBatchPreviewProductionDTO | None = None
