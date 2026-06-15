from __future__ import annotations

from datetime import UTC, datetime
import re
import tomllib
from pathlib import Path

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.factory.auto_factory import AutoFactoryBatchService
from mt_clip_factory.factory.automation_policy import ProductAutomationPolicyError, parse_fill_policies_from_pipeline_data
from mt_clip_factory.factory.auto_factory_dto import AutoFactoryBatchOrderDTO, AutoFactoryProductRequestDTO
from mt_clip_factory.factory.auto_factory_folder_dto import (
    AutoFactoryFolderAssetActionDTO,
    AutoFactoryFolderPipelineConfigDTO,
    AutoFactoryFolderProductConfigDTO,
    AutoFactoryFolderProductReportDTO,
    AutoFactoryFolderRunReportDTO,
)
from mt_clip_factory.factory.caption_runtime import ProductAutomationMetadataStore
from mt_clip_factory.factory.product_run_store import ProductRunArtifactStore
from mt_clip_factory.library.dto import RegisterAssetCommand
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.tag_dto import AssignTagToAssetCommand
from mt_clip_factory.library.tag_services import TagManagementService

_ASSET_FOLDER_TYPES = {
    "foreground": "foreground_video",
    "background": "background_video",
    "music": "background_music",
    "voice": "voiceover",
}
_CONTRACTS_DIR_NAME = "contracts"
_ASSETS_DIR_NAME = "assets"

