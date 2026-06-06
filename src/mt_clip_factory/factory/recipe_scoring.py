from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from mt_clip_factory.domain.assets import Asset
from mt_clip_factory.domain.enums import AssetType
from mt_clip_factory.domain.recipes import Recipe, RecipeItem


@dataclass(slots=True, frozen=True)
class RecipeScoreAssessment:
    recipe_score: float
    duplicate_risk: float
    metrics: dict[str, float | int]


def score_and_persist_recipe(
    uow,
    *,
    recipe: Recipe,
    items: Sequence[RecipeItem],
    assets: dict[int, Asset],
    review_assessment=None,
) -> RecipeScoreAssessment:
    assessment = assess_recipe_score(
        recipe=recipe,
        items=items,
        assets=assets,
        review_assessment=review_assessment,
    )
    recipe.recipe_score = assessment.recipe_score
    recipe.duplicate_risk = assessment.duplicate_risk
    uow.recipes.update(recipe)
    return assessment


def assess_recipe_score(
    *,
    recipe: Recipe,
    items: Sequence[RecipeItem],
    assets: dict[int, Asset],
    review_assessment=None,
) -> RecipeScoreAssessment:
    item_count = len(items)
    distinct_assets = len({item.asset_id for item in items})
    distinct_roles = len({item.role for item in items})
    visual_asset_count = sum(1 for item in items if _asset_type_for(item, assets) in _VISUAL_TYPES)
    voice_asset_count = sum(1 for item in items if _asset_type_for(item, assets) == AssetType.VOICEOVER.value)
    music_asset_count = sum(1 for item in items if _asset_type_for(item, assets) == AssetType.BACKGROUND_MUSIC.value)
    metadata_score = _metadata_score(recipe)
    asset_score = _asset_score(
        item_count=item_count,
        distinct_roles=distinct_roles,
        visual_asset_count=visual_asset_count,
        voice_asset_count=voice_asset_count,
        music_asset_count=music_asset_count,
    )
    confidence_score = _confidence_score(item_count=item_count, review_assessment=review_assessment)
    recipe_score = round(min(1.0, metadata_score + asset_score + confidence_score), 3)
    duplicate_risk = _duplicate_risk(
        item_count=item_count,
        distinct_assets=distinct_assets,
        distinct_roles=distinct_roles,
        visual_asset_count=visual_asset_count,
        review_duplicate_risk=0.0 if review_assessment is None else float(review_assessment.duplicate_risk),
    )
    return RecipeScoreAssessment(
        recipe_score=recipe_score,
        duplicate_risk=duplicate_risk,
        metrics={
            "metadata_score": metadata_score,
            "asset_score": asset_score,
            "confidence_score": confidence_score,
            "item_count": item_count,
            "distinct_assets": distinct_assets,
            "distinct_roles": distinct_roles,
            "visual_asset_count": visual_asset_count,
            "voice_asset_count": voice_asset_count,
            "music_asset_count": music_asset_count,
        },
    )


def _metadata_score(recipe: Recipe) -> float:
    score = 0.0
    if recipe.target_platform:
        score += 0.05
    if recipe.target_ratio:
        score += 0.05
    if recipe.duration_sec and recipe.duration_sec > 0:
        score += 0.05
    if recipe.hook_text:
        score += 0.05
    if recipe.cta_text:
        score += 0.05
    if recipe.target_audience:
        score += 0.04
    if recipe.script_angle:
        score += 0.03
    if recipe.mood:
        score += 0.03
    return round(score, 3)


def _asset_score(
    *,
    item_count: int,
    distinct_roles: int,
    visual_asset_count: int,
    voice_asset_count: int,
    music_asset_count: int,
) -> float:
    score = 0.0
    if visual_asset_count > 0:
        score += 0.2
    if item_count >= 2:
        score += 0.05
    if distinct_roles >= 2:
        score += 0.05
    if voice_asset_count > 0:
        score += 0.1
    if music_asset_count > 0:
        score += 0.05
    if visual_asset_count > 1 or item_count >= 3:
        score += 0.05
    return round(score, 3)


def _confidence_score(*, item_count: int, review_assessment) -> float:
    if review_assessment is None:
        return 0.05 if item_count > 0 else 0.0
    review_bonus = 0.05 if not review_assessment.required else 0.0
    return round((0.2 * float(review_assessment.quality_score)) + review_bonus, 3)


def _duplicate_risk(
    *,
    item_count: int,
    distinct_assets: int,
    distinct_roles: int,
    visual_asset_count: int,
    review_duplicate_risk: float,
) -> float:
    if item_count == 0:
        return 1.0
    reuse_risk = max(0.0, 1.0 - (distinct_assets / item_count))
    role_risk = 0.2 if distinct_roles < min(2, item_count) else 0.0
    visual_gap_risk = 0.2 if visual_asset_count == 0 else 0.0
    single_asset_risk = 0.1 if item_count >= 3 and distinct_assets == 1 else 0.0
    baseline_risk = min(1.0, reuse_risk + role_risk + visual_gap_risk + single_asset_risk)
    return round(min(1.0, max(baseline_risk, review_duplicate_risk)), 3)


def _asset_type_for(item: RecipeItem, assets: dict[int, Asset]) -> str | None:
    if item.asset_type:
        return item.asset_type
    asset = assets.get(item.asset_id)
    if asset is None:
        return None
    return asset.asset_type.value


_VISUAL_TYPES = {
    AssetType.BACKGROUND_VIDEO.value,
    AssetType.FOREGROUND_VIDEO.value,
    AssetType.TEMPLATE.value,
}
