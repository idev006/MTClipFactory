from __future__ import annotations

from pathlib import Path

import pytest

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.factory.dto import AssignAssetToRecipeCommand, CreateRecipeCommand
from mt_clip_factory.factory.preview_artifacts import PreviewManifestBuilder
from mt_clip_factory.factory.renderers import RenderedPreviewOutput
from mt_clip_factory.factory.services import (
    FinalRenderPrerequisiteError,
    PreviewBuildInputError,
    RecipeAlreadyExistsError,
    RecipeApprovalError,
    VideoAssemblyFactoryService,
)
from mt_clip_factory.library.contracts import AnalyzedMediaMetadata
from mt_clip_factory.library.dto import RegisterAssetCommand
from mt_clip_factory.library.readiness import AssetReadinessEvaluator
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.storage import LocalAssetStorage


class FakeMetadataAnalyzer:
    def analyze(self, file_path: Path) -> AnalyzedMediaMetadata:
        return AnalyzedMediaMetadata(
            duration_sec=3.0,
            width=1920,
            height=1080,
            fps=30.0,
            ratio="16:9",
            file_size_mb=round(file_path.stat().st_size / (1024 * 1024), 4),
            codec="h264",
            has_audio=True,
        )


def _build_asset_service(unit_of_work_factory, media_root: Path) -> AssetIntakeService:
    return AssetIntakeService(
        unit_of_work_factory=unit_of_work_factory,
        asset_storage=LocalAssetStorage(media_root),
        metadata_analyzer=FakeMetadataAnalyzer(),
        readiness_evaluator=AssetReadinessEvaluator(),
    )


def _build_factory_service(unit_of_work_factory, preview_root: Path) -> VideoAssemblyFactoryService:
    class FakePreviewRenderer:
        def render_output(self, *, product_code: str, output_stem: str, source_files: list[Path]) -> RenderedPreviewOutput:
            output_dir = preview_root / product_code / "videos"
            output_dir.mkdir(parents=True, exist_ok=True)
            target_path = output_dir / f"{output_stem}.mp4"
            target_path.write_bytes(source_files[0].read_bytes())
            return RenderedPreviewOutput(file_path=target_path, duration_sec=3.0)

    return VideoAssemblyFactoryService(
        unit_of_work_factory=unit_of_work_factory,
        preview_manifest_builder=PreviewManifestBuilder(preview_root),
        preview_renderer=FakePreviewRenderer(),
        final_renderer=FakePreviewRenderer(),
    )


def _register_ready_asset(unit_of_work_factory, tmp_path: Path) -> tuple[int, int]:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library")
    source_file = tmp_path / "hero.mp4"
    source_file.write_bytes(b"video-bytes")
    asset_id = asset_service.register_asset(
        RegisterAssetCommand(
            product_id=product_id,
            asset_type="background_video",
            source_file_path=source_file,
            asset_code="hero_asset",
        )
    )
    return product_id, asset_id


def test_factory_service_creates_and_lists_recipe(unit_of_work_factory, tmp_path) -> None:
    product_id, _ = _register_ready_asset(unit_of_work_factory, tmp_path)
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")

    recipe_id = service.create_recipe(
        CreateRecipeCommand(
            product_id=product_id,
            recipe_code="Honey Launch",
            target_platform="tiktok",
            target_ratio="9:16",
        )
    )

    recipes = service.list_recipes()
    assert recipe_id == 1
    assert len(recipes) == 1
    assert recipes[0].recipe_code == "honey_launch"
    assert recipes[0].item_count == 0


def test_factory_service_rejects_duplicate_recipe_code(unit_of_work_factory, tmp_path) -> None:
    product_id, _ = _register_ready_asset(unit_of_work_factory, tmp_path)
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))

    with pytest.raises(RecipeAlreadyExistsError):
        service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))


def test_factory_service_assigns_asset_and_returns_recipe_details(unit_of_work_factory, tmp_path) -> None:
    product_id, asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))

    item_id = service.assign_asset_to_recipe(
        AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role="hero")
    )

    recipe = service.get_recipe(recipe_id)
    assert item_id == 1
    assert len(recipe.items) == 1
    assert recipe.items[0].asset_code == "hero_asset"
    assert recipe.items[0].role == "hero"