_MEDIA_SUFFIXES_BY_ASSET_TYPE = {
    "foreground_video": {".mp4", ".mov", ".mkv", ".avi", ".webm"},
    "background_video": {".mp4", ".mov", ".mkv", ".avi", ".webm"},
    "background_music": {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"},
    "voiceover": {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"},
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
        tag_management_service: TagManagementService,
        automation_metadata_store: ProductAutomationMetadataStore | None = None,
        run_artifact_store: ProductRunArtifactStore | None = None,
    ) -> None:
        self._product_service = product_service
        self._asset_intake_service = asset_intake_service
        self._auto_factory_service = auto_factory_service
        self._tag_management_service = tag_management_service
        self._automation_metadata_store = automation_metadata_store
        self._run_artifact_store = run_artifact_store

    def _apply_tag_labels_to_asset(self, *, asset_id: int, tag_labels: tuple[str, ...]) -> None:
        for label in tag_labels:
            tag_group, tag_name = label.split(":", maxsplit=1)
            tag_id = self._tag_management_service.ensure_tag(tag_group=tag_group, tag_name=tag_name)
            self._tag_management_service.assign_tag_to_asset(
                AssignTagToAssetCommand(asset_id=asset_id, tag_id=tag_id)
            )

    def run_batch_root(
        self,
        batch_root: Path,
        *,
        batch_code: str | None = None,
        scan_depth: int = 1,
        materialize: bool = True,
        build_previews: bool = False,
    ) -> AutoFactoryFolderRunReportDTO:
        if build_previews and not materialize:
            raise AutoFactoryFolderContractError("build_previews requires materialize=True so preview jobs have recipes to run.")

        root_path = Path(batch_root)
        product_dirs = _discover_product_dirs(root_path, scan_depth=scan_depth)
        product_configs = {product_dir: _load_product_config(product_dir) for product_dir in product_dirs}
        pipeline_configs = {product_dir: _load_pipeline_config(product_dir) for product_dir in product_dirs}
        effective_batch_code = _slugify(batch_code or root_path.name or "auto_factory_batch")

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

            self._sync_product_runtime_contracts(
                product_code=product_config.product_code,
                product_dir=product_dir,
                batch_code=effective_batch_code,
            )

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

        order = AutoFactoryBatchOrderDTO(
            batch_code=effective_batch_code,
            product_requests=tuple(
                _to_product_request(product_configs[product_dir], pipeline_configs[product_dir])
                for product_dir in product_dirs
            ),
        )
        for product_dir in product_dirs:
            self._write_product_run_snapshot(
                batch_code=effective_batch_code,
                scan_depth=scan_depth,
                materialize=materialize,
                build_previews=build_previews,
                product_dir=product_dir,
                product_config=product_configs[product_dir],
                pipeline_config=pipeline_configs[product_dir],
                product_report=next(
                    report
                    for report in product_reports
                    if report.product_code == product_configs[product_dir].product_code
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
            scan_depth=scan_depth,
            order=order,
            discovered_product_dirs=tuple(str(product_dir) for product_dir in product_dirs),
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
            source_dir = _resolve_asset_folder(product_dir, folder_name)
            if source_dir is None:
                continue
            tag_config = _load_folder_tag_config(source_dir)
            for source_file in sorted(
                path for path in source_dir.iterdir() if _is_ingestible_asset_file(path, asset_type=asset_type)
            ):
                asset_code = _build_asset_code(product_code=product_code, asset_type=asset_type, file_stem=source_file.stem)
                tag_labels = _resolve_tag_labels_for_file(tag_config, source_file.name)
                if asset_code in existing_assets:
                    existing_asset = self._asset_intake_service.find_asset_by_code(asset_code)
                    if existing_asset is not None:
                        self._apply_tag_labels_to_asset(asset_id=existing_asset.asset_id, tag_labels=tag_labels)
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
                asset_id = self._asset_intake_service.register_asset(
                    RegisterAssetCommand(
                        product_id=product_id,
                        asset_type=asset_type,
                        source_file_path=source_file,
                        asset_code=asset_code,
                    )
                )
                self._apply_tag_labels_to_asset(asset_id=asset_id, tag_labels=tag_labels)
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

    def _sync_product_runtime_contracts(self, *, product_code: str, product_dir: Path, batch_code: str | None) -> None:
        if self._automation_metadata_store is None:
            return
        synced_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        source_file = _resolve_contract_file(product_dir, "captions.toml", required=False)
        self._automation_metadata_store.sync_caption_contract(
            product_code=product_code,
            source_file=source_file,
        )
        pipeline_file = _resolve_contract_file(product_dir, "pipeline.toml", required=False)
        self._automation_metadata_store.sync_pipeline_contract(
            product_code=product_code,
            source_file=pipeline_file,
        )
        self._automation_metadata_store.sync_runtime_context(
            product_code=product_code,
            source_product_dir=product_dir,
            batch_code=batch_code,
            synced_at=synced_at,
        )

    def _write_product_run_snapshot(
        self,
        *,
        batch_code: str,
        scan_depth: int,
        materialize: bool,
        build_previews: bool,
        product_dir: Path,
        product_config: AutoFactoryFolderProductConfigDTO,
        pipeline_config: AutoFactoryFolderPipelineConfigDTO,
        product_report: AutoFactoryFolderProductReportDTO,
    ) -> None:
        del product_dir
        if self._run_artifact_store is None:
            return
        snapshot_path = self._run_artifact_store.write_order_snapshot(
            product_code=product_config.product_code,
            batch_code=batch_code,
            payload={
                "scan_depth": scan_depth,
                "materialize_requested": materialize,
                "build_previews_requested": build_previews,
                "requested_output_count": pipeline_config.requested_output_count,
                "target_platform": pipeline_config.target_platform,
                "target_ratio": pipeline_config.target_ratio,
                "uniqueness_scope": pipeline_config.uniqueness_scope,
                "duration_mode": pipeline_config.duration_mode,
                "min_duration_sec": pipeline_config.min_duration_sec,
                "max_duration_sec": pipeline_config.max_duration_sec,
                "created_product": product_report.created_product,
                "registered_asset_count": product_report.registered_asset_count,
                "skipped_existing_asset_count": product_report.skipped_existing_asset_count,
            },
        )
        self._run_artifact_store.append_journal_event(
            product_code=product_config.product_code,
            batch_code=batch_code,
            event_type="intake_completed",
            status="succeeded",
            fields={
                "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "order_snapshot_path": None if snapshot_path is None else str(snapshot_path),
                "registered_asset_count": product_report.registered_asset_count,
                "skipped_existing_asset_count": product_report.skipped_existing_asset_count,
            },
        )


def _discover_product_dirs(batch_root: Path, *, scan_depth: int) -> tuple[Path, ...]:
    if not batch_root.exists() or not batch_root.is_dir():
        raise AutoFactoryFolderContractError(f"Batch root does not exist or is not a directory: {batch_root}")
    if scan_depth < 0:
        raise AutoFactoryFolderContractError(f"scan_depth must be >= 0 but got {scan_depth}")

    product_dirs: list[Path] = []

    def walk(current_dir: Path, depth: int) -> None:
        if _is_product_contract_dir(current_dir):
            product_dirs.append(current_dir)
            return
        if depth >= scan_depth:
            return
        child_dirs = sorted(path for path in current_dir.iterdir() if path.is_dir())
        for child_dir in child_dirs:
            walk(child_dir, depth + 1)

    walk(batch_root, 0)
    if not product_dirs:
        raise AutoFactoryFolderContractError(
            f"No product folders were found under {batch_root}. Expected directories containing "
            "product.toml and pipeline.toml, either at the product root or under contracts/."
        )
    return tuple(product_dirs)


def _is_product_contract_dir(path: Path) -> bool:
    return path.is_dir() and _has_contract_file(path, "product.toml") and _has_contract_file(path, "pipeline.toml")


def _load_product_config(product_dir: Path) -> AutoFactoryFolderProductConfigDTO:
    product_file = _resolve_contract_file(product_dir, "product.toml")
    data = _load_toml(product_file)
    section = data.get("product")
    if not isinstance(section, dict):
        raise AutoFactoryFolderContractError(f"Missing [product] section in {product_file}")

    product_code = _slugify(str(section.get("product_code", "")))
    product_name = str(section.get("product_name", "")).strip()
    if not product_code:
        raise AutoFactoryFolderContractError(f"product_code is required in {product_file}")
    if not product_name:
        raise AutoFactoryFolderContractError(f"product_name is required in {product_file}")

    return AutoFactoryFolderProductConfigDTO(
        product_code=product_code,
        product_name=product_name,
        category=_optional_text(section.get("category")),
        brand_name=_optional_text(section.get("brand_name")),
        description=_optional_text(section.get("description")),
        default_platform=_optional_text(section.get("default_platform")),
    )


def _load_pipeline_config(product_dir: Path) -> AutoFactoryFolderPipelineConfigDTO:
    pipeline_file = _resolve_contract_file(product_dir, "pipeline.toml")
    data = _load_toml(pipeline_file)
    try:
        parse_fill_policies_from_pipeline_data(data, source_name=str(pipeline_file))
    except ProductAutomationPolicyError as exc:
        raise AutoFactoryFolderContractError(str(exc)) from exc
    section = data.get("request")
    if not isinstance(section, dict):
        raise AutoFactoryFolderContractError(f"Missing [request] section in {pipeline_file}")
    selection_tags_section = data.get("selection_tags")
    if selection_tags_section is None:
        selection_tags_section = {}
    if not isinstance(selection_tags_section, dict):
        raise AutoFactoryFolderContractError(f"Invalid [selection_tags] section in {pipeline_file}")

    requested_output_count = section.get("requested_output_count")
    if not isinstance(requested_output_count, int) or requested_output_count <= 0:
        raise AutoFactoryFolderContractError(
            f"requested_output_count must be a positive integer in {pipeline_file}"
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
        foreground_required_tag_labels=_optional_text_list(selection_tags_section.get("foreground")),
        background_required_tag_labels=_optional_text_list(selection_tags_section.get("background")),
        music_required_tag_labels=_optional_text_list(selection_tags_section.get("music")),
        voice_required_tag_labels=_optional_text_list(selection_tags_section.get("voice")),
    )


def _load_toml(file_path: Path) -> dict:
    with file_path.open("rb") as file_handle:
        data = tomllib.load(file_handle)
    if not isinstance(data, dict):
        raise AutoFactoryFolderContractError(f"Invalid TOML object in {file_path}")
    return data


def _has_contract_file(product_dir: Path, file_name: str) -> bool:
    legacy_file, versioned_file = _contract_file_candidates(product_dir, file_name)
    return legacy_file.exists() or versioned_file.exists()


def _resolve_contract_file(product_dir: Path, file_name: str, *, required: bool = True) -> Path | None:
    legacy_file, versioned_file = _contract_file_candidates(product_dir, file_name)
    return _resolve_layout_path(
        product_dir=product_dir,
        legacy_path=legacy_file,
        versioned_path=versioned_file,
        logical_name=file_name,
        required=required,
    )


def _contract_file_candidates(product_dir: Path, file_name: str) -> tuple[Path, Path]:
    return product_dir / file_name, product_dir / _CONTRACTS_DIR_NAME / file_name


def _resolve_asset_folder(product_dir: Path, folder_name: str) -> Path | None:
    return _resolve_layout_path(
        product_dir=product_dir,
        legacy_path=product_dir / folder_name,
        versioned_path=product_dir / _ASSETS_DIR_NAME / folder_name,
        logical_name=f"{folder_name}/",
        required=False,
    )


def _resolve_layout_path(
    *,
    product_dir: Path,
    legacy_path: Path,
    versioned_path: Path,
    logical_name: str,
    required: bool,
) -> Path | None:
    legacy_exists = legacy_path.exists()
    versioned_exists = versioned_path.exists()
    if legacy_exists and versioned_exists:
        raise AutoFactoryFolderContractError(
            f"Ambiguous product folder layout for {logical_name} under {product_dir}. "
            f"Found both legacy path {legacy_path} and versioned path {versioned_path}. "
            "Keep only one layout for each logical location."
        )
    if versioned_exists:
        return versioned_path
    if legacy_exists:
        return legacy_path
    if required:
        raise AutoFactoryFolderContractError(
            f"Missing required {logical_name} under {product_dir}. "
            f"Expected either {legacy_path} or {versioned_path}."
        )
    return None


def _load_folder_tag_config(folder_path: Path) -> dict[str, object]:
    tag_file = folder_path / "tags.toml"
    if not tag_file.exists():
        return {"global_tags": (), "file_tags": {}}

    data = _load_toml(tag_file)
    global_tags = _normalize_tag_label_list(data.get("global_tags"), file_path=tag_file)
    file_tags_section = data.get("file_tags")
    if file_tags_section is None:
        file_tags_section = {}
    if not isinstance(file_tags_section, dict):
        raise AutoFactoryFolderContractError(f"Expected [file_tags] table in {tag_file}")

    normalized_file_tags: dict[str, tuple[str, ...]] = {}
    for file_name, tag_values in file_tags_section.items():
        normalized_file_name = _optional_text(file_name)
        if normalized_file_name is None:
            continue
        normalized_file_tags[normalized_file_name] = _normalize_tag_label_list(tag_values, file_path=tag_file)

    return {
        "global_tags": global_tags,
        "file_tags": normalized_file_tags,
    }


def _resolve_tag_labels_for_file(tag_config: dict[str, object], file_name: str) -> tuple[str, ...]:
    global_tags = tuple(tag_config.get("global_tags", ()))
    file_tags = dict(tag_config.get("file_tags", {}))
    resolved: list[str] = []
    seen: set[str] = set()
    for label in (*global_tags, *tuple(file_tags.get(file_name, ()))):
        normalized = label.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        resolved.append(normalized)
    return tuple(resolved)


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
        foreground_required_tag_labels=pipeline_config.foreground_required_tag_labels,
        background_required_tag_labels=pipeline_config.background_required_tag_labels,
        music_required_tag_labels=pipeline_config.music_required_tag_labels,
        voice_required_tag_labels=pipeline_config.voice_required_tag_labels,
    )


def _build_asset_code(*, product_code: str, asset_type: str, file_stem: str) -> str:
    type_prefix = _ASSET_TYPE_CODE_PREFIX[asset_type]
    slug = _slugify(file_stem)
    if not slug:
        raise AutoFactoryFolderContractError("Asset file stem must contain at least one slugifiable character.")
    return f"{product_code}_{type_prefix}_{slug}"


def _is_ingestible_asset_file(file_path: Path, *, asset_type: str) -> bool:
    if not file_path.is_file():
        return False
    suffix = file_path.suffix.lower()
    return suffix in _MEDIA_SUFFIXES_BY_ASSET_TYPE.get(asset_type, set())


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


def _optional_text_list(value) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise AutoFactoryFolderContractError(f"Expected list of text values but got {value!r}")
    normalized_values: list[str] = []
    for item in value:
        text = _optional_text(item)
        if text is None:
            continue
        normalized_values.append(text.casefold())
    return tuple(normalized_values)


def _normalize_tag_label_list(value, *, file_path: Path) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise AutoFactoryFolderContractError(f"Expected list of tag labels in {file_path} but got {value!r}")

    normalized_values: list[str] = []
    seen: set[str] = set()
    for item in value:
        label = _normalize_tag_label(item, file_path=file_path)
        if label in seen:
            continue
        seen.add(label)
        normalized_values.append(label)
    return tuple(normalized_values)


def _normalize_tag_label(value, *, file_path: Path) -> str:
    text = _optional_text(value)
    if text is None:
        raise AutoFactoryFolderContractError(f"Tag labels must be non-empty in {file_path}")
    normalized = text.casefold()
    if normalized.count(":") != 1:
        raise AutoFactoryFolderContractError(
            f"Tag labels must use exactly one group:name separator in {file_path}: {text!r}"
        )
    tag_group, tag_name = normalized.split(":", maxsplit=1)
    tag_group = tag_group.strip()
    tag_name = tag_name.strip()
    if not tag_group or not tag_name:
        raise AutoFactoryFolderContractError(f"Tag labels must have non-empty group and name in {file_path}: {text!r}")
    return f"{tag_group}:{tag_name}"
