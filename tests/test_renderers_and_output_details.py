from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from mt_clip_factory.control_center.dto import SystemSettingsDTO
from mt_clip_factory.factory.audio_composition import PreviewAudioMixPlan, PreviewAudioTrack
from mt_clip_factory.factory.caption_runtime import ResolvedCaptionRole
from mt_clip_factory.factory.preview_composition import PreviewLayerClip, PreviewSegmentClip
from mt_clip_factory.factory.renderers import FFmpegPreviewRenderer, LocalPreviewRenderer
from mt_clip_factory.factory.visual_compositing import GreenscreenAnalysis, dominant_green_ratio
from mt_clip_factory.ui.factory.recipe_builder_aftercare import _build_manifest_caption_lines, _build_manifest_visual_lines
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


def _build_caption_role(
    *,
    font_file: Path,
    rendered_lines: tuple[str, ...],
    alignment: str,
    textbox_alignment: str,
    line_left_positions_px: tuple[int, ...],
    line_top_positions_px: tuple[int, ...],
    line_font_sizes_px: tuple[int, ...],
    line_widths_px: tuple[int, ...],
    line_height_px: int,
    line_heights_px: tuple[int, ...],
    text_block_width_px: int,
    text_block_height_px: int,
    max_text_width_px: int,
    box_left_px: int,
    box_top_px: int,
    box_width_px: int,
    box_height_px: int,
    padding: int,
    textbox_width_ratio: float,
    line_box_left_positions_px: tuple[int, ...] = (),
    line_box_top_positions_px: tuple[int, ...] = (),
    line_box_widths_px: tuple[int, ...] = (),
    line_box_heights_px: tuple[int, ...] = (),
    textbox_height_ratio: float = 0.0,
    vertical_alignment: str = "top",
    textbox_mode: str = "grouped",
    textbox_height_mode: str = "content_hug",
    line_advance_ratio: float = 1.0,
    style_preset: str | None = None,
    box_border_color: str | None = None,
    box_border_opacity: float = 0.0,
    box_border_width: int = 0,
) -> ResolvedCaptionRole:
    return ResolvedCaptionRole(
        role="main",
        source_text="\n".join(rendered_lines),
        rendered_text="\n".join(rendered_lines),
        segment_type="hook",
        sequence_index=1,
        seed_key="seed",
        selection_index=0,
        rendered_lines=rendered_lines,
        line_break_mode="manual",
        fit_strategy="manual_breaks",
        line_count=len(rendered_lines),
        font_family="THSarabun",
        font_fallbacks=(),
        font_size=72,
        requested_font_size=72,
        font_size_unit="px",
        min_font_size=48,
        font_weight="bold",
        font_source=str(font_file),
        font_file=font_file,
        font_resolution_mode="workspace_primary",
        font_resolution_target="THSarabun",
        position="center",
        alignment=alignment,
        vertical_alignment=vertical_alignment,
        textbox_alignment=textbox_alignment,
        textbox_mode=textbox_mode,
        textbox_height_mode=textbox_height_mode,
        style_preset=style_preset,
        text_color="#FFFFFF",
        stroke_color="#000000",
        stroke_width=3,
        background_color="#000000",
        background_opacity=0.15,
        box_border_color=box_border_color,
        box_border_opacity=box_border_opacity,
        box_border_width=box_border_width,
        padding=padding,
        max_lines=3,
        max_chars_per_line=18,
        max_width_ratio=textbox_width_ratio,
        textbox_width_ratio=textbox_width_ratio,
        textbox_height_ratio=textbox_height_ratio,
        line_spacing_ratio=0.12,
        line_advance_ratio=line_advance_ratio,
        safe_top_ratio=0.14,
        safe_bottom_ratio=0.46,
        line_spacing_px=8,
        line_font_sizes_px=line_font_sizes_px,
        line_widths_px=line_widths_px,
        line_height_px=line_height_px,
        line_heights_px=line_heights_px,
        text_block_width_px=text_block_width_px,
        text_block_height_px=text_block_height_px,
        max_text_width_px=max_text_width_px,
        line_left_positions_px=line_left_positions_px,
        line_top_positions_px=line_top_positions_px,
        line_box_left_positions_px=line_box_left_positions_px,
        line_box_top_positions_px=line_box_top_positions_px,
        line_box_widths_px=line_box_widths_px,
        line_box_heights_px=line_box_heights_px,
        box_left_px=box_left_px,
        box_top_px=box_top_px,
        box_width_px=box_width_px,
        box_height_px=box_height_px,
        frame_width_px=1080,
        frame_height_px=1920,
        overflow_policy="wrap_then_scale_then_review",
        enter_animation="pop_in",
        overflowed=False,
        review_required=False,
        truncated_for_runtime=False,
    )


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


