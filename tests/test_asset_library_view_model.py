from __future__ import annotations

import pytest

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.library.dto import AssetSummaryDTO
from mt_clip_factory.library.services import AssetSourceFileMissingError
from mt_clip_factory.presentation.library.asset_library import AssetLibraryViewModel


class FakeAssetIntakeService:
    def __init__(self) -> None:
        self.assets: list[AssetSummaryDTO] = []
        self.calls: list[tuple[int, str, str, str | None]] = []

    def register_asset(self, command) -> int:
        if "missing" in str(command.source_file_path):
            raise AssetSourceFileMissingError(str(command.source_file_path))
        self.calls.append(
            (command.product_id, command.asset_type, str(command.source_file_path), command.asset_code)
        )
        asset_id = len(self.assets) + 1
        self.assets.append(
            AssetSummaryDTO(
                asset_id=asset_id,
                product_id=command.product_id,
                product_code="honey",
                asset_code=command.asset_code or "auto_code",
                asset_type=command.asset_type,
                file_name="hero.mp4",
                status="ready",
                ratio=None,
                duration_sec=None,
                file_size_mb=0.001,
                tag_labels=(),
            )
        )
        return asset_id

    def list_assets(
        self,
        product_id: int | None = None,
        asset_type: str | None = None,
        status: str | None = None,
    ) -> list[AssetSummaryDTO]:
        return list(self.assets)


def test_asset_view_model_loads_products_and_assets(unit_of_work_factory) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = FakeAssetIntakeService()
    view_model = AssetLibraryViewModel(product_service=product_service, asset_intake_service=asset_service)

    view_model.load()

    assert view_model.status == "ready"
    assert len(view_model.products) == 1
    assert view_model.assets == []


def test_asset_view_model_registers_asset_and_refreshes(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = FakeAssetIntakeService()
    view_model = AssetLibraryViewModel(product_service=product_service, asset_intake_service=asset_service)

    asset_id = view_model.register_asset(
        product_id=product_id,
        asset_type="background_video",
        source_file_path=str(tmp_path / "hero.mp4"),
        asset_code="hero_asset",
    )

    assert asset_id == 1
    assert view_model.status == "ready"
    assert "Registered asset #1" in view_model.feedback
    assert len(view_model.assets) == 1


def test_asset_view_model_surfaces_register_errors(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = FakeAssetIntakeService()
    view_model = AssetLibraryViewModel(product_service=product_service, asset_intake_service=asset_service)

    with pytest.raises(FileNotFoundError):
        view_model.register_asset(
            product_id=product_id,
            asset_type="background_video",
            source_file_path=str(tmp_path / "missing.mp4"),
            asset_code="hero_asset",
        )

    assert view_model.status == "error"
    assert "missing.mp4" in view_model.feedback


def test_asset_view_model_applies_filters(unit_of_work_factory) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = FakeAssetIntakeService()
    view_model = AssetLibraryViewModel(product_service=product_service, asset_intake_service=asset_service)

    view_model.apply_filters(product_id=1, asset_type="background_video", status="ready")

    assert view_model.status == "ready"
