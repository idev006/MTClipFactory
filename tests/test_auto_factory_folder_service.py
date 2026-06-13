from __future__ import annotations

from pathlib import Path

import pytest

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.factory.audio_composition import PreviewAudioMixPlan
from mt_clip_factory.factory.auto_factory import AutoFactoryBatchService, AutoFactoryCapacityError
from mt_clip_factory.factory.auto_factory_folder import AutoFactoryFolderContractError, AutoFactoryFolderService
from mt_clip_factory.factory.preview_composition import PreviewSegmentClip
from mt_clip_factory.factory.preview_artifacts import PreviewManifestBuilder
from mt_clip_factory.factory.renderers import RenderedPreviewOutput
from mt_clip_factory.factory.services import VideoAssemblyFactoryService
from mt_clip_factory.library.contracts import AnalyzedMediaMetadata
from mt_clip_factory.library.readiness import AssetReadinessEvaluator
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.storage import LocalAssetStorage


class FolderMetadataAnalyzer:
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


def _build_services(unit_of_work_factory, tmp_path: Path, durations_by_name: dict[str, float]):
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    asset_service = AssetIntakeService(
        unit_of_work_factory=unit_of_work_factory,
        asset_storage=LocalAssetStorage(tmp_path / "media_library"),
        metadata_analyzer=FolderMetadataAnalyzer(durations_by_name),
        readiness_evaluator=AssetReadinessEvaluator(),
    )
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
        ) -> RenderedPreviewOutput:
            del audio_mix_plan, target_ratio
            output_dir = tmp_path / "previews" / product_code / "videos"
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
    factory_service = VideoAssemblyFactoryService(
        unit_of_work_factory=unit_of_work_factory,
        preview_manifest_builder=PreviewManifestBuilder(tmp_path / "previews"),
        preview_renderer=renderer,
        final_renderer=renderer,
    )
    auto_factory_service = AutoFactoryBatchService(
        product_service=product_service,
        asset_intake_service=asset_service,
        video_assembly_factory_service=factory_service,
    )
    folder_service = AutoFactoryFolderService(
        product_service=product_service,
        asset_intake_service=asset_service,
        auto_factory_service=auto_factory_service,
    )
    return product_service, asset_service, factory_service, folder_service


def _write_product_folder(
    batch_root: Path,
    *,
    folder_name: str,
    product_code: str,
    product_name: str,
    requested_output_count: int,
    with_background: bool = True,
    with_music: bool = True,
    with_voice: bool = True,
) -> Path:
    product_dir = batch_root / folder_name
    product_dir.mkdir(parents=True, exist_ok=True)
    (product_dir / "product.toml").write_text(
        "\n".join(
            [
                "[product]",
                f'product_code = "{product_code}"',
                f'product_name = "{product_name}"',
                'default_platform = "shopee"',
            ]
        ),
        encoding="utf-8",
    )
    (product_dir / "pipeline.toml").write_text(
        "\n".join(
            [
                "[request]",
                f"requested_output_count = {requested_output_count}",
                'target_platform = "shopee"',
                'target_ratio = "9:16"',
                'uniqueness_scope = "batch"',
                'duration_mode = "voice_with_bounds"',
                "min_duration_sec = 12.0",
                "max_duration_sec = 30.0",
            ]
        ),
        encoding="utf-8",
    )
    (product_dir / "foreground").mkdir(exist_ok=True)
    (product_dir / "foreground" / "hook_a.mp4").write_bytes(b"fg1")
    (product_dir / "foreground" / "hook_b.mp4").write_bytes(b"fg2")
    if with_background:
        (product_dir / "background").mkdir(exist_ok=True)
        (product_dir / "background" / "bg_a.mp4").write_bytes(b"bg1")
    if with_music:
        (product_dir / "music").mkdir(exist_ok=True)
        (product_dir / "music" / "music_a.mp3").write_bytes(b"music1")
    if with_voice:
        (product_dir / "voice").mkdir(exist_ok=True)
        (product_dir / "voice" / "voice_a.mp3").write_bytes(b"voice1")
    return product_dir


def test_folder_service_creates_products_registers_assets_and_materializes_batch(unit_of_work_factory, tmp_path) -> None:
    _, asset_service, factory_service, folder_service = _build_services(
        unit_of_work_factory,
        tmp_path,
        {"voice_a.mp3": 17.4},
    )
    batch_root = tmp_path / "batch_root"
    _write_product_folder(
        batch_root,
        folder_name="ProductA",
        product_code="product_a",
        product_name="Product A",
        requested_output_count=2,
    )

    report = folder_service.run_batch_root(batch_root)

    assert report.batch_code == "batch_root"
    assert report.scan_depth == 1
    assert len(report.product_reports) == 1
    assert report.product_reports[0].created_product is True
    assert report.product_reports[0].registered_asset_count == 5
    assert report.discovered_product_dirs == (str(batch_root / "ProductA"),)
    assert report.materialization is not None
    assert len(report.materialization.created_recipes) == 2
    recipes = sorted(factory_service.list_recipes(), key=lambda recipe: recipe.recipe_code)
    assert [recipe.recipe_code for recipe in recipes] == ["product_a_batch_root_001", "product_a_batch_root_002"]
    assets = sorted(asset_service.list_assets(), key=lambda asset: asset.asset_code)
    assert [asset.asset_code for asset in assets] == [
        "product_a_bg_bg_a",
        "product_a_fg_hook_a",
        "product_a_fg_hook_b",
        "product_a_music_music_a",
        "product_a_voice_voice_a",
    ]


