from __future__ import annotations

from pathlib import Path

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.factory.audio_composition import PreviewAudioMixPlan
from mt_clip_factory.factory.auto_factory import AutoFactoryBatchService
from mt_clip_factory.factory.auto_factory_dto import AutoFactoryBatchOrderDTO, AutoFactoryProductRequestDTO
from mt_clip_factory.factory.dto import AssignAssetToRecipeCommand, CreateRecipeCommand
from mt_clip_factory.factory.preview_artifacts import PreviewManifestBuilder
from mt_clip_factory.factory.preview_composition import PreviewSegmentClip
from mt_clip_factory.factory.renderers import RenderedPreviewOutput
from mt_clip_factory.factory.services import VideoAssemblyFactoryService
from mt_clip_factory.library.contracts import AnalyzedMediaMetadata
from mt_clip_factory.library.dto import RegisterAssetCommand
from mt_clip_factory.library.readiness import AssetReadinessEvaluator
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.storage import LocalAssetStorage


class PlanningMetadataAnalyzer:
    def __init__(self, durations_by_name: dict[str, float]) -> None:
        self._durations_by_name = durations_by_name

    def analyze(self, file_path: Path) -> AnalyzedMediaMetadata:
        duration_sec = self._durations_by_name.get(file_path.name, 12.5)
        is_audio = file_path.suffix.lower() == ".mp3"
        return AnalyzedMediaMetadata(
            duration_sec=duration_sec,
            width=None if is_audio else 1920,
            height=None if is_audio else 1080,
            fps=None if is_audio else 30.0,
            ratio=None if is_audio else "16:9",
            file_size_mb=round(file_path.stat().st_size / (1024 * 1024), 4),
            codec="aac" if is_audio else "h264",
            has_audio=True,
        )


def _build_asset_service(unit_of_work_factory, media_root: Path, durations_by_name: dict[str, float]) -> AssetIntakeService:
    return AssetIntakeService(
        unit_of_work_factory=unit_of_work_factory,
        asset_storage=LocalAssetStorage(media_root),
        metadata_analyzer=PlanningMetadataAnalyzer(durations_by_name),
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
            segment_clips: tuple[PreviewSegmentClip, ...] = (),
            audio_mix_plan: PreviewAudioMixPlan | None = None,
            target_ratio: str | None = None,
            target_path: Path | None = None,
            fill_policies=None,
        ) -> RenderedPreviewOutput:
            del product_code, output_stem, audio_mix_plan, target_ratio, fill_policies
            resolved_target_path = target_path or (preview_root / "videos" / "synthetic.mp4")
            resolved_target_path.parent.mkdir(parents=True, exist_ok=True)
            payload = (
                b"".join(segment.source_file.read_bytes() for segment in segment_clips)
                if segment_clips
                else source_files[0].read_bytes()
            )
            resolved_target_path.write_bytes(payload)
            duration_sec = round(sum(segment.target_duration_sec for segment in segment_clips), 3) if segment_clips else 3.0
            return RenderedPreviewOutput(
                file_path=resolved_target_path,
                duration_sec=duration_sec,
                audio_mix_summary=None,
                visual_composite_summary=None,
            )

    renderer = FakePreviewRenderer()
    return VideoAssemblyFactoryService(
        unit_of_work_factory=unit_of_work_factory,
        preview_manifest_builder=PreviewManifestBuilder(preview_root),
        preview_renderer=renderer,
        final_renderer=renderer,
    )


def _register_asset(
    asset_service: AssetIntakeService,
    *,
    product_id: int,
    tmp_path: Path,
    asset_type: str,
    asset_code: str,
    file_name: str,
) -> int:
    source_file = tmp_path / file_name
    source_file.write_bytes(asset_code.encode("utf-8"))
    return asset_service.register_asset(
        RegisterAssetCommand(
            product_id=product_id,
            asset_type=asset_type,
            source_file_path=source_file,
            asset_code=asset_code,
        )
    )


def _build_auto_factory_service(unit_of_work_factory, tmp_path: Path, durations_by_name: dict[str, float]) -> AutoFactoryBatchService:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library", durations_by_name)
    factory_service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    return AutoFactoryBatchService(
        product_service=product_service,
        asset_intake_service=asset_service,
        video_assembly_factory_service=factory_service,
    )


def _materialize_history_recipe(
    factory_service: VideoAssemblyFactoryService,
    *,
    product_id: int,
    recipe_code: str,
    planned_recipe,
) -> int:  # noqa: ANN001
    recipe_id = factory_service.create_recipe(
        CreateRecipeCommand(
            product_id=product_id,
            recipe_code=recipe_code,
            target_platform=planned_recipe.target_platform,
            target_ratio=planned_recipe.target_ratio,
            duration_sec=planned_recipe.duration_sec,
        )
    )
    for assignment in planned_recipe.assignments:
        factory_service.assign_asset_to_recipe(
            AssignAssetToRecipeCommand(
                recipe_id=recipe_id,
                asset_id=assignment.asset_id,
                role=assignment.role,
            )
        )
    return recipe_id


