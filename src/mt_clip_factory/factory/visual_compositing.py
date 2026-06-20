from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from mt_clip_factory.control_center.dto import SystemSettingsDTO
from mt_clip_factory.factory.caption_bitmap_overlay import render_segment_caption_bitmap
from mt_clip_factory.factory.preview_composition import PreviewSegmentClip
from mt_clip_factory.factory.video_frame_normalization import build_visual_filter
from mt_clip_factory.visual_keying import KEY_COLOR_PRESETS, normalize_visual_key_color, normalize_visual_key_profile, resolve_profile_key_color

_GREEN_SCREEN_SIMILARITY = "0.26"
_GREEN_SCREEN_BLEND = "0.10"
_SAMPLE_SIZE = 48
_MIN_GREEN_SCREEN_RATIO = 0.28


@dataclass(slots=True, frozen=True)
class GreenscreenAnalysis:
    likely_greenscreen: bool
    dominant_color_ratio: float | None
    key_profile: str | None
    key_color: str | None


def render_segmented_visual_output(
    *,
    settings: SystemSettingsDTO,
    segment_clips: tuple[PreviewSegmentClip, ...],
    target_path: Path,
    include_audio: bool,
    target_ratio: str | None,
    output_resolution: str | None,
    run_ffmpeg,
) -> dict:
    analysis_cache: dict[Path, GreenscreenAnalysis] = {}
    summaries: list[dict] = []
    with TemporaryDirectory(prefix="mtclipfactory_preview_segments_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        rendered_segments: list[Path] = []
        for segment in segment_clips:
            segment_path = temp_dir / f"{segment.sequence_index:02d}_{segment.segment_type}.mp4"
            summary = _render_segment(
                settings=settings,
                segment=segment,
                temp_dir=temp_dir,
                segment_path=segment_path,
                include_audio=include_audio,
                target_ratio=target_ratio,
                output_resolution=output_resolution,
                run_ffmpeg=run_ffmpeg,
                analysis_cache=analysis_cache,
            )
            rendered_segments.append(segment_path)
            summaries.append(summary)
        concat_file = temp_dir / "segments_concat.txt"
        concat_file.write_text(
            "\n".join(f"file '{_escape_concat_path(file_path)}'" for file_path in rendered_segments),
            encoding="utf-8",
        )
        run_ffmpeg(
            settings=settings,
            arguments=[
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-c",
                "copy",
                str(target_path),
            ],
        )
    return {
        "mode": "layered_visual_stack",
        "background_segment_count": sum(1 for summary in summaries if summary["background_asset_code"] is not None),
        "keyed_segment_count": sum(1 for summary in summaries if summary["composite_mode"].endswith("_chroma_key_overlay")),
        "segments": summaries,
    }


def _render_segment(
    *,
    settings: SystemSettingsDTO,
    segment: PreviewSegmentClip,
    temp_dir: Path,
    segment_path: Path,
    include_audio: bool,
    target_ratio: str | None,
    output_resolution: str | None,
    run_ffmpeg,
    analysis_cache: dict[Path, GreenscreenAnalysis],
) -> dict:
    background_layer = segment.background_layer
    if background_layer is None or segment.layer_name != "product_focus_visual":
        _render_single_layer_segment(
            settings=settings,
            segment=segment,
            temp_dir=temp_dir,
            source_file=segment.source_file,
            target_path=segment_path,
            include_audio=include_audio,
            target_ratio=target_ratio,
            output_resolution=output_resolution,
            target_duration_sec=segment.target_duration_sec,
            run_ffmpeg=run_ffmpeg,
        )
        return _segment_summary(segment, composite_mode="single_layer", analysis=None)

    analysis = analysis_cache.get(segment.source_file)
    if analysis is None:
        analysis = analyze_likely_greenscreen(settings, segment.source_file)
        analysis_cache[segment.source_file] = analysis
    if not analysis.likely_greenscreen:
        _render_single_layer_segment(
            settings=settings,
            segment=segment,
            temp_dir=temp_dir,
            source_file=segment.source_file,
            target_path=segment_path,
            include_audio=include_audio,
            target_ratio=target_ratio,
            output_resolution=output_resolution,
            target_duration_sec=segment.target_duration_sec,
            run_ffmpeg=run_ffmpeg,
        )
        return _segment_summary(segment, composite_mode="single_layer", analysis=analysis)
    _render_green_screen_overlay_segment(
        settings=settings,
        segment=segment,
        analysis=analysis,
        temp_dir=temp_dir,
        target_path=segment_path,
        include_audio=include_audio,
        target_ratio=target_ratio,
        output_resolution=output_resolution,
        run_ffmpeg=run_ffmpeg,
    )
    return _segment_summary(segment, composite_mode=_composite_mode_for_profile(analysis.key_profile), analysis=analysis)


def analyze_likely_greenscreen(settings: SystemSettingsDTO, source_file: Path) -> GreenscreenAnalysis:
    profile = normalize_visual_key_profile(settings.visual_key_profile)
    if profile == "disabled":
        return GreenscreenAnalysis(False, None, None, None)
    if profile != "auto":
        return GreenscreenAnalysis(
            likely_greenscreen=True,
            dominant_color_ratio=None,
            key_profile=profile,
            key_color=_to_ffmpeg_color(resolve_profile_key_color(profile, settings.visual_key_color)),
        )
    ffmpeg_path = Path(settings.ffmpeg_path)
    if not ffmpeg_path.exists():
        raise FileNotFoundError(str(ffmpeg_path))
    sample = subprocess.run(
        [
            str(ffmpeg_path),
            "-v",
            "error",
            "-ss",
            "0.4",
            "-i",
            str(source_file),
            "-frames:v",
            "1",
            "-vf",
            f"scale={_SAMPLE_SIZE}:{_SAMPLE_SIZE}",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        check=True,
        capture_output=True,
    ).stdout
    ranked_profiles = [
        ("green", dominant_green_ratio(sample)),
        ("blue", dominant_blue_ratio(sample)),
        ("magenta", dominant_magenta_ratio(sample)),
    ]
    detected_profile, ratio = max(ranked_profiles, key=lambda item: item[1])
    likely = ratio >= _MIN_GREEN_SCREEN_RATIO
    return GreenscreenAnalysis(
        likely_greenscreen=likely,
        dominant_color_ratio=round(ratio, 4),
        key_profile=detected_profile if likely else None,
        key_color=_to_ffmpeg_color(KEY_COLOR_PRESETS[detected_profile]) if likely else None,
    )


def dominant_green_ratio(sample: bytes) -> float:
    if not sample:
        return 0.0
    total_pixels = len(sample) // 3
    if total_pixels <= 0:
        return 0.0
    dominant_green_pixels = 0
    for index in range(0, total_pixels * 3, 3):
        red = sample[index]
        green = sample[index + 1]
        blue = sample[index + 2]
        if green >= 90 and green >= (red * 1.25) and green >= (blue * 1.25):
            dominant_green_pixels += 1
    return dominant_green_pixels / total_pixels


def dominant_blue_ratio(sample: bytes) -> float:
    if not sample:
        return 0.0
    total_pixels = len(sample) // 3
    if total_pixels <= 0:
        return 0.0
    dominant_blue_pixels = 0
    for index in range(0, total_pixels * 3, 3):
        red = sample[index]
        green = sample[index + 1]
        blue = sample[index + 2]
        if blue >= 90 and blue >= (red * 1.25) and blue >= (green * 1.25):
            dominant_blue_pixels += 1
    return dominant_blue_pixels / total_pixels


def dominant_magenta_ratio(sample: bytes) -> float:
    if not sample:
        return 0.0
    total_pixels = len(sample) // 3
    if total_pixels <= 0:
        return 0.0
    dominant_magenta_pixels = 0
    for index in range(0, total_pixels * 3, 3):
        red = sample[index]
        green = sample[index + 1]
        blue = sample[index + 2]
        if red >= 90 and blue >= 90 and red >= (green * 1.25) and blue >= (green * 1.25):
            dominant_magenta_pixels += 1
    return dominant_magenta_pixels / total_pixels


def _render_single_layer_segment(
    *,
    settings: SystemSettingsDTO,
    segment: PreviewSegmentClip,
    temp_dir: Path,
    source_file: Path,
    target_path: Path,
    include_audio: bool,
    target_ratio: str | None,
    output_resolution: str | None,
    target_duration_sec: float,
    run_ffmpeg,
) -> None:
    caption_bitmap_path = render_segment_caption_bitmap(temp_dir=temp_dir, segment=segment)
    base_filter = _layer_fill_filter(
        fill_mode=segment.fill_mode,
        base_filter=build_visual_filter(target_ratio=target_ratio, output_resolution=output_resolution),
    )
    if caption_bitmap_path is None:
        visual_filter = base_filter
        arguments = [
            "-y",
            *_looping_input_arguments(fill_mode=segment.fill_mode),
            "-i",
            str(source_file),
            "-t",
            str(target_duration_sec),
            "-vf",
            visual_filter,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "30",
        ]
    else:
        arguments = [
            "-y",
            *_looping_input_arguments(fill_mode=segment.fill_mode),
            "-i",
            str(source_file),
            "-loop",
            "1",
            "-i",
            str(caption_bitmap_path),
            "-t",
            str(target_duration_sec),
            "-filter_complex",
            _caption_bitmap_filter_graph(base_filter=base_filter),
            "-map",
            "[vout]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "30",
        ]
    if include_audio:
        arguments.extend(["-c:a", "aac", "-b:a", "96k", "-shortest"])
    else:
        arguments.append("-an")
    arguments.append(str(target_path))
    run_ffmpeg(settings=settings, arguments=arguments)


def _render_green_screen_overlay_segment(
    *,
    settings: SystemSettingsDTO,
    segment: PreviewSegmentClip,
    analysis: GreenscreenAnalysis,
    temp_dir: Path,
    target_path: Path,
    include_audio: bool,
    target_ratio: str | None,
    output_resolution: str | None,
    run_ffmpeg,
) -> None:
    if segment.background_layer is None:
        raise ValueError("Background layer is required for green-screen overlay rendering.")
    if analysis.key_color is None:
        raise ValueError("Resolved key color is required for chroma-key overlay rendering.")
    caption_bitmap_path = render_segment_caption_bitmap(temp_dir=temp_dir, segment=segment)
    arguments = [
        "-y",
        *_looping_input_arguments(fill_mode=segment.background_layer.fill_mode),
        "-i",
        str(segment.background_layer.source_file),
        *_looping_input_arguments(fill_mode=segment.fill_mode),
        "-i",
        str(segment.source_file),
    ]
    if caption_bitmap_path is not None:
        arguments.extend(
            [
                "-loop",
                "1",
                "-i",
                str(caption_bitmap_path),
            ]
        )
    arguments.extend(
        [
        "-t",
        str(segment.target_duration_sec),
        "-filter_complex",
        _overlay_filter_graph(
            segment=segment,
            target_ratio=target_ratio,
            output_resolution=output_resolution,
            key_color=analysis.key_color,
            key_profile=analysis.key_profile,
            include_caption_bitmap=caption_bitmap_path is not None,
        ),
        "-map",
        "[vout]",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "30",
        ]
    )
    if include_audio:
        arguments.extend(["-map", "1:a:0?", "-c:a", "aac", "-b:a", "96k", "-shortest"])
    else:
        arguments.append("-an")
    arguments.append(str(target_path))
    run_ffmpeg(settings=settings, arguments=arguments)


def _overlay_filter_graph(
    *,
    segment: PreviewSegmentClip,
    target_ratio: str | None,
    output_resolution: str | None,
    key_color: str,
    key_profile: str | None,
    include_caption_bitmap: bool,
) -> str:
    background_filter = _layer_fill_filter(
        fill_mode=segment.background_layer.fill_mode if segment.background_layer is not None else "trim_to_segment",
        base_filter=build_visual_filter(target_ratio=target_ratio, output_resolution=output_resolution),
    )
    foreground_filter = _layer_fill_filter(
        fill_mode=segment.fill_mode,
        base_filter=build_visual_filter(target_ratio=target_ratio, output_resolution=output_resolution),
    )
    despill_filter = ",despill=green" if key_profile == "green" else ""
    output_label = "[vbase]" if include_caption_bitmap else "[vout]"
    overlay_graph = (
        f"[0:v]{background_filter}[bg];"
        f"[1:v]{foreground_filter},colorkey={key_color}:{_GREEN_SCREEN_SIMILARITY}:{_GREEN_SCREEN_BLEND}{despill_filter}[fg];"
        f"[bg][fg]overlay=0:0:format=auto{output_label}"
    )
    if not include_caption_bitmap:
        return overlay_graph
    return f"{overlay_graph};[2:v]format=rgba[cap];[vbase][cap]overlay=0:0:format=auto[vout]"


def _segment_summary(
    segment: PreviewSegmentClip,
    *,
    composite_mode: str,
    analysis: GreenscreenAnalysis | None,
) -> dict:
    return {
        "segment_type": segment.segment_type,
        "sequence_index": segment.sequence_index,
        "primary_asset_code": segment.asset_code,
        "primary_layer_name": segment.layer_name,
        "primary_fill_mode": segment.fill_mode,
        "background_asset_code": None if segment.background_layer is None else segment.background_layer.asset_code,
        "background_fill_mode": None if segment.background_layer is None else segment.background_layer.fill_mode,
        "composite_mode": composite_mode,
        "dominant_key_ratio": None if analysis is None else analysis.dominant_color_ratio,
        "likely_keyed_foreground": None if analysis is None else analysis.likely_greenscreen,
        "key_color_profile": None if analysis is None else analysis.key_profile,
        "key_color": None if analysis is None else analysis.key_color,
    }


def _escape_concat_path(file_path: Path) -> str:
    return str(file_path).replace("\\", "/").replace("'", r"'\''")


def _to_ffmpeg_color(value: str | None) -> str | None:
    if value is None:
        return None
    return normalize_visual_key_color(value).replace("#", "0x")


def _composite_mode_for_profile(profile: str | None) -> str:
    match profile:
        case "green":
            return "green_chroma_key_overlay"
        case "blue":
            return "blue_chroma_key_overlay"
        case "magenta":
            return "magenta_chroma_key_overlay"
        case "custom":
            return "custom_chroma_key_overlay"
        case _:
            return "chroma_key_overlay"


def _caption_bitmap_filter_graph(*, base_filter: str) -> str:
    return f"[0:v]{base_filter}[vbase];[1:v]format=rgba[cap];[vbase][cap]overlay=0:0:format=auto[vout]"


def _looping_input_arguments(*, fill_mode: str) -> list[str]:
    if fill_mode == "loop_to_segment":
        return ["-stream_loop", "-1"]
    return []


def _layer_fill_filter(*, fill_mode: str, base_filter: str) -> str:
    if fill_mode in {"freeze_last_frame", "review_if_short"}:
        return ",".join((base_filter, "tpad=stop_mode=clone:stop_duration=3600"))
    return base_filter

