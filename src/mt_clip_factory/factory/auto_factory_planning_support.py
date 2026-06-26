from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace

from mt_clip_factory.factory.auto_factory_dto import PlannedBatchAssetAssignmentDTO
from mt_clip_factory.factory.caption_selection_support import CaptionSelectionSignature

_SEMANTIC_VISUAL_ROLES = ("hook", "problem", "benefit", "proof", "cta")
_SELECTION_ROLE_WEIGHTS = {
    "voice": 8.0,
    "foreground": 5.0,
    "hook": 5.0,
    "problem": 4.0,
    "benefit": 4.0,
    "proof": 4.0,
    "cta": 4.0,
    "background": 5.0,
    "music": 3.0,
}
_SIMILARITY_REASON_LIMIT = 6


@dataclass(slots=True, frozen=True)
class _VariantBlueprint:
    target_platform: str | None
    target_ratio: str | None
    duration_sec: float | None
    duration_source: str
    fingerprint: str
    fingerprint_hash: str
    assignments: tuple[PlannedBatchAssetAssignmentDTO, ...]
    assignment_signature: tuple[tuple[str, int], ...]
    foreground_sequence: tuple[int, ...]
    variant_index: int
    caption_signatures_by_slot: tuple[CaptionSelectionSignature | None, ...] = ()
    near_duplicate_score: float = 0.0
    near_duplicate_reasons: tuple[str, ...] = ()
    caption_signature: tuple[tuple[str, str, str], ...] = ()
    main_caption_signature: tuple[tuple[str, str], ...] = ()


@dataclass(slots=True, frozen=True)
class _PlanningHistory:
    exact_signature_weights: Counter
    exact_fingerprint_hashes: frozenset[str]
    foreground_sequence_weights: Counter
    role_asset_weights: Counter

    @classmethod
    def empty(cls) -> _PlanningHistory:
        return cls(
            exact_signature_weights=Counter(),
            exact_fingerprint_hashes=frozenset(),
            foreground_sequence_weights=Counter(),
            role_asset_weights=Counter(),
        )


@dataclass(slots=True, frozen=True)
class _SimilarityAssessment:
    score: float
    reasons: tuple[str, ...]


def _select_blueprints_greedily(
    candidate_blueprints: tuple[_VariantBlueprint, ...],
    *,
    planned_count: int,
    planning_history: _PlanningHistory,
) -> tuple[_VariantBlueprint, ...]:
    remaining = list(candidate_blueprints)
    selected: list[_VariantBlueprint] = []
    selected_fingerprint_hashes: set[str] = set()
    selected_exact_signature_counts: Counter = Counter()
    selected_foreground_sequence_counts: Counter = Counter()
    selected_role_asset_counts: Counter = Counter()
    selected_main_caption_counts: Counter = Counter()
    selected_headline_foreground_counts: Counter = Counter()
    selected_headline_music_counts: Counter = Counter()

    while remaining and len(selected) < planned_count:
        slot_position = len(selected)
        eligible = [
            (index, blueprint)
            for index, blueprint in enumerate(remaining)
            if blueprint.fingerprint_hash not in planning_history.exact_fingerprint_hashes
            and blueprint.fingerprint_hash not in selected_fingerprint_hashes
        ]
        if not eligible:
            break
        best_index, best_blueprint = min(
            eligible,
            key=lambda entry: _selection_score(
                entry[1],
                planning_history=planning_history,
                selected_exact_signature_counts=selected_exact_signature_counts,
                selected_foreground_sequence_counts=selected_foreground_sequence_counts,
                selected_role_asset_counts=selected_role_asset_counts,
                selected_main_caption_counts=selected_main_caption_counts,
                selected_headline_foreground_counts=selected_headline_foreground_counts,
                selected_headline_music_counts=selected_headline_music_counts,
                slot_position=slot_position,
            ),
        )
        remaining.pop(best_index)
        slot_signature = _resolve_slot_caption_signature(best_blueprint, slot_position=slot_position)
        similarity = _assess_near_duplicate(
            best_blueprint,
            planning_history=planning_history,
            selected_exact_signature_counts=selected_exact_signature_counts,
            selected_foreground_sequence_counts=selected_foreground_sequence_counts,
            selected_role_asset_counts=selected_role_asset_counts,
            selected_main_caption_counts=selected_main_caption_counts,
            selected_headline_foreground_counts=selected_headline_foreground_counts,
            selected_headline_music_counts=selected_headline_music_counts,
            slot_signature=slot_signature,
        )
        selected_blueprint = replace(
            best_blueprint,
            near_duplicate_score=similarity.score,
            near_duplicate_reasons=similarity.reasons,
            caption_signature=() if slot_signature is None else slot_signature.role_texts,
            main_caption_signature=() if slot_signature is None else slot_signature.main_role_texts,
        )
        selected.append(selected_blueprint)
        selected_fingerprint_hashes.add(selected_blueprint.fingerprint_hash)
        selected_exact_signature_counts[selected_blueprint.assignment_signature] += 1
        if selected_blueprint.foreground_sequence:
            selected_foreground_sequence_counts[selected_blueprint.foreground_sequence] += 1
        for assignment in selected_blueprint.assignments:
            selected_role_asset_counts[(assignment.role, assignment.asset_id)] += 1
        if selected_blueprint.main_caption_signature:
            selected_main_caption_counts[selected_blueprint.main_caption_signature] += 1
            foreground_asset_id = _role_asset_id(selected_blueprint, role_name="foreground")
            if foreground_asset_id is not None:
                selected_headline_foreground_counts[(selected_blueprint.main_caption_signature, foreground_asset_id)] += 1
            music_asset_id = _role_asset_id(selected_blueprint, role_name="music")
            if music_asset_id is not None:
                selected_headline_music_counts[(selected_blueprint.main_caption_signature, music_asset_id)] += 1

    return tuple(selected)


