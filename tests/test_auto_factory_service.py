from __future__ import annotations

from pathlib import Path

import pytest

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.factory.audio_composition import PreviewAudioMixPlan
from mt_clip_factory.factory.auto_factory import (
    AutoFactoryBatchService,
    AutoFactoryCapacityError,
)
from mt_clip_factory.factory.auto_factory_dto import (
    AutoFactoryBatchOrderDTO,
    AutoFactoryProductRequestDTO,
)
from mt_clip_factory.factory.dto import AssignAssetToRecipeCommand, CreateRecipeCommand
from mt_clip_factory.factory.preview_composition import PreviewSegmentClip
from mt_clip_factory.factory.preview_artifacts import PreviewManifestBuilder
from mt_clip_factory.factory.renderers import RenderedPreviewOutput
from mt_clip_factory.factory.services import VideoAssemblyFactoryService
from mt_clip_factory.library.contracts import AnalyzedMediaMetadata
from mt_clip_factory.library.dto import RegisterAssetCommand
from mt_clip_factory.library.readiness import AssetReadinessEvaluator
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.storage import LocalAssetStorage
from mt_clip_factory.library.tag_dto import AssignTagToAssetCommand, CreateTagCommand
from mt_clip_factory.library.tag_services import TagManagementService


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


def _build_factory_service(
    unit_of_work_factory,
    preview_root: Path,
    *,
    fail_preview_stems: set[str] | None = None,
) -> VideoAssemblyFactoryService:
    class FakePreviewRenderer:
        def __init__(self) -> None:
            self.calls: list[dict] = []

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
            del fill_policies
            self.calls.append(
                {
                    "product_code": product_code,
                    "output_stem": output_stem,
                    "source_files": source_files,
                    "segment_clips": segment_clips,
                    "audio_mix_plan": audio_mix_plan,
                    "target_ratio": target_ratio,
                }
            )
            if fail_preview_stems and output_stem in fail_preview_stems:
                raise RuntimeError(f"synthetic preview failure for {output_stem}")

            resolved_target_path = target_path or (preview_root / product_code / "videos" / f"{output_stem}.mp4")
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


def _assign_tag_to_asset(tag_service: TagManagementService, *, asset_id: int, tag_group: str, tag_name: str) -> int:
    tag_id = tag_service.create_tag(CreateTagCommand(tag_name=tag_name, tag_group=tag_group))
    tag_service.assign_tag_to_asset(AssignTagToAssetCommand(asset_id=asset_id, tag_id=tag_id))
    return tag_id


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


def _assignment_signature(planned_recipe) -> tuple[tuple[str, str], ...]:  # noqa: ANN001
    return tuple(sorted((assignment.role, assignment.asset_code) for assignment in planned_recipe.assignments))


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
        fingerprint_hash=planned_recipe.fingerprint_hash,
        assignments=tuple(replaced),
    )


