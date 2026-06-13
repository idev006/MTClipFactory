from __future__ import annotations

from pathlib import Path

import pytest

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.factory.auto_factory import (
    AutoFactoryBatchService,
    AutoFactoryCapacityError,
)
from mt_clip_factory.factory.auto_factory_dto import (
    AutoFactoryBatchOrderDTO,
    AutoFactoryProductRequestDTO,
)
from mt_clip_factory.factory.preview_artifacts import PreviewManifestBuilder
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
    return VideoAssemblyFactoryService(
        unit_of_work_factory=unit_of_work_factory,
        preview_manifest_builder=PreviewManifestBuilder(preview_root),
        preview_renderer=object(),
        final_renderer=object(),
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
