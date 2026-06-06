from __future__ import annotations

from mt_clip_factory.domain.assets import Asset
from mt_clip_factory.domain.enums import AssetType
from mt_clip_factory.domain.recipes import Recipe, RecipeItem
from mt_clip_factory.factory.recipe_scoring import assess_recipe_score
from mt_clip_factory.factory.review_gate import ReviewAssessment


def test_recipe_scoring_flags_empty_recipe_as_high_risk() -> None:
    assessment = assess_recipe_score(
        recipe=Recipe(product_id=1, recipe_code="empty_recipe"),
        items=(),
        assets={},
    )

    assert assessment.recipe_score == 0.0
    assert assessment.duplicate_risk == 1.0
    assert assessment.metrics["item_count"] == 0


def test_recipe_scoring_rewards_complete_multi_layer_recipe() -> None:
    recipe = Recipe(
        product_id=1,
        recipe_code="launch_mix",
        target_platform="tiktok",
        target_ratio="9:16",
        duration_sec=30.0,
        mood="energetic",
        script_angle="ugc",
        target_audience="cold leads",
        hook_text="Stop scrolling",
        cta_text="Shop now",
    )
    items = (
        RecipeItem(recipe_id=1, asset_id=1, role="hero", asset_type=AssetType.BACKGROUND_VIDEO.value),
        RecipeItem(recipe_id=1, asset_id=2, role="voice", asset_type=AssetType.VOICEOVER.value),
        RecipeItem(recipe_id=1, asset_id=3, role="music", asset_type=AssetType.BACKGROUND_MUSIC.value),
    )
    assets = {
        1: Asset(1, "hero_asset", AssetType.BACKGROUND_VIDEO, "hero.mp4", "hero.mp4"),
        2: Asset(1, "voice_asset", AssetType.VOICEOVER, "voice.mp3", "voice.mp3"),
        3: Asset(1, "music_asset", AssetType.BACKGROUND_MUSIC, "music.mp3", "music.mp3"),
    }

    assessment = assess_recipe_score(
        recipe=recipe,
        items=items,
        assets=assets,
        review_assessment=ReviewAssessment(
            required=False,
            duplicate_risk=0.2,
            quality_score=0.8,
            summary="stable",
            signals=(),
            metrics={},
        ),
    )

    assert assessment.recipe_score == 1.0
    assert assessment.duplicate_risk == 0.2
    assert assessment.metrics["voice_asset_count"] == 1
    assert assessment.metrics["music_asset_count"] == 1


def test_recipe_scoring_penalizes_reused_single_visual_recipe() -> None:
    recipe = Recipe(product_id=1, recipe_code="reused_visual", target_platform="tiktok", target_ratio="9:16")
    items = (
        RecipeItem(recipe_id=1, asset_id=1, role="hook", asset_type=AssetType.BACKGROUND_VIDEO.value),
        RecipeItem(recipe_id=1, asset_id=1, role="benefit", asset_type=AssetType.BACKGROUND_VIDEO.value),
        RecipeItem(recipe_id=1, asset_id=1, role="cta", asset_type=AssetType.BACKGROUND_VIDEO.value),
    )

    assessment = assess_recipe_score(recipe=recipe, items=items, assets={})

    assert assessment.recipe_score == 0.5
    assert assessment.duplicate_risk == 0.767
    assert assessment.metrics["distinct_assets"] == 1
