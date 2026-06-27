from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
import tomllib

from mt_clip_factory.factory.auto_factory_dto import PlannedBatchAssetAssignmentDTO

PRESET_MODE_AUTO_BEST_FIT = "auto_best_fit"
PRESET_MODE_BALANCED_CYCLE = "balanced_cycle"
PRESET_MODE_LOCKED_PRESET = "locked_preset"
PRESET_MODE_PRESET_MIX = "preset_mix"
PRESET_MODES = (
    PRESET_MODE_AUTO_BEST_FIT,
    PRESET_MODE_BALANCED_CYCLE,
    PRESET_MODE_LOCKED_PRESET,
    PRESET_MODE_PRESET_MIX,
)


class CreativePresetContractError(ValueError):
    """Raised when a creative preset contract is invalid."""


@dataclass(slots=True, frozen=True)
class CreativePresetDefinition:
    preset_code: str
    display_name: str
    enabled: bool
    selection_weight: float
    campaign_goal: str | None = None
    tone_tags: tuple[str, ...] = ()
    platforms: tuple[str, ...] = ()
    target_ratios: tuple[str, ...] = ()
    preferred_foreground_tags: tuple[str, ...] = ()
    preferred_background_tags: tuple[str, ...] = ()
    preferred_voice_tags: tuple[str, ...] = ()
    preferred_music_tags: tuple[str, ...] = ()
    headline_pool_names: tuple[str, ...] = ()
    cta_pool_names: tuple[str, ...] = ()
    main_style_preset: str | None = None
    sub_style_preset: str | None = None
    caption_density: str | None = None
    segment_profile: str | None = None
    preferred_duration_sec: float | None = None
    cooldown_outputs: int = 0
    max_batch_share: float | None = None
    pair_rotation_bias: float = 1.0
    force_fresh_background_before_repeat: bool = False
    force_fresh_headline_before_repeat: bool = False


@dataclass(slots=True, frozen=True)
class ResolvedCreativePresetSelection:
    preset_code: str
    preset_signature: str
    reasons: tuple[str, ...]


def parse_creative_preset_contract_text(
    raw_text: str,
    *,
    source_name: str,
) -> tuple[CreativePresetDefinition, ...]:
    try:
        data = tomllib.loads(raw_text)
    except tomllib.TOMLDecodeError as exc:
        raise CreativePresetContractError(f"Invalid creative_presets.toml for {source_name}: {exc}") from exc
    if not isinstance(data, dict):
        raise CreativePresetContractError(f"Invalid creative_presets.toml for {source_name}: root object must be a table.")
    presets_section = data.get("presets")
    if not isinstance(presets_section, dict):
        raise CreativePresetContractError(
            f"Invalid creative_presets.toml for {source_name}: missing [presets] table."
        )

    definitions: list[CreativePresetDefinition] = []
    for preset_code, section in sorted(presets_section.items()):
        if not isinstance(section, dict):
            raise CreativePresetContractError(
                f"Invalid creative_presets.toml for {source_name}: [presets.{preset_code}] must be a table."
            )
        normalized_code = _normalize_code(str(preset_code))
        if not normalized_code:
            raise CreativePresetContractError(
                f"Invalid creative_presets.toml for {source_name}: preset code {preset_code!r} is invalid."
            )
        selection_weight = _optional_float(section.get("selection_weight"), default=1.0)
        if selection_weight <= 0:
            raise CreativePresetContractError(
                f"Invalid creative_presets.toml for {source_name}: selection_weight for {normalized_code} must be > 0."
            )
        cooldown_outputs = _optional_int(section.get("cooldown_outputs"), default=0)
        if cooldown_outputs < 0:
            raise CreativePresetContractError(
                f"Invalid creative_presets.toml for {source_name}: cooldown_outputs for {normalized_code} must be >= 0."
            )
        max_batch_share = _optional_float(section.get("max_batch_share"))
        if max_batch_share is not None and not (0.0 < max_batch_share <= 1.0):
            raise CreativePresetContractError(
                f"Invalid creative_presets.toml for {source_name}: max_batch_share for {normalized_code} must be within (0, 1]."
            )
        definitions.append(
            CreativePresetDefinition(
                preset_code=normalized_code,
                display_name=_optional_text(section.get("display_name")) or normalized_code.replace("_", " ").title(),
                enabled=_optional_bool(section.get("enabled"), default=True),
                selection_weight=selection_weight,
                campaign_goal=_optional_text(section.get("campaign_goal")),
                tone_tags=_text_list(section.get("tone_tags")),
                platforms=_text_list(section.get("platforms")),
                target_ratios=_text_list(section.get("target_ratios")),
                preferred_foreground_tags=_text_list(section.get("preferred_foreground_tags")),
                preferred_background_tags=_text_list(section.get("preferred_background_tags")),
                preferred_voice_tags=_text_list(section.get("preferred_voice_tags")),
                preferred_music_tags=_text_list(section.get("preferred_music_tags")),
                headline_pool_names=_text_list(section.get("headline_pool_names")),
                cta_pool_names=_text_list(section.get("cta_pool_names")),
                main_style_preset=_optional_text(section.get("main_style_preset")),
                sub_style_preset=_optional_text(section.get("sub_style_preset")),
                caption_density=_optional_text(section.get("caption_density")),
                segment_profile=_optional_text(section.get("segment_profile")),
                preferred_duration_sec=_optional_float(section.get("preferred_duration_sec")),
                cooldown_outputs=cooldown_outputs,
                max_batch_share=max_batch_share,
                pair_rotation_bias=_optional_float(section.get("pair_rotation_bias"), default=1.0),
                force_fresh_background_before_repeat=_optional_bool(
                    section.get("force_fresh_background_before_repeat"),
                    default=False,
                ),
                force_fresh_headline_before_repeat=_optional_bool(
                    section.get("force_fresh_headline_before_repeat"),
                    default=False,
                ),
            )
        )
    return tuple(definitions)


