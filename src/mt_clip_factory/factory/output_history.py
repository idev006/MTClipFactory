from __future__ import annotations

from collections.abc import Mapping

OUTPUT_HISTORY_SCOPE_APPROVED = "approved_output"
OUTPUT_HISTORY_SCOPE_AUTOMATION = "auto_factory_preview"
OUTPUT_HISTORY_SCOPE_DRAFT = "draft_preview"

AUTOMATION_OUTPUT_SOURCE_MODES = frozenset({"auto_factory_folder", "folder_control_surface"})
USABLE_OUTPUT_HISTORY_SCOPES = (
    OUTPUT_HISTORY_SCOPE_APPROVED,
    OUTPUT_HISTORY_SCOPE_AUTOMATION,
)


def resolve_output_history_scope(*, approved: bool, source_mode: str | None) -> str:
    if approved:
        return OUTPUT_HISTORY_SCOPE_APPROVED
    normalized_source_mode = (source_mode or "").strip().lower()
    if normalized_source_mode in AUTOMATION_OUTPUT_SOURCE_MODES:
        return OUTPUT_HISTORY_SCOPE_AUTOMATION
    return OUTPUT_HISTORY_SCOPE_DRAFT


def output_history_scope_is_usable(scope: str | None) -> bool:
    return scope in USABLE_OUTPUT_HISTORY_SCOPES


def extract_clip_formula_hash(payload: Mapping[str, object]) -> str | None:
    segment_inventory = _mapping(payload.get("segment_inventory"))
    if not segment_inventory:
        composition = _mapping(payload.get("composition"))
        segment_inventory = _mapping(composition.get("segment_inventory")) if composition else None
    if not segment_inventory:
        return None
    value = segment_inventory.get("clip_formula_hash")
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None
