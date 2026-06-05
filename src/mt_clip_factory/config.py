from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(slots=True, frozen=True)
class AppPaths:
    workspace_root: Path
    database_path: Path
    media_root: Path
    docs_root: Path


@dataclass(slots=True, frozen=True)
class AppConfig:
    paths: AppPaths
    ffmpeg_root: Path | None = None
    ffprobe_path: Path | None = None
    ffmpeg_path: Path | None = None


def default_config(workspace_root: Path) -> AppConfig:
    config_file = workspace_root / "app_config.toml"
    ffmpeg_root: Path | None = None
    ffprobe_path: Path | None = None
    ffmpeg_path: Path | None = None

    if config_file.exists():
        with config_file.open("rb") as file_handle:
            data = tomllib.load(file_handle)
        ffmpeg_config = data.get("ffmpeg", {})
        if ffmpeg_config.get("root"):
            ffmpeg_root = Path(ffmpeg_config["root"])
        if ffmpeg_config.get("ffprobe"):
            ffprobe_path = Path(ffmpeg_config["ffprobe"])
        if ffmpeg_config.get("ffmpeg"):
            ffmpeg_path = Path(ffmpeg_config["ffmpeg"])

    return AppConfig(
        paths=AppPaths(
            workspace_root=workspace_root,
            database_path=workspace_root / "ad_kitchen.db",
            media_root=workspace_root / "media_library",
            docs_root=workspace_root / "doc",
        ),
        ffmpeg_root=ffmpeg_root,
        ffprobe_path=ffprobe_path,
        ffmpeg_path=ffmpeg_path,
    )
