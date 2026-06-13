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
                thumbnail_path=None,
                proxy_path=None,
            ),
            AssetSummaryDTO(
                asset_id=2,
                product_id=2,
                product_code="tea",
                asset_code="proof_asset",
                asset_type="foreground_video",
                file_name="proof.mp4",
                status="retired",
                ratio="9:16",
                duration_sec=2.0,
                file_size_mb=0.002,
                tag_labels=("message:proof",),
                thumbnail_path=None,
                proxy_path=None,
            ),
        ]


class FakeTagManagementService:
    def __init__(self) -> None:
        self.tags: list[TagSummaryDTO] = []
        self.assigned_pairs: list[tuple[int, int]] = []

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
        self.assigned_pairs.append((command.asset_id, command.tag_id))


def test_tag_dictionary_view_model_loads_tags_and_assets() -> None:
    view_model = TagDictionaryViewModel(FakeTagManagementService(), FakeAssetIntakeService())

    view_model.load()

    assert view_model.status == "ready"
    assert len(view_model.assets) == 2
    assert view_model.selected_asset is not None
    assert view_model.selected_asset.asset_code == "hero_asset"
    assert view_model.selected_asset_count == 1
    assert view_model.asset_filter_product_options == ["honey", "tea"]
    assert view_model.asset_filter_type_options == ["background_video", "foreground_video"]
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


def test_tag_dictionary_view_model_filters_assets_for_tag_assignment() -> None:
    view_model = TagDictionaryViewModel(FakeTagManagementService(), FakeAssetIntakeService())

    view_model.load()
    view_model.apply_asset_filters(product_code="tea", status="retired", asset_type="foreground_video", search_text="proof")

    assert view_model.status == "ready"
    assert [asset.asset_code for asset in view_model.assets] == ["proof_asset"]
    assert view_model.selected_asset is not None
    assert view_model.selected_asset.asset_code == "proof_asset"
    assert "Showing 1 asset(s)" in view_model.feedback


def test_tag_dictionary_view_model_can_filter_tags_and_select_asset() -> None:
    tag_service = FakeTagManagementService()
    view_model = TagDictionaryViewModel(tag_service, FakeAssetIntakeService())
    view_model.create_tag(tag_name="Proof", tag_group="Message")
    view_model.create_tag(tag_name="Warm", tag_group="Mood")

    view_model.apply_tag_filters(tag_group="message", search_text="proof")
    view_model.select_asset(2)

    assert [tag.tag_name for tag in view_model.tags] == ["proof"]
    assert view_model.selected_asset is not None
    assert view_model.selected_asset.asset_code == "proof_asset"


def test_tag_dictionary_view_model_can_bulk_assign_existing_tag_to_selected_assets() -> None:
    tag_service = FakeTagManagementService()
    view_model = TagDictionaryViewModel(tag_service, FakeAssetIntakeService())
    view_model.create_tag(tag_name="Proof", tag_group="Message")
    view_model.load()

    view_model.select_assets([1, 2])
    view_model.assign_tag_to_selected_assets(tag_id=1)

    assert tag_service.assigned_pairs == [(1, 1), (2, 1)]
    assert view_model.status == "ready"
    assert view_model.selected_asset is not None
    assert view_model.selected_asset_count == 2
    assert "Assigned tag #1 to 2 asset(s)" in view_model.feedback


def test_tag_dictionary_view_model_can_create_and_bulk_assign_tag() -> None:
    tag_service = FakeTagManagementService()
    view_model = TagDictionaryViewModel(tag_service, FakeAssetIntakeService())
    view_model.load()

    tag_id = view_model.create_tag_and_assign_to_selected_assets(tag_name="Warm", tag_group="Mood")

    assert tag_id == 1
    assert tag_service.assigned_pairs == [(1, 1)]
    assert view_model.selected_asset is not None
    assert view_model.selected_asset.asset_code == "hero_asset"


def test_tag_dictionary_view_model_preserves_selected_assets_through_filters() -> None:
    view_model = TagDictionaryViewModel(FakeTagManagementService(), FakeAssetIntakeService())
    view_model.load()
    view_model.select_assets([1, 2])

    view_model.apply_asset_filters(product_code="tea")

    assert [asset.asset_id for asset in view_model.selected_assets] == [2]
    assert view_model.selected_asset is not None
    assert view_model.selected_asset.asset_id == 2
