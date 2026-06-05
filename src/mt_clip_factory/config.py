from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class AppPaths:
    workspace_root: Path
    database_path: Path
    media_root: Path
    docs_root: Path


@dataclass(slots=True, frozen=True)
class AppConfig:
    paths: AppPaths


def default_config(workspace_root: Path) -> AppConfig:
    return AppConfig(
        paths=AppPaths(
            workspace_root=workspace_root,
            database_path=workspace_root / "ad_kitchen.db",
            media_root=workspace_root / "media_library",
            docs_root=workspace_root / "doc",
        )
    )

