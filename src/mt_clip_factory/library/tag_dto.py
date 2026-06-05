from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CreateTagCommand:
    tag_name: str
    tag_group: str
    description: str | None = None


@dataclass(slots=True, frozen=True)
class AssignTagToAssetCommand:
    asset_id: int
    tag_id: int


@dataclass(slots=True, frozen=True)
class TagSummaryDTO:
    tag_id: int
    tag_name: str
    tag_group: str
    description: str | None

