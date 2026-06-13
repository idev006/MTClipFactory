from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

from mt_clip_factory.control_center.dto import SystemSettingsDTO
from mt_clip_factory.control_center.services import SystemSettingsService
from mt_clip_factory.factory.audio_composition import PreviewAudioMixPlan, PreviewAudioTrack
from mt_clip_factory.factory.audio_ducking import (
    build_sidechain_duck_filter_graph,
    build_windowed_duck_filter_graph,
    duck_gain,
    merged_duck_intervals,
    normalize_duck_mode,
    sidechain_threshold_gain,
)
from mt_clip_factory.factory.preview_composition import PreviewSegmentClip
from mt_clip_factory.factory.video_frame_normalization import build_visual_filter
from mt_clip_factory.factory.visual_compositing import render_segmented_visual_output


@dataclass(slots=True, frozen=True)
class RenderedPreviewOutput:
    file_path: Path
    duration_sec: float | None = None
    audio_mix_summary: dict | None = None
    visual_composite_summary: dict | None = None


class FFmpegPreviewRenderer:
    def __init__(
        self,
        settings_service: SystemSettingsService,
        preview_root: Path,
        *,
        output_resolution_field: str = "preview_output_resolution",
    ) -> None:
        self._settings_service = settings_service
        self._preview_root = preview_root
        self._output_resolution_field = output_resolution_field

    def render_output(
        self,
        *,
        product_code: str,
        output_stem: str,
        source_files: list[Path],
        segment_clips: tuple[PreviewSegmentClip, ...] = (),
        audio_mix_plan: PreviewAudioMixPlan | None = None,
        target_ratio: str | None = None,
    ) -> RenderedPreviewOutput:
        if not source_files:
            raise ValueError("At least one source file is required for preview rendering.")

        settings = self._settings_service.load()
        output_dir = self._preview_root / product_code / "videos"
        output_dir.mkdir(parents=True, exist_ok=True)
        target_path = output_dir / f"{output_stem}.mp4"
        if audio_mix_plan is not None:
            audio_mix_summary, visual_composite_summary = self._render_output_with_audio_mix(
                settings=settings,
                target_path=target_path,
                source_files=source_files,
                segment_clips=segment_clips,
                audio_mix_plan=audio_mix_plan,
                target_ratio=target_ratio,
            )
            return RenderedPreviewOutput(
                file_path=target_path,
                duration_sec=audio_mix_plan.target_duration_sec,
                audio_mix_summary=audio_mix_summary,
                visual_composite_summary=visual_composite_summary,
            )
        visual_composite_summary = self._render_visual_output(
            settings=settings,
            target_path=target_path,
            source_files=source_files,
            segment_clips=segment_clips,
            include_audio=True,
            target_ratio=target_ratio,
        )
        if segment_clips:
            return RenderedPreviewOutput(
                file_path=target_path,
                duration_sec=round(sum(segment.target_duration_sec for segment in segment_clips), 3),
                visual_composite_summary=visual_composite_summary,
            )
        return RenderedPreviewOutput(file_path=target_path, visual_composite_summary=visual_composite_summary)

    def render_preview(
        self,
        *,
        product_code: str,
        recipe_code: str,
        source_files: list[Path],
        segment_clips: tuple[PreviewSegmentClip, ...] = (),
        audio_mix_plan: PreviewAudioMixPlan | None = None,
        target_ratio: str | None = None,
    ) -> RenderedPreviewOutput:
        return self.render_output(
            product_code=product_code,
            output_stem=recipe_code,
            source_files=source_files,
            segment_clips=segment_clips,
            audio_mix_plan=audio_mix_plan,
            target_ratio=target_ratio,
        )

    def _render_output_with_audio_mix(
        self,
        *,
        settings: SystemSettingsDTO,
        target_path: Path,
        source_files: list[Path],
        segment_clips: tuple[PreviewSegmentClip, ...],
        audio_mix_plan: PreviewAudioMixPlan,
        target_ratio: str | None,
    ) -> tuple[dict, dict | None]:
        with TemporaryDirectory(prefix="mtclipfactory_preview_audio_mix_") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            silent_video_path = temp_dir / "silent_video.mp4"
            visual_composite_summary = self._render_visual_output(
                settings=settings,
                target_path=silent_video_path,
                source_files=source_files,
                segment_clips=segment_clips,
                include_audio=False,
                target_ratio=target_ratio,
            )
            voice_track_path, voice_summary = self._render_audio_track_sequence(
                settings=settings,
                temp_dir=temp_dir,
                prefix="voice",
                tracks=audio_mix_plan.voice_tracks,
                target_duration_sec=audio_mix_plan.target_duration_sec,
                allow_loop=False,
            )
            voice_track_path, voice_gain_summary = self._apply_gain_stage(
                settings=settings,
                temp_dir=temp_dir,
                track_path=voice_track_path,
                prefix="voice",
                gain_db=settings.voice_mix_gain_db,
            )
            voice_summary = {**voice_summary, **voice_gain_summary}
            music_track_path, music_summary = self._render_audio_track_sequence(
                settings=settings,
                temp_dir=temp_dir,
                prefix="music",
                tracks=audio_mix_plan.music_tracks,
                target_duration_sec=audio_mix_plan.target_duration_sec,
                allow_loop=settings.background_music_loop_enabled,
            )
            music_track_path, music_gain_summary = self._apply_gain_stage(
                settings=settings,
                temp_dir=temp_dir,
                track_path=music_track_path,
                prefix="music",
                gain_db=settings.music_mix_gain_db,
            )
            music_summary = {**music_summary, **music_gain_summary}
            music_track_path, ducking_summary = self._apply_ducking(
                settings=settings,
                temp_dir=temp_dir,
                music_track_path=music_track_path,
                voice_track_path=voice_track_path,
                voice_tracks=audio_mix_plan.voice_tracks,
                target_duration_sec=audio_mix_plan.target_duration_sec,
            )
            mixed_audio_path = self._mix_audio_tracks(
                settings=settings,
                temp_dir=temp_dir,
                voice_track_path=voice_track_path,
                music_track_path=music_track_path,
            )
            if mixed_audio_path is None:
                shutil.copy2(silent_video_path, target_path)
            else:
                self._run_ffmpeg(
                    settings=settings,
                    arguments=[
                        "-y",
                        "-i",
                        str(silent_video_path),
                        "-i",
                        str(mixed_audio_path),
                        "-map",
                        "0:v:0",
                        "-map",
                        "1:a:0",
                        "-c:v",
                        "copy",
                        "-c:a",
                        "aac",
                        "-shortest",
                        str(target_path),
                    ],
                )
        return {
            "mode": "runtime_audio_mix",
            "target_duration_sec": audio_mix_plan.target_duration_sec,
            "voice_loop_requested": settings.voice_loop_enabled,
            "voice_loop_applied": False,
            "voice_loop_policy_note": "primary_voice_never_auto_loops",
            "background_music_loop_enabled": settings.background_music_loop_enabled,
            "voice_tracks": _track_summary(audio_mix_plan.voice_tracks),
            "music_tracks": _track_summary(audio_mix_plan.music_tracks),
            "mix_balance": {
                "strategy": "voice_priority_gain_stage",
                "voice_mix_gain_db": settings.voice_mix_gain_db,
                "music_mix_gain_db": settings.music_mix_gain_db,
            },
            "voice_mix": voice_summary,
            "music_mix": music_summary,
            "ducking": ducking_summary,
            "audio_present": mixed_audio_path is not None,
        }, visual_composite_summary

    def _render_visual_output(
        self,
        *,
        settings: SystemSettingsDTO,
        target_path: Path,
        source_files: list[Path],
        segment_clips: tuple[PreviewSegmentClip, ...],
        include_audio: bool,
        target_ratio: str | None,
    ) -> dict | None:
        if segment_clips:
            return self._render_segmented_output(
                settings=settings,
                segment_clips=segment_clips,
                target_path=target_path,
                include_audio=include_audio,
                target_ratio=target_ratio,
            )
        if len(source_files) == 1:
            self._render_single_source(
                settings=settings,
                source_file=source_files[0],
                target_path=target_path,
                include_audio=include_audio,
                target_ratio=target_ratio,
            )
            return None
        self._render_concat_sources(
            settings=settings,
            source_files=source_files,
            target_path=target_path,
            include_audio=include_audio,
            target_ratio=target_ratio,
        )
        return None

    def _render_single_source(
        self,
        *,
        settings: SystemSettingsDTO,
        source_file: Path,
        target_path: Path,
        include_audio: bool,
        target_ratio: str | None,
    ) -> None:
        output_resolution = self._configured_output_resolution(settings)
        arguments = [
            "-y",
            "-i",
            str(source_file),
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
            arguments.extend(["-c:a", "aac", "-b:a", "96k"])
        else:
            arguments.append("-an")
        arguments.append(str(target_path))
        self._run_ffmpeg(settings=settings, arguments=arguments)

    def _render_concat_sources(
        self,
        *,
        settings: SystemSettingsDTO,
        source_files: list[Path],
        target_path: Path,
        include_audio: bool,
        target_ratio: str | None,
    ) -> None:
        output_resolution = self._configured_output_resolution(settings)
        with TemporaryDirectory(prefix="mtclipfactory_preview_") as temp_dir_name:
            concat_file = Path(temp_dir_name) / "concat_list.txt"
            concat_file.write_text(
                "\n".join(f"file '{_escape_concat_path(file_path)}'" for file_path in source_files),
                encoding="utf-8",
            )
            arguments = [
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
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
                arguments.extend(["-c:a", "aac", "-b:a", "96k"])
            else:
                arguments.append("-an")
            arguments.append(str(target_path))
            self._run_ffmpeg(settings=settings, arguments=arguments)

    def _render_segmented_output(
        self,
        *,
        settings: SystemSettingsDTO,
        segment_clips: tuple[PreviewSegmentClip, ...],
        target_path: Path,
        include_audio: bool,
        target_ratio: str | None,
    ) -> dict:
        return render_segmented_visual_output(
            settings=settings,
            segment_clips=segment_clips,
            target_path=target_path,
            include_audio=include_audio,
            target_ratio=target_ratio,
            output_resolution=self._configured_output_resolution(settings),
            run_ffmpeg=self._run_ffmpeg,
        )

    def _configured_output_resolution(self, settings: SystemSettingsDTO) -> str | None:
        return getattr(settings, self._output_resolution_field, "") or None

    def _render_audio_track_sequence(
        self,
        *,
        settings: SystemSettingsDTO,
        temp_dir: Path,
        prefix: str,
        tracks: tuple[PreviewAudioTrack, ...],
        target_duration_sec: float,
        allow_loop: bool,
    ) -> tuple[Path | None, dict]:
        if not tracks:
            return None, {"track_count": 0, "applied_fill_mode": "none", "total_duration_sec": 0.0}
        rendered_clips: list[Path] = []
        total_duration_sec = 0.0
        for track in tracks:
            clip_path = temp_dir / f"{prefix}_{track.sequence_index:02d}.m4a"
            self._run_ffmpeg(
                settings=settings,
                arguments=[
                    "-y",
                    "-i",
                    str(track.source_file),
                    "-vn",
                    "-t",
                    str(track.playback_duration_sec),
                    "-c:a",
                    "aac",
                    str(clip_path),
                ],
            )
            rendered_clips.append(clip_path)
            total_duration_sec = round(total_duration_sec + track.playback_duration_sec, 3)
        base_path = rendered_clips[0] if len(rendered_clips) == 1 else temp_dir / f"{prefix}_base.m4a"
        if len(rendered_clips) > 1:
            concat_file = temp_dir / f"{prefix}_concat.txt"
            concat_file.write_text(
                "\n".join(f"file '{_escape_concat_path(file_path)}'" for file_path in rendered_clips),
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
                    "-c",
                    "copy",
                    str(base_path),
                ],
            )
        if allow_loop and total_duration_sec > 0 and total_duration_sec < target_duration_sec:
            looped_path = temp_dir / f"{prefix}_looped.m4a"
            self._run_ffmpeg(
                settings=settings,
                arguments=[
                    "-y",
                    "-stream_loop",
                    "-1",
                    "-i",
                    str(base_path),
                    "-vn",
                    "-t",
                    str(target_duration_sec),
                    "-c:a",
                    "aac",
                    str(looped_path),
                ],
            )
            return looped_path, {
                "track_count": len(tracks),
                "applied_fill_mode": "loop_to_timeline",
                "base_duration_sec": total_duration_sec,
                "output_duration_sec": target_duration_sec,
            }
        if total_duration_sec > target_duration_sec:
            trimmed_path = temp_dir / f"{prefix}_trimmed.m4a"
            self._run_ffmpeg(
                settings=settings,
                arguments=[
                    "-y",
                    "-i",
                    str(base_path),
                    "-vn",
                    "-t",
                    str(target_duration_sec),
                    "-c:a",
                    "aac",
                    str(trimmed_path),
                ],
            )
            return trimmed_path, {
                "track_count": len(tracks),
                "applied_fill_mode": "trim_to_timeline",
                "base_duration_sec": total_duration_sec,
                "output_duration_sec": target_duration_sec,
            }
        applied_fill_mode = "natural" if total_duration_sec >= target_duration_sec else "silence_tail"
        return base_path, {
            "track_count": len(tracks),
            "applied_fill_mode": applied_fill_mode,
            "base_duration_sec": total_duration_sec,
            "output_duration_sec": total_duration_sec,
        }

    def _apply_ducking(
        self,
        *,
        settings: SystemSettingsDTO,
        temp_dir: Path,
        music_track_path: Path | None,
        voice_track_path: Path | None,
        voice_tracks: tuple[PreviewAudioTrack, ...],
        target_duration_sec: float,
    ) -> tuple[Path | None, dict]:
        if music_track_path is None:
            return None, {"applied": False, "reason": "no_music_track"}
        if not settings.music_duck_enabled:
            return music_track_path, {"applied": False, "reason": "duck_disabled_in_settings"}
        mode = normalize_duck_mode(settings.music_duck_mode)
        if mode == "sidechain_compressor":
            return self._apply_sidechain_ducking(
                settings=settings,
                temp_dir=temp_dir,
                music_track_path=music_track_path,
                voice_track_path=voice_track_path,
            )
        return self._apply_windowed_ducking(
            settings=settings,
            temp_dir=temp_dir,
            music_track_path=music_track_path,
            voice_tracks=voice_tracks,
            target_duration_sec=target_duration_sec,
        )

    def _apply_sidechain_ducking(
        self,
        *,
        settings: SystemSettingsDTO,
        temp_dir: Path,
        music_track_path: Path,
        voice_track_path: Path | None,
    ) -> tuple[Path, dict]:
        if voice_track_path is None:
            return music_track_path, {"applied": False, "reason": "no_voice_track", "requested_mode": settings.music_duck_mode}
        threshold_gain = sidechain_threshold_gain(settings.music_duck_threshold_db)
        filter_graph = build_sidechain_duck_filter_graph(
            threshold_gain=threshold_gain,
            ratio=settings.music_duck_ratio,
            attack_ms=settings.music_duck_attack_ms,
            release_ms=settings.music_duck_release_ms,
        )
        ducked_path = temp_dir / "music_ducked_sidechain.m4a"
        self._run_ffmpeg(
            settings=settings,
            arguments=[
                "-y",
                "-i",
                str(music_track_path),
                "-i",
                str(voice_track_path),
                "-filter_complex",
                filter_graph,
                "-map",
                "[ducked]",
                "-c:a",
                "aac",
                str(ducked_path),
            ],
        )
        return ducked_path, {
            "applied": True,
            "requested_mode": settings.music_duck_mode,
            "mode": "sidechain_compressor",
            "threshold_db": settings.music_duck_threshold_db,
            "threshold_gain": threshold_gain,
            "ratio": settings.music_duck_ratio,
            "attack_ms": settings.music_duck_attack_ms,
            "release_ms": settings.music_duck_release_ms,
        }

    def _apply_windowed_ducking(
        self,
        *,
        settings: SystemSettingsDTO,
        temp_dir: Path,
        music_track_path: Path,
        voice_tracks: tuple[PreviewAudioTrack, ...],
        target_duration_sec: float,
    ) -> tuple[Path, dict]:
        intervals = merged_duck_intervals(
            voice_tracks=voice_tracks,
            attack_ms=settings.music_duck_attack_ms,
            release_ms=settings.music_duck_release_ms,
            target_duration_sec=target_duration_sec,
        )
        if not intervals:
            return music_track_path, {"applied": False, "reason": "no_voice_intervals", "requested_mode": settings.music_duck_mode}
        gain = duck_gain(settings.music_duck_db)
        filter_graph = build_windowed_duck_filter_graph(intervals=intervals, gain=gain)
        ducked_path = temp_dir / "music_ducked_windowed.m4a"
        self._run_ffmpeg(
            settings=settings,
            arguments=[
                "-y",
                "-i",
                str(music_track_path),
                "-filter_complex",
                filter_graph,
                "-map",
                f"[m{len(intervals) - 1}]",
                "-c:a",
                "aac",
                str(ducked_path),
            ],
        )
        return ducked_path, {
            "applied": True,
            "requested_mode": settings.music_duck_mode,
            "mode": "windowed_volume_duck",
            "duck_db": settings.music_duck_db,
            "duck_gain": gain,
            "attack_ms": settings.music_duck_attack_ms,
            "release_ms": settings.music_duck_release_ms,
            "intervals": [
                {
                    "start_sec": round(start_sec, 3),
                    "end_sec": round(end_sec, 3),
                }
                for start_sec, end_sec in intervals
            ],
        }

    def _apply_gain_stage(
        self,
        *,
        settings: SystemSettingsDTO,
        temp_dir: Path,
        track_path: Path | None,
        prefix: str,
        gain_db: int,
    ) -> tuple[Path | None, dict]:
        if track_path is None:
            return None, {"gain_db": gain_db, "gain_stage_applied": False, "gain_reason": "no_track"}
        if gain_db == 0:
            return track_path, {"gain_db": gain_db, "gain_stage_applied": False, "gain_reason": "unity_gain"}
        gained_path = temp_dir / f"{prefix}_gain_staged.m4a"
        self._run_ffmpeg(
            settings=settings,
            arguments=[
                "-y",
                "-i",
                str(track_path),
                "-vn",
                "-af",
                f"volume={gain_db}dB",
                "-c:a",
                "aac",
                str(gained_path),
            ],
        )
        return gained_path, {"gain_db": gain_db, "gain_stage_applied": True}

    def _mix_audio_tracks(
        self,
        *,
        settings: SystemSettingsDTO,
        temp_dir: Path,
        voice_track_path: Path | None,
        music_track_path: Path | None,
    ) -> Path | None:
        if voice_track_path is None and music_track_path is None:
            return None
        if voice_track_path is None:
            return music_track_path
        if music_track_path is None:
            return voice_track_path
        mixed_audio_path = temp_dir / "mixed_audio.m4a"
        self._run_ffmpeg(
            settings=settings,
            arguments=[
                "-y",
                "-i",
                str(music_track_path),
                "-i",
                str(voice_track_path),
                "-filter_complex",
                "[0:a][1:a]amix=inputs=2:duration=longest:dropout_transition=0[mix]",
                "-map",
                "[mix]",
                "-c:a",
                "aac",
                str(mixed_audio_path),
            ],
        )
        return mixed_audio_path

    def _run_ffmpeg(self, settings: SystemSettingsDTO, arguments: list[str]) -> None:
        ffmpeg_path = Path(settings.ffmpeg_path)
        if not ffmpeg_path.exists():
            raise FileNotFoundError(str(ffmpeg_path))
        subprocess.run([str(ffmpeg_path), *arguments], check=True, capture_output=True, text=True)


class LocalPreviewRenderer:
    def __init__(self, preview_root: Path) -> None:
        self._preview_root = preview_root

    def render_output(
        self,
        *,
        product_code: str,
        output_stem: str,
        source_files: list[Path],
        segment_clips: tuple[PreviewSegmentClip, ...] = (),
        audio_mix_plan: PreviewAudioMixPlan | None = None,
        target_ratio: str | None = None,
    ) -> RenderedPreviewOutput:
        if not source_files:
            raise ValueError("At least one source file is required for preview rendering.")
        output_dir = self._preview_root / product_code / "videos"
        output_dir.mkdir(parents=True, exist_ok=True)
        suffix = source_files[0].suffix or ".bin"
        target_path = output_dir / f"{output_stem}{suffix}"
        if segment_clips:
            payload = b"".join(segment.source_file.read_bytes() for segment in segment_clips)
            target_path.write_bytes(payload)
            audio_mix_summary = None if audio_mix_plan is None else _build_local_audio_mix_summary(audio_mix_plan)
            return RenderedPreviewOutput(
                file_path=target_path,
                duration_sec=round(sum(segment.target_duration_sec for segment in segment_clips), 3),
                audio_mix_summary=audio_mix_summary,
                visual_composite_summary=_build_local_visual_composite_summary(segment_clips),
            )
        shutil.copy2(source_files[0], target_path)
        audio_mix_summary = None if audio_mix_plan is None else _build_local_audio_mix_summary(audio_mix_plan)
        return RenderedPreviewOutput(
            file_path=target_path,
            audio_mix_summary=audio_mix_summary,
            visual_composite_summary=None,
        )

    def render_preview(
        self,
        *,
        product_code: str,
        recipe_code: str,
        source_files: list[Path],
        segment_clips: tuple[PreviewSegmentClip, ...] = (),
        audio_mix_plan: PreviewAudioMixPlan | None = None,
        target_ratio: str | None = None,
    ) -> RenderedPreviewOutput:
        return self.render_output(
            product_code=product_code,
            output_stem=recipe_code,
            source_files=source_files,
            segment_clips=segment_clips,
            audio_mix_plan=audio_mix_plan,
            target_ratio=target_ratio,
        )


def _build_local_audio_mix_summary(audio_mix_plan: PreviewAudioMixPlan) -> dict:
    return {
        "mode": "local_simulated_audio_mix",
        "target_duration_sec": audio_mix_plan.target_duration_sec,
        "voice_tracks": _track_summary(audio_mix_plan.voice_tracks),
        "music_tracks": _track_summary(audio_mix_plan.music_tracks),
        "ducking": {
            "applied": bool(audio_mix_plan.voice_tracks and audio_mix_plan.music_tracks),
            "reason": "simulated_local_renderer",
        },
    }


def _build_local_visual_composite_summary(segment_clips: tuple[PreviewSegmentClip, ...]) -> dict:
    return {
        "mode": "local_simulated_visual_stack",
        "background_segment_count": sum(1 for segment in segment_clips if segment.background_layer is not None),
        "keyed_segment_count": 0,
        "segments": [
            {
                "segment_type": segment.segment_type,
                "sequence_index": segment.sequence_index,
                "primary_asset_code": segment.asset_code,
                "primary_layer_name": segment.layer_name,
                "background_asset_code": None if segment.background_layer is None else segment.background_layer.asset_code,
                "composite_mode": "single_layer",
            }
            for segment in segment_clips
        ],
    }


def _track_summary(tracks: tuple[PreviewAudioTrack, ...]) -> list[dict]:
    return [
        {
            "asset_code": track.asset_code,
            "asset_id": track.asset_id,
            "fill_mode": track.fill_mode,
            "layer_name": track.layer_name,
            "playback_duration_sec": track.playback_duration_sec,
            "sequence_index": track.sequence_index,
            "source_duration_sec": track.source_duration_sec,
            "source_file": str(track.source_file),
            "start_sec": track.start_sec,
        }
        for track in tracks
    ]


def _escape_concat_path(file_path: Path) -> str:
    return str(file_path).replace("\\", "\\\\").replace("'", "'\\''")