def test_folder_service_skips_existing_assets_when_rerun(unit_of_work_factory, tmp_path) -> None:
    _, asset_service, _, folder_service = _build_services(
        unit_of_work_factory,
        tmp_path,
        {"voice_a.mp3": 15.0},
    )
    batch_root = tmp_path / "batch_root"
    _write_product_folder(
        batch_root,
        folder_name="ProductA",
        product_code="product_a",
        product_name="Product A",
        requested_output_count=2,
    )

    first_report = folder_service.run_batch_root(batch_root, materialize=False)
    second_report = folder_service.run_batch_root(batch_root, materialize=False)

    assert first_report.product_reports[0].registered_asset_count == 5
    assert second_report.product_reports[0].registered_asset_count == 0
    assert second_report.product_reports[0].skipped_existing_asset_count == 5
    assert len(asset_service.list_assets()) == 5


def test_folder_service_propagates_capacity_shortfall(unit_of_work_factory, tmp_path) -> None:
    _, _, _, folder_service = _build_services(
        unit_of_work_factory,
        tmp_path,
        {"voice_a.mp3": 15.0},
    )
    batch_root = tmp_path / "batch_root"
    _write_product_folder(
        batch_root,
        folder_name="ProductA",
        product_code="product_a",
        product_name="Product A",
        requested_output_count=3,
        with_background=False,
        with_music=False,
        with_voice=True,
    )

    with pytest.raises(AutoFactoryCapacityError, match="requested=3, feasible=2"):
        folder_service.run_batch_root(batch_root)


def test_folder_service_builds_one_batch_order_from_multiple_product_dirs(unit_of_work_factory, tmp_path) -> None:
    product_service, _, factory_service, folder_service = _build_services(
        unit_of_work_factory,
        tmp_path,
        {"voice_a.mp3": 15.0, "voice_b.mp3": 19.0},
    )
    batch_root = tmp_path / "batch_root"
    _write_product_folder(
        batch_root,
        folder_name="ProductA",
        product_code="product_a",
        product_name="Product A",
        requested_output_count=2,
    )
    _write_product_folder(
        batch_root,
        folder_name="ProductB",
        product_code="product_b",
        product_name="Product B",
        requested_output_count=2,
    )
    (batch_root / "ProductB" / "voice" / "voice_a.mp3").unlink()
    (batch_root / "ProductB" / "voice" / "voice_b.mp3").write_bytes(b"voice2")

    report = folder_service.run_batch_root(batch_root)

    assert len(report.order.product_requests) == 2
    assert {request.product_code for request in report.order.product_requests} == {"product_a", "product_b"}
    assert len(product_service.list_products()) == 2
    assert len(factory_service.list_recipes()) == 4


def test_folder_service_can_materialize_and_build_previews(unit_of_work_factory, tmp_path) -> None:
    _, _, _, folder_service = _build_services(
        unit_of_work_factory,
        tmp_path,
        {"voice_a.mp3": 17.2},
    )
    batch_root = tmp_path / "batch_root"
    _write_product_folder(
        batch_root,
        folder_name="ProductA",
        product_code="product_a",
        product_name="Product A",
        requested_output_count=2,
    )

    report = folder_service.run_batch_root(batch_root, build_previews=True)

    assert report.materialization is not None
    assert report.preview_production is not None
    assert report.preview_production.succeeded_recipe_count == 2
    assert report.preview_production.failed_recipe_count == 0
    assert all(result.output_path is not None for result in report.preview_production.recipe_results)
    assert all(Path(result.output_path or "").exists() for result in report.preview_production.recipe_results)


def test_folder_service_rejects_preview_request_without_materialization(unit_of_work_factory, tmp_path) -> None:
    _, _, _, folder_service = _build_services(unit_of_work_factory, tmp_path, {})
    batch_root = tmp_path / "batch_root"
    _write_product_folder(
        batch_root,
        folder_name="ProductA",
        product_code="product_a",
        product_name="Product A",
        requested_output_count=1,
    )

    with pytest.raises(AutoFactoryFolderContractError, match="build_previews requires materialize=True"):
        folder_service.run_batch_root(batch_root, materialize=False, build_previews=True)


