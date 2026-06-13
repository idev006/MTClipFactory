from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from mt_clip_factory.domain.entities import utc_now
from mt_clip_factory.domain.enums import AssetType


@dataclass(slots=True)
class Asset:
    product_id: int
    asset_code: str
    asset_type: AssetType
    file_path: str
    file_name: str
    duration_sec: float | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    ratio: str | None = None
    file_size_mb: float | None = None
    codec: str | None = None
    has_audio: bool = False
    thumbnail_path: str | None = None
    proxy_path: str | None = None
    alpha_path: str | None = None
    rgba_cache_path: str | None = None
    quality_score: float = 0.0
    status: str = "analyzed"
    created_at: datetime = field(default_factory=utc_now)
    id: int | None = None


@dataclass(slots=True, frozen=True)
class AssetSummary:
    asset_id: int
    product_id: int
    product_code: str
    asset_code: str
    asset_type: AssetType
    file_name: str
    status: str
    ratio: str | None = None
    duration_sec: float | None = None
    file_size_mb: float | None = None
    tag_labels: tuple[str, ...] = ()
    thumbnail_path: str | None = None
    proxy_path: str | None = None


@dataclass(slots=True, frozen=True)
class AssetRecipeReference:
    recipe_id: int
    recipe_code: str
    recipe_status: str
    output_count: int


@dataclass(slots=True, frozen=True)
class AssetJobReference:
    job_id: int
    job_code: str
    job_type: str
    job_status: str