def _replace_assignment_role(planned_recipe, *, role: str, asset_id: int, asset_code: str, asset_type: str):  # noqa: ANN001
    replaced = []
    for assignment in planned_recipe.assignments:
        if assignment.role == role:
            replaced.append(
                type(assignment)(
                    asset_id=asset_id,
                    asset_code=asset_code,
                    asset_type=asset_type,
                    role=role,
                )
            )
        else:
            replaced.append(assignment)
    return type(planned_recipe)(
        product_id=planned_recipe.product_id,
        product_code=planned_recipe.product_code,
        recipe_code=planned_recipe.recipe_code,
        request_index=planned_recipe.request_index,
        target_platform=planned_recipe.target_platform,
        target_ratio=planned_recipe.target_ratio,
        duration_sec=planned_recipe.duration_sec,
        duration_source=planned_recipe.duration_source,
        fingerprint=planned_recipe.fingerprint,
        assignments=tuple(replaced),
    )


def test_auto_factory_reports_zero_near_duplicate_score_for_clean_first_recipe(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="cleanrisk", product_name="Clean Risk"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library", {"voice_01.mp3": 12.0})
    for asset_index in range(5):
        _register_asset(
            asset_service,
            product_id=product_id,
            tmp_path=tmp_path,
            asset_type="foreground_video",
            asset_code=f"fg_{asset_index + 1:02d}",
            file_name=f"fg{asset_index + 1:02d}.mp4",
        )
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_video", asset_code="bg_01", file_name="bg01.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_music", asset_code="music_01", file_name="music01.mp3")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="voiceover", asset_code="voice_01", file_name="voice_01.mp3")
    service = _build_auto_factory_service(unit_of_work_factory, tmp_path, {"voice_01.mp3": 12.0})

    plan = service.plan_batch(
        AutoFactoryBatchOrderDTO(
            batch_code="cleanrisk_batch",
            product_requests=(AutoFactoryProductRequestDTO(product_code="cleanrisk", requested_output_count=1),),
        )
    )

    recipe = plan.planned_recipes[0]

    assert recipe.near_duplicate_score == 0.0
    assert recipe.near_duplicate_reasons == ()


def test_auto_factory_reports_exact_combo_reuse_when_history_forces_repeat(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="forcedrepeat", product_name="Forced Repeat"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library", {"voice_01.mp3": 12.0})
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="foreground_video", asset_code="fg_01", file_name="fg01.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_video", asset_code="bg_01", file_name="bg01.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_music", asset_code="music_01", file_name="music01.mp3")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="voiceover", asset_code="voice_01", file_name="voice_01.mp3")
    factory_service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    service = AutoFactoryBatchService(
        product_service=product_service,
        asset_intake_service=asset_service,
        video_assembly_factory_service=factory_service,
    )
    order = AutoFactoryBatchOrderDTO(
        batch_code="forcedrepeat_batch",
        product_requests=(AutoFactoryProductRequestDTO(product_code="forcedrepeat", requested_output_count=1),),
    )

    baseline_plan = service.plan_batch(order)
    _materialize_history_recipe(
        factory_service,
        product_id=product_id,
        recipe_code="forcedrepeat_history_001",
        planned_recipe=baseline_plan.planned_recipes[0],
    )

    rerun_plan = service.plan_batch(order)
    rerun_recipe = rerun_plan.planned_recipes[0]

    assert rerun_recipe.near_duplicate_score == 1.0
    assert "exact_combo_reused" in rerun_recipe.near_duplicate_reasons


def test_auto_factory_reports_voice_overuse_risk_when_voice_must_repeat(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="voicescore", product_name="Voice Score"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library", {"voice_01.mp3": 12.0})
    for asset_index in range(5):
        _register_asset(
            asset_service,
            product_id=product_id,
            tmp_path=tmp_path,
            asset_type="foreground_video",
            asset_code=f"fg_{asset_index + 1:02d}",
            file_name=f"fg{asset_index + 1:02d}.mp4",
        )
    bg_01 = _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_video", asset_code="bg_01", file_name="bg01.mp4")
    bg_02 = _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_video", asset_code="bg_02", file_name="bg02.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="voiceover", asset_code="voice_01", file_name="voice_01.mp3")
    factory_service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    service = AutoFactoryBatchService(
        product_service=product_service,
        asset_intake_service=asset_service,
        video_assembly_factory_service=factory_service,
    )
    order = AutoFactoryBatchOrderDTO(
        batch_code="voicescore_batch",
        product_requests=(AutoFactoryProductRequestDTO(product_code="voicescore", requested_output_count=1),),
    )

    baseline_plan = service.plan_batch(order)
    baseline_recipe = baseline_plan.planned_recipes[0]
    baseline_background = next(assignment for assignment in baseline_recipe.assignments if assignment.role == "background")
    overused_background_id = bg_02 if baseline_background.asset_id == bg_01 else bg_01
    overused_background_code = "bg_02" if overused_background_id == bg_02 else "bg_01"
    historical_recipe = _replace_assignment_role(
        baseline_recipe,
        role="background",
        asset_id=overused_background_id,
        asset_code=overused_background_code,
        asset_type="background_video",
    )
    for history_index in range(3):
        _materialize_history_recipe(
            factory_service,
            product_id=product_id,
            recipe_code=f"voicescore_history_{history_index + 1:03d}",
            planned_recipe=historical_recipe,
        )

    rerun_plan = service.plan_batch(order)
    rerun_recipe = rerun_plan.planned_recipes[0]

    assert rerun_recipe.near_duplicate_score > 0.0
    assert "voice_asset_overused" in rerun_recipe.near_duplicate_reasons
    assert "exact_combo_reused" not in rerun_recipe.near_duplicate_reasons
