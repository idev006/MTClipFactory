from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from mt_clip_factory.control_center.dto import SystemSettingsDTO
from mt_clip_factory.factory.preview_composition import PreviewSegmentClip
from mt_clip_factory.factory.video_frame_normalization import build_visual_filter

_GREEN_SCREEN_COLOR = "0x00FF00"
_GREEN_SCREEN_SIMILARITY = "0.26"
_GREEN_SCREEN_BLEND = "0.10"
_SAMPLE_SIZE = 48
_MIN_GREEN_SCREEN_RATIO = 0.28


@dataclass(slots=True, frozen=True)
class GreenscreenAnalysis:
    likely_greenscreen: bool
    dominant_green_ratio: float


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
        "keyed_segment_count": sum(1 for summary in summaries if summary["composite_mode"] == "green_chroma_key_overlay"),
        "segments": summaries,
    }


def _render_segment(
    *,
    settings: SystemSettingsDTO,
    segment: PreviewSegmentClip,
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
        target_path=segment_path,
        include_audio=include_audio,
        target_ratio=target_ratio,
        output_resolution=output_resolution,
        run_ffmpeg=run_ffmpeg,
    )
    return _segment_summary(segment, composite_mode="green_chroma_key_overlay", analysis=analysis)


def analyze_likely_greenscreen(settings: SystemSettingsDTO, source_file: Path) -> GreenscreenAnalysis:
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
    ratio = dominant_green_ratio(sample)
    return GreenscreenAnalysis(
        likely_greenscreen=ratio >= _MIN_GREEN_SCREEN_RATIO,
        dominant_green_ratio=round(ratio, 4),
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


def _render_single_layer_segment(
    *,
    settings: SystemSettingsDTO,
    source_file: Path,
    target_path: Path,
    include_audio: bool,
    target_ratio: str | None,
    output_resolution: str | None,
    target_duration_sec: float,
    run_ffmpeg,
) -> None:
    arguments = [
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        str(source_file),
        "-t",
        str(target_duration_sec),
        "-vf",
        build_visual_filter(target_ratio=target_ratio, output_resolution=output_resolution),
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
    target_path: Path,
    include_audio: bool,
    target_ratio: str | None,
    output_resolution: str | None,
    run_ffmpeg,
) -> None:
    if segment.background_layer is None:
        raise ValueError("Background layer is required for green-screen overlay rendering.")
    arguments = [
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        str(segment.background_layer.source_file),
        "-stream_loop",
        "-1",
        "-i",
        str(segment.source_file),
        "-t",
        str(segment.target_duration_sec),
        "-filter_complex",
        _overlay_filter_graph(target_ratio=target_ratio, output_resolution=output_resolution),
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
        arguments.extend(["-map", "1:a:0?", "-c:a", "aac", "-b:a", "96k", "-shortest"])
    else:
        arguments.append("-an")
    arguments.append(str(target_path))
    run_ffmpeg(settings=settings, arguments=arguments)


def _overlay_filter_graph(*, target_ratio: str | None, output_resolution: str | None) -> str:
    base_filter = build_visual_filter(target_ratio=target_ratio, output_resolution=output_resolution)
    return (
        f"[0:v]{base_filter}[bg];"
        f"[1:v]{base_filter},colorkey={_GREEN_SCREEN_COLOR}:{_GREEN_SCREEN_SIMILARITY}:{_GREEN_SCREEN_BLEND},despill=green[fg];"
        "[bg][fg]overlay=0:0:format=auto[vout]"
    )


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
        "background_asset_code": None if segment.background_layer is None else segment.background_layer.asset_code,
        "composite_mode": composite_mode,
        "dominant_green_ratio": None if analysis is None else analysis.dominant_green_ratio,
        "likely_greenscreen": None if analysis is None else analysis.likely_greenscreen,
    }


def _escape_concat_path(file_path: Path) -> str:
    return str(file_path).replace("\\", "/").replace("'", r"'\''")
