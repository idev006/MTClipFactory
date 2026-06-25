from __future__ import annotations

from collections import Counter
from math import gcd

from mt_clip_factory.factory.auto_factory_planning_support import _PlanningHistory, _SEMANTIC_VISUAL_ROLES
from mt_clip_factory.library.dto import AssetSummaryDTO

_MIN_CANDIDATE_SCAN = 64
_CANDIDATE_SCAN_MULTIPLIER = 24
_MAX_CANDIDATE_SCAN = 4096
_PERMUTATION_PRIMES = (11, 13, 17, 19)


def _resolve_candidate_scan_limit(*, planned_count: int, feasible_count: int) -> int:
    bounded_scan = max(_MIN_CANDIDATE_SCAN, planned_count * _CANDIDATE_SCAN_MULTIPLIER, planned_count)
    return min(feasible_count, _MAX_CANDIDATE_SCAN, bounded_scan)


def _enumerate_variant_dimension_selections(
    *,
    limit: int,
    sequence_options: tuple[tuple[int, ...], ...],
    background_options: tuple[AssetSummaryDTO | None, ...],
    music_options: tuple[AssetSummaryDTO | None, ...],
    voice_options: tuple[AssetSummaryDTO | None, ...],
) -> tuple[dict[str, object], ...]:
    dimension_options: dict[str, tuple[object, ...]] = {
        "foreground_sequence": sequence_options,
        "background": background_options,
        "music": music_options,
        "voice": voice_options,
    }
    axis_names = ("foreground_sequence", "background", "music", "voice")
    axis_sizes = tuple(len(dimension_options[name]) for name in axis_names)
    total_coordinates = 1
    for axis_size in axis_sizes:
        total_coordinates *= axis_size
    if total_coordinates <= 0:
        return ()

    permutation_limit = min(limit, total_coordinates)
    start = _permutation_start(total_coordinates, axis_sizes)
    step = _permutation_step(total_coordinates, axis_sizes)
    coordinates = [
        _rank_to_coordinate((start + (offset * step)) % total_coordinates, axis_sizes)
        for offset in range(permutation_limit)
    ]
    return tuple(
        {
            axis_name: dimension_options[axis_name][coordinate[axis_index]]
            for axis_index, axis_name in enumerate(axis_names)
        }
        for coordinate in coordinates
    )


def _order_role_assets_for_diversity_frontier(
    assets: tuple[AssetSummaryDTO, ...],
    *,
    role_name: str,
    planning_history: _PlanningHistory,
) -> tuple[AssetSummaryDTO, ...]:
    return tuple(
        sorted(
            assets,
            key=lambda asset: float(planning_history.role_asset_weights[(role_name, asset.asset_id)]),
        )
    )


def _order_foreground_sequences_for_diversity_frontier(
    sequences: tuple[tuple[int, ...], ...],
    *,
    planning_history: _PlanningHistory,
) -> tuple[tuple[int, ...], ...]:
    return tuple(
        sorted(
            sequences,
            key=lambda sequence: (
                float(planning_history.foreground_sequence_weights[sequence]),
                _foreground_sequence_role_reuse_pressure(sequence, planning_history=planning_history),
                _foreground_sequence_internal_repeat_count(sequence),
            ),
        )
    )


def _build_persistent_foreground_sequences(
    asset_ids: tuple[int, ...],
    *,
    role_count: int,
) -> tuple[tuple[int, ...], ...]:
    if not asset_ids:
        return ()
    return tuple(tuple(asset_id for _ in range(role_count)) for asset_id in asset_ids)


def _foreground_sequence_role_reuse_pressure(
    sequence: tuple[int, ...],
    *,
    planning_history: _PlanningHistory,
) -> float:
    return sum(
        float(planning_history.role_asset_weights[(role_name, asset_id)])
        for role_name, asset_id in zip(_SEMANTIC_VISUAL_ROLES, sequence)
    )


def _foreground_sequence_internal_repeat_count(sequence: tuple[int, ...]) -> int:
    if len(set(sequence)) <= 1:
        return 0
    counts = Counter(sequence)
    return sum(max(0, count - 1) for count in counts.values())


def _rank_to_coordinate(rank: int, axis_sizes: tuple[int, ...]) -> tuple[int, ...]:
    coordinate: list[int] = []
    remaining = rank
    for axis_size in axis_sizes:
        coordinate.append(remaining % axis_size)
        remaining //= axis_size
    return tuple(coordinate)


def _permutation_start(total_coordinates: int, axis_sizes: tuple[int, ...]) -> int:
    if total_coordinates <= 1:
        return 0
    return sum((axis_index + 3) * axis_size * axis_size for axis_index, axis_size in enumerate(axis_sizes)) % total_coordinates


def _permutation_step(total_coordinates: int, axis_sizes: tuple[int, ...]) -> int:
    if total_coordinates <= 1:
        return 1
    candidate = sum(axis_size * prime for axis_size, prime in zip(axis_sizes, _PERMUTATION_PRIMES, strict=False))
    candidate = candidate % total_coordinates
    if candidate in {0, 1}:
        candidate = max(2, (total_coordinates // 2) | 1)
    while gcd(candidate, total_coordinates) != 1:
        candidate += 1
    return candidate
