from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import TYPE_CHECKING
import uuid

from mt_clip_factory.control_center.dto import SystemSettingsDTO

if TYPE_CHECKING:
    from mt_clip_factory.control_center.services import SystemSettingsService


class FFmpegArtifactGenerator:
    def __init__(self, settings_service: SystemSettingsService, media_root: Path) -> None:
        self._settings_service = settings_service
        self._media_root = media_root

    def generate_thumbnail(self, source_file_path: Path, product_code: str, asset_code: str) -> Path:
        settings = self._settings_service.load()
        target_dir = self._media_root / "products" / product_code / "cache" / "thumbnails"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{asset_code}.jpg"
        self._run_ffmpeg(
            settings=settings,
            arguments=[
                "-y",
                "-ss",
                "00:00:00.500",
                "-i",
                str(source_file_path),
                "-frames:v",
                "1",
                "-vf",
                "scale=540:-1",
                str(target_path),
            ],
        )
        return target_path

    def generate_proxy(self, source_file_path: Path, product_code: str, asset_code: str) -> Path:
        settings = self._settings_service.load()
        target_dir = self._media_root / "products" / product_code / "cache" / "proxy"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{asset_code}.mp4"
        self._run_ffmpeg(
            settings=settings,
            arguments=[
                "-y",
                "-i",
                str(source_file_path),
                "-vf",
                "scale='min(720,iw)':-2",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "28",
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                str(target_path),
            ],
        )
        return target_path

    def _run_ffmpeg(self, settings: SystemSettingsDTO, arguments: list[str]) -> None:
        ffmpeg_path = Path(settings.ffmpeg_path)
        if not ffmpeg_path.exists():
            raise FileNotFoundError(str(ffmpeg_path))
        subprocess.run([str(ffmpeg_path), *arguments], check=True, capture_output=True, text=True)


def build_artifact_job_code(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def encode_job_input(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True)


def decode_job_input(payload: str | None) -> dict:
    if not payload:
        return {}
    return json.loads(payload)
