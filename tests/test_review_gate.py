from __future__ import annotations

from pathlib import Path

from mt_clip_factory.domain.composition_plans import CompositionPlan
from mt_clip_factory.factory.audio_composition import PreviewAudioMixPlan, PreviewAudioTrack
from mt_clip_factory.factory.preview_composition import PreviewComposition, PreviewLayerClip, PreviewSegmentClip
from mt_clip_factory.factory.review_gate import assess_review_gate, default_review_settings, review_gate_manifest_payload


def test_review_gate_flags_duration_unknown_emergency_fill() -> None:
    assessment = assess_review_gate(
        plan=CompositionPlan(recipe_id=1, duration_source="voiceover", target_duration_sec=9.0, resolved_duration_sec=9.0),
        composition=PreviewComposition(
            manifest_payload={},
            source_files=(Path("visual.mp4"),),
            segment_clips=(
                PreviewSegmentClip(
                    sequence_index=1,
                    segment_type="hook",
                    layer_name="background_visual",
                    asset_id=11,
                    asset_code="visual_asset",
                    source_file=Path("visual.mp4"),
                    start_sec=0.0,
                    end_sec=3.0,
                    target_duration_sec=3.0,
                    fill_mode="duration_unknown",
                ),
            ),
            audio_mix_plan=PreviewAudioMixPlan(
                target_duration_sec=9.0,
                voice_tracks=(
                    PreviewAudioTrack(
                        sequence_index=1,
                        layer_name="primary_voice",
                        asset_id=21,
                        asset_code="voice_asset",
                        source_file=Path("voice.mp3"),
                        start_sec=0.0,
                        playback_duration_sec=9.0,
                        source_duration_sec=None,
                        fill_mode="duration_unknown",
                    ),
                ),
                music_tracks=(),
            ),
        ),
        settings=default_review_settings(),
    )

    manifest_payload = review_gate_manifest_payload(assessment)

    assert assessment.required is True
    assert assessment.metrics["duration_unknown_visual_segments"] == 1
    assert assessment.metrics["duration_unknown_audio_tracks"] == 1
    assert [signal.code for signal in assessment.signals] == ["emergency_fill_detected"]
    assert manifest_payload["metrics"]["duration_unknown_audio_tracks"] == 1


def test_review_gate_flags_audio_masking_without_confirmed_ducking() -> None:
    assessment = assess_review_gate(
        plan=CompositionPlan(recipe_id=1, duration_source="voiceover", target_duration_sec=6.0, resolved_duration_sec=6.0),
        composition=PreviewComposition(
            manifest_payload={},
            source_files=(Path("visual.mp4"),),
            segment_clips=(
                PreviewSegmentClip(
                    sequence_index=1,
                    segment_type="hook",
                    layer_name="background_visual",
                    asset_id=11,
                    asset_code="visual_asset",
                    source_file=Path("visual.mp4"),
                    start_sec=0.0,
                    end_sec=6.0,
                    target_duration_sec=6.0,
                    fill_mode="trim_to_segment",
                ),
            ),
            audio_mix_plan=None,
        ),
        settings=default_review_settings(),
        audio_mix_summary={
            "voice_track_count": 1,
            "music_track_count": 1,
            "ducking": {
                "applied": False,
                "reason": "duck_disabled_in_settings",
            },
        },
    )

    assert assessment.required is True
    assert assessment.metrics["voice_track_count"] == 1
    assert assessment.metrics["music_track_count"] == 1
    assert [signal.code for signal in assessment.signals] == ["audio_masking_risk"]
    assert assessment.signals[0].metric_value == "duck_disabled_in_settings"


def test_review_gate_does_not_flag_ducked_audio_mix_on_its_own() -> None:
    assessment = assess_review_gate(
        plan=CompositionPlan(recipe_id=1, duration_source="voiceover", target_duration_sec=6.0, resolved_duration_sec=6.0),
        composition=PreviewComposition(
            manifest_payload={},
            source_files=(Path("visual.mp4"),),
            segment_clips=(
                PreviewSegmentClip(
                    sequence_index=1,
                    segment_type="hook",
                    layer_name="background_visual",
                    asset_id=11,
                    asset_code="visual_asset",
                    source_file=Path("visual.mp4"),
                    start_sec=0.0,
                    end_sec=6.0,
                    target_duration_sec=6.0,
                    fill_mode="trim_to_segment",
                ),
            ),
            audio_mix_plan=None,
        ),
        settings=default_review_settings(),
        audio_mix_summary={
            "voice_tracks": [{"asset_code": "voice_asset"}],
            "music_tracks": [{"asset_code": "music_asset"}],
            "ducking": {
                "applied": True,
                "mode": "sidechain_compressor",
            },
        },
    )

    assert assessment.required is False
    assert assessment.signals == ()


