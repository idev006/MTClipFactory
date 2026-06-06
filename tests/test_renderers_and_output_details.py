from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from mt_clip_factory.control_center.dto import SystemSettingsDTO
from mt_clip_factory.factory.audio_composition import PreviewAudioMixPlan, PreviewAudioTrack
from mt_clip_factory.factory.renderers import FFmpegPreviewRenderer, LocalPreviewRenderer
from mt_clip_factory.ui.factory.recipe_builder_window import _build_manifest_audio_lines


class StaticSettingsService:
    def __init__(self, settings: SystemSettingsDTO) -> None:
        self._settings = settings

    def load(self) -> SystemSettingsDTO:
        return self._settings


class InspectableFFmpegPreviewRenderer(FFmpegPreviewRenderer):
    def __init__(self, settings_service, preview_root: Path) -> None:
        super().__init__(settings_service, preview_root)
        self.commands: list[list[str]] = []

    def _run_ffmpeg(self, settings: SystemSettingsDTO, arguments: list[str]) -> None:
        self.commands.append(list(arguments))
        Path(arguments[-1]).parent.mkdir(parents=True, exist_ok=True)
        Path(arguments[-1]).write_bytes(b"ffmpeg-output")


def _settings(tmp_path: Path) -> SystemSettingsDTO:
    ffmpeg_path = tmp_path / "ffmpeg.exe"
    ffmpeg_path.write_bytes(b"ffmpeg")
    return SystemSettingsDTO(
        database_path=str(tmp_path / "db.sqlite"),
        media_root=str(tmp_path / "media"),
        docs_root=str(tmp_path / "doc"),
        outputs_root=str(tmp_path / "outputs"),
        preview_root=str(tmp_path / "preview"),
        ffmpeg_root=str(tmp_path),
        ffprobe_path=str(tmp_path / "ffprobe.exe"),
        ffmpeg_path=str(ffmpeg_path),
        cpu_limit_percent=90,
        ram_limit_percent=80,
        disk_free_gb_min=20,
        max_preview_workers=1,
        max_final_workers=1,
        auto_refresh_seconds=10,
        auto_recover_queued_jobs=False,
        max_recovery_jobs_per_run=25,
        failed_job_escalation_threshold=2,
        voice_loop_enabled=False,
        background_music_loop_enabled=True,
        music_duck_enabled=True,
        music_duck_mode="sidechain_compressor",
        music_duck_db=-15,
        music_duck_attack_ms=250,
        music_duck_release_ms=500,
        music_duck_threshold_db=-24,
        music_duck_ratio=8.0,
    )


def _audio_mix_plan(tmp_path: Path) -> PreviewAudioMixPlan:
    voice_source = tmp_path / "voice.mp3"
    music_source = tmp_path / "music.mp3"
    voice_source.write_bytes(b"voice")
    music_source.write_bytes(b"music")
    return PreviewAudioMixPlan(
        target_duration_sec=10.0,
        voice_tracks=(
            PreviewAudioTrack(
                sequence_index=1,
                layer_name="primary_voice",
                asset_id=11,
                asset_code="voice_asset",
                source_file=voice_source,
                start_sec=0.0,
                playback_duration_sec=4.0,
                source_duration_sec=4.0,
                fill_mode="no_loop",
            ),
        ),
        music_tracks=(
            PreviewAudioTrack(
                sequence_index=1,
                layer_name="background_music",
                asset_id=12,
                asset_code="music_asset",
                source_file=music_source,
                start_sec=0.0,
                playback_duration_sec=3.0,
                source_duration_sec=3.0,
                fill_mode="sequence_fill",
            ),
        ),
    )


def test_ffmpeg_renderer_builds_runtime_audio_mix_commands(tmp_path) -> None:
    settings = _settings(tmp_path)
    renderer = InspectableFFmpegPreviewRenderer(StaticSettingsService(settings), tmp_path / "preview_root")
    source_file = tmp_path / "visual.mp4"
    source_file.write_bytes(b"visual")

    rendered = renderer.render_output(
        product_code="honey",
        output_stem="runtime_mix",
        source_files=[source_file],
        audio_mix_plan=_audio_mix_plan(tmp_path),
    )

    assert rendered.file_path.exists()
    assert rendered.audio_mix_summary is not None
    assert rendered.audio_mix_summary["ducking"]["applied"] is True
    assert rendered.audio_mix_summary["ducking"]["mode"] == "sidechain_compressor"
    assert any("-an" in command for command in renderer.commands)
    assert any("sidechaincompress=" in " ".join(command) for command in renderer.commands)
    assert any("amix=inputs=2" in " ".join(command) for command in renderer.commands)
    assert any(command.count("-map") >= 2 for command in renderer.commands)


def test_ffmpeg_renderer_supports_windowed_duck_fallback_mode(tmp_path) -> None:
    settings = _settings(tmp_path)
    settings = replace(settings, music_duck_mode="windowed_volume_duck")
    renderer = InspectableFFmpegPreviewRenderer(StaticSettingsService(settings), tmp_path / "preview_root")
    source_file = tmp_path / "visual.mp4"
    source_file.write_bytes(b"visual")

    rendered = renderer.render_output(
        product_code="honey",
        output_stem="windowed_mix",
        source_files=[source_file],
        audio_mix_plan=_audio_mix_plan(tmp_path),
    )

    assert rendered.audio_mix_summary is not None
    assert rendered.audio_mix_summary["ducking"]["mode"] == "windowed_volume_duck"
    assert any("volume=volume=" in " ".join(command) for command in renderer.commands)


def test_local_renderer_returns_simulated_audio_mix_summary(tmp_path) -> None:
    source_file = tmp_path / "visual.mp4"
    source_file.write_bytes(b"visual")
    renderer = LocalPreviewRenderer(tmp_path / "preview_root")

    rendered = renderer.render_output(
        product_code="honey",
        output_stem="local_mix",
        source_files=[source_file],
        audio_mix_plan=_audio_mix_plan(tmp_path),
    )

    assert rendered.audio_mix_summary is not None
    assert rendered.audio_mix_summary["mode"] == "local_simulated_audio_mix"
    assert rendered.audio_mix_summary["ducking"]["applied"] is True


def test_output_detail_helper_reads_runtime_audio_mix_from_manifest(tmp_path) -> None:
    manifest_path = tmp_path / "preview_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "audio_mix": {
                    "mode": "runtime_audio_mix",
                    "audio_present": True,
                    "voice_loop_applied": False,
                    "voice_tracks": [{"asset_code": "voice_asset"}],
                    "music_tracks": [{"asset_code": "music_asset"}],
                    "ducking": {
                        "applied": True,
                        "mode": "sidechain_compressor",
                        "threshold_db": -24,
                        "ratio": 8.0,
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    lines = _build_manifest_audio_lines(str(manifest_path))

    assert "Runtime Audio Mix:" in lines
    assert "- Duck Applied: True" in lines
    assert "- Duck Threshold (dB): -24" in lines
    assert "- Duck Ratio: 8.0" in lines
    assert "- Music Track Count: 1" in lines
