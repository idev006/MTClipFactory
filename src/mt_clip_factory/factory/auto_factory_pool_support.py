from __future__ import annotations

from mt_clip_factory.factory.auto_factory_dto import AutoFactoryProductRequestDTO
from mt_clip_factory.factory.auto_factory_planning_support import _SEMANTIC_VISUAL_ROLES
from mt_clip_factory.library.dto import AssetSummaryDTO


def _foreground_sequence_from_recipe_items(recipe_items) -> tuple[int, ...]:
    explicit_foreground = tuple(
        item.asset_id
        for item in recipe_items
        if item.role.strip().lower() == "foreground"
    )
    if explicit_foreground:
        asset_id = explicit_foreground[0]
        return tuple(asset_id for _ in _SEMANTIC_VISUAL_ROLES)
    role_to_asset_id = {
        item.role.strip().lower(): item.asset_id
        for item in recipe_items
        if item.role.strip().lower() in _SEMANTIC_VISUAL_ROLES
    }
    return tuple(role_to_asset_id[role] for role in _SEMANTIC_VISUAL_ROLES if role in role_to_asset_id)


def _resolve_required_visual_shortfall_reason(
    *,
    foreground_assets: tuple[AssetSummaryDTO, ...],
    background_assets: tuple[AssetSummaryDTO, ...],
    all_foreground_assets: tuple[AssetSummaryDTO, ...],
    all_background_assets: tuple[AssetSummaryDTO, ...],
    product_request: AutoFactoryProductRequestDTO,
) -> str:
    reasons: list[str] = []
    foreground_reason = _resolve_missing_visual_reason(
        asset_label="foreground",
        filtered_assets=foreground_assets,
        all_assets=all_foreground_assets,
        required_tag_labels=product_request.foreground_required_tag_labels,
    )
    if foreground_reason is not None:
        reasons.append(foreground_reason)
    background_reason = _resolve_missing_visual_reason(
        asset_label="background",
        filtered_assets=background_assets,
        all_assets=all_background_assets,
        required_tag_labels=product_request.background_required_tag_labels,
    )
    if background_reason is not None:
        reasons.append(background_reason)
    return "; ".join(reasons)


def _filter_assets_by_required_tags(
    assets: tuple[AssetSummaryDTO, ...],
    required_tag_labels: tuple[str, ...],
) -> tuple[AssetSummaryDTO, ...]:
    if not required_tag_labels:
        return assets
    required = {label.strip().casefold() for label in required_tag_labels if label.strip()}
    if not required:
        return assets
    filtered_assets: list[AssetSummaryDTO] = []
    for asset in assets:
        asset_tags = {label.strip().casefold() for label in asset.tag_labels if label.strip()}
        if required.issubset(asset_tags):
            filtered_assets.append(asset)
    return tuple(filtered_assets)


def _resolve_missing_visual_reason(
    *,
    asset_label: str,
    filtered_assets: tuple[AssetSummaryDTO, ...],
    all_assets: tuple[AssetSummaryDTO, ...],
    required_tag_labels: tuple[str, ...],
) -> str | None:
    if filtered_assets:
        return None
    if required_tag_labels and all_assets:
        return f"no ready {asset_label} assets matched required tag filters"
    return f"no ready {asset_label} assets for persistent foreground/background clip policy"