def test_review_gate_counts_background_and_foreground_assets_for_visual_diversity() -> None:
    assessment = assess_review_gate(
        plan=CompositionPlan(recipe_id=1, duration_source="background", target_duration_sec=6.0, resolved_duration_sec=6.0),
        composition=PreviewComposition(
            manifest_payload={},
            source_files=(Path("foreground.mp4"), Path("background.mp4")),
            segment_clips=(
                PreviewSegmentClip(
                    sequence_index=1,
                    segment_type="hook",
                    layer_name="product_focus_visual",
                    asset_id=21,
                    asset_code="foreground_asset",
                    source_file=Path("foreground.mp4"),
                    start_sec=0.0,
                    end_sec=3.0,
                    target_duration_sec=3.0,
                    fill_mode="trim_to_segment",
                    background_layer=PreviewLayerClip(
                        layer_name="background_visual",
                        asset_id=11,
                        asset_code="background_asset",
                        source_file=Path("background.mp4"),
                        fill_mode="trim_to_segment",
                        source_duration_sec=3.0,
                    ),
                ),
                PreviewSegmentClip(
                    sequence_index=2,
                    segment_type="cta",
                    layer_name="product_focus_visual",
                    asset_id=21,
                    asset_code="foreground_asset",
                    source_file=Path("foreground.mp4"),
                    start_sec=3.0,
                    end_sec=6.0,
                    target_duration_sec=3.0,
                    fill_mode="trim_to_segment",
                    background_layer=PreviewLayerClip(
                        layer_name="background_visual",
                        asset_id=11,
                        asset_code="background_asset",
                        source_file=Path("background.mp4"),
                        fill_mode="trim_to_segment",
                        source_duration_sec=3.0,
                    ),
                ),
            ),
            audio_mix_plan=None,
        ),
        settings=default_review_settings(),
    )

    assert assessment.metrics["distinct_visual_assets"] == 2
    assert not any(signal.code == "low_visual_diversity" for signal in assessment.signals)


def test_review_gate_allows_persistent_primary_asset_when_recipe_uses_single_selected_visual() -> None:
    assessment = assess_review_gate(
        plan=CompositionPlan(recipe_id=1, duration_source="background", target_duration_sec=8.0, resolved_duration_sec=8.0),
        composition=PreviewComposition(
            manifest_payload={},
            source_files=(Path("foreground.mp4"), Path("background.mp4")),
            segment_clips=(
                PreviewSegmentClip(
                    sequence_index=1,
                    segment_type="hook",
                    layer_name="product_focus_visual",
                    asset_id=21,
                    asset_code="foreground_asset",
                    source_file=Path("foreground.mp4"),
                    start_sec=0.0,
                    end_sec=2.0,
                    target_duration_sec=2.0,
                    fill_mode="loop_to_segment",
                    background_layer=PreviewLayerClip(
                        layer_name="background_visual",
                        asset_id=11,
                        asset_code="background_asset",
                        source_file=Path("background.mp4"),
                        fill_mode="loop_to_segment",
                        source_duration_sec=2.0,
                    ),
                ),
                PreviewSegmentClip(
                    sequence_index=2,
                    segment_type="benefit",
                    layer_name="product_focus_visual",
                    asset_id=21,
                    asset_code="foreground_asset",
                    source_file=Path("foreground.mp4"),
                    start_sec=2.0,
                    end_sec=4.0,
                    target_duration_sec=2.0,
                    fill_mode="loop_to_segment",
                    background_layer=PreviewLayerClip(
                        layer_name="background_visual",
                        asset_id=11,
                        asset_code="background_asset",
                        source_file=Path("background.mp4"),
                        fill_mode="loop_to_segment",
                        source_duration_sec=2.0,
                    ),
                ),
                PreviewSegmentClip(
                    sequence_index=3,
                    segment_type="proof",
                    layer_name="product_focus_visual",
                    asset_id=21,
                    asset_code="foreground_asset",
                    source_file=Path("foreground.mp4"),
                    start_sec=4.0,
                    end_sec=6.0,
                    target_duration_sec=2.0,
                    fill_mode="loop_to_segment",
                    background_layer=PreviewLayerClip(
                        layer_name="background_visual",
                        asset_id=11,
                        asset_code="background_asset",
                        source_file=Path("background.mp4"),
                        fill_mode="loop_to_segment",
                        source_duration_sec=2.0,
                    ),
                ),
                PreviewSegmentClip(
                    sequence_index=4,
                    segment_type="cta",
                    layer_name="product_focus_visual",
                    asset_id=21,
                    asset_code="foreground_asset",
                    source_file=Path("foreground.mp4"),
                    start_sec=6.0,
                    end_sec=8.0,
                    target_duration_sec=2.0,
                    fill_mode="loop_to_segment",
                    background_layer=PreviewLayerClip(
                        layer_name="background_visual",
                        asset_id=11,
                        asset_code="background_asset",
                        source_file=Path("background.mp4"),
                        fill_mode="loop_to_segment",
                        source_duration_sec=2.0,
                    ),
                ),
            ),
            audio_mix_plan=None,
        ),
        settings=default_review_settings(),
    )

    assert assessment.metrics["max_consecutive_same_asset_segments"] == 4
    assert not any(signal.code == "repeated_visual_asset" for signal in assessment.signals)
