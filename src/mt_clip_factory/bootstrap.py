from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import sessionmaker

from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.config import AppConfig, default_config
from mt_clip_factory.control_center.services import DashboardService, SystemSettingsService
from mt_clip_factory.factory.preview_artifacts import PreviewManifestBuilder
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


def build_resource_library_module(workspace_root: Path) -> ResourceLibraryModule:
    config: AppConfig = default_config(workspace_root)
    ensure_schema_current(workspace_root, config.paths.database_path)
    engine = create_engine_from_path(config.paths.database_path)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings_service = SystemSettingsService(config.paths.app_config_path)

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
    video_assembly_factory_service = VideoAssemblyFactoryService(
        unit_of_work_factory=uow_factory,
        preview_manifest_builder=PreviewManifestBuilder(config.paths.preview_root / "manifests"),
        preview_renderer=FFmpegPreviewRenderer(settings_service, config.paths.preview_root),
        final_renderer=FFmpegPreviewRenderer(settings_service, config.paths.outputs_root / "final"),
        system_settings_service=settings_service,
    )
    tag_management_service = TagManagementService(unit_of_work_factory=uow_factory)
    dashboard_service = DashboardService(
        config=config,
        product_service=product_service,
        asset_intake_service=asset_intake_service,
        artifact_generation_service=artifact_generation_service,
        video_assembly_factory_service=video_assembly_factory_service,
        tag_management_service=tag_management_service,
        system_settings_service=settings_service,
    )
    if dashboard_service.should_auto_recover_queued_jobs():
        dashboard_service.recover_queued_jobs(trigger="startup")
    return ResourceLibraryModule(
        product_service=product_service,
        asset_intake_service=asset_intake_service,
        artifact_generation_service=artifact_generation_service,
        video_assembly_factory_service=video_assembly_factory_service,
        tag_management_service=tag_management_service,
        system_settings_service=settings_service,
        dashboard_service=dashboard_service,
    )