def _voice_only_audio_mix_plan(tmp_path: Path) -> PreviewAudioMixPlan:
    voice_source = tmp_path / "voice_only.mp3"
    voice_source.write_bytes(b"voice")
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
        music_tracks=(),
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


def test_ffmpeg_renderer_pads_voice_only_mix_with_silence_tail_to_target_duration(tmp_path) -> None:
    settings = _settings(tmp_path)
    renderer = InspectableFFmpegPreviewRenderer(StaticSettingsService(settings), tmp_path / "preview_root")
    source_file = tmp_path / "visual.mp4"
    source_file.write_bytes(b"visual")

    rendered = renderer.render_output(
        product_code="honey",
        output_stem="voice_only_mix",
        source_files=[source_file],
        audio_mix_plan=_voice_only_audio_mix_plan(tmp_path),
        target_ratio="9:16",
    )

    assert rendered.audio_mix_summary is not None
    assert rendered.audio_mix_summary["voice_mix"]["applied_fill_mode"] == "silence_tail"
    assert rendered.audio_mix_summary["voice_mix"]["output_duration_sec"] == 10.0
    assert any("apad=pad_dur=6.0" in " ".join(command) for command in renderer.commands)


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


def test_ffmpeg_renderer_builds_drawtext_filters_for_caption_layers(tmp_path) -> None:
    settings = _settings(tmp_path)
    renderer = InspectableFFmpegPreviewRenderer(StaticSettingsService(settings), tmp_path / "preview_root")
    source_file = tmp_path / "visual.mp4"
    font_file = tmp_path / "THSarabun.ttf"
    source_file.write_bytes(b"visual")
    font_file.write_bytes(b"font")

    renderer.render_output(
        product_code="honey",
        output_stem="caption_preview",
        source_files=[source_file],
        segment_clips=(
            PreviewSegmentClip(
                sequence_index=1,
                segment_type="hook",
                layer_name="background_visual",
                asset_id=11,
                asset_code="visual_asset",
                source_file=source_file,
                start_sec=0.0,
                end_sec=3.0,
                target_duration_sec=3.0,
                fill_mode="trim_to_segment",
                captions=(
                    ResolvedCaptionRole(
                        role="main",
                        source_text="พลังบวกทุกวัน",
                        rendered_text="พลังบวกทุกวัน",
                        segment_type="hook",
                        sequence_index=1,
                        seed_key="seed",
                        selection_index=0,
                        rendered_lines=("caption",),
                        line_break_mode="manual",
                        fit_strategy="manual_breaks",
                        line_count=1,
                        font_family="THSarabun",
                        font_fallbacks=(),
                        font_size=72,
                        requested_font_size=72,
                        font_size_unit="px",
                        min_font_size=48,
                        font_weight="bold",
                        font_source=str(font_file),
                        font_file=font_file,
                        font_resolution_mode="workspace_primary",
                        font_resolution_target="THSarabun",
                        position="center",
                        alignment="center",
                        vertical_alignment="top",
                        textbox_alignment="center",
                        textbox_mode="grouped",
                        textbox_height_mode="content_hug",
                        style_preset="sale_blast",
                        text_color="#FFFFFF",
                        stroke_color="#000000",
                        stroke_width=3,
                        background_color="#000000",
                        background_opacity=0.15,
                        box_border_color="#FFD447",
                        box_border_opacity=0.96,
                        box_border_width=4,
                        padding=20,
                        max_lines=3,
                        max_chars_per_line=18,
                        max_width_ratio=0.78,
                        textbox_width_ratio=0.78,
                        textbox_height_ratio=0.0,
                        line_spacing_ratio=0.12,
                        line_advance_ratio=1.0,
                        safe_top_ratio=0.14,
                        safe_bottom_ratio=0.46,
                        line_spacing_px=8,
                        line_font_sizes_px=(72,),
                        line_widths_px=(320,),
                        line_height_px=80,
                        line_heights_px=(80,),
                        text_block_width_px=320,
                        text_block_height_px=80,
                        max_text_width_px=560,
                        line_left_positions_px=(200,),
                        line_top_positions_px=(600,),
                        line_box_left_positions_px=(),
                        line_box_top_positions_px=(),
                        line_box_widths_px=(),
                        line_box_heights_px=(),
                        box_left_px=180,
                        box_top_px=580,
                        box_width_px=360,
                        box_height_px=120,
                        frame_width_px=720,
                        frame_height_px=1280,
                        overflow_policy="wrap_then_scale_then_review",
                        enter_animation="pop_in",
                        overflowed=False,
                        review_required=False,
                        truncated_for_runtime=False,
                    ),
                ),
            ),
        ),
        target_ratio="9:16",
    )

    assert any("drawtext=" in " ".join(command) for command in renderer.commands)
    assert any("drawbox=" in " ".join(command) for command in renderer.commands)
    assert any("fontfile='" in " ".join(command) for command in renderer.commands)