def test_folder_service_rejects_missing_request_section(unit_of_work_factory, tmp_path) -> None:
    _, _, _, folder_service = _build_services(unit_of_work_factory, tmp_path, {})
    batch_root = tmp_path / "batch_root"
    product_dir = batch_root / "BrokenProduct"
    product_dir.mkdir(parents=True)
    (product_dir / "product.toml").write_text(
        "\n".join(
            [
                "[product]",
                'product_code = "broken"',
                'product_name = "Broken Product"',
            ]
        ),
        encoding="utf-8",
    )
    (product_dir / "pipeline.toml").write_text("[not_request]\nrequested_output_count = 1\n", encoding="utf-8")

    with pytest.raises(AutoFactoryFolderContractError, match="Missing \\[request\\] section"):
        folder_service.run_batch_root(batch_root, materialize=False)


def test_folder_service_can_discover_root_level_product_folder_at_depth_zero(unit_of_work_factory, tmp_path) -> None:
    product_service, asset_service, _, folder_service = _build_services(
        unit_of_work_factory,
        tmp_path,
        {"voice_a.mp3": 12.0},
    )
    batch_root = tmp_path / "single_product_root"
    _write_product_folder(
        batch_root.parent,
        folder_name=batch_root.name,
        product_code="root_product",
        product_name="Root Product",
        requested_output_count=1,
    )

    report = folder_service.run_batch_root(batch_root, scan_depth=0, materialize=False)

    assert report.scan_depth == 0
    assert report.discovered_product_dirs == (str(batch_root),)
    assert [product.product_code for product in product_service.list_products()] == ["root_product"]
    assert sorted(asset.asset_code for asset in asset_service.list_assets()) == [
        "root_product_bg_bg_a",
        "root_product_fg_hook_a",
        "root_product_fg_hook_b",
        "root_product_music_music_a",
        "root_product_voice_voice_a",
    ]


def test_folder_service_can_discover_nested_product_folders_up_to_requested_depth(unit_of_work_factory, tmp_path) -> None:
    product_service, _, _, folder_service = _build_services(
        unit_of_work_factory,
        tmp_path,
        {"voice_a.mp3": 12.0},
    )
    batch_root = tmp_path / "nested_batch_root"
    nested_parent = batch_root / "group_a" / "campaign_x"
    _write_product_folder(
        nested_parent,
        folder_name="ProductNested",
        product_code="nested_product",
        product_name="Nested Product",
        requested_output_count=1,
    )

    with pytest.raises(AutoFactoryFolderContractError, match="No product folders were found"):
        folder_service.run_batch_root(batch_root, scan_depth=1, materialize=False)

    report = folder_service.run_batch_root(batch_root, scan_depth=3, materialize=False)

    assert report.discovered_product_dirs == (str(nested_parent / "ProductNested"),)
    assert [product.product_code for product in product_service.list_products()] == ["nested_product"]


def test_folder_service_rejects_negative_scan_depth(unit_of_work_factory, tmp_path) -> None:
    _, _, _, folder_service = _build_services(unit_of_work_factory, tmp_path, {})
    batch_root = tmp_path / "batch_root"
    batch_root.mkdir(parents=True)

    with pytest.raises(AutoFactoryFolderContractError, match="scan_depth must be >= 0"):
        folder_service.run_batch_root(batch_root, scan_depth=-1, materialize=False)


def test_folder_service_reads_optional_selection_tags_into_order(unit_of_work_factory, tmp_path) -> None:
    _, _, _, folder_service = _build_services(unit_of_work_factory, tmp_path, {})
    batch_root = tmp_path / "batch_root"
    product_dir = _write_product_folder(
        batch_root,
        folder_name="ProductA",
        product_code="product_a",
        product_name="Product A",
        requested_output_count=1,
    )
    (product_dir / "pipeline.toml").write_text(
        "\n".join(
            [
                "[request]",
                "requested_output_count = 1",
                'target_platform = "shopee"',
                'target_ratio = "9:16"',
                'uniqueness_scope = "batch"',
                'duration_mode = "voice_with_bounds"',
                "min_duration_sec = 12.0",
                "max_duration_sec = 30.0",
                "",
                "[selection_tags]",
                'foreground = ["message:proof"]',
                'background = ["scene:studio"]',
                'music = ["mood:warm"]',
                'voice = ["language:th"]',
            ]
        ),
        encoding="utf-8",
    )

    report = folder_service.run_batch_root(batch_root, materialize=False)

    product_request = report.order.product_requests[0]
    assert product_request.foreground_required_tag_labels == ("message:proof",)
    assert product_request.background_required_tag_labels == ("scene:studio",)
    assert product_request.music_required_tag_labels == ("mood:warm",)
    assert product_request.voice_required_tag_labels == ("language:th",)