def test_auto_factory_plans_batch_unique_variants(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library", {"voice_01.mp3": 18.2})
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="foreground_video", asset_code="fg_01", file_name="fg01.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="foreground_video", asset_code="fg_02", file_name="fg02.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_video", asset_code="bg_01", file_name="bg01.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_music", asset_code="music_01", file_name="music01.mp3")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="voiceover", asset_code="voice_01", file_name="voice_01.mp3")
    service = _build_auto_factory_service(unit_of_work_factory, tmp_path, {"voice_01.mp3": 18.2})

    plan = service.plan_batch(
        AutoFactoryBatchOrderDTO(
            batch_code="launch_01",
            product_requests=(
                AutoFactoryProductRequestDTO(
                    product_code="honey",
                    requested_output_count=2,
                    target_platform="shopee",
                    target_ratio="9:16",
                ),
            ),
        )
    )

    assert plan.batch_code == "launch_01"
    assert len(plan.summaries) == 1
    assert plan.summaries[0].planner_feasible_unique_count == 2
    assert plan.summaries[0].can_fulfill_exactly is True
    assert len(plan.planned_recipes) == 2
    assert plan.planned_recipes[0].fingerprint != plan.planned_recipes[1].fingerprint
    assert plan.planned_recipes[0].duration_source == "voice_with_bounds"
    assert plan.planned_recipes[0].duration_sec == 18.2
    assert [assignment.role for assignment in plan.planned_recipes[0].assignments] == [
        "background",
        "hook",
        "problem",
        "benefit",
        "proof",
        "cta",
        "voice",
        "music",
    ]


def test_auto_factory_keeps_seeded_visual_order_deterministic_per_batch(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="seeded", product_name="Seeded"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library", {"voice_01.mp3": 12.0})
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="foreground_video", asset_code="fg_01", file_name="fg01.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="foreground_video", asset_code="fg_02", file_name="fg02.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="foreground_video", asset_code="fg_03", file_name="fg03.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_video", asset_code="bg_01", file_name="bg01.mp4")
    service = _build_auto_factory_service(unit_of_work_factory, tmp_path, {"voice_01.mp3": 12.0})

    first = service.plan_batch(
        AutoFactoryBatchOrderDTO(
            batch_code="seed_batch",
            product_requests=(AutoFactoryProductRequestDTO(product_code="seeded", requested_output_count=2),),
        )
    )
    second = service.plan_batch(
        AutoFactoryBatchOrderDTO(
            batch_code="seed_batch",
            product_requests=(AutoFactoryProductRequestDTO(product_code="seeded", requested_output_count=2),),
        )
    )
    third = service.plan_batch(
        AutoFactoryBatchOrderDTO(
            batch_code="other_batch",
            product_requests=(AutoFactoryProductRequestDTO(product_code="seeded", requested_output_count=2),),
        )
    )

    first_hook_codes = [assignment.asset_code for assignment in first.planned_recipes[0].assignments if assignment.role == "hook"]
    second_hook_codes = [assignment.asset_code for assignment in second.planned_recipes[0].assignments if assignment.role == "hook"]
    third_hook_codes = [assignment.asset_code for assignment in third.planned_recipes[0].assignments if assignment.role == "hook"]

    assert first_hook_codes == second_hook_codes
    assert first.planned_recipes[0].fingerprint != third.planned_recipes[0].fingerprint


def test_auto_factory_diversifies_voice_early_within_batch(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="voices", product_name="Voices"))
    asset_service = _build_asset_service(
        unit_of_work_factory,
        tmp_path / "media_library",
        {"voice_01.mp3": 12.0, "voice_02.mp3": 13.0},
    )
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="foreground_video", asset_code="fg_01", file_name="fg01.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="foreground_video", asset_code="fg_02", file_name="fg02.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_video", asset_code="bg_01", file_name="bg01.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="voiceover", asset_code="voice_01", file_name="voice_01.mp3")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="voiceover", asset_code="voice_02", file_name="voice_02.mp3")
    service = _build_auto_factory_service(unit_of_work_factory, tmp_path, {"voice_01.mp3": 12.0, "voice_02.mp3": 13.0})

    plan = service.plan_batch(
        AutoFactoryBatchOrderDTO(
            batch_code="voices_batch",
            product_requests=(AutoFactoryProductRequestDTO(product_code="voices", requested_output_count=2),),
        )
    )

    voice_codes = [
        next(assignment.asset_code for assignment in recipe.assignments if assignment.role == "voice")
        for recipe in plan.planned_recipes
    ]

    assert len(set(voice_codes)) == 2


def test_auto_factory_spreads_backgrounds_early_within_batch(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="bgspread", product_name="BG Spread"))
    asset_service = _build_asset_service(
        unit_of_work_factory,
        tmp_path / "media_library",
        {"voice_01.mp3": 12.0},
    )
    for asset_index in range(1, 10):
        _register_asset(
            asset_service,
            product_id=product_id,
            tmp_path=tmp_path,
            asset_type="foreground_video",
            asset_code=f"fg_{asset_index:02d}",
            file_name=f"fg{asset_index:02d}.mp4",
        )
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_video", asset_code="bg_01", file_name="bg01.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_video", asset_code="bg_02", file_name="bg02.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="voiceover", asset_code="voice_01", file_name="voice_01.mp3")
    service = _build_auto_factory_service(unit_of_work_factory, tmp_path, {"voice_01.mp3": 12.0})

    plan = service.plan_batch(
        AutoFactoryBatchOrderDTO(
            batch_code="bgspread_batch",
            product_requests=(AutoFactoryProductRequestDTO(product_code="bgspread", requested_output_count=2),),
        )
    )

    background_codes = [
        next(assignment.asset_code for assignment in recipe.assignments if assignment.role == "background")
        for recipe in plan.planned_recipes
    ]

    assert len(set(background_codes)) == 2


