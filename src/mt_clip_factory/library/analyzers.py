from __future__ import annotations

from pathlib import Path

from mt_clip_factory.library.contracts import AnalyzedMediaMetadata


class BasicFileMetadataAnalyzer:
    _audio_extensions = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}

    def analyze(self, file_path: Path) -> AnalyzedMediaMetadata:
        file_size_mb = round(file_path.stat().st_size / (1024 * 1024), 4)
        return AnalyzedMediaMetadata(
            file_size_mb=file_size_mb,
            has_audio=file_path.suffix.lower() in self._audio_extensions,
        )
