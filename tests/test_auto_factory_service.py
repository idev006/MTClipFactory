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
        ) -> RenderedPreviewOutput:
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

            output_dir = preview_root / product_code / "videos"
            output_dir.mkdir(parents=True, exist_ok=True)
            target_path = output_dir / f"{output_stem}.mp4"
            payload = (
                b"".join(segment.source_file.read_bytes() for segment in segment_clips)
                if segment_clips
                else source_files[0].read_bytes()
            )
            target_path.write_bytes(payload)
            duration_sec = round(sum(segment.target_duration_sec for segment in segment_clips), 3) if segment_clips else 3.0
            return RenderedPreviewOutput(
                file_path=target_path,
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
