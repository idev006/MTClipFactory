from __future__ import annotations

from pathlib import Path
import subprocess
import wave

import pytest

from mt_clip_factory.library.analyzers import FFprobeMetadataAnalyzer


FFPROBE_PATH = Path(r"F:\ffmpeg\bin\ffprobe.exe")
FFMPEG_PATH = Path(r"F:\ffmpeg\bin\ffmpeg.exe")


@pytest.mark.skipif(not FFPROBE_PATH.exists(), reason="ffprobe is not available")
def test_ffprobe_analyzes_wav_metadata(tmp_path) -> None:
    audio_path = tmp_path / "sample.wav"
    with wave.open(str(audio_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x00\x00" * 16000)

    analyzer = FFprobeMetadataAnalyzer(FFPROBE_PATH)
    metadata = analyzer.analyze(audio_path)

    assert metadata.duration_sec is not None
    assert metadata.duration_sec > 0.9
    assert metadata.has_audio is True
    assert metadata.file_size_mb is not None


@pytest.mark.skipif(not (FFPROBE_PATH.exists() and FFMPEG_PATH.exists()), reason="ffmpeg/ffprobe is not available")
def test_ffprobe_analyzes_video_metadata(tmp_path) -> None:
    video_path = tmp_path / "sample.mp4"
    command = [
        str(FFMPEG_PATH),
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=320x240:d=1",
        str(video_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)

    analyzer = FFprobeMetadataAnalyzer(FFPROBE_PATH)
    metadata = analyzer.analyze(video_path)

    assert metadata.width == 320
    assert metadata.height == 240
    assert metadata.duration_sec is not None
    assert metadata.duration_sec > 0
    assert metadata.ratio == "320:240"
