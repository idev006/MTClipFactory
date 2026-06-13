from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from mt_clip_factory.control_center.dto import SystemSettingsDTO
from mt_clip_factory.factory.audio_composition import PreviewAudioMixPlan, PreviewAudioTrack
from mt_clip_factory.factory.preview_composition import PreviewLayerClip, PreviewSegmentClip
from mt_clip_factory.factory.renderers import FFmpegPreviewRenderer, LocalPreviewRenderer
from mt_clip_factory.factory.visual_compositing import GreenscreenAnalysis, dominant_green_ratio
from mt_clip_factory.ui.factory.recipe_builder_aftercare import _build_manifest_visual_lines
from mt_clip_factory.ui.factory.recipe_builder_window import _build_manifest_audio_lines, _build_manifest_review_lines


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
        visual_key_profile="auto",
        visual_key_color="#00FF00",
        music_duck_mode="sidechain_compressor",
        music_duck_db=-15,
        music_duck_attack_ms=250,
        music_duck_release_ms=500,
        music_duck_threshold_db=-24,
        music_duck_ratio=8.0,
        voice_mix_gain_db=0,
        music_mix_gain_db=-4,
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
        target_ratio="9:16",
    )

    assert rendered.file_path.exists()
    assert rendered.audio_mix_summary is not None
    assert rendered.audio_mix_summary["ducking"]["applied"] is True
    assert rendered.audio_mix_summary["ducking"]["mode"] == "sidechain_compressor"
    assert rendered.audio_mix_summary["mix_balance"]["music_mix_gain_db"] == -4
    assert rendered.audio_mix_summary["music_mix"]["gain_stage_applied"] is True
    assert any("-an" in command for command in renderer.commands)
    assert any("sidechaincompress=" in " ".join(command) for command in renderer.commands)
    assert any("amix=inputs=2" in " ".join(command) for command in renderer.commands)
    assert any("volume=-4dB" in " ".join(command) for command in renderer.commands)
    assert any(command.count("-map") >= 2 for command in renderer.commands)
    assert any("pad=720:1280" in " ".join(command) for command in renderer.commands)


def test_ffmpeg_renderer_supports_windowed_duck_fallback_mode(tmp_path) -> None:
    settings = _settings(tmp_path)
    settings = replace(settings, music_duck_mode="windowed_volume_duck", voice_mix_gain_db=2, music_mix_gain_db=-6)
    renderer = InspectableFFmpegPreviewRenderer(StaticSettingsService(settings), tmp_path / "preview_root")
    source_file = tmp_path / "visual.mp4"
    source_file.write_bytes(b"visual")

    rendered = renderer.render_output(
        product_code="honey",
        output_stem="windowed_mix",
        source_files=[source_file],
        audio_mix_plan=_audio_mix_plan(tmp_path),
        target_ratio="16:9",
    )

    assert rendered.audio_mix_summary is not None
    assert rendered.audio_mix_summary["ducking"]["mode"] == "windowed_volume_duck"
    assert rendered.audio_mix_summary["mix_balance"]["voice_mix_gain_db"] == 2
    assert rendered.audio_mix_summary["voice_mix"]["gain_stage_applied"] is True
    assert any("volume=volume=" in " ".join(command) for command in renderer.commands)
    assert any("volume=2dB" in " ".join(command) for command in renderer.commands)
    assert any("volume=-6dB" in " ".join(command) for command in renderer.commands)
    assert any("pad=1280:720" in " ".join(command) for command in renderer.commands)


def test_ffmpeg_renderer_uses_configured_exact_output_resolution(tmp_path) -> None:
    settings = _settings(tmp_path)
    settings = replace(settings, preview_output_resolution="1080x1920")
    renderer = InspectableFFmpegPreviewRenderer(StaticSettingsService(settings), tmp_path / "preview_root")
    source_file = tmp_path / "visual.mp4"
    source_file.write_bytes(b"visual")

    renderer.render_output(
        product_code="honey",
        output_stem="exact_resolution",
        source_files=[source_file],
        target_ratio="9:16",
    )

    assert any("pad=1080:1920" in " ".join(command) for command in renderer.commands)


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


def test_ffmpeg_renderer_builds_green_screen_overlay_when_background_layer_exists(tmp_path, monkeypatch) -> None:
    settings = _settings(tmp_path)
    renderer = InspectableFFmpegPreviewRenderer(StaticSettingsService(settings), tmp_path / "preview_root")
    background_source = tmp_path / "background.mp4"
    foreground_source = tmp_path / "foreground.mp4"
    background_source.write_bytes(b"background")
    foreground_source.write_bytes(b"foreground")
    monkeypatch.setattr(
        "mt_clip_factory.factory.visual_compositing.analyze_likely_greenscreen",
        lambda settings, source_file: GreenscreenAnalysis(
            likely_greenscreen=True,
            dominant_color_ratio=0.8,
            key_profile="green",
            key_color="0x00FF00",
        ),
    )

    rendered = renderer.render_output(
        product_code="honey",
        output_stem="layered_preview",
        source_files=[foreground_source],
        segment_clips=(
            PreviewSegmentClip(
                sequence_index=1,
                segment_type="hook",
                layer_name="product_focus_visual",
                asset_id=11,
                asset_code="foreground_asset",
                source_file=foreground_source,
                start_sec=0.0,
                end_sec=3.0,
                target_duration_sec=3.0,
                fill_mode="trim_to_segment",
                background_layer=PreviewLayerClip(
                    layer_name="background_visual",
                    asset_id=22,
                    asset_code="background_asset",
                    source_file=background_source,
                    fill_mode="trim_to_segment",
                ),
            ),
        ),
        target_ratio="9:16",
    )

    assert rendered.visual_composite_summary is not None
    assert rendered.visual_composite_summary["keyed_segment_count"] == 1
    assert any("-filter_complex" in command for command in renderer.commands)
    assert any("colorkey=" in " ".join(command) for command in renderer.commands)
    assert any("overlay=0:0" in " ".join(command) for command in renderer.commands)


