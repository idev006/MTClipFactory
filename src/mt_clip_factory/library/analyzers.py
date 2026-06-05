from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Protocol

from mt_clip_factory.library.contracts import AnalyzedMediaMetadata


class BasicFileMetadataAnalyzer:
    _audio_extensions = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}

    def analyze(self, file_path: Path) -> AnalyzedMediaMetadata:
        file_size_mb = round(file_path.stat().st_size / (1024 * 1024), 4)
        return AnalyzedMediaMetadata(
            file_size_mb=file_size_mb,
            has_audio=file_path.suffix.lower() in self._audio_extensions,
        )


class FFprobeMetadataAnalyzer:
    def __init__(self, ffprobe_path: Path) -> None:
        self._ffprobe_path = ffprobe_path

    def analyze(self, file_path: Path) -> AnalyzedMediaMetadata:
        command = [
            str(self._ffprobe_path),
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(file_path),
        ]
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
        data = json.loads(completed.stdout or "{}")
        streams = data.get("streams", [])
        format_data = data.get("format", {})

        video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
        audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)

        duration_value = format_data.get("duration")
        duration_sec = float(duration_value) if duration_value not in (None, "N/A") else None
        width = int(video_stream["width"]) if video_stream and video_stream.get("width") else None
        height = int(video_stream["height"]) if video_stream and video_stream.get("height") else None
        fps = _parse_fps(video_stream.get("avg_frame_rate") if video_stream else None)
        file_size_bytes = int(format_data["size"]) if format_data.get("size") else file_path.stat().st_size
        file_size_mb = round(file_size_bytes / (1024 * 1024), 4)
        codec = None
        if video_stream and video_stream.get("codec_name"):
            codec = str(video_stream["codec_name"])
        elif audio_stream and audio_stream.get("codec_name"):
            codec = str(audio_stream["codec_name"])

        ratio = None
        if width and height:
            ratio = f"{width}:{height}"

        return AnalyzedMediaMetadata(
            duration_sec=duration_sec,
            width=width,
            height=height,
            fps=fps,
            ratio=ratio,
            file_size_mb=file_size_mb,
            codec=codec,
            has_audio=audio_stream is not None,
            format_name=format_data.get("format_name"),
        )


class FallbackMetadataAnalyzer:
    def __init__(self, primary_analyzer, fallback_analyzer) -> None:
        self._primary_analyzer = primary_analyzer
        self._fallback_analyzer = fallback_analyzer

    def analyze(self, file_path: Path) -> AnalyzedMediaMetadata:
        try:
            return self._primary_analyzer.analyze(file_path)
        except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError, ValueError):
            return self._fallback_analyzer.analyze(file_path)


class SettingsReader(Protocol):
    def load(self):
        ...


class ConfiguredMetadataAnalyzer:
    def __init__(self, settings_service: SettingsReader) -> None:
        self._settings_service = settings_service
        self._fallback_analyzer = BasicFileMetadataAnalyzer()

    def analyze(self, file_path: Path) -> AnalyzedMediaMetadata:
        settings = self._settings_service.load()
        ffprobe_path = Path(settings.ffprobe_path)
        if ffprobe_path.exists():
            analyzer = FallbackMetadataAnalyzer(
                primary_analyzer=FFprobeMetadataAnalyzer(ffprobe_path),
                fallback_analyzer=self._fallback_analyzer,
            )
            return analyzer.analyze(file_path)
        return self._fallback_analyzer.analyze(file_path)


def _parse_fps(raw_value: str | None) -> float | None:
    if not raw_value or raw_value in {"0/0", "N/A"}:
        return None
    if "/" not in raw_value:
        return float(raw_value)
    numerator_text, denominator_text = raw_value.split("/", maxsplit=1)
    numerator = float(numerator_text)
    denominator = float(denominator_text)
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)