def select_creative_preset_for_assignments(
    *,
    assignments: tuple[PlannedBatchAssetAssignmentDTO, ...],
    mode: str,
    requested_codes: tuple[str, ...],
    definitions: tuple[CreativePresetDefinition, ...],
    target_platform: str | None,
    target_ratio: str | None,
    duration_sec: float | None,
    selected_preset_counts: Counter,
    selected_preset_last_slots: dict[str, int],
    slot_position: int,
    planned_count: int,
) -> ResolvedCreativePresetSelection | None:
    if mode not in PRESET_MODES:
        raise CreativePresetContractError(f"Unsupported creative preset mode: {mode}")
    eligible = _eligible_presets(
        definitions=definitions,
        requested_codes=requested_codes,
        target_platform=target_platform,
        target_ratio=target_ratio,
    )
    if not eligible:
        if requested_codes:
            raise CreativePresetContractError(
                f"No eligible creative presets matched requested codes: {', '.join(requested_codes)}"
            )
        return None
    best = max(
        eligible,
        key=lambda definition: _preset_selection_score(
            definition,
            assignments=assignments,
            mode=mode,
            selected_preset_counts=selected_preset_counts,
            selected_preset_last_slots=selected_preset_last_slots,
            slot_position=slot_position,
            planned_count=planned_count,
            duration_sec=duration_sec,
        ),
    )
    reasons = _selection_reasons(
        best,
        assignments=assignments,
        mode=mode,
        selected_preset_counts=selected_preset_counts,
        duration_sec=duration_sec,
    )
    return ResolvedCreativePresetSelection(
        preset_code=best.preset_code,
        preset_signature=_preset_signature(best),
        reasons=reasons,
    )


def summarize_creative_preset_contract(
    definitions: tuple[CreativePresetDefinition, ...],
) -> dict[str, object]:
    platform_labels = {
        platform
        for definition in definitions
        for platform in definition.platforms
    }
    ratio_labels = {
        ratio
        for definition in definitions
        for ratio in definition.target_ratios
    }
    headline_pool_names = {
        pool_name
        for definition in definitions
        for pool_name in definition.headline_pool_names
    }
    return {
        "preset_count": len(definitions),
        "enabled_preset_count": sum(1 for definition in definitions if definition.enabled),
        "preset_codes": tuple(definition.preset_code for definition in definitions),
        "platform_count": len(platform_labels),
        "ratio_count": len(ratio_labels),
        "headline_pool_name_count": len(headline_pool_names),
    }


def _eligible_presets(
    *,
    definitions: tuple[CreativePresetDefinition, ...],
    requested_codes: tuple[str, ...],
    target_platform: str | None,
    target_ratio: str | None,
) -> tuple[CreativePresetDefinition, ...]:
    requested = frozenset(_normalize_code(code) for code in requested_codes if _normalize_code(code))
    eligible: list[CreativePresetDefinition] = []
    for definition in definitions:
        if not definition.enabled:
            continue
        if requested and definition.preset_code not in requested:
            continue
        if definition.platforms and target_platform and target_platform not in definition.platforms:
            continue
        if definition.target_ratios and target_ratio and target_ratio not in definition.target_ratios:
            continue
        eligible.append(definition)
    return tuple(eligible)


