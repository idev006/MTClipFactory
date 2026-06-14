from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import sessionmaker

from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.config import AppConfig, default_config
from mt_clip_factory.control_center.dto import PathRootsDTO
from mt_clip_factory.control_center.services import DashboardService, SystemSettingsService
from mt_clip_factory.factory.auto_factory import AutoFactoryBatchService
from mt_clip_factory.factory.auto_factory_folder import AutoFactoryFolderService
from mt_clip_factory.factory.caption_runtime import CaptionRuntimeService, ProductAutomationMetadataStore
from mt_clip_factory.factory.preview_artifacts import PreviewManifestBuilder
from mt_clip_factory.factory.production_order_service import ProductionOrderService
from mt_clip_factory.factory.renderers import FFmpegPreviewRenderer
from mt_clip_factory.factory.services import VideoAssemblyFactoryService
from mt_clip_factory.infrastructure.decision_event_repositories import SqlAlchemyDecisionEventRepository
from mt_clip_factory.infrastructure.factory_repositories import SqlAlchemyRecipeRepository
from mt_clip_factory.infrastructure.database import create_engine_from_path
from mt_clip_factory.infrastructure.job_repositories import SqlAlchemyJobRepository
from mt_clip_factory.infrastructure.migrations import ensure_schema_current
from mt_clip_factory.infrastructure.output_repositories import SqlAlchemyOutputRepository
from mt_clip_factory.infrastructure.repositories import (
    SqlAlchemyAssetRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyTagRepository,
)
from mt_clip_factory.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from mt_clip_factory.library.analyzers import ConfiguredMetadataAnalyzer
from mt_clip_factory.library.artifact_services import ArtifactGenerationService
from mt_clip_factory.library.artifacts import FFmpegArtifactGenerator
from mt_clip_factory.library.module import ResourceLibraryModule
from mt_clip_factory.library.readiness import AssetReadinessEvaluator
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.storage import LocalAssetStorage
from mt_clip_factory.library.tag_services import TagManagementService


def build_product_service(workspace_root: Path) -> ProductApplicationService:
    config: AppConfig = default_config(workspace_root)
    ensure_schema_current(workspace_root, config.paths.database_path)
    engine = create_engine_from_path(config.paths.database_path)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(
            session_factory=session_factory,
            product_repository_type=SqlAlchemyProductRepository,
            asset_repository_type=SqlAlchemyAssetRepository,
            tag_repository_type=SqlAlchemyTagRepository,
            job_repository_type=SqlAlchemyJobRepository,
            recipe_repository_type=SqlAlchemyRecipeRepository,
            output_repository_type=SqlAlchemyOutputRepository,
            decision_event_repository_type=SqlAlchemyDecisionEventRepository,
        )

    return ProductApplicationService(unit_of_work_factory=uow_factory)


def build_resource_library_module(
    workspace_root: Path,
    *,
    run_startup_recovery: bool = True,
    path_reload_policy: str = "restart_required",
) -> ResourceLibraryModule:
    config: AppConfig = default_config(workspace_root)
    ensure_schema_current(workspace_root, config.paths.database_path)
    engine = create_engine_from_path(config.paths.database_path)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings_service = SystemSettingsService(
        config.paths.app_config_path,
        runtime_path_roots=_runtime_path_roots_from_config(config),
        reload_policy=path_reload_policy,
    )

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(
            session_factory=session_factory,
            product_repository_type=SqlAlchemyProductRepository,
            asset_repository_type=SqlAlchemyAssetRepository,
            tag_repository_type=SqlAlchemyTagRepository,
            job_repository_type=SqlAlchemyJobRepository,
            recipe_repository_type=SqlAlchemyRecipeRepository,
            output_repository_type=SqlAlchemyOutputRepository,
            decision_event_repository_type=SqlAlchemyDecisionEventRepository,
        )

    product_service = ProductApplicationService(unit_of_work_factory=uow_factory)
    artifact_generator = FFmpegArtifactGenerator(settings_service, config.paths.media_root)
    asset_intake_service = AssetIntakeService(
        unit_of_work_factory=uow_factory,
        asset_storage=LocalAssetStorage(config.paths.media_root),
        metadata_analyzer=ConfiguredMetadataAnalyzer(settings_service),
        readiness_evaluator=AssetReadinessEvaluator(),
    )
    artifact_generation_service = ArtifactGenerationService(
        unit_of_work_factory=uow_factory,
        artifact_generator=artifact_generator,
    )
    automation_metadata_store = ProductAutomationMetadataStore(config.paths.media_root)
    caption_runtime_service = CaptionRuntimeService(
        metadata_store=automation_metadata_store,
        fonts_root=workspace_root / "fonts",
    )
    video_assembly_factory_service = VideoAssemblyFactoryService(
        unit_of_work_factory=uow_factory,
        preview_manifest_builder=PreviewManifestBuilder(config.paths.preview_root / "manifests"),
        preview_renderer=FFmpegPreviewRenderer(
            settings_service,
            config.paths.preview_root,
            output_resolution_field="preview_output_resolution",
        ),
        final_renderer=FFmpegPreviewRenderer(
            settings_service,
            config.paths.outputs_root / "final",
            output_resolution_field="final_output_resolution",
        ),
        system_settings_service=settings_service,
        caption_runtime_service=caption_runtime_service,
    )
    auto_factory_service = AutoFactoryBatchService(
        product_service=product_service,
        asset_intake_service=asset_intake_service,
        video_assembly_factory_service=video_assembly_factory_service,
    )
    tag_management_service = TagManagementService(unit_of_work_factory=uow_factory)
    auto_factory_folder_service = AutoFactoryFolderService(
        product_service=product_service,
        asset_intake_service=asset_intake_service,
        auto_factory_service=auto_factory_service,
        tag_management_service=tag_management_service,
        automation_metadata_store=automation_metadata_store,
    )
    production_order_service = ProductionOrderService(
        unit_of_work_factory=uow_factory,
        auto_factory_service=auto_factory_service,
    )
    dashboard_service = DashboardService(
        config=config,
        product_service=product_service,
        asset_intake_service=asset_intake_service,
        artifact_generation_service=artifact_generation_service,
        video_assembly_factory_service=video_assembly_factory_service,
        tag_management_service=tag_management_service,
        system_settings_service=settings_service,
    )
    if run_startup_recovery and dashboard_service.should_auto_recover_queued_jobs():
        dashboard_service.recover_queued_jobs(trigger="startup")
    return ResourceLibraryModule(
        product_service=product_service,
        asset_intake_service=asset_intake_service,
        artifact_generation_service=artifact_generation_service,
        video_assembly_factory_service=video_assembly_factory_service,
        tag_management_service=tag_management_service,
        system_settings_service=settings_service,
        dashboard_service=dashboard_service,
        auto_factory_service=auto_factory_service,
        auto_factory_folder_service=auto_factory_folder_service,
        production_order_service=production_order_service,
    )


def _runtime_path_roots_from_config(config: AppConfig) -> PathRootsDTO:
    return PathRootsDTO(
        database_path=str(config.paths.database_path),
        media_root=str(config.paths.media_root),
        docs_root=str(config.paths.docs_root),
        outputs_root=str(config.paths.outputs_root),
        preview_root=str(config.paths.preview_root),
    )
