from __future__ import annotations

from mt_clip_factory.domain.assets import Asset
from mt_clip_factory.domain.enums import AssetType
from mt_clip_factory.domain.recipes import Recipe, RecipeItem
from mt_clip_factory.factory.automation_policy import AssetFillPolicy, ProductAutomationFillPolicies, default_fill_policies
from mt_clip_factory.factory.composition_planning import build_default_composition


def _asset(*, asset_id: int, asset_code: str, asset_type: AssetType, duration_sec: float) -> Asset:
    return Asset(
        id=asset_id,
        product_id=1,
        asset_code=asset_code,
        asset_type=asset_type,
        file_path=f"F:/tmp/{asset_code}.mp4",
        file_name=f"{asset_code}.mp4",
        duration_sec=duration_sec,
    )


def _item(*, asset_id: int, role: str, asset_code: str, asset_type: str) -> RecipeItem:
    return RecipeItem(
        recipe_id=1,
        asset_id=asset_id,
        role=role,
        asset_code=asset_code,
        asset_type=asset_type,
    )


def test_loopable_background_music_does_not_expand_master_duration() -> None:
    recipe = Recipe(product_id=1, recipe_code="music-loop-safe", duration_sec=12.0, id=1)
    voice = _asset(asset_id=11, asset_code="voice_a", asset_type=AssetType.VOICEOVER, duration_sec=6.0)
    music = _asset(asset_id=12, asset_code="music_long", asset_type=AssetType.BACKGROUND_MUSIC, duration_sec=120.0)
    policies = default_fill_policies()

    planned = build_default_composition(
        recipe,
        [
            _item(asset_id=voice.id or 11, role="voice", asset_code=voice.asset_code, asset_type="voiceover"),
            _item(asset_id=music.id or 12, role="music", asset_code=music.asset_code, asset_type="background_music"),
        ],
        {11: voice, 12: music},
        fill_policies=policies,
    )

    assert planned.plan.duration_source == "recipe_duration"
    assert planned.plan.resolved_duration_sec == 12.0


def test_non_loopable_background_music_can_expand_master_duration() -> None:
    recipe = Recipe(product_id=1, recipe_code="music-authoritative", duration_sec=12.0, id=1)
    voice = _asset(asset_id=11, asset_code="voice_a", asset_type=AssetType.VOICEOVER, duration_sec=6.0)
    music = _asset(asset_id=12, asset_code="music_long", asset_type=AssetType.BACKGROUND_MUSIC, duration_sec=120.0)
    defaults = default_fill_policies()
    policies = ProductAutomationFillPolicies(
        voiceover=defaults.voiceover,
        background_music=AssetFillPolicy(
            asset_type="background_music",
            loop_enabled=False,
            shortfall_mode="silence_tail",
        ),
        background_video=defaults.background_video,
        foreground_video=defaults.foreground_video,
    )

    planned = build_default_composition(
        recipe,
        [
            _item(asset_id=voice.id or 11, role="voice", asset_code=voice.asset_code, asset_type="voiceover"),
            _item(asset_id=music.id or 12, role="music", asset_code=music.asset_code, asset_type="background_music"),
        ],
        {11: voice, 12: music},
        fill_policies=policies,
    )

    assert planned.plan.duration_source == "longest_contributing_layer"
    assert planned.plan.resolved_duration_sec == 120.0


def test_segment_profile_overrides_duration_based_segment_formula() -> None:
    recipe = Recipe(
        product_id=1,
        recipe_code="preset-proof-focus",
        duration_sec=18.0,
        mood="trust",
        script_angle="daily support",
        cta_text="shop now",
        id=1,
    )
    background = _asset(
        asset_id=21,
        asset_code="bg_asset",
        asset_type=AssetType.BACKGROUND_VIDEO,
        duration_sec=18.0,
    )

    planned = build_default_composition(
        recipe,
        [
            _item(
                asset_id=background.id or 21,
                role="hero",
                asset_code=background.asset_code,
                asset_type="background_video",
            ),
        ],
        {21: background},
        segment_profile="proof_focus",
    )

    assert [segment.segment_type for segment in planned.segments] == ["proof", "benefit", "cta"]
    assert planned.segments[0].message_text == "trust"
    assert planned.segments[-1].message_text == "shop now"
    assert planned.segments[-1].end_sec == 18.0
