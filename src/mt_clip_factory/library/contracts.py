from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from mt_clip_factory.domain.enums import AssetType


@dataclass(slots=True, frozen=True)
class AnalyzedMediaMetadata:
    duration_sec: float | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    ratio: str | None = None
    file_size_mb: float | None = None
    codec: str | None = None
    has_audio: bool = False


@dataclass(slots=True, frozen=True)
class StoredAssetFile:
    file_path: Path
    file_name: str


class AssetMetadataAnalyzer(Protocol):
    def analyze(self, file_path: Path) -> AnalyzedMediaMetadata:
        ...


class AssetStorage(Protocol):
    def store_asset(
        self,
        product_code: str,
        asset_type: AssetType,
        asset_code: str,
        source_file_path: Path,
    ) -> StoredAssetFile:
        ...

