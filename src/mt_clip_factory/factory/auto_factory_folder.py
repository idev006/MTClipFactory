from __future__ import annotations

import re
import tomllib
from pathlib import Path

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.factory.auto_factory import AutoFactoryBatchService
from mt_clip_factory.factory.auto_factory_dto import AutoFactoryBatchOrderDTO, AutoFactoryProductRequestDTO
from mt_clip_factory.factory.auto_factory_folder_dto import (
    AutoFactoryFolderAssetActionDTO,
    AutoFactoryFolderPipelineConfigDTO,
    AutoFactoryFolderProductConfigDTO,
    AutoFactoryFolderProductReportDTO,
    AutoFactoryFolderRunReportDTO,
)
from mt_clip_factory.library.dto import RegisterAssetCommand
from mt_clip_factory.library.services import AssetIntakeService

_ASSET_FOLDER_TYPES = {
    "foreground": "foreground_video",
    "background": "background_video",
    "music": "background_music",
    "voice": "voiceover",
}

_ASSET_TYPE_CODE_PREFIX = {
    "foreground_video": "fg",
    "background_video": "bg",
    "background_music": "music",
    "voiceover": "voice",
}


class AutoFactoryFolderContractError(ValueError):
    """Raised when the product-folder automation contract is invalid."""


class AutoFactoryFolderService:
    def __init__(
        self,
        *,
        product_service: ProductApplicationService,
        asset_intake_service: AssetIntakeService,
        auto_factory_service: AutoFactoryBatchService,
    ) -> None:
        self._product_service = product_service
        self._asset_intake_service = asset_intake_service
        self._auto_factory_service = auto_factory_service

    def run_batch_root(
        self,
        batch_root: Path,
        *,
        batch_code: str | None = None,
        materialize: bool = True,
        build_previews: bool = False,
    ) -> AutoFactoryFolderRunReportDTO:
        if build_previews and not materialize:
            raise AutoFactoryFolderContractError("build_previews requires materialize=True so preview jobs have recipes to run.")

        root_path = Path(batch_root)
        product_dirs = _discover_product_dirs(root_path)
        product_configs = {product_dir: _load_product_config(product_dir) for product_dir in product_dirs}
        pipeline_configs = {product_dir: _load_pipeline_config(product_dir) for product_dir in product_dirs}

        existing_product_ids = {product.product_code: product.product_id for product in self._product_service.list_products()}
        product_reports: list[AutoFactoryFolderProductReportDTO] = []
        asset_actions: list[AutoFactoryFolderAssetActionDTO] = []

        for product_dir in product_dirs:
            product_config = product_configs[product_dir]
            existing_product_id = existing_product_ids.get(product_config.product_code)
            if existing_product_id is None:
                product_id = self._product_service.create_product(
                    CreateProductCommand(
                        product_code=product_config.product_code,
                        product_name=product_config.product_name,
                        category=product_config.category,
                        brand_name=product_config.brand_name,
                        description=product_config.description,
                        default_platform=product_config.default_platform,
                    )
                )
                created_product = True
                existing_product_ids[product_config.product_code] = product_id
            else:
                product_id = existing_product_id
                created_product = False

            registered_asset_count, skipped_existing_asset_count, product_actions = self._intake_product_assets(
                product_dir=product_dir,
                product_code=product_config.product_code,
                product_id=product_id,
            )
            asset_actions.extend(product_actions)
            product_reports.append(
                AutoFactoryFolderProductReportDTO(
                    product_id=product_id,
                    product_code=product_config.product_code,
                    created_product=created_product,
                    registered_asset_count=registered_asset_count,
                    skipped_existing_asset_count=skipped_existing_asset_count,
                )
            )

        effective_batch_code = _slugify(batch_code or root_path.name or "auto_factory_batch")
        order = AutoFactoryBatchOrderDTO(
            batch_code=effective_batch_code,
            product_requests=tuple(
                _to_product_request(product_configs[product_dir], pipeline_configs[product_dir])
                for product_dir in product_dirs
            ),
        )
        materialization = None
        preview_production = None
        if materialize and build_previews:
            execution = self._auto_factory_service.materialize_batch_and_build_previews(order)
            materialization = execution.materialization
            preview_production = execution.preview_production
        elif materialize:
            materialization = self._auto_factory_service.materialize_batch(order)
        return AutoFactoryFolderRunReportDTO(
            batch_code=effective_batch_code,
            order=order,
            product_reports=tuple(product_reports),
            asset_actions=tuple(asset_actions),
            materialization=materialization,
            preview_production=preview_production,
        )

    def _intake_product_assets(
        self,
        *,
        product_dir: Path,
        product_code: str,
        product_id: int,
    ) -> tuple[int, int, list[AutoFactoryFolderAssetActionDTO]]:
        existing_assets = {
            asset.asset_code
            for asset in self._asset_intake_service.list_assets(product_id=product_id)
        }
        registered_asset_count = 0
        skipped_existing_asset_count = 0
        actions: list[AutoFactoryFolderAssetActionDTO] = []

        for folder_name, asset_type in _ASSET_FOLDER_TYPES.items():
            source_dir = product_dir / folder_name
            if not source_dir.exists():
                continue
            for source_file in sorted(path for path in source_dir.iterdir() if path.is_file()):
                asset_code = _build_asset_code(product_code=product_code, asset_type=asset_type, file_stem=source_file.stem)
                if asset_code in existing_assets:
                    skipped_existing_asset_count += 1
                    actions.append(
                        AutoFactoryFolderAssetActionDTO(
                            product_code=product_code,
                            asset_type=asset_type,
                            asset_code=asset_code,
                            source_file=str(source_file),
                            action="skipped_existing",
                        )
                    )
                    continue
                self._asset_intake_service.register_asset(
                    RegisterAssetCommand(
                        product_id=product_id,
                        asset_type=asset_type,
                        source_file_path=source_file,
                        asset_code=asset_code,
                    )
                )
                existing_assets.add(asset_code)
                registered_asset_count += 1
                actions.append(
                    AutoFactoryFolderAssetActionDTO(
                        product_code=product_code,
                        asset_type=asset_type,
                        asset_code=asset_code,
                        source_file=str(source_file),
                        action="registered",
                    )
                )

        return registered_asset_count, skipped_existing_asset_count, actions