def test_auto_factory_avoids_historically_repeated_exact_combo_when_alternative_exists(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="repeatfix", product_name="Repeat Fix"))
    asset_service = _build_asset_service(
        unit_of_work_factory,
        tmp_path / "media_library",
        {"voice_01.mp3": 12.0, "voice_02.mp3": 13.0},
    )
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="foreground_video", asset_code="fg_01", file_name="fg01.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="foreground_video", asset_code="fg_02", file_name="fg02.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_video", asset_code="bg_01", file_name="bg01.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="voiceover", asset_code="voice_01", file_name="voice_01.mp3")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="voiceover", asset_code="voice_02", file_name="voice_02.mp3")
    factory_service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    service = AutoFactoryBatchService(
        product_service=product_service,
        asset_intake_service=asset_service,
        video_assembly_factory_service=factory_service,
    )
    order = AutoFactoryBatchOrderDTO(
        batch_code="repeatfix_batch",
        product_requests=(AutoFactoryProductRequestDTO(product_code="repeatfix", requested_output_count=1),),
    )

    baseline_plan = service.plan_batch(order)
    baseline_recipe = baseline_plan.planned_recipes[0]
    _materialize_history_recipe(
        factory_service,
        product_id=product_id,
        recipe_code="repeatfix_history_001",
        planned_recipe=baseline_recipe,
    )

    rerun_plan = service.plan_batch(order)

    assert _assignment_signature(rerun_plan.planned_recipes[0]) != _assignment_signature(baseline_recipe)
    assert rerun_plan.planned_recipes[0].near_duplicate_score < 1.0
    assert "exact_combo_reused" not in rerun_plan.planned_recipes[0].near_duplicate_reasons


def test_auto_factory_deprioritizes_historically_overused_voice_even_when_combo_changes(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="voicecool", product_name="Voice Cool"))
    asset_service = _build_asset_service(
        unit_of_work_factory,
        tmp_path / "media_library",
        {"voice_01.mp3": 12.0, "voice_02.mp3": 13.0},
    )
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="foreground_video", asset_code="fg_01", file_name="fg01.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="foreground_video", asset_code="fg_02", file_name="fg02.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="foreground_video", asset_code="fg_03", file_name="fg03.mp4")
    bg_01 = _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_video", asset_code="bg_01", file_name="bg01.mp4")
    bg_02 = _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_video", asset_code="bg_02", file_name="bg02.mp4")
    music_01 = _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_music", asset_code="music_01", file_name="music01.mp3")
    music_02 = _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_music", asset_code="music_02", file_name="music02.mp3")
    voice_01 = _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="voiceover", asset_code="voice_01", file_name="voice_01.mp3")
    voice_02 = _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="voiceover", asset_code="voice_02", file_name="voice_02.mp3")
    factory_service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    service = AutoFactoryBatchService(
        product_service=product_service,
        asset_intake_service=asset_service,
        video_assembly_factory_service=factory_service,
    )
    order = AutoFactoryBatchOrderDTO(
        batch_code="voicecool_batch",
        product_requests=(AutoFactoryProductRequestDTO(product_code="voicecool", requested_output_count=1),),
    )

    baseline_plan = service.plan_batch(order)
    baseline_recipe = baseline_plan.planned_recipes[0]
    baseline_voice = next(assignment for assignment in baseline_recipe.assignments if assignment.role == "voice")
    other_background = (bg_02, "bg_02") if bg_01 != bg_02 else (bg_01, "bg_01")
    other_music = (music_02, "music_02") if music_01 != music_02 else (music_01, "music_01")
    overused_voice_id = voice_01 if baseline_voice.asset_id == voice_01 else voice_02
    overused_voice_code = "voice_01" if overused_voice_id == voice_01 else "voice_02"
    alternative_recipe = _replace_assignment_role(
        baseline_recipe,
        role="voice",
        asset_id=overused_voice_id,
        asset_code=overused_voice_code,
        asset_type="voiceover",
    )
    alternative_recipe = _replace_assignment_role(
        alternative_recipe,
        role="background",
        asset_id=other_background[0],
        asset_code=other_background[1],
        asset_type="background_video",
    )
    alternative_recipe = _replace_assignment_role(
        alternative_recipe,
        role="music",
        asset_id=other_music[0],
        asset_code=other_music[1],
        asset_type="background_music",
    )
    for history_index in range(3):
        _materialize_history_recipe(
            factory_service,
            product_id=product_id,
            recipe_code=f"voicecool_history_{history_index + 1:03d}",
            planned_recipe=alternative_recipe,
        )

    rerun_plan = service.plan_batch(order)
    rerun_voice = next(assignment for assignment in rerun_plan.planned_recipes[0].assignments if assignment.role == "voice")

    assert rerun_voice.asset_id != overused_voice_id