def test_ffmpeg_renderer_can_target_textbox_only_caption_geometry_without_full_pipeline(tmp_path) -> None:
    settings = _settings(tmp_path)
    renderer = InspectableFFmpegPreviewRenderer(StaticSettingsService(settings), tmp_path / "preview_root")
    source_file = tmp_path / "visual.mp4"
    font_file = tmp_path / "THSarabun.ttf"
    source_file.write_bytes(b"visual")
    font_file.write_bytes(b"font")

    renderer.render_output(
        product_code="honey",
        output_stem="textbox_only_preview",
        source_files=[source_file],
        segment_clips=(
            PreviewSegmentClip(
                sequence_index=1,
                segment_type="hook",
                layer_name="background_visual",
                asset_id=11,
                asset_code="visual_asset",
                source_file=source_file,
                start_sec=0.0,
                end_sec=1.0,
                target_duration_sec=1.0,
                fill_mode="trim_to_segment",
                captions=(
                    _build_caption_role(
                        font_file=font_file,
                        rendered_lines=("main line", "second line", "third line"),
                        alignment="left",
                        textbox_alignment="center",
                        line_left_positions_px=(132, 132, 132),
                        line_top_positions_px=(420, 510, 600),
                        line_font_sizes_px=(72, 60, 56),
                        line_widths_px=(300, 280, 250),
                        line_height_px=78,
                        line_heights_px=(78, 66, 62),
                        text_block_width_px=300,
                        text_block_height_px=222,
                        max_text_width_px=816,
                        box_left_px=108,
                        box_top_px=396,
                        box_width_px=864,
                        box_height_px=270,
                        padding=24,
                        textbox_width_ratio=0.8,
                    ),
                ),
            ),
        ),
        target_ratio="9:16",
    )

    command_text = "\n".join(" ".join(command) for command in renderer.commands)

    assert "drawbox=x=108:y=396:w=864:h=270:color=#000000@0.15:t=fill" in command_text
    assert command_text.count("drawtext=") >= 3
    assert "fontsize=72:x=132:y=420" in command_text
    assert "fontsize=60:x=132:y=510" in command_text
    assert "fontsize=56:x=132:y=600" in command_text


