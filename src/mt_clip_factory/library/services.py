from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from mt_clip_factory.domain.assets import Asset
from mt_clip_factory.domain.enums import AssetType
from mt_clip_factory.domain.services import UnitOfWork
from mt_clip_factory.library.contracts import AssetMetadataAnalyzer, AssetStorage
from mt_clip_factory.library.dto import (
    AssetJobReferenceDTO,
    AssetMediaPurgeReportDTO,
    AssetRecipeReferenceDTO,
    AssetReferenceReportDTO,
    AssetSummaryDTO,
    RegisterAssetCommand,
    UpdateAssetCommand,
)
from mt_clip_factory.library.readiness import AssetReadinessEvaluator


class AssetCodeAlreadyExistsError(ValueError):
    """Raised when an asset code already exists."""


class AssetSourceFileMissingError(FileNotFoundError):
    """Raised when the source file does not exist."""


class ProductForAssetNotFoundError(ValueError):
    """Raised when the selected product does not exist."""


class AssetNotFoundError(ValueError):
    """Raised when the selected asset does not exist."""


class AssetInUseError(ValueError):
    """Raised when an asset is still referenced by workflow records."""


class AssetRetireRequiredError(ValueError):
    """Raised when an asset must be retired before media purge."""


class AssetMediaAlreadyPurgedError(ValueError):
    """Raised when an asset's media files were already purged."""


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
                    thumbnail_path=summary.thumbnail_path,
                    proxy_path=summary.proxy_path,
                )
                for summary in uow.assets.list_summaries(
                    product_id=product_id,
                    asset_type=asset_type,
                    status=status,
                )
            ]

    def update_asset(self, command: UpdateAssetCommand) -> int:
        asset_code = _slugify_asset_code(command.asset_code)
        if not asset_code:
            raise ValueError("Asset code is required.")

        with self._unit_of_work_factory() as uow:
            asset = _require_asset(uow, command.asset_id)
            if asset.status == "purged":
                raise AssetSourceFileMissingError(
                    "Asset media has already been purged. Register a replacement asset instead of renaming this record."
                )

            existing = uow.assets.get_by_code(asset_code)
            if existing is not None and existing.id != asset.id:
                raise AssetCodeAlreadyExistsError(asset_code)

            if asset.asset_code == asset_code:
                return asset.id

            old_asset_code = asset.asset_code
            primary_path = Path(asset.file_path)
            if not primary_path.exists():
                raise AssetSourceFileMissingError(str(primary_path))
            renamed_primary = _rename_path_for_asset_code(
                primary_path,
                old_asset_code=old_asset_code,
                new_asset_code=asset_code,
                required=True,
            )
            asset.asset_code = asset_code
            asset.file_path = str(renamed_primary)
            asset.file_name = renamed_primary.name
            asset.thumbnail_path = _rename_optional_path_for_asset_code(asset.thumbnail_path, old_asset_code, asset_code)
            asset.proxy_path = _rename_optional_path_for_asset_code(asset.proxy_path, old_asset_code, asset_code)
            asset.alpha_path = _rename_optional_path_for_asset_code(asset.alpha_path, old_asset_code, asset_code)
            asset.rgba_cache_path = _rename_optional_path_for_asset_code(asset.rgba_cache_path, old_asset_code, asset_code)
            uow.assets.update(asset)
            uow.commit()
            return asset.id

    def delete_asset(self, asset_id: int) -> None:
        with self._unit_of_work_factory() as uow:
            asset = _require_asset(uow, asset_id)
            if uow.assets.has_recipe_item_references(asset_id):
                raise AssetInUseError(
                    "Asset is attached to one or more recipe items. Use 'Show References' and 'Retire Selected' instead."
                )
            if uow.assets.has_job_references(asset_id):
                raise AssetInUseError(
                    "Asset has artifact jobs and cannot be deleted. Use 'Show References' and 'Retire Selected' instead."
                )
            file_paths = _asset_file_paths(asset)
            uow.assets.delete(asset_id)
            uow.commit()

        for file_path in file_paths:
            if file_path is None:
                continue
            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                continue

    def retire_asset(self, asset_id: int) -> int:
        with self._unit_of_work_factory() as uow:
            asset = _require_asset(uow, asset_id)
            if asset.status == "purged":
                raise AssetMediaAlreadyPurgedError(
                    "Asset media is already purged. Keep this record for history and register a replacement asset for future work."
                )
            if asset.status == "retired":
                return asset.id
            asset.status = "retired"
            uow.assets.update(asset)
            uow.commit()
            return asset.id

    def purge_asset_media(self, asset_id: int) -> AssetMediaPurgeReportDTO:
        with self._unit_of_work_factory() as uow:
            asset = _require_asset(uow, asset_id)
            if asset.status == "purged":
                raise AssetMediaAlreadyPurgedError("Asset media is already purged.")
            if asset.status != "retired":
                raise AssetRetireRequiredError("Retire the asset before purging its media.")
            file_paths = _asset_file_paths(asset)
            asset.status = "purged"
            asset.thumbnail_path = None
            asset.proxy_path = None
            asset.alpha_path = None
            asset.rgba_cache_path = None
            uow.assets.update(asset)
            uow.commit()

        deleted_count = 0
        reclaimed_bytes = 0
        for file_path in file_paths:
            if file_path is None or not file_path.exists():
                continue
            try:
                reclaimed_bytes += file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1
            except OSError:
                continue

        return AssetMediaPurgeReportDTO(
            asset_id=asset_id,
            asset_code=asset.asset_code,
            purged_file_count=deleted_count,
            reclaimed_bytes=reclaimed_bytes,
        )

    def describe_asset_references(self, asset_id: int) -> AssetReferenceReportDTO:
        with self._unit_of_work_factory() as uow:
            asset = _require_asset(uow, asset_id)
            recipe_references = tuple(
                AssetRecipeReferenceDTO(
                    recipe_id=reference.recipe_id,
                    recipe_code=reference.recipe_code,
                    recipe_status=reference.recipe_status,
                    output_count=reference.output_count,
                )
                for reference in uow.assets.list_recipe_references(asset_id)
            )
            job_references = tuple(
                AssetJobReferenceDTO(
                    job_id=reference.job_id,
                    job_code=reference.job_code,
                    job_type=reference.job_type,
                    job_status=reference.job_status,
                )
                for reference in uow.assets.list_job_references(asset_id)
            )
            return AssetReferenceReportDTO(
                asset_id=asset.id,
                asset_code=asset.asset_code,
                asset_status=asset.status,
                recipe_references=recipe_references,
                job_references=job_references,
                can_delete=not recipe_references and not job_references,
                can_purge_media=asset.status == "retired",
            )