def test_auto_factory_blocks_historical_exact_fingerprint_during_strict_materialization(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="hashblock", product_name="Hash Block"))
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
        batch_code="hashblock_batch",
        product_requests=(AutoFactoryProductRequestDTO(product_code="hashblock", requested_output_count=1),),
    )

    baseline_plan = service.plan_batch(order)
    _materialize_history_recipe(
        factory_service,
        product_id=product_id,
        recipe_code="hashblock_history_001",
        planned_recipe=baseline_plan.planned_recipes[0],
    )

    rerun_plan = service.plan_batch(order)

    assert rerun_plan.summaries[0].planner_feasible_unique_count == 0
    assert rerun_plan.summaries[0].planned_output_count == 0
    assert rerun_plan.summaries[0].limiting_reason == "exact fingerprint history exhausted fresh variants"
    assert rerun_plan.planned_recipes == ()
    with pytest.raises(AutoFactoryCapacityError, match="requested=1, feasible=0"):
        service.materialize_batch(order)


def test_auto_factory_reports_shortfall_and_blocks_strict_materialization(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="tea", product_name="Tea"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library", {"voice_01.mp3": 16.0})
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="foreground_video", asset_code="fg_01", file_name="fg01.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="foreground_video", asset_code="fg_02", file_name="fg02.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="voiceover", asset_code="voice_01", file_name="voice_01.mp3")
    service = _build_auto_factory_service(unit_of_work_factory, tmp_path, {"voice_01.mp3": 16.0})
    order = AutoFactoryBatchOrderDTO(
        batch_code="tea_batch",
        product_requests=(AutoFactoryProductRequestDTO(product_code="tea", requested_output_count=3),),
    )

    plan = service.plan_batch(order)

    assert plan.summaries[0].planner_feasible_unique_count == 2
    assert plan.summaries[0].planned_output_count == 2
    assert plan.summaries[0].shortfall_count == 1
    assert plan.summaries[0].can_fulfill_exactly is False
    with pytest.raises(AutoFactoryCapacityError, match="requested=3, feasible=2"):
        service.materialize_batch(order)