def test_factory_service_builds_preview_output_job(unit_of_work_factory, tmp_path) -> None:
    product_id, asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role="hero"))

    job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(job_id)

    jobs = service.list_preview_jobs()
    recipe = service.get_recipe(recipe_id)
    outputs = service.list_outputs(recipe_id=recipe_id)
    products = ProductApplicationService(unit_of_work_factory=unit_of_work_factory).list_products()
    assert jobs[0].job_id == job_id
    assert jobs[0].job_type == "render_recipe_preview"
    assert jobs[0].status == "done"
    assert jobs[0].output_path is not None
    assert Path(jobs[0].output_path).exists()
    assert jobs[0].output_path.endswith(".mp4")
    assert recipe.status == "candidate"
    assert len(outputs) == 1
    assert outputs[0].approved is False
    assert products[0].output_count == 1


def test_factory_service_marks_preview_job_failed_when_recipe_has_no_items(unit_of_work_factory, tmp_path) -> None:
    product_id, _ = _register_ready_asset(unit_of_work_factory, tmp_path)
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))
    job_id = service.enqueue_preview_job(recipe_id)

    with pytest.raises(PreviewBuildInputError, match="has no items"):
        service.run_preview_job(job_id)

    jobs = service.list_preview_jobs(status="failed")
    assert len(jobs) == 1
    assert jobs[0].job_id == job_id
    assert jobs[0].error_message is not None


def test_factory_service_requires_approved_output_before_approving_recipe(unit_of_work_factory, tmp_path) -> None:
    product_id, asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role="hero"))
    preview_job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(preview_job_id)

    with pytest.raises(RecipeApprovalError, match="Approve at least one output"):
        service.approve_recipe(recipe_id)


def test_factory_service_approves_output_and_recipe(unit_of_work_factory, tmp_path) -> None:
    product_id, asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role="hero"))
    preview_job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(preview_job_id)
    output_id = service.list_outputs(recipe_id=recipe_id)[0].output_id

    service.approve_output(output_id)
    service.approve_recipe(recipe_id)

    recipe = service.get_recipe(recipe_id)
    outputs = service.list_outputs(recipe_id=recipe_id, approved=True)
    assert recipe.status == "approved"
    assert len(outputs) == 1


def test_factory_service_rejects_recipe(unit_of_work_factory, tmp_path) -> None:
    product_id, _ = _register_ready_asset(unit_of_work_factory, tmp_path)
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))

    service.reject_recipe(recipe_id)

    recipe = service.get_recipe(recipe_id)
    assert recipe.status == "rejected"


def test_factory_service_blocks_final_render_until_recipe_is_approved(unit_of_work_factory, tmp_path) -> None:
    product_id, asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role="hero"))

    with pytest.raises(FinalRenderPrerequisiteError, match="Approve the recipe"):
        service.enqueue_final_render_job(recipe_id)


def test_factory_service_builds_final_render_job(unit_of_work_factory, tmp_path) -> None:
    product_id, asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role="hero"))
    preview_job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(preview_job_id)
    output_id = service.list_outputs(recipe_id=recipe_id)[0].output_id
    service.approve_output(output_id)
    service.approve_recipe(recipe_id)

    final_job_id = service.enqueue_final_render_job(recipe_id)
    service.run_final_render_job(final_job_id)

    jobs = service.list_final_render_jobs()
    outputs = service.list_outputs(recipe_id=recipe_id)
    products = ProductApplicationService(unit_of_work_factory=unit_of_work_factory).list_products()
    assert jobs[0].job_id == final_job_id
    assert jobs[0].job_type == "render_recipe_final"
    assert jobs[0].status == "done"
    assert jobs[0].output_path is not None
    assert jobs[0].output_path.endswith(".mp4")
    assert len(outputs) == 2
    assert outputs[0].approved is True
    assert products[0].output_count == 2
