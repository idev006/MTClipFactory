from __future__ import annotations

import pytest

from mt_clip_factory.library.dto import AssetSummaryDTO
from mt_clip_factory.library.tag_dto import TagSummaryDTO
from mt_clip_factory.presentation.library.tag_dictionary import TagDictionaryViewModel


class FakeAssetIntakeService:
    def list_assets(
        self,
        product_id: int | None = None,
        asset_type: str | None = None,
        status: str | None = None,
    ) -> list[AssetSummaryDTO]:
        return [
            AssetSummaryDTO(
                asset_id=1,
                product_id=1,
                product_code="honey",
                asset_code="hero_asset",
                asset_type="background_video",
                file_name="hero.mp4",
                status="ready",
                ratio="16:9",
                duration_sec=1.0,
                file_size_mb=0.001,
                tag_labels=("mood:warm",),
            )
        ]


class FakeTagManagementService:
    def __init__(self) -> None:
        self.tags: list[TagSummaryDTO] = []

    def create_tag(self, command) -> int:
        if not command.tag_name.strip():
            raise ValueError("Tag name is required.")
        tag_id = len(self.tags) + 1
        self.tags.append(
            TagSummaryDTO(
                tag_id=tag_id,
                tag_name=command.tag_name.strip().lower(),
                tag_group=command.tag_group.strip().lower(),
                description=command.description,
            )
        )
        return tag_id

    def list_tags(self, tag_group: str | None = None) -> list[TagSummaryDTO]:
        return list(self.tags)

    def assign_tag_to_asset(self, command) -> None:
        if command.asset_id <= 0:
            raise ValueError("invalid asset")


def test_tag_dictionary_view_model_loads_tags_and_assets() -> None:
    view_model = TagDictionaryViewModel(FakeTagManagementService(), FakeAssetIntakeService())

    view_model.load()

    assert view_model.status == "ready"
    assert len(view_model.assets) == 1
    assert view_model.tags == []


def test_tag_dictionary_view_model_creates_tag() -> None:
    view_model = TagDictionaryViewModel(FakeTagManagementService(), FakeAssetIntakeService())

    tag_id = view_model.create_tag(tag_name="Warm", tag_group="Mood", description="Warm mood")

    assert tag_id == 1
    assert view_model.status == "ready"
    assert len(view_model.tags) == 1
    assert "Created tag #1" in view_model.feedback


def test_tag_dictionary_view_model_surfaces_errors() -> None:
    view_model = TagDictionaryViewModel(FakeTagManagementService(), FakeAssetIntakeService())

    with pytest.raises(ValueError):
        view_model.create_tag(tag_name="   ", tag_group="Mood")

    assert view_model.status == "error"
