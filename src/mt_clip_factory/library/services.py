from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from mt_clip_factory.domain.assets import Asset
from mt_clip_factory.domain.enums import AssetType
from mt_clip_factory.domain.services import UnitOfWork
from mt_clip_factory.library.contracts import AssetMetadataAnalyzer, AssetStorage
from mt_clip_factory.library.dto import AssetSummaryDTO, RegisterAssetCommand
from mt_clip_factory.library.readiness import AssetReadinessEvaluator


class AssetCodeAlreadyExistsError(ValueError):
    """Raised when an asset code already exists."""


class AssetSourceFileMissingError(FileNotFoundError):
    """Raised when the source file does not exist."""


class ProductForAssetNotFoundError(ValueError):
    """Raised when the selected product does not exist."""


def _slugify_asset_code(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return normalized.strip("_")


def _resolve_asset_code(command: RegisterAssetCommand) -> str:
    raw_value = command.asset_code if command.asset_code else command.source_file_path.stem
    asset_code = _slugify_asset_code(raw_value)
    if not asset_code:
        raise ValueError("Asset code is required.")
    return asset_code


def _resolve_asset_type(raw_value: str) -> AssetType:
    try:
        return AssetType(raw_value)
    except ValueError as exc:
        raise ValueError(f"Unsupported asset type: {raw_value}") from exc


class AssetIntakeService:
    def __init__(
        self,
        unit_of_work_factory: Callable[[], UnitOfWork],
        asset_storage: AssetStorage,
        metadata_analyzer: AssetMetadataAnalyzer,
        readiness_evaluator: AssetReadinessEvaluator,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._asset_storage = asset_storage
        self._metadata_analyzer = metadata_analyzer
        self._readiness_evaluator = readiness_evaluator

    def register_asset(self, command: RegisterAssetCommand) -> int:
        source_file_path = Path(command.source_file_path)
        if not source_file_path.exists():
            raise AssetSourceFileMissingError(str(source_file_path))

        asset_type = _resolve_asset_type(command.asset_type)
        asset_code = _resolve_asset_code(command)

        with self._unit_of_work_factory() as uow:
            product = uow.products.get_by_id(command.product_id)
            if product is None or product.id is None:
                raise ProductForAssetNotFoundError(str(command.product_id))

            existing = uow.assets.get_by_code(asset_code)
            if existing is not None:
                raise AssetCodeAlreadyExistsError(asset_code)

            stored_file = self._asset_storage.store_asset(
                product_code=product.product_code,
                asset_type=asset_type,
                asset_code=asset_code,
                source_file_path=source_file_path,
            )
            metadata = self._metadata_analyzer.analyze(stored_file.file_path)
            readiness = self._readiness_evaluator.evaluate(asset_type=asset_type, metadata=metadata)

            asset = Asset(
                product_id=product.id,
                asset_code=asset_code,
                asset_type=asset_type,
                file_path=str(stored_file.file_path),
                file_name=stored_file.file_name,
                duration_sec=metadata.duration_sec,
                width=metadata.width,
                height=metadata.height,
                fps=metadata.fps,
                ratio=metadata.ratio,
                file_size_mb=metadata.file_size_mb,
                codec=metadata.codec,
                has_audio=metadata.has_audio,
                status=readiness.status,
            )
            created = uow.assets.add(asset)
            uow.commit()

            if created.id is None:
                raise RuntimeError("Asset identifier was not assigned.")
            return created.id

    def list_assets(
        self,
        product_id: int | None = None,
        asset_type: str | None = None,
        status: str | None = None,
    ) -> list[AssetSummaryDTO]:
        with self._unit_of_work_factory() as uow:
            return [
                AssetSummaryDTO(
                    asset_id=summary.asset_id,
                    product_id=summary.product_id,
                    product_code=summary.product_code,
                    asset_code=summary.asset_code,
                    asset_type=summary.asset_type.value,
                    file_name=summary.file_name,
                    status=summary.status,
                    ratio=summary.ratio,
                    duration_sec=summary.duration_sec,
                    file_size_mb=summary.file_size_mb,
                    tag_labels=summary.tag_labels,
                )
                for summary in uow.assets.list_summaries(
                    product_id=product_id,
                    asset_type=asset_type,
                    status=status,
                )
            ]