def _selection_score(
    blueprint: _VariantBlueprint,
    *,
    planning_history: _PlanningHistory,
    selected_exact_signature_counts: Counter,
    selected_foreground_sequence_counts: Counter,
    selected_role_asset_counts: Counter,
    selected_main_caption_counts: Counter,
    selected_headline_foreground_counts: Counter,
    selected_headline_music_counts: Counter,
    slot_position: int,
) -> tuple[float, int]:
    slot_signature = _resolve_slot_caption_signature(blueprint, slot_position=slot_position)
    similarity = _assess_near_duplicate(
        blueprint,
        planning_history=planning_history,
        selected_exact_signature_counts=selected_exact_signature_counts,
        selected_foreground_sequence_counts=selected_foreground_sequence_counts,
        selected_role_asset_counts=selected_role_asset_counts,
        selected_main_caption_counts=selected_main_caption_counts,
        selected_headline_foreground_counts=selected_headline_foreground_counts,
        selected_headline_music_counts=selected_headline_music_counts,
        slot_signature=slot_signature,
    )
    history_exact_penalty = float(planning_history.exact_signature_weights[blueprint.assignment_signature]) * 400.0
    selected_exact_penalty = float(selected_exact_signature_counts[blueprint.assignment_signature]) * 1000.0
    history_foreground_penalty = float(planning_history.foreground_sequence_weights[blueprint.foreground_sequence]) * 70.0
    selected_foreground_penalty = float(selected_foreground_sequence_counts[blueprint.foreground_sequence]) * 180.0
    history_role_penalty = 0.0
    selected_role_penalty = 0.0
    for assignment in blueprint.assignments:
        role_weight = _SELECTION_ROLE_WEIGHTS.get(assignment.role, 1.0)
        history_role_penalty += (
            float(planning_history.role_asset_weights[(assignment.role, assignment.asset_id)]) * role_weight
        )
        selected_role_penalty += (
            float(selected_role_asset_counts[(assignment.role, assignment.asset_id)]) * role_weight
        )
    internal_repeat_penalty = float(_foreground_internal_repeat_count(blueprint.foreground_sequence)) * 25.0
    total_penalty = (
        selected_exact_penalty
        + history_exact_penalty
        + selected_foreground_penalty
        + history_foreground_penalty
        + (selected_role_penalty * 24.0)
        + (history_role_penalty * 7.0)
        + internal_repeat_penalty
        + (similarity.score * 500.0)
    )
    return total_penalty, blueprint.variant_index