def test_ffmpeg_renderer_can_draw_grouped_textbox_border(tmp_path) -> None:
    settings = _settings(tmp_path)
    renderer = InspectableFFmpegPreviewRenderer(StaticSettingsService(settings), tmp_path / "preview_root")
    source_file = tmp_path / "visual.mp4"
    font_file = tmp_path / "THSarabun.ttf"
    source_file.write_bytes(b"visual")
    font_file.write_bytes(b"font")

    renderer.render_output(
        product_code="honey",
        output_stem="textbox_border_preview",
        source_files=[source_file],
        segment_clips=(
            PreviewSegmentClip(
                sequence_index=1,
                segment_type="hook",
                layer_name="background_visual",
                asset_id=11,
                asset_code="visual_asset",
                source_file=source_file,
                start_sec=0.0,
                end_sec=1.0,
                target_duration_sec=1.0,
                fill_mode="trim_to_segment",
                captions=(
                    _build_caption_role(
                        font_file=font_file,
                        rendered_lines=("limited offer",),
                        alignment="center",
                        textbox_alignment="center",
                        line_left_positions_px=(180,),
                        line_top_positions_px=(420,),
                        line_font_sizes_px=(72,),
                        line_widths_px=(320,),
                        line_height_px=80,
                        line_heights_px=(80,),
                        text_block_width_px=320,
                        text_block_height_px=80,
                        max_text_width_px=816,
                        box_left_px=108,
                        box_top_px=396,
                        box_width_px=864,
                        box_height_px=160,
                        padding=24,
                        textbox_width_ratio=0.8,
                        box_border_color="#FFD447",
                        box_border_opacity=0.96,
                        box_border_width=4,
                    ),
                ),
            ),
        ),
        target_ratio="9:16",
    )

    command_text = "\n".join(" ".join(command) for command in renderer.commands)

    assert "drawbox=x=108:y=396:w=864:h=160:color=#000000@0.15:t=fill" in command_text
    assert "drawbox=x=108:y=396:w=864:h=160:color=#FFD447@0.96:t=4" in command_text


def test_ffmpeg_renderer_can_draw_one_textbox_per_caption_line(tmp_path) -> None:
    settings = _settings(tmp_path)
    renderer = InspectableFFmpegPreviewRenderer(StaticSettingsService(settings), tmp_path / "preview_root")
    source_file = tmp_path / "visual.mp4"
    font_file = tmp_path / "THSarabun.ttf"
    source_file.write_bytes(b"visual")
    font_file.write_bytes(b"font")

    renderer.render_output(
        product_code="honey",
        output_stem="per_line_textbox_preview",
        source_files=[source_file],
        segment_clips=(
            PreviewSegmentClip(
                sequence_index=1,
                segment_type="hook",
                layer_name="background_visual",
                asset_id=11,
                asset_code="visual_asset",
                source_file=source_file,
                start_sec=0.0,
                end_sec=1.0,
                target_duration_sec=1.0,
                fill_mode="trim_to_segment",
                captions=(
                    _build_caption_role(
                        font_file=font_file,
                        rendered_lines=("wow", "amazing offer", "buy now"),
                        alignment="center",
                        textbox_alignment="center",
                        line_left_positions_px=(300, 220, 260),
                        line_top_positions_px=(420, 510, 600),
                        line_font_sizes_px=(72, 72, 72),
                        line_widths_px=(120, 280, 180),
                        line_height_px=78,
                        line_heights_px=(78, 78, 78),
                        text_block_width_px=280,
                        text_block_height_px=270,
                        max_text_width_px=716,
                        box_left_px=182,
                        box_top_px=396,
                        box_width_px=716,
                        box_height_px=320,
                        padding=24,
                        textbox_width_ratio=0.66,
                        textbox_mode="per_line",
                        line_box_left_positions_px=(276, 196, 236),
                        line_box_top_positions_px=(396, 486, 576),
                        line_box_widths_px=(168, 328, 228),
                        line_box_heights_px=(126, 126, 126),
                    ),
                ),
            ),
        ),
        target_ratio="9:16",
    )

    command_text = "\n".join(" ".join(command) for command in renderer.commands)

    assert command_text.count("drawbox=") >= 3
    assert "drawbox=x=276:y=396:w=168:h=126:color=#000000@0.15:t=fill" in command_text
    assert "drawbox=x=196:y=486:w=328:h=126:color=#000000@0.15:t=fill" in command_text
    assert "drawbox=x=236:y=576:w=228:h=126:color=#000000@0.15:t=fill" in command_text


