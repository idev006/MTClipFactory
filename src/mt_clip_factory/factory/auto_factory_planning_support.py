from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace
import math

from mt_clip_factory.factory.asset_diversity import is_collapsed_diversity_key
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
    pool_profile_caption_signatures: tuple[CaptionSelectionSignature | None, ...] = ()
    near_duplicate_score: float = 0.0
    near_duplicate_reasons: tuple[str, ...] = ()
    caption_signature: tuple[tuple[str, str, str], ...] = ()
    main_caption_signature: tuple[tuple[str, str], ...] = ()
    creative_preset_code: str | None = None
    creative_preset_signature: str | None = None
    creative_preset_reasons: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class _PlanningHistory:
    exact_signature_weights: Counter
    exact_fingerprint_hashes: frozenset[str]
    foreground_sequence_weights: Counter
    role_asset_weights: Counter
    role_family_weights: Counter = field(default_factory=Counter)

    @classmethod
    def empty(cls) -> _PlanningHistory:
        return cls(
            exact_signature_weights=Counter(),
            exact_fingerprint_hashes=frozenset(),
            foreground_sequence_weights=Counter(),
            role_asset_weights=Counter(),
            role_family_weights=Counter(),
        )


@dataclass(slots=True, frozen=True)
class _PlanningPoolProfile:
    role_asset_pool_ids: dict[str, frozenset[int]]
    role_asset_pool_sizes: dict[str, int]
    role_family_pool_keys: dict[str, frozenset[str]]
    role_family_pool_sizes: dict[str, int]
    role_family_key_asset_counts: dict[tuple[str, str], int]
    foreground_sequence_pool_size: int
    main_caption_pool_size: int
    headline_foreground_combo_pool_size: int
    headline_music_combo_pool_size: int


@dataclass(slots=True, frozen=True)
class _SimilarityAssessment:
    score: float
    reasons: tuple[str, ...]


