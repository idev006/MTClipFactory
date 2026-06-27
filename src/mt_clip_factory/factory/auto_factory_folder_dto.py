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
    foreground_required_tag_labels: tuple[str, ...] = ()
    background_required_tag_labels: tuple[str, ...] = ()
    music_required_tag_labels: tuple[str, ...] = ()
    voice_required_tag_labels: tuple[str, ...] = ()
    creative_preset_mode: str = "auto_best_fit"
    creative_preset_codes: tuple[str, ...] = ()


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
    product_dir: str | None = None


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


@dataclass(slots=True, frozen=True)
class AutoFactoryFolderPreflightIssueDTO:
    severity: str
    code: str
    message: str
    location: str | None = None


@dataclass(slots=True, frozen=True)
class AutoFactoryFolderContractAuditDTO:
    contract_name: str
    resolved_path: str | None
    layout_mode: str | None
    required: bool
    present: bool


@dataclass(slots=True, frozen=True)
class AutoFactoryFolderCaptionContractAuditDTO:
    selection_mode: str | None
    seed_scope: str | None
    segment_pool_names: tuple[str, ...]
    main_pool_entry_count: int
    sub_pool_entry_count: int
    main_style_preset: str | None = None
    sub_style_preset: str | None = None
    main_font_family: str | None = None
    sub_font_family: str | None = None


@dataclass(slots=True, frozen=True)
class AutoFactoryFolderCreativePresetContractAuditDTO:
    preset_count: int
    enabled_preset_count: int
    preset_codes: tuple[str, ...]
    platform_count: int
    ratio_count: int
    headline_pool_name_count: int


@dataclass(slots=True, frozen=True)
class AutoFactoryFolderAssetFolderAuditDTO:
    folder_name: str
    asset_type: str
    resolved_path: str | None
    layout_mode: str | None
    ingestible_file_count: int
    ingestible_files: tuple[str, ...]
    tag_file_present: bool
    global_tag_count: int
    file_tag_entry_count: int
    tagged_file_count: int
    required_tag_labels: tuple[str, ...] = ()
    matching_required_file_count: int = 0
    issues: tuple[AutoFactoryFolderPreflightIssueDTO, ...] = ()


@dataclass(slots=True, frozen=True)
class AutoFactoryFolderPreflightProductReportDTO:
    product_dir: str
    layout_mode: str
    status: str
    product_code: str | None
    product_name: str | None
    requested_output_count: int | None
    ready_for_automation: bool
    contracts: tuple[AutoFactoryFolderContractAuditDTO, ...]
    asset_folders: tuple[AutoFactoryFolderAssetFolderAuditDTO, ...]
    issues: tuple[AutoFactoryFolderPreflightIssueDTO, ...]
    ingestible_asset_count: int
    product_config: AutoFactoryFolderProductConfigDTO | None = None
    pipeline_config: AutoFactoryFolderPipelineConfigDTO | None = None
    caption_contract: AutoFactoryFolderCaptionContractAuditDTO | None = None
    creative_preset_contract: AutoFactoryFolderCreativePresetContractAuditDTO | None = None


@dataclass(slots=True, frozen=True)
class AutoFactoryFolderPreflightReportDTO:
    root_folder: str
    scan_depth: int
    discovered_product_dirs: tuple[str, ...]
    status: str
    error_count: int
    warning_count: int
    product_reports: tuple[AutoFactoryFolderPreflightProductReportDTO, ...]
