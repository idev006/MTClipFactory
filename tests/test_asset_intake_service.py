from __future__ import annotations

from pathlib import Path

import pytest

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.domain.jobs import Job
from mt_clip_factory.domain.recipes import Recipe
from mt_clip_factory.library.contracts import AnalyzedMediaMetadata
from mt_clip_factory.library.dto import RegisterAssetCommand, UpdateAssetCommand
from mt_clip_factory.library.readiness import AssetReadinessEvaluator
from mt_clip_factory.library.services import (
    AssetCodeAlreadyExistsError,
    AssetInUseError,
    AssetNotFoundError,
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


def test_update_asset_renames_primary_and_artifact_files(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library")
    source_file = tmp_path / "hero.mp4"
    source_file.write_bytes(b"video-bytes")

    asset_id = asset_service.register_asset(
        RegisterAssetCommand(
            product_id=product_id,
            asset_type="background_video",
            source_file_path=source_file,
            asset_code="hero_asset",
        )
    )

    with unit_of_work_factory() as uow:
        asset = uow.assets.get_by_id(asset_id)
        assert asset is not None
        thumbnail_path = Path(asset.file_path).with_suffix(".jpg")
        proxy_path = Path(asset.file_path).with_name("hero_asset_proxy.mp4")
        thumbnail_path.write_bytes(b"thumb")
        proxy_path.write_bytes(b"proxy")
        asset.thumbnail_path = str(thumbnail_path)
        asset.proxy_path = str(proxy_path)
        uow.assets.update(asset)
        uow.commit()

    updated_asset_id = asset_service.update_asset(UpdateAssetCommand(asset_id=asset_id, asset_code="hero_asset_v2"))

    assert updated_asset_id == asset_id
    assets = asset_service.list_assets()
    assert assets[0].asset_code == "hero_asset_v2"
    stored_file = tmp_path / "media_library" / "products" / "honey" / "background_videos" / "hero_asset_v2.mp4"
    assert stored_file.exists()
    assert not (tmp_path / "media_library" / "products" / "honey" / "background_videos" / "hero_asset.mp4").exists()


def test_delete_asset_removes_record_and_primary_file(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library")
    source_file = tmp_path / "hero.mp4"
    source_file.write_bytes(b"video-bytes")

    asset_id = asset_service.register_asset(
        RegisterAssetCommand(
            product_id=product_id,
            asset_type="background_video",
            source_file_path=source_file,
            asset_code="hero_asset",
        )
    )

    asset_service.delete_asset(asset_id)

    assert asset_service.list_assets() == []
    stored_file = tmp_path / "media_library" / "products" / "honey" / "background_videos" / "hero_asset.mp4"
    assert not stored_file.exists()


def test_delete_asset_rejects_assets_attached_to_recipe_items(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library")
    source_file = tmp_path / "hero.mp4"
    source_file.write_bytes(b"video-bytes")
    asset_id = asset_service.register_asset(
        RegisterAssetCommand(
            product_id=product_id,
            asset_type="background_video",
            source_file_path=source_file,
            asset_code="hero_asset",
        )
    )

    with unit_of_work_factory() as uow:
        recipe = uow.recipes.add(Recipe(product_id=product_id, recipe_code="recipe_01"))
        assert recipe.id is not None
        uow.recipes.add_item(recipe.id, asset_id, "hook")
        uow.commit()

    with pytest.raises(AssetInUseError):
        asset_service.delete_asset(asset_id)


def test_delete_asset_rejects_assets_with_artifact_jobs(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library")
    source_file = tmp_path / "hero.mp4"
    source_file.write_bytes(b"video-bytes")
    asset_id = asset_service.register_asset(
        RegisterAssetCommand(
            product_id=product_id,
            asset_type="background_video",
            source_file_path=source_file,
            asset_code="hero_asset",
        )
    )

    with unit_of_work_factory() as uow:
        uow.jobs.add(Job(job_code="artifact_01", job_type="generate_thumbnail", asset_id=asset_id))
        uow.commit()

    with pytest.raises(AssetInUseError):
        asset_service.delete_asset(asset_id)


def test_update_asset_rejects_unknown_asset(unit_of_work_factory, tmp_path) -> None:
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library")

    with pytest.raises(AssetNotFoundError):
        asset_service.update_asset(UpdateAssetCommand(asset_id=999, asset_code="missing_asset"))