def test_auto_factory_filters_asset_pools_by_required_tag_labels(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="gel", product_name="Gel"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library", {})
    tag_service = TagManagementService(unit_of_work_factory=unit_of_work_factory)
    fg_proof = _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="foreground_video",
        asset_code="fg_proof",
        file_name="fg_proof.mp4",
    )
    fg_hook = _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="foreground_video",
        asset_code="fg_hook",
        file_name="fg_hook.mp4",
    )
    bg_studio = _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="background_video",
        asset_code="bg_studio",
        file_name="bg_studio.mp4",
    )
    _assign_tag_to_asset(tag_service, asset_id=fg_proof, tag_group="message", tag_name="proof")
    _assign_tag_to_asset(tag_service, asset_id=fg_hook, tag_group="message", tag_name="hook")
    _assign_tag_to_asset(tag_service, asset_id=bg_studio, tag_group="scene", tag_name="studio")
    service = _build_auto_factory_service(unit_of_work_factory, tmp_path, {})

    plan = service.plan_batch(
        AutoFactoryBatchOrderDTO(
            batch_code="gel_batch",
            product_requests=(
                AutoFactoryProductRequestDTO(
                    product_code="gel",
                    requested_output_count=1,
                    fixed_duration_sec=15.0,
                    foreground_required_tag_labels=("message:proof",),
                    background_required_tag_labels=("scene:studio",),
                ),
            ),
        )
    )

    assert plan.summaries[0].planner_feasible_unique_count == 1
    assert [assignment.asset_code for assignment in plan.planned_recipes[0].assignments] == [
        "bg_studio",
        "fg_proof",
        "fg_proof",
        "fg_proof",
        "fg_proof",
        "fg_proof",
    ]


def test_auto_factory_reports_truthful_shortfall_when_tag_filters_remove_visual_assets(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="foam", product_name="Foam"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library", {})
    _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="foreground_video",
        asset_code="fg_plain",
        file_name="fg_plain.mp4",
    )
    service = _build_auto_factory_service(unit_of_work_factory, tmp_path, {})

    plan = service.plan_batch(
        AutoFactoryBatchOrderDTO(
            batch_code="foam_batch",
            product_requests=(
                AutoFactoryProductRequestDTO(
                    product_code="foam",
                    requested_output_count=1,
                    fixed_duration_sec=15.0,
                    foreground_required_tag_labels=("message:proof",),
                ),
            ),
        )
    )

    assert plan.summaries[0].planner_feasible_unique_count == 0
    assert plan.summaries[0].limiting_reason == "no ready renderable visual assets matched required tag filters"


