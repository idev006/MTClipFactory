from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path


SCHEMA_NAME = "mtclipfactory_manifest"
SCHEMA_VERSION = "2.0"


def build_manifest_envelope(
    *,
    product_code: str,
    recipe_code: str,
    stage_name: str,
    target_platform: str | None,
    target_ratio: str | None,
    output_path: Path | None,
    manifest_path: Path,
    batch_code: str | None,
    run_root: Path | None,
    journal_path: Path | None,
    order_snapshot_path: Path | None,
    product_local: bool,
    payload: dict[str, object],
) -> dict[str, object]:
    composition_plan = _dict_section(payload.get("composition_plan"))
    segments = _list_section(payload.get("segments"))
    items = _list_section(payload.get("items"))
    fill_policy = _dict_section(payload.get("fill_policy"))
    captions = _dict_section(payload.get("captions"))
    review_gate = _dict_section(payload.get("review_gate"))
    audio_mix = _dict_section(payload.get("audio_mix"))
    visual_composite = _dict_section(payload.get("visual_composite"))

    envelope = dict(payload)
    envelope["manifest_meta"] = {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "manifest_kind": f"{stage_name}_render",
        "generated_at_utc": _utc_isoformat(),
    }
    envelope["artifact"] = {
        "product_code": product_code,
        "recipe_code": recipe_code,
        "stage_name": stage_name,
        "target_platform": target_platform,
        "target_ratio": target_ratio,
        "output_path": None if output_path is None else str(output_path),
        "manifest_path": str(manifest_path),
    }
    envelope["run"] = {
        "batch_code": batch_code,
        "product_local": product_local,
        "run_root": None if run_root is None else str(run_root),
        "journal_path": None if journal_path is None else str(journal_path),
        "order_snapshot_path": None if order_snapshot_path is None else str(order_snapshot_path),
    }
    envelope["composition"] = {
        "plan": composition_plan,
        "segments": segments,
        "items": items,
        "fill_policy": fill_policy,
        "captions": captions,
    }
    envelope["render"] = {
        "audio_mix": audio_mix,
        "visual_composite": visual_composite,
    }
    envelope["quality"] = {
        "review_gate": review_gate,
    }
    return envelope


def read_manifest_section(payload: dict[str, object], *, section_name: str, legacy_key: str) -> dict[str, object]:
    section = payload.get(section_name)
    if isinstance(section, dict):
        legacy = section.get(legacy_key)
        if isinstance(legacy, dict):
            return legacy
    legacy_top_level = payload.get(legacy_key)
    if isinstance(legacy_top_level, dict):
        return legacy_top_level
    return {}


def read_manifest_list(payload: dict[str, object], *, section_name: str, legacy_key: str) -> list[object]:
    section = payload.get(section_name)
    if isinstance(section, dict):
        nested = section.get(legacy_key)
        if isinstance(nested, list):
            return nested
    legacy_top_level = payload.get(legacy_key)
    if isinstance(legacy_top_level, list):
        return legacy_top_level
    return []


def _dict_section(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _list_section(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _utc_isoformat() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
