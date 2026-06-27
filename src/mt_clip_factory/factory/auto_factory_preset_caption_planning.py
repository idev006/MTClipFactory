from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from mt_clip_factory.factory.auto_factory_dto import AutoFactoryProductRequestDTO
from mt_clip_factory.factory.caption_selection_support import CaptionSelectionSignature
from mt_clip_factory.factory.creative_preset_runtime import (
    CreativePresetDefinition,
    ResolvedCreativePresetSelection,
    select_creative_preset_for_assignments,
)


@dataclass(slots=True, frozen=True)
class CaptionPlanningSignatureLookup:
    default_signatures_by_slot: tuple[CaptionSelectionSignature | None, ...]
    signatures_by_preset_code: dict[str, tuple[CaptionSelectionSignature | None, ...]]
    pool_profile_signatures: tuple[CaptionSelectionSignature | None, ...]


@dataclass(slots=True, frozen=True)
class ResolvedCaptionPlanningContext:
    slot_signature: CaptionSelectionSignature | None
    creative_preset_code: str | None = None
    creative_preset_signature: str | None = None
    creative_preset_reasons: tuple[str, ...] = ()


def build_caption_planning_signature_lookup(
    *,
    resolve_signatures_for_slots,
    product_code: str,
    batch_code: str,
    planned_count: int,
    creative_preset_definitions: tuple[CreativePresetDefinition, ...],
) -> CaptionPlanningSignatureLookup:
    default_signatures_by_slot = resolve_signatures_for_slots(
        product_code=product_code,
        batch_code=batch_code,
        planned_count=planned_count,
        creative_preset_code=None,
    )
    signatures_by_preset_code = {
        definition.preset_code: resolve_signatures_for_slots(
            product_code=product_code,
            batch_code=batch_code,
            planned_count=planned_count,
            creative_preset_code=definition.preset_code,
        )
        for definition in creative_preset_definitions
    }
    return CaptionPlanningSignatureLookup(
        default_signatures_by_slot=default_signatures_by_slot,
        signatures_by_preset_code=signatures_by_preset_code,
        pool_profile_signatures=_merge_unique_signature_samples(
            default_signatures_by_slot,
            *signatures_by_preset_code.values(),
        ),
    )


def resolve_caption_planning_context(
    *,
    blueprint,
    slot_position: int,
    planned_count: int,
    product_request: AutoFactoryProductRequestDTO,
    creative_preset_definitions: tuple[CreativePresetDefinition, ...],
    selected_preset_counts: Counter[str],
    selected_preset_last_slots: dict[str, int],
    signature_lookup: CaptionPlanningSignatureLookup,
) -> ResolvedCaptionPlanningContext:
    creative_preset_selection = select_creative_preset_for_assignments(
        assignments=blueprint.assignments,
        mode=product_request.creative_preset_mode,
        requested_codes=product_request.creative_preset_codes,
        definitions=creative_preset_definitions,
        target_platform=blueprint.target_platform,
        target_ratio=blueprint.target_ratio,
        duration_sec=blueprint.duration_sec,
        selected_preset_counts=selected_preset_counts,
        selected_preset_last_slots=selected_preset_last_slots,
        slot_position=slot_position,
        planned_count=planned_count,
    )
    if creative_preset_selection is None:
        return ResolvedCaptionPlanningContext(
            slot_signature=_signature_for_slot(signature_lookup.default_signatures_by_slot, slot_position=slot_position),
        )
    return _resolved_context_for_preset_selection(
        creative_preset_selection,
        signature_lookup=signature_lookup,
        slot_position=slot_position,
    )


def _resolved_context_for_preset_selection(
    creative_preset_selection: ResolvedCreativePresetSelection,
    *,
    signature_lookup: CaptionPlanningSignatureLookup,
    slot_position: int,
) -> ResolvedCaptionPlanningContext:
    preset_signatures = signature_lookup.signatures_by_preset_code.get(
        creative_preset_selection.preset_code,
        signature_lookup.default_signatures_by_slot,
    )
    return ResolvedCaptionPlanningContext(
        slot_signature=_signature_for_slot(preset_signatures, slot_position=slot_position),
        creative_preset_code=creative_preset_selection.preset_code,
        creative_preset_signature=creative_preset_selection.preset_signature,
        creative_preset_reasons=creative_preset_selection.reasons,
    )


def _signature_for_slot(
    signatures_by_slot: tuple[CaptionSelectionSignature | None, ...],
    *,
    slot_position: int,
) -> CaptionSelectionSignature | None:
    if slot_position < 0 or slot_position >= len(signatures_by_slot):
        return None
    signature = signatures_by_slot[slot_position]
    return signature if isinstance(signature, CaptionSelectionSignature) else None


def _merge_unique_signature_samples(
    *signature_groups: tuple[CaptionSelectionSignature | None, ...],
) -> tuple[CaptionSelectionSignature | None, ...]:
    merged: list[CaptionSelectionSignature | None] = []
    seen: set[tuple[tuple[str, str, str], ...]] = set()
    for signatures in signature_groups:
        for signature in signatures:
            if signature is None:
                continue
            key = signature.role_texts
            if key in seen:
                continue
            seen.add(key)
            merged.append(signature)
    return tuple(merged)
