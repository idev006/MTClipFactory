from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Tag:
    tag_name: str
    tag_group: str
    description: str | None = None
    id: int | None = None


@dataclass(slots=True, frozen=True)
class TagSummary:
    tag_id: int
    tag_name: str
    tag_group: str
    description: str | None = None

