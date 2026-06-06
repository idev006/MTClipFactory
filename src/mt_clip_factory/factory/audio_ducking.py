from __future__ import annotations

from mt_clip_factory.factory.audio_composition import PreviewAudioTrack

SUPPORTED_DUCK_MODES = ("sidechain_compressor", "windowed_volume_duck")
DEFAULT_DUCK_MODE = "sidechain_compressor"


def normalize_duck_mode(mode: str | None) -> str:
    if mode in SUPPORTED_DUCK_MODES:
        return str(mode)
    return DEFAULT_DUCK_MODE


def duck_gain(duck_db: int) -> float:
    return round(10 ** (duck_db / 20), 6)


def sidechain_threshold_gain(threshold_db: int) -> float:
    return round(10 ** (threshold_db / 20), 6)


def merged_duck_intervals(
    *,
    voice_tracks: tuple[PreviewAudioTrack, ...],
    attack_ms: int,
    release_ms: int,
    target_duration_sec: float,
) -> list[tuple[float, float]]:
    if not voice_tracks:
        return []
    attack_sec = max(attack_ms, 0) / 1000
    release_sec = max(release_ms, 0) / 1000
    windows = sorted(
        (
            max(track.start_sec - attack_sec, 0.0),
            min(track.start_sec + track.playback_duration_sec + release_sec, target_duration_sec),
        )
        for track in voice_tracks
    )
    merged: list[tuple[float, float]] = []
    for start_sec, end_sec in windows:
        if not merged or start_sec > merged[-1][1]:
            merged.append((start_sec, end_sec))
            continue
        merged[-1] = (merged[-1][0], max(merged[-1][1], end_sec))
    return [(round(start_sec, 3), round(end_sec, 3)) for start_sec, end_sec in merged]


def build_windowed_duck_filter_graph(*, intervals: list[tuple[float, float]], gain: float) -> str:
    filters: list[str] = []
    source_label = "0:a"
    for index, (start_sec, end_sec) in enumerate(intervals):
        target_label = f"m{index}"
        filters.append(
            f"[{source_label}]volume=volume={gain}:enable='between(t,{start_sec},{end_sec})'[{target_label}]"
        )
        source_label = target_label
    return ";".join(filters)


def build_sidechain_duck_filter_graph(*, threshold_gain: float, ratio: float, attack_ms: int, release_ms: int) -> str:
    attack = max(attack_ms, 0)
    release = max(release_ms, 0)
    normalized_ratio = max(ratio, 1.0)
    return (
        "[0:a][1:a]"
        f"sidechaincompress=threshold={threshold_gain}:ratio={normalized_ratio}:"
        f"attack={attack}:release={release}[ducked]"
    )
