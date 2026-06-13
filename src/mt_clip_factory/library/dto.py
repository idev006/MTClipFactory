from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class RegisterAssetCommand:
    product_id: int
    asset_type: str
    source_file_path: Path
    asset_code: str | None = None


@dataclass(slots=True, frozen=True)
class UpdateAssetCommand:
    asset_id: int
    asset_code: str


@dataclass(slots=True, frozen=True)
class AssetSummaryDTO:
    asset_id: int
    product_id: int
    product_code: str
    asset_code: str
    asset_type: str
    file_name: str
    status: str
    ratio: str | None
    duration_sec: float | None
    file_size_mb: float | None
    tag_labels: tuple[str, ...]
    thumbnail_path: str | None
    proxy_path: str | None


@dataclass(slots=True, frozen=True)
class AssetRecipeReferenceDTO:
    recipe_id: int
    recipe_code: str
    recipe_status: str
    output_count: int


@dataclass(slots=True, frozen=True)
class AssetJobReferenceDTO:
    job_id: int
    job_code: str
    job_type: str
    job_status: str


@dataclass(slots=True, frozen=True)
class AssetReferenceReportDTO:
    asset_id: int
    asset_code: str
    asset_status: str
    recipe_references: tuple[AssetRecipeReferenceDTO, ...]
    job_references: tuple[AssetJobReferenceDTO, ...]
    can_delete: bool
    can_purge_media: bool


@dataclass(slots=True, frozen=True)
class AssetMediaPurgeReportDTO:
    asset_id: int
    asset_code: str
    purged_file_count: int
    reclaimed_bytes: int
