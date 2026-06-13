from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from mt_clip_factory.library.dto import AssetSummaryDTO
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.tag_dto import AssignTagToAssetCommand, CreateTagCommand, TagSummaryDTO
from mt_clip_factory.library.tag_services import TagManagementService


class TagDictionaryViewModel(QObject):
    tags_changed = Signal()
    assets_changed = Signal()
    selected_asset_changed = Signal()
    status_changed = Signal()
    feedback_changed = Signal()

    def __init__(self, tag_management_service: TagManagementService, asset_intake_service: AssetIntakeService) -> None:
        super().__init__()
        self._tag_management_service = tag_management_service
        self._asset_intake_service = asset_intake_service
        self._tags: list[TagSummaryDTO] = []
        self._filtered_tags: list[TagSummaryDTO] = []
        self._all_assets: list[AssetSummaryDTO] = []
        self._assets: list[AssetSummaryDTO] = []
        self._selected_asset_id: int | None = None
        self._status = "idle"
        self._feedback = ""
        self._asset_filter_product_code: str | None = None
        self._asset_filter_status: str | None = None
        self._asset_filter_asset_type: str | None = None
        self._asset_filter_search_text = ""
        self._tag_filter_group: str | None = None
        self._tag_filter_search_text = ""

    def _get_status(self) -> str:
        return self._status

    def _set_status(self, value: str) -> None:
        if self._status == value:
            return
        self._status = value
        self.status_changed.emit()

    def _get_feedback(self) -> str:
        return self._feedback

    def _set_feedback(self, value: str) -> None:
        if self._feedback == value:
            return
        self._feedback = value
        self.feedback_changed.emit()

    status = Property(str, _get_status, notify=status_changed)
    feedback = Property(str, _get_feedback, notify=feedback_changed)

    @property
    def tags(self) -> list[TagSummaryDTO]:
        return list(self._filtered_tags)

    @property
    def all_tags(self) -> list[TagSummaryDTO]:
        return list(self._tags)

    @property
    def assets(self) -> list[AssetSummaryDTO]:
        return list(self._assets)

    @property
    def selected_asset(self) -> AssetSummaryDTO | None:
        for asset in self._all_assets:
            if asset.asset_id == self._selected_asset_id:
                return asset
        return None

    @property
    def tag_group_suggestions(self) -> list[str]:
        return sorted({tag.tag_group for tag in self._tags})

    @property
    def tag_filter_group_options(self) -> list[str]:
        return sorted({tag.tag_group for tag in self._tags})

    @property
    def asset_filter_product_options(self) -> list[str]:
        return sorted({asset.product_code for asset in self._all_assets})

    @property
    def asset_filter_type_options(self) -> list[str]:
        return sorted({asset.asset_type for asset in self._all_assets})

    @Slot()
    def load(self) -> None:
        self._set_status("loading")
        self._tags = self._tag_management_service.list_tags()
        self._filtered_tags = self._filter_tags(self._tags)
        self._all_assets = self._asset_intake_service.list_assets()
        self._assets = self._filter_assets(self._all_assets)
        self._selected_asset_id = _resolve_selected_asset_id(self._selected_asset_id, self._all_assets)
        self.tags_changed.emit()
        self.assets_changed.emit()
        self.selected_asset_changed.emit()
        self._set_status("ready")

    def create_tag(self, *, tag_name: str, tag_group: str, description: str | None = None) -> int:
        self._set_status("submitting")
        try:
            tag_id = self._tag_management_service.create_tag(
                CreateTagCommand(tag_name=tag_name, tag_group=tag_group, description=description)
            )
        except ValueError as exc:
            self._set_feedback(str(exc))
            self._set_status("error")
            raise

        self._set_feedback(f"Created tag #{tag_id}")
        self.load()
        return tag_id

    def create_tag_and_assign_to_selected_asset(
        self,
        *,
        tag_name: str,
        tag_group: str,
        description: str | None = None,
    ) -> int:
        selected_asset = self.selected_asset
        if selected_asset is None:
            raise ValueError("Select one asset before creating and attaching a tag.")
        tag_id = self.create_tag(tag_name=tag_name, tag_group=tag_group, description=description)
        self.assign_tag_to_asset(asset_id=selected_asset.asset_id, tag_id=tag_id)
        return tag_id

    def apply_asset_filters(
        self,
        *,
        product_code: str | None = None,
        status: str | None = None,
        asset_type: str | None = None,
        search_text: str | None = None,
    ) -> None:
        self._asset_filter_product_code = _normalize_optional_filter(product_code)
        self._asset_filter_status = _normalize_optional_filter(status)
        self._asset_filter_asset_type = _normalize_optional_filter(asset_type)
        self._asset_filter_search_text = (search_text or "").strip().casefold()
        self._assets = self._filter_assets(self._all_assets)
        self.assets_changed.emit()
        self._set_feedback(
            f"Showing {len(self._assets)} asset(s) after tag-assignment filters."
        )
        self._selected_asset_id = _resolve_selected_asset_id(self._selected_asset_id, self._assets)
        self.selected_asset_changed.emit()
        self._set_status("ready")

    def apply_tag_filters(
        self,
        *,
        tag_group: str | None = None,
        search_text: str | None = None,
    ) -> None:
        self._tag_filter_group = _normalize_optional_filter(tag_group)
        self._tag_filter_search_text = (search_text or "").strip().casefold()
        self._filtered_tags = self._filter_tags(self._tags)
        self.tags_changed.emit()
        self._set_feedback(
            f"Showing {len(self._filtered_tags)} available tag(s) for the selected asset workflow."
        )
        self._set_status("ready")

    def select_asset(self, asset_id: int | None) -> None:
        self._selected_asset_id = _resolve_selected_asset_id(asset_id, self._all_assets)
        self.selected_asset_changed.emit()
        selected_asset = self.selected_asset
        if selected_asset is None:
            self._set_feedback("No asset selected for tagging.")
        else:
            self._set_feedback(
                f"Selected asset #{selected_asset.asset_id} {selected_asset.asset_code} with {len(selected_asset.tag_labels)} tag(s)."
            )
        self._set_status("ready")

    def assign_tag_to_asset(self, *, asset_id: int, tag_id: int) -> None:
        self._set_status("assigning")
        try:
            self._tag_management_service.assign_tag_to_asset(
                AssignTagToAssetCommand(asset_id=asset_id, tag_id=tag_id)
            )
        except ValueError as exc:
            self._set_feedback(str(exc))
            self._set_status("error")
            raise

        self._set_feedback(f"Assigned tag #{tag_id} to asset #{asset_id}")
        self.load()

    def assign_tag_to_selected_asset(self, *, tag_id: int) -> None:
        selected_asset = self.selected_asset
        if selected_asset is None:
            raise ValueError("Select one asset before assigning a tag.")
        self.assign_tag_to_asset(asset_id=selected_asset.asset_id, tag_id=tag_id)

    def _filter_assets(self, assets: list[AssetSummaryDTO]) -> list[AssetSummaryDTO]:
        filtered: list[AssetSummaryDTO] = []
        for asset in assets:
            if self._asset_filter_product_code is not None and asset.product_code != self._asset_filter_product_code:
                continue
            if self._asset_filter_status is not None and asset.status != self._asset_filter_status:
                continue
            if self._asset_filter_asset_type is not None and asset.asset_type != self._asset_filter_asset_type:
                continue
            if self._asset_filter_search_text and not _asset_matches_search(asset, self._asset_filter_search_text):
                continue
            filtered.append(asset)
        return filtered

    def _filter_tags(self, tags: list[TagSummaryDTO]) -> list[TagSummaryDTO]:
        filtered: list[TagSummaryDTO] = []
        for tag in tags:
            if self._tag_filter_group is not None and tag.tag_group != self._tag_filter_group:
                continue
            if self._tag_filter_search_text and not _tag_matches_search(tag, self._tag_filter_search_text):
                continue
            filtered.append(tag)
        return filtered


def _normalize_optional_filter(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _asset_matches_search(asset: AssetSummaryDTO, search_text: str) -> bool:
    haystack = " ".join(
        [
            asset.product_code,
            asset.asset_code,
            asset.asset_type,
            asset.file_name,
            asset.status,
            *asset.tag_labels,
        ]
    ).casefold()
    return search_text in haystack


def _tag_matches_search(tag: TagSummaryDTO, search_text: str) -> bool:
    haystack = " ".join(
        [
            tag.tag_group,
            tag.tag_name,
            tag.description or "",
            f"{tag.tag_group}:{tag.tag_name}",
        ]
    ).casefold()
    return search_text in haystack


def _resolve_selected_asset_id(selected_asset_id: int | None, assets: list[AssetSummaryDTO]) -> int | None:
    if not assets:
        return None
    asset_ids = {asset.asset_id for asset in assets}
    if selected_asset_id in asset_ids:
        return selected_asset_id
    return assets[0].asset_id