def _preset_selection_score(
    definition: CreativePresetDefinition,
    *,
    assignments: tuple[PlannedBatchAssetAssignmentDTO, ...],
    mode: str,
    selected_preset_counts: Counter,
    selected_preset_last_slots: dict[str, int],
    slot_position: int,
    planned_count: int,
    duration_sec: float | None,
) -> tuple[float, float, str]:
    score = definition.selection_weight * 100.0
    score += _preferred_tag_fit_score(definition, assignments=assignments)
    score += _duration_fit_score(definition, duration_sec=duration_sec)
    if mode in {PRESET_MODE_BALANCED_CYCLE, PRESET_MODE_PRESET_MIX}:
        score -= float(selected_preset_counts[definition.preset_code]) * 60.0
    elif mode == PRESET_MODE_AUTO_BEST_FIT:
        score -= float(selected_preset_counts[definition.preset_code]) * 18.0
    elif mode == PRESET_MODE_LOCKED_PRESET:
        score += 200.0
    last_slot = selected_preset_last_slots.get(definition.preset_code)
    if last_slot is not None and definition.cooldown_outputs > 0:
        distance = slot_position - last_slot
        if distance <= definition.cooldown_outputs:
            score -= 150.0 * float(definition.cooldown_outputs - distance + 1)
    if definition.max_batch_share is not None and planned_count > 0:
        projected_share = float(selected_preset_counts[definition.preset_code] + 1) / float(planned_count)
        if projected_share > definition.max_batch_share:
            score -= 200.0 * float(projected_share - definition.max_batch_share)
    return score, definition.selection_weight, definition.preset_code


def _preferred_tag_fit_score(
    definition: CreativePresetDefinition,
    *,
    assignments: tuple[PlannedBatchAssetAssignmentDTO, ...],
) -> float:
    score = 0.0
    for assignment in assignments:
        preferred_tags = _preferred_tags_for_role(definition, role_name=assignment.role)
        if not preferred_tags:
            continue
        matched = sum(1 for tag in preferred_tags if tag in assignment.tag_labels)
        score += float(matched) * 22.0
        if matched == 0:
            score -= 12.0
    return score


def _duration_fit_score(definition: CreativePresetDefinition, *, duration_sec: float | None) -> float:
    if duration_sec is None or definition.preferred_duration_sec is None:
        return 0.0
    delta = abs(float(duration_sec) - float(definition.preferred_duration_sec))
    return max(0.0, 14.0 - (delta * 2.0))


def _selection_reasons(
    definition: CreativePresetDefinition,
    *,
    assignments: tuple[PlannedBatchAssetAssignmentDTO, ...],
    mode: str,
    selected_preset_counts: Counter,
    duration_sec: float | None,
) -> tuple[str, ...]:
    reasons = [f"preset_mode:{mode}", f"preset_code:{definition.preset_code}"]
    if selected_preset_counts[definition.preset_code] <= 0:
        reasons.append("fresh_preset_in_batch")
    matched_roles = [
        assignment.role
        for assignment in assignments
        if _preferred_tags_for_role(definition, role_name=assignment.role)
        and any(tag in assignment.tag_labels for tag in _preferred_tags_for_role(definition, role_name=assignment.role))
    ]
    if matched_roles:
        reasons.append(f"tag_fit:{'/'.join(sorted(dict.fromkeys(matched_roles)))}")
    if duration_sec is not None and definition.preferred_duration_sec is not None:
        if abs(float(duration_sec) - float(definition.preferred_duration_sec)) <= 2.0:
            reasons.append("duration_fit")
    return tuple(reasons[:6])


def _preset_signature(definition: CreativePresetDefinition) -> str:
    parts = [
        definition.preset_code,
        definition.segment_profile or "-",
        definition.caption_density or "-",
        ",".join(definition.headline_pool_names) or "-",
        definition.main_style_preset or "-",
        definition.sub_style_preset or "-",
    ]
    return "|".join(parts)


def _preferred_tags_for_role(definition: CreativePresetDefinition, *, role_name: str) -> tuple[str, ...]:
    mapping = {
        "foreground": definition.preferred_foreground_tags,
        "background": definition.preferred_background_tags,
        "voice": definition.preferred_voice_tags,
        "music": definition.preferred_music_tags,
    }
    return mapping.get(role_name, ())


def _normalize_code(value: str) -> str:
    normalized = "".join(character if character.isalnum() or character == "_" else "_" for character in value.strip().lower())
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _text_list(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise CreativePresetContractError("Expected a TOML list of text values.")
    normalized: list[str] = []
    for item in value:
        item_text = _optional_text(item)
        if item_text:
            normalized.append(item_text)
    return tuple(dict.fromkeys(normalized))


def _optional_bool(value: object, *, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise CreativePresetContractError("Expected a TOML boolean value.")
    return value


def _optional_float(value: object, *, default: float | None = None) -> float | None:
    if value is None:
        return default
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise CreativePresetContractError("Expected a TOML numeric value.")
    return float(value)


def _optional_int(value: object, *, default: int) -> int:
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool):
        raise CreativePresetContractError("Expected a TOML integer value.")
    return value
