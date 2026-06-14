from __future__ import annotations

from pathlib import Path

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.factory.dto import AssignAssetToRecipeCommand, CreateRecipeCommand
from mt_clip_factory.factory.preview_artifacts import PreviewManifestBuilder
from mt_clip_factory.factory.renderers import RenderedPreviewOutput
from mt_clip_factory.factory.services import VideoAssemblyFactoryService
from mt_clip_factory.library.contracts import AnalyzedMediaMetadata
from mt_clip_factory.library.dto import RegisterAssetCommand
from mt_clip_factory.library.readiness import AssetReadinessEvaluator
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.storage import LocalAssetStorage


class FakeMetadataAnalyzer:
    def __init__(self, duration_sec: float = 3.0) -> None:
        self._duration_sec = duration_sec

    def analyze(self, file_path: Path) -> AnalyzedMediaMetadata:
        return AnalyzedMediaMetadata(
            duration_sec=self._duration_sec,
            width=1920,
            height=1080,
            fps=30.0,
            ratio="16:9",
            file_size_mb=round(file_path.stat().st_size / (1024 * 1024), 4),
            codec="h264",
            has_audio=True,
        )


def _build_asset_service(unit_of_work_factory, media_root: Path, *, duration_sec: float = 3.0) -> AssetIntakeService:
    return AssetIntakeService(
        unit_of_work_factory=unit_of_work_factory,
        asset_storage=LocalAssetStorage(media_root),
        metadata_analyzer=FakeMetadataAnalyzer(duration_sec),
        readiness_evaluator=AssetReadinessEvaluator(),
    )


def _build_factory_service(unit_of_work_factory, preview_root: Path) -> VideoAssemblyFactoryService:
    class FakePreviewRenderer:
        def render_output(
            self,
            *,
            product_code: str,
            output_stem: str,
            source_files: list[Path],
            segment_clips=(),
            audio_mix_plan=None,
            target_path: Path | None = None,
            fill_policies=None,
        ) -> RenderedPreviewOutput:
            del fill_policies
            resolved_target_path = target_path or (preview_root / product_code / "videos" / f"{output_stem}.mp4")
            resolved_target_path.parent.mkdir(parents=True, exist_ok=True)
            resolved_target_path.write_bytes(source_files[0].read_bytes())
            return RenderedPreviewOutput(file_path=resolved_target_path, duration_sec=3.0)

    return VideoAssemblyFactoryService(
        unit_of_work_factory=unit_of_work_factory,
        preview_manifest_builder=PreviewManifestBuilder(preview_root),
        preview_renderer=FakePreviewRenderer(),
        final_renderer=FakePreviewRenderer(),
    )


def _register_ready_asset(
    unit_of_work_factory,
    tmp_path: Path,
    *,
    asset_type: str,
    asset_code: str,
    duration_sec: float = 3.0,
) -> tuple[int, int]:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    products = product_service.list_products()
    if products:
        product_id = products[0].product_id
    else:
        product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library", duration_sec=duration_sec)
    source_file = tmp_path / f"{asset_code}.mp4"
    source_file.write_bytes(f"{asset_code}-bytes".encode("utf-8"))
    asset_id = asset_service.register_asset(
        RegisterAssetCommand(
            product_id=product_id,
            asset_type=asset_type,
            source_file_path=source_file,
            asset_code=asset_code,
        )
    )
    return product_id, asset_id


def test_composition_plan_prefers_recipe_duration_and_infers_layers(unit_of_work_factory, tmp_path) -> None:
    product_id, background_id = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="background_video",
        asset_code="background_asset",
    )
    _, voice_id = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="voiceover",
        asset_code="voice_asset",
    )
    _, music_id = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="background_music",
        asset_code="music_asset",
    )
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(
        CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch", duration_sec=30.0)
    )
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=background_id, role="bg"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=voice_id, role="voice"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=music_id, role="music"))

    plan = service.get_composition_plan(recipe_id)

    assert plan.duration_source == "recipe_duration"
    assert plan.target_duration_sec == 30.0
    assert plan.resolved_duration_sec == 30.0
    assert [layer.layer_name for layer in plan.layers] == [
        "primary_voice",
        "background_music",
        "background_visual",
    ]
    assert [segment.segment_type for segment in plan.segments] == [
        "hook",
        "problem",
        "benefit",
        "proof",
        "cta",
    ]
    assert plan.segments[0].start_sec == 0.0
    assert plan.segments[-1].end_sec == 30.0
    assert {decision.decision_type for decision in plan.decisions} == {
        "master_duration_resolved",
        "layer_assignment_inferred",
        "timeline_segment_planned",
    }


def test_composition_plan_falls_back_to_voiceover_duration(unit_of_work_factory, tmp_path) -> None:
    product_id, voice_one_id = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="voiceover",
        asset_code="voice_one",
    )
    _, voice_two_id = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="voiceover",
        asset_code="voice_two",
    )
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Voice Duration"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=voice_one_id, role="voice"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=voice_two_id, role="voice"))

    plan = service.get_composition_plan(recipe_id)

    assert plan.duration_source == "longest_contributing_layer"
    assert plan.target_duration_sec is None
    assert plan.resolved_duration_sec == 6.0
    assert [segment.segment_type for segment in plan.segments] == ["hook", "benefit", "cta"]
    assert len(plan.decisions) == 5


def test_composition_plan_raises_resolved_duration_to_longest_contributing_visual_layer(unit_of_work_factory, tmp_path) -> None:
    product_id, foreground_id = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="foreground_video",
        asset_code="foreground_long",
        duration_sec=12.0,
    )
    _, voice_id = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="voiceover",
        asset_code="voice_short",
        duration_sec=4.0,
    )
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(
        CreateRecipeCommand(product_id=product_id, recipe_code="Longest Layer", duration_sec=6.0)
    )
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=foreground_id, role="fg"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=voice_id, role="voice"))

    plan = service.get_composition_plan(recipe_id)

    assert plan.duration_source == "longest_contributing_layer"
    assert plan.target_duration_sec == 6.0
    assert plan.resolved_duration_sec == 12.0
    assert plan.segments[-1].end_sec == 12.0
