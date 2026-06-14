from __future__ import annotations

from collections.abc import Callable

from mt_clip_factory.domain.services import UnitOfWork
from mt_clip_factory.domain.tags import Tag
from mt_clip_factory.library.tag_dto import AssignTagToAssetCommand, CreateTagCommand, TagSummaryDTO


class TagAlreadyExistsError(ValueError):
    """Raised when a tag name/group pair already exists."""


class TagNotFoundError(ValueError):
    """Raised when a tag cannot be found."""


class AssetForTaggingNotFoundError(ValueError):
    """Raised when an asset cannot be found for tagging."""


def _normalize_tag_value(value: str, field_name: str) -> str:
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError(f"{field_name} is required.")
    return normalized


class TagManagementService:
    def __init__(self, unit_of_work_factory: Callable[[], UnitOfWork]) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def create_tag(self, command: CreateTagCommand) -> int:
        tag_name = _normalize_tag_value(command.tag_name, "Tag name")
        tag_group = _normalize_tag_value(command.tag_group, "Tag group")

        with self._unit_of_work_factory() as uow:
            existing = uow.tags.get_by_name_and_group(tag_name, tag_group)
            if existing is not None:
                raise TagAlreadyExistsError(f"{tag_group}:{tag_name}")

            created = uow.tags.add(
                Tag(
                    tag_name=tag_name,
                    tag_group=tag_group,
                    description=command.description.strip() if command.description else None,
                )
            )
            uow.commit()
            if created.id is None:
                raise RuntimeError("Tag identifier was not assigned.")
            return created.id

    def list_tags(self, tag_group: str | None = None) -> list[TagSummaryDTO]:
        with self._unit_of_work_factory() as uow:
            return [
                TagSummaryDTO(
                    tag_id=summary.tag_id,
                    tag_name=summary.tag_name,
                    tag_group=summary.tag_group,
                    description=summary.description,
                )
                for summary in uow.tags.list_summaries(tag_group=tag_group)
            ]

    def ensure_tag(self, *, tag_group: str, tag_name: str, description: str | None = None) -> int:
        normalized_tag_name = _normalize_tag_value(tag_name, "Tag name")
        normalized_tag_group = _normalize_tag_value(tag_group, "Tag group")

        with self._unit_of_work_factory() as uow:
            existing = uow.tags.get_by_name_and_group(normalized_tag_name, normalized_tag_group)
            if existing is not None and existing.id is not None:
                return existing.id

            created = uow.tags.add(
                Tag(
                    tag_name=normalized_tag_name,
                    tag_group=normalized_tag_group,
                    description=description.strip() if description else None,
                )
            )
            uow.commit()
            if created.id is None:
                raise RuntimeError("Tag identifier was not assigned.")
            return created.id

    def assign_tag_to_asset(self, command: AssignTagToAssetCommand) -> None:
        with self._unit_of_work_factory() as uow:
            asset = uow.assets.get_by_id(command.asset_id)
            if asset is None:
                raise AssetForTaggingNotFoundError(str(command.asset_id))

            tag = uow.tags.get_by_id(command.tag_id)
            if tag is None:
                raise TagNotFoundError(str(command.tag_id))

            uow.assets.assign_tag(command.asset_id, command.tag_id)
            uow.commit()