def _select_blueprints_greedily(
    candidate_blueprints: tuple[_VariantBlueprint, ...],
    *,
    planned_count: int,
    planning_history: _PlanningHistory,
    planning_context_resolver=None,
) -> tuple[_VariantBlueprint, ...]:
    remaining = list(candidate_blueprints)
    pool_profile = _build_planning_pool_profile(candidate_blueprints)
    selected: list[_VariantBlueprint] = []
    selected_fingerprint_hashes: set[str] = set()
    selected_exact_signature_counts: Counter = Counter()
    selected_foreground_sequence_counts: Counter = Counter()
    selected_role_asset_counts: Counter = Counter()
    selected_role_family_counts: Counter = Counter()
    selected_main_caption_counts: Counter = Counter()
    selected_headline_foreground_counts: Counter = Counter()
    selected_headline_music_counts: Counter = Counter()
    selected_preset_counts: Counter = Counter()
    selected_preset_last_slots: dict[str, int] = {}

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
        eligible_with_context = [
            (
                index,
                blueprint,
                _resolve_planning_context(
                    blueprint,
                    slot_position=slot_position,
                    selected_preset_counts=selected_preset_counts,
                    selected_preset_last_slots=selected_preset_last_slots,
                    planning_context_resolver=planning_context_resolver,
                ),
            )
            for index, blueprint in eligible
        ]
        best_index, best_blueprint, best_context = min(
            eligible_with_context,
            key=lambda entry: _selection_score(
                entry[1],
                planning_history=planning_history,
                selected_exact_signature_counts=selected_exact_signature_counts,
                selected_foreground_sequence_counts=selected_foreground_sequence_counts,
                selected_role_asset_counts=selected_role_asset_counts,
                selected_role_family_counts=selected_role_family_counts,
                selected_main_caption_counts=selected_main_caption_counts,
                selected_headline_foreground_counts=selected_headline_foreground_counts,
                selected_headline_music_counts=selected_headline_music_counts,
                pool_profile=pool_profile,
                slot_position=slot_position,
                slot_signature=entry[2][0],
            ),
        )
        remaining.pop(best_index)
        similarity = _assess_near_duplicate(
            best_blueprint,
            planning_history=planning_history,
            selected_exact_signature_counts=selected_exact_signature_counts,
            selected_foreground_sequence_counts=selected_foreground_sequence_counts,
            selected_role_asset_counts=selected_role_asset_counts,
            selected_role_family_counts=selected_role_family_counts,
            selected_main_caption_counts=selected_main_caption_counts,
            selected_headline_foreground_counts=selected_headline_foreground_counts,
            selected_headline_music_counts=selected_headline_music_counts,
            pool_profile=pool_profile,
            slot_signature=best_context[0],
        )
        selected_blueprint = replace(
            best_blueprint,
            near_duplicate_score=similarity.score,
            near_duplicate_reasons=similarity.reasons,
            caption_signature=() if best_context[0] is None else best_context[0].role_texts,
            main_caption_signature=() if best_context[0] is None else best_context[0].main_role_texts,
            creative_preset_code=best_context[1],
            creative_preset_signature=best_context[2],
            creative_preset_reasons=best_context[3],
        )
        selected.append(selected_blueprint)
        selected_fingerprint_hashes.add(selected_blueprint.fingerprint_hash)
        selected_exact_signature_counts[selected_blueprint.assignment_signature] += 1
        if selected_blueprint.foreground_sequence:
            selected_foreground_sequence_counts[selected_blueprint.foreground_sequence] += 1
        for assignment in selected_blueprint.assignments:
            selected_role_asset_counts[(assignment.role, assignment.asset_id)] += 1
            if is_collapsed_diversity_key(assignment.diversity_key):
                selected_role_family_counts[(assignment.role, assignment.diversity_key)] += 1
        if selected_blueprint.main_caption_signature:
            selected_main_caption_counts[selected_blueprint.main_caption_signature] += 1
            foreground_asset_id = _role_asset_id(selected_blueprint, role_name="foreground")
            if foreground_asset_id is not None:
                selected_headline_foreground_counts[(selected_blueprint.main_caption_signature, foreground_asset_id)] += 1
            music_asset_id = _role_asset_id(selected_blueprint, role_name="music")
            if music_asset_id is not None:
                selected_headline_music_counts[(selected_blueprint.main_caption_signature, music_asset_id)] += 1
        if selected_blueprint.creative_preset_code:
            selected_preset_counts[selected_blueprint.creative_preset_code] += 1
            selected_preset_last_slots[selected_blueprint.creative_preset_code] = slot_position

    return tuple(selected)


