from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from mt_clip_factory.control_center.dto import SystemSettingsDTO
from mt_clip_factory.factory.audio_composition import PreviewAudioMixPlan, PreviewAudioTrack
from mt_clip_factory.factory.automation_policy import AssetFillPolicy, ProductAutomationFillPolicies, default_fill_policies
from mt_clip_factory.factory.renderers import FFmpegPreviewRenderer


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


def test_ffmpeg_renderer_loops_voice_track_when_product_policy_requests_it(tmp_path) -> None:
    settings = replace(_settings(tmp_path), music_duck_enabled=False)
    renderer = InspectableFFmpegPreviewRenderer(StaticSettingsService(settings), tmp_path / "preview_root")
    visual = tmp_path / "visual.mp4"
    voice = tmp_path / "voice.mp3"
    visual.write_bytes(b"visual")
    voice.write_bytes(b"voice")
    defaults = default_fill_policies()
    fill_policies = ProductAutomationFillPolicies(
        voiceover=AssetFillPolicy(
            asset_type="voiceover",
            loop_enabled=True,
            shortfall_mode="loop_to_timeline",
        ),
        background_music=defaults.background_music,
        background_video=defaults.background_video,
        foreground_video=defaults.foreground_video,
    )

    rendered = renderer.render_output(
        product_code="honey",
        output_stem="voice_loop_preview",
        source_files=[visual],
        audio_mix_plan=PreviewAudioMixPlan(
            target_duration_sec=10.0,
            voice_tracks=(
                PreviewAudioTrack(
                    sequence_index=1,
                    layer_name="primary_voice",
                    asset_id=11,
                    asset_code="voice_asset",
                    source_file=voice,
                    start_sec=0.0,
                    playback_duration_sec=4.0,
                    source_duration_sec=4.0,
                    fill_mode="loop_to_timeline",
                ),
            ),
            music_tracks=(),
        ),
        target_ratio="9:16",
        fill_policies=fill_policies,
    )

    assert rendered.audio_mix_summary is not None
    assert rendered.audio_mix_summary["voice_loop_requested"] is True
    assert rendered.audio_mix_summary["voice_loop_applied"] is True
    assert rendered.audio_mix_summary["voice_mix"]["applied_fill_mode"] == "loop_to_timeline"
    assert any("-stream_loop" in command for command in renderer.commands)
