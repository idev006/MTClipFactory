from __future__ import annotations

from pathlib import Path

import pytest

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.library.contracts import AnalyzedMediaMetadata
from mt_clip_factory.library.dto import RegisterAssetCommand
from mt_clip_factory.library.readiness import AssetReadinessEvaluator
from mt_clip_factory.library.services import (
    AssetCodeAlreadyExistsError,
    AssetIntakeService,
    AssetSourceFileMissingError,
    ProductForAssetNotFoundError,
)
from mt_clip_factory.library.storage import LocalAssetStorage


class FakeMetadataAnalyzer:
    def analyze(self, file_path: Path) -> AnalyzedMediaMetadata:
        return AnalyzedMediaMetadata(
            duration_sec=12.5,
            width=1920,
            height=1080,
            fps=30.0,
            ratio="16:9",
            file_size_mb=round(file_path.stat().st_size / (1024 * 1024), 4),
            codec="h264",
            has_audio=True,
        )


def _build_asset_service(unit_of_work_factory, media_root: Path) -> AssetIntakeService:
    return AssetIntakeService(
        unit_of_work_factory=unit_of_work_factory,
        asset_storage=LocalAssetStorage(media_root),
        metadata_analyzer=FakeMetadataAnalyzer(),
        readiness_evaluator=AssetReadinessEvaluator(),
    )


def test_register_asset_copies_file_and_persists_record(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    source_file = tmp_path / "hero clip.mp4"
    source_file.write_bytes(b"video-bytes")
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library")

    asset_id = asset_service.register_asset(
        RegisterAssetCommand(
            product_id=product_id,
            asset_type="background_video",
            source_file_path=source_file,
        )
    )

    assets = asset_service.list_assets()
    assert asset_id == 1
    assert len(assets) == 1
    assert assets[0].product_code == "honey"
    assert assets[0].asset_code == "hero_clip"
    assert assets[0].asset_type == "background_video"
    assert assets[0].status == "ready"
    stored_file = tmp_path / "media_library" / "products" / "honey" / "background_videos" / "hero_clip.mp4"
    assert stored_file.exists()


def test_register_asset_rejects_missing_source_file(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library")

    with pytest.raises(AssetSourceFileMissingError):
        asset_service.register_asset(
            RegisterAssetCommand(
                product_id=product_id,
                asset_type="background_video",
                source_file_path=tmp_path / "missing.mp4",
            )
        )


def test_register_asset_rejects_duplicate_asset_code(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library")
    first_file = tmp_path / "first.mp4"
    second_file = tmp_path / "second.mp4"
    first_file.write_bytes(b"first")
    second_file.write_bytes(b"second")

    asset_service.register_asset(
        RegisterAssetCommand(
            product_id=product_id,
            asset_type="background_video",
            source_file_path=first_file,
            asset_code="shared_asset",
        )
    )

    with pytest.raises(AssetCodeAlreadyExistsError):
        asset_service.register_asset(
            RegisterAssetCommand(
                product_id=product_id,
                asset_type="background_video",
                source_file_path=second_file,
                asset_code="shared_asset",
            )
        )


def test_register_asset_rejects_unknown_product(unit_of_work_factory, tmp_path) -> None:
    source_file = tmp_path / "hero.mp4"
    source_file.write_bytes(b"video-bytes")
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library")

    with pytest.raises(ProductForAssetNotFoundError):
        asset_service.register_asset(
            RegisterAssetCommand(
                product_id=999,
                asset_type="background_video",
                source_file_path=source_file,
            )
        )
