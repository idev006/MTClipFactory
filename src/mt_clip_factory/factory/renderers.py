from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

from mt_clip_factory.control_center.dto import SystemSettingsDTO
from mt_clip_factory.control_center.services import SystemSettingsService


@dataclass(slots=True, frozen=True)
class RenderedPreviewOutput:
    file_path: Path
    duration_sec: float | None = None


class FFmpegPreviewRenderer:
    def __init__(self, settings_service: SystemSettingsService, preview_root: Path) -> None:
        self._settings_service = settings_service
        self._preview_root = preview_root

    def render_preview(
        self,
        *,
        product_code: str,
        recipe_code: str,
        source_files: list[Path],
    ) -> RenderedPreviewOutput:
        if not source_files:
            raise ValueError("At least one source file is required for preview rendering.")

        settings = self._settings_service.load()
        output_dir = self._preview_root / product_code / "videos"
        output_dir.mkdir(parents=True, exist_ok=True)
        target_path = output_dir / f"{recipe_code}.mp4"

        if len(source_files) == 1:
            self._run_ffmpeg(
                settings=settings,
                arguments=[
                    "-y",
                    "-i",
                    str(source_files[0]),
                    "-vf",
                    "scale='min(1280,iw)':-2",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "30",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "96k",
                    str(target_path),
                ],
            )
            return RenderedPreviewOutput(file_path=target_path)

        with TemporaryDirectory(prefix="mtclipfactory_preview_") as temp_dir_name:
            concat_file = Path(temp_dir_name) / "concat_list.txt"
            concat_file.write_text(
                "\n".join(f"file '{_escape_concat_path(file_path)}'" for file_path in source_files),
                encoding="utf-8",
            )
            self._run_ffmpeg(
                settings=settings,
                arguments=[
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat_file),
                    "-vf",
                    "scale='min(1280,iw)':-2",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "30",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "96k",
                    str(target_path),
                ],
            )
        return RenderedPreviewOutput(file_path=target_path)

    def _run_ffmpeg(self, settings: SystemSettingsDTO, arguments: list[str]) -> None:
        ffmpeg_path = Path(settings.ffmpeg_path)
        if not ffmpeg_path.exists():
            raise FileNotFoundError(str(ffmpeg_path))
        subprocess.run([str(ffmpeg_path), *arguments], check=True, capture_output=True, text=True)


class LocalPreviewRenderer:
    def __init__(self, preview_root: Path) -> None:
        self._preview_root = preview_root

    def render_preview(
        self,
        *,
        product_code: str,
        recipe_code: str,
        source_files: list[Path],
    ) -> RenderedPreviewOutput:
        if not source_files:
            raise ValueError("At least one source file is required for preview rendering.")
        output_dir = self._preview_root / product_code / "videos"
        output_dir.mkdir(parents=True, exist_ok=True)
        suffix = source_files[0].suffix or ".bin"
        target_path = output_dir / f"{recipe_code}{suffix}"
        shutil.copy2(source_files[0], target_path)
        return RenderedPreviewOutput(file_path=target_path)


def _escape_concat_path(file_path: Path) -> str:
    return str(file_path).replace("\\", "\\\\").replace("'", "'\\''")
