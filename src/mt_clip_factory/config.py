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
    outputs_root: Path
    preview_root: Path
    app_config_path: Path


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
    database_path = workspace_root / "ad_kitchen.db"
    media_root = workspace_root / "media_library"
    docs_root = workspace_root / "doc"
    outputs_root = workspace_root / "outputs"
    preview_root = outputs_root / "preview"

    if config_file.exists():
        with config_file.open("rb") as file_handle:
            data = tomllib.load(file_handle)
        paths_config = data.get("paths", {})
        if paths_config.get("database_path"):
            database_path = _resolve_config_path(workspace_root, paths_config["database_path"])
        if paths_config.get("media_root"):
            media_root = _resolve_config_path(workspace_root, paths_config["media_root"])
        if paths_config.get("docs_root"):
            docs_root = _resolve_config_path(workspace_root, paths_config["docs_root"])
        if paths_config.get("outputs_root"):
            outputs_root = _resolve_config_path(workspace_root, paths_config["outputs_root"])
        if paths_config.get("preview_root"):
            preview_root = _resolve_config_path(workspace_root, paths_config["preview_root"])
        else:
            preview_root = outputs_root / "preview"
        ffmpeg_config = data.get("ffmpeg", {})
        if ffmpeg_config.get("root"):
            ffmpeg_root = _resolve_config_path(workspace_root, ffmpeg_config["root"])
        if ffmpeg_config.get("ffprobe"):
            ffprobe_path = _resolve_config_path(workspace_root, ffmpeg_config["ffprobe"])
        if ffmpeg_config.get("ffmpeg"):
            ffmpeg_path = _resolve_config_path(workspace_root, ffmpeg_config["ffmpeg"])

    return AppConfig(
        paths=AppPaths(
            workspace_root=workspace_root,
            database_path=database_path,
            media_root=media_root,
            docs_root=docs_root,
            outputs_root=outputs_root,
            preview_root=preview_root,
            app_config_path=config_file,
        ),
        ffmpeg_root=ffmpeg_root,
        ffprobe_path=ffprobe_path,
        ffmpeg_path=ffmpeg_path,
    )


def _resolve_config_path(workspace_root: Path, raw_value: str) -> Path:
    path = Path(raw_value)
    if path.is_absolute():
        return path
    return workspace_root / path
