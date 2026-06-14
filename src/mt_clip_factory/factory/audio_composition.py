from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mt_clip_factory.domain.assets import Asset
from mt_clip_factory.domain.composition_plans import CompositionPlan
from mt_clip_factory.factory.automation_policy import ProductAutomationFillPolicies, default_fill_policies


@dataclass(slots=True, frozen=True)
class PreviewAudioTrack:
    sequence_index: int
    layer_name: str
    asset_id: int
    asset_code: str
    source_file: Path
    start_sec: float
    playback_duration_sec: float
    source_duration_sec: float | None
    fill_mode: str


@dataclass(slots=True, frozen=True)
class PreviewAudioMixPlan:
    target_duration_sec: float
    voice_tracks: tuple[PreviewAudioTrack, ...]
    music_tracks: tuple[PreviewAudioTrack, ...]


def build_audio_mix_plan(
    plan: CompositionPlan,
    assets: dict[int, Asset],
    *,
    fill_policies: ProductAutomationFillPolicies | None = None,
) -> PreviewAudioMixPlan | None:
    target_duration_sec = round(plan.resolved_duration_sec or 0.0, 3)
    if target_duration_sec <= 0:
        return None
    policies = fill_policies or default_fill_policies()
    voice_tracks = _build_tracks(
        _resolve_assignment_assets(plan, assets, layer_name="primary_voice"),
        layer_name="primary_voice",
        target_duration_sec=target_duration_sec,
        no_loop_fill_mode=policies.voiceover.shortfall_mode if policies.voiceover.shortfall_mode == "review_if_short" else "no_loop",
    )
    music_tracks = _build_tracks(
        _resolve_assignment_assets(plan, assets, layer_name="background_music"),
        layer_name="background_music",
        target_duration_sec=target_duration_sec,
        no_loop_fill_mode="sequence_fill",
    )
    if not voice_tracks and not music_tracks:
        return None
    return PreviewAudioMixPlan(
        target_duration_sec=target_duration_sec,
        voice_tracks=voice_tracks,
        music_tracks=music_tracks,
    )


def _resolve_assignment_assets(
    plan: CompositionPlan,
    assets: dict[int, Asset],
    *,
    layer_name: str,
) -> tuple[Asset, ...]:
    for assignment in plan.layer_assignments:
        if assignment.layer_name != layer_name:
            continue
        return tuple(
            asset
            for asset_id in assignment.asset_ids
            for asset in [assets.get(asset_id)]
            if asset is not None
        )
    return ()


def _build_tracks(
    layer_assets: tuple[Asset, ...],
    *,
    layer_name: str,
    target_duration_sec: float,
    no_loop_fill_mode: str,
) -> tuple[PreviewAudioTrack, ...]:
    tracks: list[PreviewAudioTrack] = []
    cursor = 0.0
    for sequence_index, asset in enumerate(layer_assets, start=1):
        remaining_duration_sec = round(target_duration_sec - cursor, 3)
        if remaining_duration_sec <= 0:
            break
        playback_duration_sec = _resolve_playback_duration(asset.duration_sec, remaining_duration_sec)
        if playback_duration_sec <= 0:
            continue
        fill_mode = _resolve_fill_mode(
            source_duration_sec=asset.duration_sec,
            playback_duration_sec=playback_duration_sec,
            no_loop_fill_mode=no_loop_fill_mode,
        )
        tracks.append(
            PreviewAudioTrack(
                sequence_index=sequence_index,
                layer_name=layer_name,
                asset_id=asset.id or 0,
                asset_code=asset.asset_code,
                source_file=Path(asset.file_path),
                start_sec=round(cursor, 3),
                playback_duration_sec=playback_duration_sec,
                source_duration_sec=asset.duration_sec,
                fill_mode=fill_mode,
            )
        )
        cursor = round(cursor + playback_duration_sec, 3)
    return tuple(tracks)


def _resolve_playback_duration(source_duration_sec: float | None, remaining_duration_sec: float) -> float:
    if remaining_duration_sec <= 0:
        return 0.0
    if source_duration_sec is None or source_duration_sec <= 0:
        return round(remaining_duration_sec, 3)
    return round(min(source_duration_sec, remaining_duration_sec), 3)


def _resolve_fill_mode(
    *,
    source_duration_sec: float | None,
    playback_duration_sec: float,
    no_loop_fill_mode: str,
) -> str:
    if source_duration_sec is None or source_duration_sec <= 0:
        return "duration_unknown"
    if source_duration_sec > playback_duration_sec:
        return "trim_to_timeline"
    return no_loop_fill_mode
