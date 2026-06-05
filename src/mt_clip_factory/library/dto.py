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