def test_ffmpeg_renderer_can_draw_one_textbox_border_per_caption_line(tmp_path) -> None:
    settings = _settings(tmp_path)
    renderer = InspectableFFmpegPreviewRenderer(StaticSettingsService(settings), tmp_path / "preview_root")
    source_file = tmp_path / "visual.mp4"
    font_file = tmp_path / "THSarabun.ttf"
    source_file.write_bytes(b"visual")
    font_file.write_bytes(b"font")

    renderer.render_output(
        product_code="honey",
        output_stem="per_line_textbox_border_preview",
        source_files=[source_file],
        segment_clips=(
            PreviewSegmentClip(
                sequence_index=1,
                segment_type="hook",
                layer_name="background_visual",
                asset_id=11,
                asset_code="visual_asset",
                source_file=source_file,
                start_sec=0.0,
                end_sec=1.0,
                target_duration_sec=1.0,
                fill_mode="trim_to_segment",
                captions=(
                    _build_caption_role(
                        font_file=font_file,
                        rendered_lines=("wow", "amazing offer", "buy now"),
                        alignment="center",
                        textbox_alignment="center",
                        line_left_positions_px=(300, 220, 260),
                        line_top_positions_px=(420, 510, 600),
                        line_font_sizes_px=(72, 72, 72),
                        line_widths_px=(120, 280, 180),
                        line_height_px=78,
                        line_heights_px=(78, 78, 78),
                        text_block_width_px=280,
                        text_block_height_px=270,
                        max_text_width_px=716,
                        box_left_px=182,
                        box_top_px=396,
                        box_width_px=716,
                        box_height_px=320,
                        padding=24,
                        textbox_width_ratio=0.66,
                        textbox_mode="per_line",
                        line_box_left_positions_px=(276, 196, 236),
                        line_box_top_positions_px=(396, 486, 576),
                        line_box_widths_px=(168, 328, 228),
                        line_box_heights_px=(126, 126, 126),
                        box_border_color="#FFFFFF",
                        box_border_opacity=0.90,
                        box_border_width=3,
                    ),
                ),
            ),
        ),
        target_ratio="9:16",
    )

    command_text = "\n".join(" ".join(command) for command in renderer.commands)

    assert "drawbox=x=276:y=396:w=168:h=126:color=#FFFFFF@0.9:t=3" in command_text
    assert "drawbox=x=196:y=486:w=328:h=126:color=#FFFFFF@0.9:t=3" in command_text
    assert "drawbox=x=236:y=576:w=228:h=126:color=#FFFFFF@0.9:t=3" in command_text


def test_ffmpeg_renderer_uses_freeze_last_frame_for_short_visual_segments(tmp_path) -> None:
    settings = _settings(tmp_path)
    renderer = InspectableFFmpegPreviewRenderer(StaticSettingsService(settings), tmp_path / "preview_root")
    source_file = tmp_path / "visual.mp4"
    source_file.write_bytes(b"visual")

    renderer.render_output(
        product_code="honey",
        output_stem="freeze_frame_preview",
        source_files=[source_file],
        segment_clips=(
            PreviewSegmentClip(
                sequence_index=1,
                segment_type="hook",
                layer_name="background_visual",
                asset_id=11,
                asset_code="visual_asset",
                source_file=source_file,
                start_sec=0.0,
                end_sec=5.0,
                target_duration_sec=5.0,
                fill_mode="freeze_last_frame",
            ),
        ),
        target_ratio="9:16",
    )

    command_text = "\n".join(" ".join(command) for command in renderer.commands)
    assert "tpad=stop_mode=clone" in command_text
    assert "-stream_loop -1" not in command_text


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


