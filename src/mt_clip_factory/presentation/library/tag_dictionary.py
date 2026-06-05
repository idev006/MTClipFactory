from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from mt_clip_factory.library.dto import AssetSummaryDTO
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.tag_dto import AssignTagToAssetCommand, CreateTagCommand, TagSummaryDTO
from mt_clip_factory.library.tag_services import TagManagementService


class TagDictionaryViewModel(QObject):
    tags_changed = Signal()
    assets_changed = Signal()
    status_changed = Signal()
    feedback_changed = Signal()

    def __init__(self, tag_management_service: TagManagementService, asset_intake_service: AssetIntakeService) -> None:
        super().__init__()
        self._tag_management_service = tag_management_service
        self._asset_intake_service = asset_intake_service
        self._tags: list[TagSummaryDTO] = []
        self._assets: list[AssetSummaryDTO] = []
        self._status = "idle"
        self._feedback = ""

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
        return list(self._tags)

    @property
    def assets(self) -> list[AssetSummaryDTO]:
        return list(self._assets)

    @Slot()
    def load(self) -> None:
        self._set_status("loading")
        self._tags = self._tag_management_service.list_tags()
        self._assets = self._asset_intake_service.list_assets()
        self.tags_changed.emit()
        self.assets_changed.emit()
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
