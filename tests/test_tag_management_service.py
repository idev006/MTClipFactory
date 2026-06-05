from __future__ import annotations

from pathlib import Path

import pytest

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.library.contracts import AnalyzedMediaMetadata
from mt_clip_factory.library.dto import RegisterAssetCommand
from mt_clip_factory.library.readiness import AssetReadinessEvaluator
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.storage import LocalAssetStorage
from mt_clip_factory.library.tag_dto import AssignTagToAssetCommand, CreateTagCommand
from mt_clip_factory.library.tag_services import AssetForTaggingNotFoundError, TagAlreadyExistsError, TagManagementService


class FakeMetadataAnalyzer:
    def analyze(self, file_path: Path) -> AnalyzedMediaMetadata:
        return AnalyzedMediaMetadata(
            duration_sec=1.0,
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


def test_create_tag_and_list_tags(unit_of_work_factory) -> None:
    service = TagManagementService(unit_of_work_factory=unit_of_work_factory)

    tag_id = service.create_tag(CreateTagCommand(tag_name="Warm", tag_group="Mood", description="Warm mood"))
    tags = service.list_tags()

    assert tag_id == 1
    assert len(tags) == 1
    assert tags[0].tag_name == "warm"
    assert tags[0].tag_group == "mood"


def test_create_tag_rejects_duplicate_name_group(unit_of_work_factory) -> None:
    service = TagManagementService(unit_of_work_factory=unit_of_work_factory)
    service.create_tag(CreateTagCommand(tag_name="Warm", tag_group="Mood"))

    with pytest.raises(TagAlreadyExistsError):
        service.create_tag(CreateTagCommand(tag_name="warm", tag_group="mood"))


def test_assign_tag_to_asset(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library")
    tag_service = TagManagementService(unit_of_work_factory=unit_of_work_factory)
    source_file = tmp_path / "hero.mp4"
    source_file.write_bytes(b"video")

    asset_id = asset_service.register_asset(
        RegisterAssetCommand(
            product_id=product_id,
            asset_type="background_video",
            source_file_path=source_file,
        )
    )
    tag_id = tag_service.create_tag(CreateTagCommand(tag_name="Warm", tag_group="Mood"))

    tag_service.assign_tag_to_asset(AssignTagToAssetCommand(asset_id=asset_id, tag_id=tag_id))

    with unit_of_work_factory() as uow:
        assert list(uow.assets.list_tag_ids(asset_id)) == [tag_id]

    assets = asset_service.list_assets(status="ready")
    assert assets[0].tag_labels == ("mood:warm",)


def test_assign_tag_rejects_missing_asset(unit_of_work_factory) -> None:
    tag_service = TagManagementService(unit_of_work_factory=unit_of_work_factory)
    tag_id = tag_service.create_tag(CreateTagCommand(tag_name="Warm", tag_group="Mood"))

    with pytest.raises(AssetForTaggingNotFoundError):
        tag_service.assign_tag_to_asset(AssignTagToAssetCommand(asset_id=999, tag_id=tag_id))
