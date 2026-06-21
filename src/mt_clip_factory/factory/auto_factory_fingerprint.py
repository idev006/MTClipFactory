from __future__ import annotations

from collections.abc import Sequence
from hashlib import sha256

from mt_clip_factory.factory.auto_factory_dto import PlannedBatchAssetAssignmentDTO
from mt_clip_factory.factory.dto import RecipeItemDTO


def build_planned_recipe_fingerprint(
    *,
    product_code: str,
    target_platform: str | None,
    target_ratio: str | None,
    duration_source: str,
    duration_sec: float | None,
    assignments: Sequence[PlannedBatchAssetAssignmentDTO],
) -> str:
    grouped_assignments = [
        f"{assignment.role}:{assignment.asset_id}"
        for assignment in sorted(assignments, key=lambda item: (item.role, item.asset_id, item.asset_code))
    ]
    fingerprint_parts = (
        product_code,
        target_platform or "",
        target_ratio or "",
        duration_source,
        "" if duration_sec is None else f"{duration_sec:.3f}",
        *grouped_assignments,
    )
    return "|".join(fingerprint_parts)


def build_planned_recipe_fingerprint_hash(
    *,
    product_code: str,
    target_platform: str | None,
    target_ratio: str | None,
    duration_sec: float | None,
    assignments: Sequence[PlannedBatchAssetAssignmentDTO],
) -> str:
    role_asset_pairs = tuple((assignment.role, assignment.asset_id) for assignment in assignments)
    return build_recipe_fingerprint_hash(
        product_code=product_code,
        target_platform=target_platform,
        target_ratio=target_ratio,
        duration_sec=duration_sec,
        role_asset_pairs=role_asset_pairs,
    )


def build_history_recipe_fingerprint_hash(
    *,
    product_code: str,
    target_platform: str | None,
    target_ratio: str | None,
    duration_sec: float | None,
    items: Sequence[RecipeItemDTO],
) -> str:
    role_asset_pairs = tuple((item.role, item.asset_id) for item in items)
    return build_recipe_fingerprint_hash(
        product_code=product_code,
        target_platform=target_platform,
        target_ratio=target_ratio,
        duration_sec=duration_sec,
        role_asset_pairs=role_asset_pairs,
    )


def build_recipe_fingerprint_hash(
    *,
    product_code: str,
    target_platform: str | None,
    target_ratio: str | None,
    duration_sec: float | None,
    role_asset_pairs: Sequence[tuple[str, int]],
) -> str:
    normalized_pairs = tuple(
        sorted(
            (role.strip().lower(), asset_id)
            for role, asset_id in role_asset_pairs
            if role.strip()
        )
    )
    fingerprint_basis_parts = (
        product_code.strip().lower(),
        (target_platform or "").strip().lower(),
        (target_ratio or "").strip().lower(),
        "" if duration_sec is None else f"{float(duration_sec):.3f}",
        *(f"{role}:{asset_id}" for role, asset_id in normalized_pairs),
    )
    fingerprint_basis = "|".join(fingerprint_basis_parts)
    return sha256(fingerprint_basis.encode("utf-8")).hexdigest()