def test_ffmpeg_renderer_honors_blue_key_policy_for_non_green_backgrounds(tmp_path) -> None:
    settings = replace(_settings(tmp_path), visual_key_profile="blue", visual_key_color="#0000FF")
    renderer = InspectableFFmpegPreviewRenderer(StaticSettingsService(settings), tmp_path / "preview_root")
    background_source = tmp_path / "background.mp4"
    foreground_source = tmp_path / "foreground.mp4"
    background_source.write_bytes(b"background")
    foreground_source.write_bytes(b"foreground")

    rendered = renderer.render_output(
        product_code="honey",
        output_stem="blue_key_preview",
        source_files=[foreground_source],
        segment_clips=(
            PreviewSegmentClip(
                sequence_index=1,
                segment_type="hook",
                layer_name="product_focus_visual",
                asset_id=11,
                asset_code="foreground_asset",
                source_file=foreground_source,
                start_sec=0.0,
                end_sec=3.0,
                target_duration_sec=3.0,
                fill_mode="trim_to_segment",
                background_layer=PreviewLayerClip(
                    layer_name="background_visual",
                    asset_id=22,
                    asset_code="background_asset",
                    source_file=background_source,
                    fill_mode="trim_to_segment",
                ),
            ),
        ),
        target_ratio="9:16",
    )

    assert rendered.visual_composite_summary is not None
    assert rendered.visual_composite_summary["segments"][0]["composite_mode"] == "blue_chroma_key_overlay"
    assert any("colorkey=0x0000FF" in " ".join(command) for command in renderer.commands)


def test_output_detail_helper_reads_runtime_audio_mix_from_manifest(tmp_path) -> None:
    manifest_path = tmp_path / "preview_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "audio_mix": {
                    "mode": "runtime_audio_mix",
                    "audio_present": True,
                    "voice_loop_applied": False,
                    "mix_balance": {
                        "strategy": "voice_priority_gain_stage",
                        "voice_mix_gain_db": 2,
                        "music_mix_gain_db": -6,
                    },
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
    assert "- Mix Strategy: voice_priority_gain_stage" in lines
    assert "- Voice Mix Gain (dB): 2" in lines
    assert "- Music Mix Gain (dB): -6" in lines
    assert "- Duck Applied: True" in lines
    assert "- Duck Threshold (dB): -24" in lines
    assert "- Duck Ratio: 8.0" in lines
    assert "- Music Track Count: 1" in lines


def test_output_detail_helper_reads_review_metrics_from_manifest(tmp_path) -> None:
    manifest_path = tmp_path / "preview_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "review_gate": {
                    "required": True,
                    "duplicate_risk": 0.5,
                    "quality_score": 0.5,
                    "summary": "Review required.",
                    "signals": [
                        {
                            "code": "audio_masking_risk",
                            "metric_value": "duck_disabled_in_settings",
                            "threshold": "ducking_applied",
                        }
                    ],
                    "metrics": {
                        "duration_unknown_audio_tracks": 1,
                        "voice_track_count": 1,
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    lines = _build_manifest_review_lines(str(manifest_path))

    assert "- Signal: audio_masking_risk | value=duck_disabled_in_settings | threshold=ducking_applied" in lines
    assert "- Metric: duration_unknown_audio_tracks=1" in lines
    assert "- Metric: voice_track_count=1" in lines


def test_dominant_green_ratio_identifies_green_screen_like_frames() -> None:
    green_pixel = bytes((10, 220, 10))
    skin_pixel = bytes((180, 140, 120))
    sample = (green_pixel * 8) + (skin_pixel * 2)

    ratio = dominant_green_ratio(sample)

    assert ratio == 0.8


def test_output_detail_helper_reads_visual_composite_summary_from_manifest(tmp_path) -> None:
    manifest_path = tmp_path / "preview_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "visual_composite": {
                    "mode": "layered_visual_stack",
                    "background_segment_count": 3,
                    "keyed_segment_count": 2,
                    "segments": [
                        {
                            "sequence_index": 1,
                            "segment_type": "hook",
                            "composite_mode": "green_chroma_key_overlay",
                            "primary_asset_code": "fg_asset",
                            "background_asset_code": "bg_asset",
                            "key_color_profile": "green",
                            "key_color": "0x00FF00",
                        }
                    ],
                }
            }
        ),
        encoding="utf-8",
    )

    lines = _build_manifest_visual_lines(str(manifest_path))

    assert "Runtime Visual Composite:" in lines
    assert "- Mode: layered_visual_stack" in lines
    assert "- Keyed Segment Count: 2" in lines
    assert "- Segment Composite: #1 hook | mode=green_chroma_key_overlay | primary=fg_asset | background=bg_asset" in lines
    assert "- Key Policy: green | color=0x00FF00" in lines