def _require_asset(uow: UnitOfWork, asset_id: int) -> Asset:
    asset = uow.assets.get_by_id(asset_id)
    if asset is None or asset.id is None:
        raise AssetNotFoundError(str(asset_id))
    return asset


def _asset_file_paths(asset: Asset) -> list[Path | None]:
    return [
        Path(asset.file_path),
        Path(asset.thumbnail_path) if asset.thumbnail_path else None,
        Path(asset.proxy_path) if asset.proxy_path else None,
        Path(asset.alpha_path) if asset.alpha_path else None,
        Path(asset.rgba_cache_path) if asset.rgba_cache_path else None,
    ]


def _rename_path_for_asset_code(
    file_path: Path,
    *,
    old_asset_code: str,
    new_asset_code: str,
    required: bool,
) -> Path:
    if not file_path.exists():
        if required:
            raise AssetSourceFileMissingError(str(file_path))
        return file_path
    stem = file_path.stem
    if stem == old_asset_code:
        new_stem = new_asset_code
    elif stem.startswith(f"{old_asset_code}_"):
        new_stem = f"{new_asset_code}{stem[len(old_asset_code):]}"
    else:
        new_stem = new_asset_code
    target_path = file_path.with_name(f"{new_stem}{file_path.suffix.lower()}")
    if target_path == file_path:
        return file_path
    if target_path.exists():
        raise FileExistsError(str(target_path))
    file_path.rename(target_path)
    return target_path


def _rename_optional_path_for_asset_code(raw_path: str | None, old_asset_code: str, new_asset_code: str) -> str | None:
    if not raw_path:
        return None
    file_path = Path(raw_path)
    if not file_path.exists():
        return None
    renamed = _rename_path_for_asset_code(
        file_path,
        old_asset_code=old_asset_code,
        new_asset_code=new_asset_code,
        required=False,
    )
    return str(renamed)