def test_output_detail_helper_reads_versioned_manifest_sections(tmp_path) -> None:
    manifest_path = tmp_path / "preview_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "manifest_meta": {
                    "schema_name": "mtclipfactory_manifest",
                    "schema_version": "2.0",
                    "manifest_kind": "preview_render",
                },
                "composition": {
                    "captions": {
                        "enabled": True,
                        "segment_count": 1,
                        "role_count": 1,
                        "overflow_role_count": 0,
                        "review_required_role_count": 0,
                        "segments": [
                            {
                                "sequence_index": 1,
                                "segment_type": "hook",
                                "roles": [
                                    {
                                        "role": "main",
                                        "fit_strategy": "single_line_best_fit",
                                        "font_resolution_target": "TH Chakra Petch",
                                        "review_required": False,
                                        "rendered_text": "SALE TODAY",
                                    }
                                ],
                            }
                        ],
                    }
                },
                "render": {
                    "audio_mix": {
                        "mode": "runtime_audio_mix",
                        "audio_present": True,
                        "voice_loop_applied": False,
                        "voice_tracks": [{"asset_code": "voice_asset"}],
                        "music_tracks": [{"asset_code": "music_asset"}],
                    },
                    "visual_composite": {
                        "mode": "layered_visual_stack",
                        "background_segment_count": 1,
                        "keyed_segment_count": 0,
                        "segments": [
                            {
                                "sequence_index": 1,
                                "segment_type": "hook",
                                "composite_mode": "single_layer",
                                "primary_asset_code": "fg_asset",
                                "background_asset_code": "bg_asset",
                            }
                        ],
                    },
                },
                "quality": {
                    "review_gate": {
                        "required": False,
                        "duplicate_risk": 0.1,
                        "quality_score": 0.9,
                        "summary": "Looks clean.",
                        "signals": [],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    review_lines = _build_manifest_review_lines(str(manifest_path))
    audio_lines = _build_manifest_audio_lines(str(manifest_path))
    visual_lines = _build_manifest_visual_lines(str(manifest_path))
    caption_lines = _build_manifest_caption_lines(str(manifest_path))

    assert "- Required: False" in review_lines
    assert "- Mode: runtime_audio_mix" in audio_lines
    assert "- Mode: layered_visual_stack" in visual_lines
    assert "- Caption Role: main | fit=single_line_best_fit | font=TH Chakra Petch | review=False" in caption_lines


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


def test_output_detail_helper_reads_caption_summary_from_manifest(tmp_path) -> None:
    manifest_path = tmp_path / "preview_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "captions": {
                    "enabled": True,
                    "segment_count": 1,
                    "role_count": 2,
                    "overflow_role_count": 1,
                    "review_required_role_count": 1,
                    "segments": [
                        {
                            "sequence_index": 1,
                            "segment_type": "hook",
                            "roles": [
                                {
                                    "role": "main",
                                    "fit_strategy": "truncated_for_runtime",
                                    "font_resolution_target": "THSarabun",
                                    "review_required": True,
                                    "rendered_text": "พลังบวก…",
                                }
                            ],
                        }
                    ],
                }
            }
        ),
        encoding="utf-8",
    )

    lines = _build_manifest_caption_lines(str(manifest_path))

    assert "Runtime Captions:" in lines
    assert "- Overflow Role Count: 1" in lines
    assert "- Caption Role: main | fit=truncated_for_runtime | font=THSarabun | review=True" in lines