def test_auto_factory_materializes_internal_recipes(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="soap", product_name="Soap"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library", {"voice_01.mp3": 14.0})
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="foreground_video", asset_code="fg_01", file_name="fg01.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="foreground_video", asset_code="fg_02", file_name="fg02.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_video", asset_code="bg_01", file_name="bg01.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_music", asset_code="music_01", file_name="music01.mp3")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="voiceover", asset_code="voice_01", file_name="voice_01.mp3")
    factory_service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    service = AutoFactoryBatchService(
        product_service=product_service,
        asset_intake_service=asset_service,
        video_assembly_factory_service=factory_service,
    )

    materialized = service.materialize_batch(
        AutoFactoryBatchOrderDTO(
            batch_code="soap_batch",
            product_requests=(
                AutoFactoryProductRequestDTO(
                    product_code="soap",
                    requested_output_count=2,
                    target_platform="tiktok",
                    target_ratio="9:16",
                ),
            ),
        )
    )

    assert len(materialized.created_recipes) == 2
    recipes = sorted(factory_service.list_recipes(product_id=product_id), key=lambda recipe: recipe.recipe_code)
    assert [recipe.recipe_code for recipe in recipes] == ["soap_soap_batch_001", "soap_soap_batch_002"]
    first_recipe = factory_service.get_recipe(materialized.created_recipes[0].recipe_id)
    assert len(first_recipe.items) == 8
    assert first_recipe.target_platform == "tiktok"
    assert first_recipe.target_ratio == "9:16"
    assert first_recipe.duration_sec == 14.0


def test_auto_factory_uses_fixed_fallback_duration_when_no_voiceover_exists(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="cream", product_name="Cream"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library", {})
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="foreground_video", asset_code="fg_01", file_name="fg01.mp4")
    _register_asset(asset_service, product_id=product_id, tmp_path=tmp_path, asset_type="background_video", asset_code="bg_01", file_name="bg01.mp4")
    service = _build_auto_factory_service(unit_of_work_factory, tmp_path, {})

    plan = service.plan_batch(
        AutoFactoryBatchOrderDTO(
            batch_code="cream_batch",
            product_requests=(
                AutoFactoryProductRequestDTO(
                    product_code="cream",
                    requested_output_count=1,
                    fixed_duration_sec=20.0,
                ),
            ),
        )
    )

    assert plan.planned_recipes[0].duration_source == "fixed_fallback"
    assert plan.planned_recipes[0].duration_sec == 20.0


def test_auto_factory_materializes_and_builds_previews(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="serum", product_name="Serum"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library", {})
    _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="foreground_video",
        asset_code="fg_01",
        file_name="fg01.mp4",
    )
    _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="foreground_video",
        asset_code="fg_02",
        file_name="fg02.mp4",
    )
    _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="background_video",
        asset_code="bg_01",
        file_name="bg01.mp4",
    )
    factory_service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    service = AutoFactoryBatchService(
        product_service=product_service,
        asset_intake_service=asset_service,
        video_assembly_factory_service=factory_service,
    )

    execution = service.materialize_batch_and_build_previews(
        AutoFactoryBatchOrderDTO(
            batch_code="serum_batch",
            product_requests=(
                AutoFactoryProductRequestDTO(
                    product_code="serum",
                    requested_output_count=2,
                    target_platform="shopee",
                    target_ratio="9:16",
                    fixed_duration_sec=15.0,
                ),
            ),
        )
    )

    assert len(execution.materialization.created_recipes) == 2
    assert execution.preview_production.succeeded_recipe_count == 2
    assert execution.preview_production.failed_recipe_count == 0
    assert len(execution.preview_production.recipe_results) == 2
    assert all(result.job_status == "done" for result in execution.preview_production.recipe_results)
    assert all(result.output_id is not None for result in execution.preview_production.recipe_results)
    assert all(result.output_code is not None for result in execution.preview_production.recipe_results)
    assert all(result.output_path is not None for result in execution.preview_production.recipe_results)
    assert all(Path(result.output_path or "").exists() for result in execution.preview_production.recipe_results)
    assert all(result.recipe_status == "candidate" for result in execution.preview_production.recipe_results)
    assert all(result.review_required is False for result in execution.preview_production.recipe_results)


def test_auto_factory_preview_batch_reports_failures_and_continues(unit_of_work_factory, tmp_path) -> None:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="mask", product_name="Mask"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library", {})
    _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="foreground_video",
        asset_code="fg_01",
        file_name="fg01.mp4",
    )
    _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="foreground_video",
        asset_code="fg_02",
        file_name="fg02.mp4",
    )
    _register_asset(
        asset_service,
        product_id=product_id,
        tmp_path=tmp_path,
        asset_type="background_video",
        asset_code="bg_01",
        file_name="bg01.mp4",
    )
    factory_service = _build_factory_service(
        unit_of_work_factory,
        tmp_path / "previews",
        fail_preview_stems={"mask_mask_batch_002"},
    )
    service = AutoFactoryBatchService(
        product_service=product_service,
        asset_intake_service=asset_service,
        video_assembly_factory_service=factory_service,
    )

    execution = service.materialize_batch_and_build_previews(
        AutoFactoryBatchOrderDTO(
            batch_code="mask_batch",
            product_requests=(
                AutoFactoryProductRequestDTO(
                    product_code="mask",
                    requested_output_count=2,
                    target_platform="shopee",
                    target_ratio="9:16",
                    fixed_duration_sec=15.0,
                ),
            ),
        )
    )

    assert execution.preview_production.succeeded_recipe_count == 1
    assert execution.preview_production.failed_recipe_count == 1
    success_result = next(result for result in execution.preview_production.recipe_results if result.job_status == "done")
    failed_result = next(result for result in execution.preview_production.recipe_results if result.job_status == "failed")
    assert success_result.output_path is not None
    assert Path(success_result.output_path).exists()
    assert failed_result.output_id is None
    assert failed_result.output_code is None
    assert failed_result.output_path is None
    assert failed_result.error_message is not None
    assert "synthetic preview failure" in failed_result.error_message
