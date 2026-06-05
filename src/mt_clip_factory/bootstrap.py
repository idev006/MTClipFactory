from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import sessionmaker

from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.config import AppConfig, default_config
from mt_clip_factory.control_center.services import DashboardService, SystemSettingsService
from mt_clip_factory.infrastructure.database import create_engine_from_path, create_schema
from mt_clip_factory.infrastructure.repositories import (
    SqlAlchemyAssetRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyTagRepository,
)
from mt_clip_factory.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from mt_clip_factory.library.analyzers import ConfiguredMetadataAnalyzer
from mt_clip_factory.library.module import ResourceLibraryModule
from mt_clip_factory.library.readiness import AssetReadinessEvaluator
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.storage import LocalAssetStorage
from mt_clip_factory.library.tag_services import TagManagementService


def build_product_service(workspace_root: Path) -> ProductApplicationService:
    config: AppConfig = default_config(workspace_root)
    engine = create_engine_from_path(config.paths.database_path)
    create_schema(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(
            session_factory=session_factory,
            product_repository_type=SqlAlchemyProductRepository,
            asset_repository_type=SqlAlchemyAssetRepository,
            tag_repository_type=SqlAlchemyTagRepository,
        )

    return ProductApplicationService(unit_of_work_factory=uow_factory)


def build_resource_library_module(workspace_root: Path) -> ResourceLibraryModule:
    config: AppConfig = default_config(workspace_root)
    engine = create_engine_from_path(config.paths.database_path)
    create_schema(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings_service = SystemSettingsService(config.paths.app_config_path)

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(
            session_factory=session_factory,
            product_repository_type=SqlAlchemyProductRepository,
            asset_repository_type=SqlAlchemyAssetRepository,
            tag_repository_type=SqlAlchemyTagRepository,
        )

    product_service = ProductApplicationService(unit_of_work_factory=uow_factory)
    asset_intake_service = AssetIntakeService(
        unit_of_work_factory=uow_factory,
        asset_storage=LocalAssetStorage(config.paths.media_root),
        metadata_analyzer=ConfiguredMetadataAnalyzer(settings_service),
        readiness_evaluator=AssetReadinessEvaluator(),
    )
    tag_management_service = TagManagementService(unit_of_work_factory=uow_factory)
    dashboard_service = DashboardService(
        config=config,
        product_service=product_service,
        asset_intake_service=asset_intake_service,
        tag_management_service=tag_management_service,
        system_settings_service=settings_service,
    )
    return ResourceLibraryModule(
        product_service=product_service,
        asset_intake_service=asset_intake_service,
        tag_management_service=tag_management_service,
        system_settings_service=settings_service,
        dashboard_service=dashboard_service,
    )