def _assess_near_duplicate(
    blueprint: _VariantBlueprint,
    *,
    planning_history: _PlanningHistory,
    selected_exact_signature_counts: Counter,
    selected_foreground_sequence_counts: Counter,
    selected_role_asset_counts: Counter,
    selected_main_caption_counts: Counter,
    selected_headline_foreground_counts: Counter,
    selected_headline_music_counts: Counter,
    slot_signature: CaptionSelectionSignature | None,
) -> _SimilarityAssessment:
    score = 0.0
    reasons: list[str] = []
    exact_reuse_count = (
        float(planning_history.exact_signature_weights[blueprint.assignment_signature])
        + float(selected_exact_signature_counts[blueprint.assignment_signature])
    )
    if exact_reuse_count > 0:
        score = 1.0
        reasons.append("exact_combo_reused")

    foreground_sequence_reuse = (
        float(planning_history.foreground_sequence_weights[blueprint.foreground_sequence])
        + float(selected_foreground_sequence_counts[blueprint.foreground_sequence])
    )
    if blueprint.foreground_sequence and foreground_sequence_reuse > 0:
        score += min(0.34 + (0.09 * max(0.0, foreground_sequence_reuse - 1.0)), 0.55)
        reasons.append("foreground_asset_reused")

    voice_reuse = _role_reuse_count(
        blueprint,
        role_name="voice",
        planning_history=planning_history,
        selected_role_asset_counts=selected_role_asset_counts,
    )
    if voice_reuse > 0:
        score += min(0.35 + (0.10 * max(0.0, voice_reuse - 1.0)), 0.55)
        reasons.append("voice_asset_overused")

    background_reuse = _role_reuse_count(
        blueprint,
        role_name="background",
        planning_history=planning_history,
        selected_role_asset_counts=selected_role_asset_counts,
    )
    if background_reuse > 0:
        score += min(0.18 + (0.06 * max(0.0, background_reuse - 1.0)), 0.30)
        reasons.append("background_asset_reused")

    music_reuse = _role_reuse_count(
        blueprint,
        role_name="music",
        planning_history=planning_history,
        selected_role_asset_counts=selected_role_asset_counts,
    )
    if music_reuse > 0:
        score += min(0.12 + (0.04 * max(0.0, music_reuse - 1.0)), 0.24)
        reasons.append("music_asset_reused")

    foreground_role_reuse = _foreground_role_reuse_count(
        blueprint,
        planning_history=planning_history,
        selected_role_asset_counts=selected_role_asset_counts,
    )
    if foreground_role_reuse >= 2:
        score += min(0.10 * foreground_role_reuse, 0.30)
        reasons.append("foreground_role_assets_reused")

    internal_repeat_count = _foreground_internal_repeat_count(blueprint.foreground_sequence)
    if internal_repeat_count > 0:
        score += min(0.08 * internal_repeat_count, 0.16)
        reasons.append("foreground_sequence_internal_repeats")

    main_caption_reuse = _main_caption_reuse_count(
        slot_signature=slot_signature,
        selected_main_caption_counts=selected_main_caption_counts,
    )
    if main_caption_reuse > 0:
        score += min(0.14 + (0.04 * max(0.0, main_caption_reuse - 1.0)), 0.24)
        reasons.append("headline_reused")

    headline_foreground_reuse = _headline_combo_reuse_count(
        blueprint,
        slot_signature=slot_signature,
        role_name="foreground",
        selected_combo_counts=selected_headline_foreground_counts,
    )
    if headline_foreground_reuse > 0:
        score += min(0.24 + (0.06 * max(0.0, headline_foreground_reuse - 1.0)), 0.36)
        reasons.append("headline_foreground_combo_reused")

    headline_music_reuse = _headline_combo_reuse_count(
        blueprint,
        slot_signature=slot_signature,
        role_name="music",
        selected_combo_counts=selected_headline_music_counts,
    )
    if headline_music_reuse > 0:
        score += min(0.10 + (0.04 * max(0.0, headline_music_reuse - 1.0)), 0.18)
        reasons.append("headline_music_combo_reused")

    unique_reasons = tuple(dict.fromkeys(reasons))
    return _SimilarityAssessment(
        score=round(min(1.0, score), 3),
        reasons=unique_reasons[:_SIMILARITY_REASON_LIMIT],
    )


def _role_reuse_count(
    blueprint: _VariantBlueprint,
    *,
    role_name: str,
    planning_history: _PlanningHistory,
    selected_role_asset_counts: Counter,
) -> float:
    for assignment in blueprint.assignments:
        if assignment.role != role_name:
            continue
        return (
            float(planning_history.role_asset_weights[(assignment.role, assignment.asset_id)])
            + float(selected_role_asset_counts[(assignment.role, assignment.asset_id)])
        )
    return 0.0


def _foreground_role_reuse_count(
    blueprint: _VariantBlueprint,
    *,
    planning_history: _PlanningHistory,
    selected_role_asset_counts: Counter,
) -> int:
    reused_count = 0
    for assignment in blueprint.assignments:
        if assignment.role not in _SEMANTIC_VISUAL_ROLES:
            continue
        historical = float(planning_history.role_asset_weights[(assignment.role, assignment.asset_id)])
        selected = float(selected_role_asset_counts[(assignment.role, assignment.asset_id)])
        if historical + selected > 0:
            reused_count += 1
    return reused_count


def _foreground_internal_repeat_count(sequence: tuple[int, ...]) -> int:
    if len(set(sequence)) <= 1:
        return 0
    counts = Counter(sequence)
    return sum(max(0, count - 1) for count in counts.values())


def _resolve_slot_caption_signature(
    blueprint: _VariantBlueprint,
    *,
    slot_position: int,
) -> CaptionSelectionSignature | None:
    signatures = blueprint.caption_signatures_by_slot
    if slot_position < 0 or slot_position >= len(signatures):
        return None
    signature = signatures[slot_position]
    return signature if isinstance(signature, CaptionSelectionSignature) else None


def _role_asset_id(blueprint: _VariantBlueprint, *, role_name: str) -> int | None:
    for assignment in blueprint.assignments:
        if assignment.role == role_name:
            return assignment.asset_id
    return None


def _main_caption_reuse_count(
    *,
    slot_signature: CaptionSelectionSignature | None,
    selected_main_caption_counts: Counter,
) -> float:
    if slot_signature is None or not slot_signature.main_role_texts:
        return 0.0
    return float(selected_main_caption_counts[slot_signature.main_role_texts])


def _headline_combo_reuse_count(
    blueprint: _VariantBlueprint,
    *,
    slot_signature: CaptionSelectionSignature | None,
    role_name: str,
    selected_combo_counts: Counter,
) -> float:
    if slot_signature is None or not slot_signature.main_role_texts:
        return 0.0
    asset_id = _role_asset_id(blueprint, role_name=role_name)
    if asset_id is None:
        return 0.0
    return float(selected_combo_counts[(slot_signature.main_role_texts, asset_id)])
