from __future__ import annotations

from mt_clip_factory.factory.creative_preset_runtime import CreativePresetDefinition


DEFAULT_SIGNATURE_SEGMENT_TYPES = ("hook", "problem", "benefit", "proof", "cta")

_SEGMENT_PROFILE_TYPES: dict[str, tuple[str, ...]] = {
    "hook_benefit_cta": ("hook", "benefit", "cta"),
    "benefit_proof_cta": ("benefit", "proof", "cta"),
    "proof_focus": ("proof", "benefit", "cta"),
    "benefit_cta": ("benefit", "cta"),
}


def resolve_segment_profile_types(
    *,
    segment_profile: str | None,
    available_segment_types: tuple[str, ...] | None = None,
) -> tuple[str, ...] | None:
    normalized_profile = _normalize_optional_text(segment_profile)
    if normalized_profile is None:
        return None
    profile_types = _SEGMENT_PROFILE_TYPES.get(normalized_profile)
    if profile_types is None:
        return None
    if available_segment_types is None:
        return profile_types
    allowed = {segment_type.casefold() for segment_type in available_segment_types}
    return tuple(segment_type for segment_type in profile_types if segment_type in allowed)


def resolve_signature_segment_types(
    *,
    requested_segment_types: tuple[str, ...] | None,
    configured_segment_types: tuple[str, ...],
    creative_preset: CreativePresetDefinition | None,
) -> tuple[str, ...]:
    if requested_segment_types is not None:
        return tuple(segment_type.casefold() for segment_type in requested_segment_types)
    if creative_preset is not None:
        preset_segment_types = resolve_segment_profile_types(
            segment_profile=creative_preset.segment_profile,
            available_segment_types=configured_segment_types,
        )
        if preset_segment_types:
            return preset_segment_types
    allowed = set(configured_segment_types)
    return tuple(segment_type for segment_type in DEFAULT_SIGNATURE_SEGMENT_TYPES if segment_type in allowed)


def role_enabled_for_density(
    *,
    segment_type: str,
    role: str,
    creative_preset: CreativePresetDefinition | None,
) -> bool:
    if role.casefold() != "sub":
        return True
    density = _normalize_optional_text(
        None if creative_preset is None else creative_preset.caption_density,
    )
    if density in {None, "dense"}:
        return True
    if density == "light":
        return False
    if density == "medium":
        return segment_type.casefold() not in {"hook", "problem"}
    return True


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    return normalized or None