def _discover_product_dirs(batch_root: Path) -> tuple[Path, ...]:
    if not batch_root.exists() or not batch_root.is_dir():
        raise AutoFactoryFolderContractError(f"Batch root does not exist or is not a directory: {batch_root}")
    product_dirs = tuple(
        sorted(
            product_dir
            for product_dir in batch_root.iterdir()
            if product_dir.is_dir() and (product_dir / "product.toml").exists() and (product_dir / "pipeline.toml").exists()
        )
    )
    if not product_dirs:
        raise AutoFactoryFolderContractError(
            f"No product folders were found under {batch_root}. Expected directories containing product.toml and pipeline.toml."
        )
    return product_dirs


def _load_product_config(product_dir: Path) -> AutoFactoryFolderProductConfigDTO:
    data = _load_toml(product_dir / "product.toml")
    section = data.get("product")
    if not isinstance(section, dict):
        raise AutoFactoryFolderContractError(f"Missing [product] section in {product_dir / 'product.toml'}")

    product_code = _slugify(str(section.get("product_code", "")))
    product_name = str(section.get("product_name", "")).strip()
    if not product_code:
        raise AutoFactoryFolderContractError(f"product_code is required in {product_dir / 'product.toml'}")
    if not product_name:
        raise AutoFactoryFolderContractError(f"product_name is required in {product_dir / 'product.toml'}")

    return AutoFactoryFolderProductConfigDTO(
        product_code=product_code,
        product_name=product_name,
        category=_optional_text(section.get("category")),
        brand_name=_optional_text(section.get("brand_name")),
        description=_optional_text(section.get("description")),
        default_platform=_optional_text(section.get("default_platform")),
    )


def _load_pipeline_config(product_dir: Path) -> AutoFactoryFolderPipelineConfigDTO:
    data = _load_toml(product_dir / "pipeline.toml")
    section = data.get("request")
    if not isinstance(section, dict):
        raise AutoFactoryFolderContractError(f"Missing [request] section in {product_dir / 'pipeline.toml'}")

    requested_output_count = section.get("requested_output_count")
    if not isinstance(requested_output_count, int) or requested_output_count <= 0:
        raise AutoFactoryFolderContractError(
            f"requested_output_count must be a positive integer in {product_dir / 'pipeline.toml'}"
        )
    return AutoFactoryFolderPipelineConfigDTO(
        requested_output_count=requested_output_count,
        target_platform=_optional_text(section.get("target_platform")),
        target_ratio=_optional_text(section.get("target_ratio")),
        uniqueness_scope=_optional_text(section.get("uniqueness_scope")) or "batch",
        duration_mode=_optional_text(section.get("duration_mode")) or "voice_with_bounds",
        fixed_duration_sec=_optional_float(section.get("fixed_duration_sec")),
        min_duration_sec=_optional_float(section.get("min_duration_sec"), fallback=12.0),
        max_duration_sec=_optional_float(section.get("max_duration_sec"), fallback=30.0),
    )


def _load_toml(file_path: Path) -> dict:
    with file_path.open("rb") as file_handle:
        data = tomllib.load(file_handle)
    if not isinstance(data, dict):
        raise AutoFactoryFolderContractError(f"Invalid TOML object in {file_path}")
    return data


def _to_product_request(
    product_config: AutoFactoryFolderProductConfigDTO,
    pipeline_config: AutoFactoryFolderPipelineConfigDTO,
) -> AutoFactoryProductRequestDTO:
    return AutoFactoryProductRequestDTO(
        product_code=product_config.product_code,
        requested_output_count=pipeline_config.requested_output_count,
        target_platform=pipeline_config.target_platform or product_config.default_platform,
        target_ratio=pipeline_config.target_ratio,
        uniqueness_scope=pipeline_config.uniqueness_scope,
        duration_mode=pipeline_config.duration_mode,
        fixed_duration_sec=pipeline_config.fixed_duration_sec,
        min_duration_sec=pipeline_config.min_duration_sec,
        max_duration_sec=pipeline_config.max_duration_sec,
    )


def _build_asset_code(*, product_code: str, asset_type: str, file_stem: str) -> str:
    type_prefix = _ASSET_TYPE_CODE_PREFIX[asset_type]
    slug = _slugify(file_stem)
    if not slug:
        raise AutoFactoryFolderContractError("Asset file stem must contain at least one slugifiable character.")
    return f"{product_code}_{type_prefix}_{slug}"


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return normalized.strip("_")


def _optional_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value, *, fallback: float | None = None) -> float | None:
    if value is None:
        return fallback
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise AutoFactoryFolderContractError(f"Expected numeric value but got {value!r}") from exc