def _selection_score(
    blueprint: _VariantBlueprint,
    *,
    planning_history: _PlanningHistory,
    selected_exact_signature_counts: Counter,
    selected_foreground_sequence_counts: Counter,
    selected_role_asset_counts: Counter,
    selected_role_family_counts: Counter,
    selected_main_caption_counts: Counter,
    selected_headline_foreground_counts: Counter,
    selected_headline_music_counts: Counter,
    pool_profile: _PlanningPoolProfile,
    slot_position: int,
    slot_signature: CaptionSelectionSignature | None,
) -> tuple[float, int]:
    similarity = _assess_near_duplicate(
        blueprint,
        planning_history=planning_history,
        selected_exact_signature_counts=selected_exact_signature_counts,
        selected_foreground_sequence_counts=selected_foreground_sequence_counts,
        selected_role_asset_counts=selected_role_asset_counts,
        selected_role_family_counts=selected_role_family_counts,
        selected_main_caption_counts=selected_main_caption_counts,
        selected_headline_foreground_counts=selected_headline_foreground_counts,
        selected_headline_music_counts=selected_headline_music_counts,
        pool_profile=pool_profile,
        slot_signature=slot_signature,
    )
    history_exact_penalty = float(planning_history.exact_signature_weights[blueprint.assignment_signature]) * 400.0
    selected_exact_penalty = float(selected_exact_signature_counts[blueprint.assignment_signature]) * 1000.0
    history_foreground_penalty = float(planning_history.foreground_sequence_weights[blueprint.foreground_sequence]) * 70.0
    selected_foreground_penalty = float(selected_foreground_sequence_counts[blueprint.foreground_sequence]) * 180.0
    history_role_penalty = 0.0
    selected_role_penalty = 0.0
    history_role_family_penalty = 0.0
    selected_role_family_penalty = 0.0
    for assignment in blueprint.assignments:
        role_weight = _SELECTION_ROLE_WEIGHTS.get(assignment.role, 1.0)
        history_role_penalty += (
            float(planning_history.role_asset_weights[(assignment.role, assignment.asset_id)]) * role_weight
        )
        selected_role_penalty += (
            float(selected_role_asset_counts[(assignment.role, assignment.asset_id)]) * role_weight
        )
        if _shared_role_diversity_key(assignment.role, assignment.diversity_key, pool_profile=pool_profile):
            history_role_family_penalty += (
                float(planning_history.role_family_weights[(assignment.role, assignment.diversity_key)]) * role_weight
            )
            selected_role_family_penalty += (
                float(selected_role_family_counts[(assignment.role, assignment.diversity_key)]) * role_weight
            )
    internal_repeat_penalty = float(_foreground_internal_repeat_count(blueprint.foreground_sequence)) * 25.0
    foreground_balance_penalty = _foreground_batch_balance_penalty(
        blueprint,
        selected_role_asset_counts=selected_role_asset_counts,
        pool_profile=pool_profile,
    )
    total_penalty = (
        selected_exact_penalty
        + history_exact_penalty
        + selected_foreground_penalty
        + history_foreground_penalty
        + (selected_role_penalty * 24.0)
        + (history_role_penalty * 7.0)
        + (selected_role_family_penalty * 42.0)
        + (history_role_family_penalty * 12.0)
        + internal_repeat_penalty
        + foreground_balance_penalty
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
    selected_role_family_counts: Counter,
    selected_main_caption_counts: Counter,
    selected_headline_foreground_counts: Counter,
    selected_headline_music_counts: Counter,
    pool_profile: _PlanningPoolProfile,
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
        score += _scaled_reuse_penalty(
            reuse_count=foreground_sequence_reuse,
            total_usage_count=_foreground_sequence_usage_total_count(
                planning_history=planning_history,
                selected_foreground_sequence_counts=selected_foreground_sequence_counts,
            ),
            pool_size=pool_profile.foreground_sequence_pool_size,
            base_penalty=0.34,
            incremental_penalty=0.09,
            max_penalty=0.55,
        )
        reasons.append("foreground_asset_reused")

    foreground_family_reuse = _role_family_reuse_count(
        blueprint,
        role_name="foreground",
        planning_history=planning_history,
        selected_role_family_counts=selected_role_family_counts,
        pool_profile=pool_profile,
    )
    if foreground_family_reuse > 0:
        score += _scaled_reuse_penalty(
            reuse_count=foreground_family_reuse,
            total_usage_count=_role_family_usage_total_count(
                role_name="foreground",
                planning_history=planning_history,
                selected_role_family_counts=selected_role_family_counts,
            ),
            pool_size=pool_profile.role_asset_pool_sizes.get("foreground", 0),
            base_penalty=0.52,
            incremental_penalty=0.12,
            max_penalty=0.78,
        )
        reasons.append("foreground_family_reused")

    voice_reuse = _role_reuse_count(
        blueprint,
        role_name="voice",
        planning_history=planning_history,
        selected_role_asset_counts=selected_role_asset_counts,
    )
    if voice_reuse > 0:
        score += _scaled_reuse_penalty(
            reuse_count=voice_reuse,
            total_usage_count=_role_usage_total_count(
                role_name="voice",
                planning_history=planning_history,
                selected_role_asset_counts=selected_role_asset_counts,
            ),
            pool_size=pool_profile.role_asset_pool_sizes.get("voice", 0),
            base_penalty=0.35,
            incremental_penalty=0.10,
            max_penalty=0.55,
        )
        reasons.append("voice_asset_overused")

    background_reuse = _role_reuse_count(
        blueprint,
        role_name="background",
        planning_history=planning_history,
        selected_role_asset_counts=selected_role_asset_counts,
    )
    if background_reuse > 0:
        score += _scaled_reuse_penalty(
            reuse_count=background_reuse,
            total_usage_count=_role_usage_total_count(
                role_name="background",
                planning_history=planning_history,
                selected_role_asset_counts=selected_role_asset_counts,
            ),
            pool_size=pool_profile.role_asset_pool_sizes.get("background", 0),
            base_penalty=0.18,
            incremental_penalty=0.06,
            max_penalty=0.30,
        )
        reasons.append("background_asset_reused")

    background_family_reuse = _role_family_reuse_count(
        blueprint,
        role_name="background",
        planning_history=planning_history,
        selected_role_family_counts=selected_role_family_counts,
        pool_profile=pool_profile,
    )
    if background_family_reuse > 0:
        score += _scaled_reuse_penalty(
            reuse_count=background_family_reuse,
            total_usage_count=_role_family_usage_total_count(
                role_name="background",
                planning_history=planning_history,
                selected_role_family_counts=selected_role_family_counts,
            ),
            pool_size=pool_profile.role_asset_pool_sizes.get("background", 0),
            base_penalty=0.26,
            incremental_penalty=0.08,
            max_penalty=0.42,
        )
        reasons.append("background_family_reused")

    music_reuse = _role_reuse_count(
        blueprint,
        role_name="music",
        planning_history=planning_history,
        selected_role_asset_counts=selected_role_asset_counts,
    )
    if music_reuse > 0:
        score += _scaled_reuse_penalty(
            reuse_count=music_reuse,
            total_usage_count=_role_usage_total_count(
                role_name="music",
                planning_history=planning_history,
                selected_role_asset_counts=selected_role_asset_counts,
            ),
            pool_size=pool_profile.role_asset_pool_sizes.get("music", 0),
            base_penalty=0.12,
            incremental_penalty=0.04,
            max_penalty=0.24,
        )
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
        score += _scaled_reuse_penalty(
            reuse_count=main_caption_reuse,
            total_usage_count=_main_caption_usage_total_count(selected_main_caption_counts),
            pool_size=pool_profile.main_caption_pool_size,
            base_penalty=0.14,
            incremental_penalty=0.04,
            max_penalty=0.24,
        )
        reasons.append("headline_reused")

    headline_foreground_reuse = _headline_combo_reuse_count(
        blueprint,
        slot_signature=slot_signature,
        role_name="foreground",
        selected_combo_counts=selected_headline_foreground_counts,
    )
    if headline_foreground_reuse > 0:
        score += _scaled_reuse_penalty(
            reuse_count=headline_foreground_reuse,
            total_usage_count=float(sum(selected_headline_foreground_counts.values())),
            pool_size=pool_profile.headline_foreground_combo_pool_size,
            base_penalty=0.24,
            incremental_penalty=0.06,
            max_penalty=0.36,
        )
        reasons.append("headline_foreground_combo_reused")

    headline_music_reuse = _headline_combo_reuse_count(
        blueprint,
        slot_signature=slot_signature,
        role_name="music",
        selected_combo_counts=selected_headline_music_counts,
    )
    if headline_music_reuse > 0:
        score += _scaled_reuse_penalty(
            reuse_count=headline_music_reuse,
            total_usage_count=float(sum(selected_headline_music_counts.values())),
            pool_size=pool_profile.headline_music_combo_pool_size,
            base_penalty=0.10,
            incremental_penalty=0.04,
            max_penalty=0.18,
        )
        reasons.append("headline_music_combo_reused")

    score = max(
        0.0,
        score
        - _foreground_balance_credit(
            blueprint,
            selected_role_asset_counts=selected_role_asset_counts,
            pool_profile=pool_profile,
        )
        - _fresh_diversity_credit(
            exact_reuse_count=exact_reuse_count,
            main_caption_reuse=main_caption_reuse,
            headline_foreground_reuse=headline_foreground_reuse,
            headline_music_reuse=headline_music_reuse,
            pool_profile=pool_profile,
            slot_signature=slot_signature,
        ),
    )

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


def _role_family_reuse_count(
    blueprint: _VariantBlueprint,
    *,
    role_name: str,
    planning_history: _PlanningHistory,
    selected_role_family_counts: Counter,
    pool_profile: _PlanningPoolProfile,
) -> float:
    diversity_key = _role_diversity_key(blueprint, role_name=role_name)
    if _shared_role_diversity_key(role_name, diversity_key, pool_profile=pool_profile) is None:
        return 0.0
    return float(planning_history.role_family_weights[(role_name, diversity_key)]) + float(
        selected_role_family_counts[(role_name, diversity_key)]
    )


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


def _resolve_planning_context(
    blueprint: _VariantBlueprint,
    *,
    slot_position: int,
    selected_preset_counts: Counter,
    selected_preset_last_slots: dict[str, int],
    planning_context_resolver,
) -> tuple[CaptionSelectionSignature | None, str | None, str | None, tuple[str, ...]]:
    if planning_context_resolver is None:
        return (_resolve_slot_caption_signature(blueprint, slot_position=slot_position), None, None, ())
    return planning_context_resolver(
        blueprint,
        slot_position,
        selected_preset_counts,
        selected_preset_last_slots,
    )


def _role_asset_id(blueprint: _VariantBlueprint, *, role_name: str) -> int | None:
    for assignment in blueprint.assignments:
        if assignment.role == role_name:
            return assignment.asset_id
    return None


def _role_diversity_key(blueprint: _VariantBlueprint, *, role_name: str) -> str | None:
    for assignment in blueprint.assignments:
        if assignment.role == role_name:
            return assignment.diversity_key
    return None


def _shared_role_diversity_key(
    role_name: str,
    diversity_key: str | None,
    *,
    pool_profile: _PlanningPoolProfile,
) -> str | None:
    if diversity_key is None:
        return None
    if pool_profile.role_family_key_asset_counts.get((role_name, diversity_key), 0) <= 1:
        return None
    return diversity_key


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


def _build_planning_pool_profile(
    candidate_blueprints: tuple[_VariantBlueprint, ...],
) -> _PlanningPoolProfile:
    role_asset_ids: dict[str, set[int]] = {}
    role_family_keys: dict[str, set[str]] = {}
    role_family_asset_ids: dict[tuple[str, str], set[int]] = {}
    foreground_sequences: set[tuple[int, ...]] = set()
    main_caption_signatures: set[tuple[tuple[str, str], ...]] = set()
    headline_foreground_combos: set[tuple[tuple[tuple[str, str], ...], int]] = set()
    headline_music_combos: set[tuple[tuple[tuple[str, str], ...], int]] = set()
    for blueprint in candidate_blueprints:
        if blueprint.foreground_sequence:
            foreground_sequences.add(blueprint.foreground_sequence)
        foreground_asset_id = _role_asset_id(blueprint, role_name="foreground")
        music_asset_id = _role_asset_id(blueprint, role_name="music")
        for assignment in blueprint.assignments:
            role_asset_ids.setdefault(assignment.role, set()).add(assignment.asset_id)
            if is_collapsed_diversity_key(assignment.diversity_key):
                role_family_keys.setdefault(assignment.role, set()).add(assignment.diversity_key)
                role_family_asset_ids.setdefault((assignment.role, assignment.diversity_key), set()).add(assignment.asset_id)
        signature_samples = blueprint.pool_profile_caption_signatures or blueprint.caption_signatures_by_slot
        for slot_signature in signature_samples:
            if slot_signature is None or not slot_signature.main_role_texts:
                continue
            main_caption_signatures.add(slot_signature.main_role_texts)
            if foreground_asset_id is not None:
                headline_foreground_combos.add((slot_signature.main_role_texts, foreground_asset_id))
            if music_asset_id is not None:
                headline_music_combos.add((slot_signature.main_role_texts, music_asset_id))
    return _PlanningPoolProfile(
        role_asset_pool_ids={role: frozenset(asset_ids) for role, asset_ids in role_asset_ids.items()},
        role_asset_pool_sizes={role: len(asset_ids) for role, asset_ids in role_asset_ids.items()},
        role_family_pool_keys={role: frozenset(keys) for role, keys in role_family_keys.items()},
        role_family_pool_sizes={role: len(keys) for role, keys in role_family_keys.items()},
        role_family_key_asset_counts={
            key: len(asset_ids)
            for key, asset_ids in role_family_asset_ids.items()
        },
        foreground_sequence_pool_size=len(foreground_sequences),
        main_caption_pool_size=len(main_caption_signatures),
        headline_foreground_combo_pool_size=len(headline_foreground_combos),
        headline_music_combo_pool_size=len(headline_music_combos),
    )


def _foreground_batch_balance_penalty(
    blueprint: _VariantBlueprint,
    *,
    selected_role_asset_counts: Counter,
    pool_profile: _PlanningPoolProfile,
) -> float:
    foreground_asset_id = _role_asset_id(blueprint, role_name="foreground")
    if foreground_asset_id is None:
        return 0.0
    foreground_pool_ids = tuple(sorted(pool_profile.role_asset_pool_ids.get("foreground", frozenset())))
    pool_size = len(foreground_pool_ids)
    if pool_size <= 1:
        return 0.0
    current_selected_count = float(selected_role_asset_counts[("foreground", foreground_asset_id)])
    selected_counts = [int(selected_role_asset_counts[("foreground", asset_id)]) for asset_id in foreground_pool_ids]
    selected_total = float(sum(selected_counts))
    projected_count = current_selected_count + 1.0
    fair_share_ceiling = _fair_share_ceiling(total_count=selected_total + 1.0, pool_size=pool_size)
    min_selected_count = min(selected_counts, default=0)
    unused_asset_count = sum(1 for count in selected_counts if count <= 0)
    penalty = 0.0
    if unused_asset_count > 0 and current_selected_count > 0:
        penalty += 1600.0
    over_fair_share = projected_count - fair_share_ceiling
    if over_fair_share > 0:
        penalty += 90.0 * over_fair_share
    ahead_of_floor = projected_count - float(min_selected_count + 1)
    if ahead_of_floor > 0:
        penalty += 60.0 * ahead_of_floor
    return penalty


def _foreground_balance_credit(
    blueprint: _VariantBlueprint,
    *,
    selected_role_asset_counts: Counter,
    pool_profile: _PlanningPoolProfile,
) -> float:
    foreground_asset_id = _role_asset_id(blueprint, role_name="foreground")
    if foreground_asset_id is None:
        return 0.0
    foreground_pool_ids = tuple(sorted(pool_profile.role_asset_pool_ids.get("foreground", frozenset())))
    pool_size = len(foreground_pool_ids)
    if pool_size <= 1:
        return 0.0
    current_selected_count = float(selected_role_asset_counts[("foreground", foreground_asset_id)])
    selected_total = float(
        sum(
            float(selected_role_asset_counts[("foreground", asset_id)])
            for asset_id in foreground_pool_ids
        )
    )
    projected_count = current_selected_count + 1.0
    fair_share_ceiling = _fair_share_ceiling(total_count=selected_total + 1.0, pool_size=pool_size)
    if current_selected_count <= 0 and selected_total < float(pool_size):
        return 0.08
    if projected_count <= fair_share_ceiling:
        return 0.04
    return 0.0


def _fair_share_ceiling(*, total_count: float, pool_size: int) -> float:
    if pool_size <= 0:
        return total_count
    return float(math.ceil(total_count / float(pool_size)))


def _scaled_reuse_penalty(
    *,
    reuse_count: float,
    total_usage_count: float,
    pool_size: int,
    base_penalty: float,
    incremental_penalty: float,
    max_penalty: float,
) -> float:
    if reuse_count <= 0:
        return 0.0
    excess_reuse = _normalized_reuse_count(
        reuse_count,
        total_usage_count=total_usage_count,
        pool_size=pool_size,
    )
    if excess_reuse > 0:
        return min(base_penalty + (incremental_penalty * max(0.0, excess_reuse - 1.0)), max_penalty)
    return base_penalty * _pool_constraint_discount(total_usage_count=total_usage_count, pool_size=pool_size)


def _normalized_reuse_count(
    reuse_count: float,
    *,
    total_usage_count: float,
    pool_size: int,
) -> float:
    if reuse_count <= 0:
        return 0.0
    if pool_size <= 0:
        return reuse_count
    balanced_baseline = int(total_usage_count // pool_size)
    return max(0.0, reuse_count - float(balanced_baseline))


def _pool_constraint_discount(*, total_usage_count: float, pool_size: int) -> float:
    if pool_size <= 0:
        return 1.0
    if total_usage_count < float(pool_size):
        return 1.0
    overflow_count = max(1.0, total_usage_count - float(pool_size) + 1.0)
    return max(0.55, float(pool_size) / (float(pool_size) + overflow_count))


def _role_usage_total_count(
    *,
    role_name: str,
    planning_history: _PlanningHistory,
    selected_role_asset_counts: Counter,
) -> float:
    historical_total = sum(
        float(count)
        for (assignment_role, _asset_id), count in planning_history.role_asset_weights.items()
        if assignment_role == role_name
    )
    selected_total = sum(
        float(count)
        for (assignment_role, _asset_id), count in selected_role_asset_counts.items()
        if assignment_role == role_name
    )
    return historical_total + selected_total


def _role_family_usage_total_count(
    *,
    role_name: str,
    planning_history: _PlanningHistory,
    selected_role_family_counts: Counter,
) -> float:
    historical_total = sum(
        float(count)
        for (assignment_role, _family_key), count in planning_history.role_family_weights.items()
        if assignment_role == role_name
    )
    selected_total = sum(
        float(count)
        for (assignment_role, _family_key), count in selected_role_family_counts.items()
        if assignment_role == role_name
    )
    return historical_total + selected_total


def _foreground_sequence_usage_total_count(
    *,
    planning_history: _PlanningHistory,
    selected_foreground_sequence_counts: Counter,
) -> float:
    return float(sum(planning_history.foreground_sequence_weights.values())) + float(
        sum(selected_foreground_sequence_counts.values())
    )


def _main_caption_usage_total_count(selected_main_caption_counts: Counter) -> float:
    return float(sum(selected_main_caption_counts.values()))


def _fresh_diversity_credit(
    *,
    exact_reuse_count: float,
    main_caption_reuse: float,
    headline_foreground_reuse: float,
    headline_music_reuse: float,
    pool_profile: _PlanningPoolProfile,
    slot_signature: CaptionSelectionSignature | None,
) -> float:
    if exact_reuse_count > 0 or slot_signature is None or not slot_signature.main_role_texts:
        return 0.0
    credit = 0.0
    if main_caption_reuse == 0 and pool_profile.main_caption_pool_size > 1:
        credit += 0.06
    if headline_foreground_reuse == 0 and pool_profile.headline_foreground_combo_pool_size > 1:
        credit += 0.08
    if headline_music_reuse == 0 and pool_profile.headline_music_combo_pool_size > 1:
        credit += 0.03
    return min(0.17, credit)
