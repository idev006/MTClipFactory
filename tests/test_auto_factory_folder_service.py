from __future__ import annotations

from pathlib import Path

import pytest

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.factory.audio_composition import PreviewAudioMixPlan
from mt_clip_factory.factory.auto_factory import AutoFactoryBatchService, AutoFactoryCapacityError
from mt_clip_factory.factory.auto_factory_folder import AutoFactoryFolderContractError, AutoFactoryFolderService
from mt_clip_factory.factory.caption_runtime import ProductAutomationMetadataStore
from mt_clip_factory.factory.preview_composition import PreviewSegmentClip
from mt_clip_factory.factory.preview_artifacts import PreviewManifestBuilder
from mt_clip_factory.factory.product_run_store import ProductRunArtifactStore
from mt_clip_factory.factory.renderers import RenderedPreviewOutput
from mt_clip_factory.factory.services import VideoAssemblyFactoryService
from mt_clip_factory.library.contracts import AnalyzedMediaMetadata
from mt_clip_factory.library.readiness import AssetReadinessEvaluator
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.storage import LocalAssetStorage
from mt_clip_factory.library.tag_services import TagManagementService


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
    tag_service = TagManagementService(unit_of_work_factory=unit_of_work_factory)
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
            del audio_mix_plan, target_ratio, fill_policies
            resolved_target_path = target_path or (tmp_path / "previews" / product_code / "videos" / f"{output_stem}.mp4")
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
    automation_metadata_store = ProductAutomationMetadataStore(tmp_path / "media_library")
    folder_service = AutoFactoryFolderService(
        product_service=product_service,
        asset_intake_service=asset_service,
        auto_factory_service=auto_factory_service,
        tag_management_service=tag_service,
        automation_metadata_store=automation_metadata_store,
        run_artifact_store=ProductRunArtifactStore(metadata_store=automation_metadata_store),
    )
    return product_service, asset_service, factory_service, folder_service, tag_service


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
    use_v2_layout: bool = False,
) -> Path:
    product_dir = batch_root / folder_name
    product_dir.mkdir(parents=True, exist_ok=True)
    contracts_dir = product_dir / "contracts" if use_v2_layout else product_dir
    assets_root_dir = product_dir / "assets" if use_v2_layout else product_dir
    contracts_dir.mkdir(parents=True, exist_ok=True)
    assets_root_dir.mkdir(parents=True, exist_ok=True)
    (contracts_dir / "product.toml").write_text(
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
    (contracts_dir / "pipeline.toml").write_text(
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
    (assets_root_dir / "foreground").mkdir(parents=True, exist_ok=True)
    (assets_root_dir / "foreground" / "hook_a.mp4").write_bytes(b"fg1")
    (assets_root_dir / "foreground" / "hook_b.mp4").write_bytes(b"fg2")
    if with_background:
        (assets_root_dir / "background").mkdir(parents=True, exist_ok=True)
        (assets_root_dir / "background" / "bg_a.mp4").write_bytes(b"bg1")
    if with_music:
        (assets_root_dir / "music").mkdir(parents=True, exist_ok=True)
        (assets_root_dir / "music" / "music_a.mp3").write_bytes(b"music1")
    if with_voice:
        (assets_root_dir / "voice").mkdir(parents=True, exist_ok=True)
        (assets_root_dir / "voice" / "voice_a.mp3").write_bytes(b"voice1")
    return product_dir


def _write_tags_toml(folder_path: Path, *, global_tags: list[str], file_tags: dict[str, list[str]]) -> None:
    lines: list[str] = ["global_tags = ["]
    lines.extend(f'  "{tag}",' for tag in global_tags)
    lines.append("]")
    lines.append("")
    lines.append("[file_tags]")
    for file_name, tags in file_tags.items():
        rendered_tags = ", ".join(f'"{tag}"' for tag in tags)
        lines.append(f'"{file_name}" = [{rendered_tags}]')
    (folder_path / "tags.toml").write_text("\n".join(lines), encoding="utf-8")


def _write_captions_toml(product_dir: Path, *, main_text: str = "พลังบวกทุกวัน") -> None:
    contracts_dir = product_dir / "contracts" if (product_dir / "contracts").exists() else product_dir
    (contracts_dir / "captions.toml").write_text(
        "\n".join(
            [
                "[caption_selection]",
                'mode = "random_with_seed"',
                "",
                "[caption_pools.hook]",
                f'main = ["{main_text}"]',
                'sub = ["เริ่มต้นวันใหม่"]',
                "",
                "[caption_properties.main]",
                'font_family = "THSarabun"',
                "",
                "[caption_properties.sub]",
                'font_family = "THSarabun"',
            ]
        ),
        encoding="utf-8",
    )


def test_folder_service_creates_products_registers_assets_and_materializes_batch(unit_of_work_factory, tmp_path) -> None:
    _, asset_service, factory_service, folder_service, _ = _build_services(
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
    _, asset_service, _, folder_service, _ = _build_services(
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


def test_folder_service_syncs_caption_contract_into_runtime_metadata(unit_of_work_factory, tmp_path) -> None:
    _, _, _, folder_service, _ = _build_services(
        unit_of_work_factory,
        tmp_path,
        {"voice_a.mp3": 15.0},
    )
    batch_root = tmp_path / "batch_root"
    product_dir = _write_product_folder(
        batch_root,
        folder_name="ProductA",
        product_code="product_a",
        product_name="Product A",
        requested_output_count=1,
    )
    _write_captions_toml(product_dir, main_text="ข้อความชุดแรก")

    folder_service.run_batch_root(batch_root, materialize=False)
    runtime_caption_path = tmp_path / "media_library" / "products" / "product_a" / "automation" / "captions.toml"

    assert runtime_caption_path.exists()
    assert "ข้อความชุดแรก" in runtime_caption_path.read_text(encoding="utf-8")

    (product_dir / "captions.toml").unlink()
    folder_service.run_batch_root(batch_root, materialize=False)

    assert not runtime_caption_path.exists()


def test_folder_service_syncs_pipeline_context_and_writes_run_snapshot(unit_of_work_factory, tmp_path) -> None:
    _, _, _, folder_service, _ = _build_services(unit_of_work_factory, tmp_path, {})
    batch_root = tmp_path / "batch_root"
    product_dir = _write_product_folder(
        batch_root,
        folder_name="ProductA",
        product_code="product_a",
        product_name="Product A",
        requested_output_count=2,
    )

    folder_service.run_batch_root(batch_root, batch_code="product_a_batch", materialize=False)

    cached_pipeline_path = tmp_path / "media_library" / "products" / "product_a" / "automation" / "pipeline.toml"
    cached_context_path = tmp_path / "media_library" / "products" / "product_a" / "automation" / "context.toml"
    order_snapshot_path = product_dir / "runs" / "product_a_batch" / "order_snapshot.toml"
    journal_path = product_dir / "runs" / "product_a_batch" / "journal.toml"

    assert cached_pipeline_path.exists()
    assert cached_context_path.exists()
    assert order_snapshot_path.exists()
    assert journal_path.exists()
    assert 'source_product_dir = "' in cached_context_path.read_text(encoding="utf-8")
    assert "requested_output_count = 2" in order_snapshot_path.read_text(encoding="utf-8")
    assert 'event_type = "intake_completed"' in journal_path.read_text(encoding="utf-8")


def test_folder_service_propagates_capacity_shortfall(unit_of_work_factory, tmp_path) -> None:
    _, _, _, folder_service, _ = _build_services(
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
    product_service, _, factory_service, folder_service, _ = _build_services(
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
    _, _, _, folder_service, _ = _build_services(
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
    _, _, _, folder_service, _ = _build_services(unit_of_work_factory, tmp_path, {})
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
    _, _, _, folder_service, _ = _build_services(unit_of_work_factory, tmp_path, {})
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
    product_service, asset_service, _, folder_service, _ = _build_services(
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


def test_folder_service_can_discover_v2_contracts_and_assets(unit_of_work_factory, tmp_path) -> None:
    product_service, asset_service, _, folder_service, _ = _build_services(
        unit_of_work_factory,
        tmp_path,
        {"voice_a.mp3": 12.0},
    )
    batch_root = tmp_path / "v2_batch_root"
    product_dir = _write_product_folder(
        batch_root,
        folder_name="ProductV2",
        product_code="product_v2",
        product_name="Product V2",
        requested_output_count=1,
        use_v2_layout=True,
    )
    _write_captions_toml(product_dir, main_text="ข้อความ v2")

    report = folder_service.run_batch_root(batch_root, materialize=False)

    runtime_caption_path = tmp_path / "media_library" / "products" / "product_v2" / "automation" / "captions.toml"
    assert report.discovered_product_dirs == (str(batch_root / "ProductV2"),)
    assert [product.product_code for product in product_service.list_products()] == ["product_v2"]
    assert sorted(asset.asset_code for asset in asset_service.list_assets()) == [
        "product_v2_bg_bg_a",
        "product_v2_fg_hook_a",
        "product_v2_fg_hook_b",
        "product_v2_music_music_a",
        "product_v2_voice_voice_a",
    ]
    assert runtime_caption_path.exists()
    assert "ข้อความ v2" in runtime_caption_path.read_text(encoding="utf-8")


def test_folder_service_rejects_ambiguous_contract_layout(unit_of_work_factory, tmp_path) -> None:
    _, _, _, folder_service, _ = _build_services(unit_of_work_factory, tmp_path, {"voice_a.mp3": 12.0})
    batch_root = tmp_path / "ambiguous_contract_batch"
    product_dir = _write_product_folder(
        batch_root,
        folder_name="ProductAmbiguous",
        product_code="product_ambiguous",
        product_name="Product Ambiguous",
        requested_output_count=1,
        use_v2_layout=True,
    )
    (product_dir / "product.toml").write_text(
        (product_dir / "contracts" / "product.toml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    with pytest.raises(AutoFactoryFolderContractError, match="Ambiguous product folder layout"):
        folder_service.run_batch_root(batch_root, materialize=False)


def test_folder_service_rejects_ambiguous_asset_layout(unit_of_work_factory, tmp_path) -> None:
    _, _, _, folder_service, _ = _build_services(unit_of_work_factory, tmp_path, {"voice_a.mp3": 12.0})
    batch_root = tmp_path / "ambiguous_asset_batch"
    product_dir = _write_product_folder(
        batch_root,
        folder_name="ProductAmbiguous",
        product_code="product_ambiguous",
        product_name="Product Ambiguous",
        requested_output_count=1,
        use_v2_layout=True,
    )
    (product_dir / "foreground").mkdir(exist_ok=True)
    (product_dir / "foreground" / "duplicate.mp4").write_bytes(b"dup")

    with pytest.raises(AutoFactoryFolderContractError, match="Ambiguous product folder layout"):
        folder_service.run_batch_root(batch_root, materialize=False)


def test_folder_service_can_discover_nested_product_folders_up_to_requested_depth(unit_of_work_factory, tmp_path) -> None:
    product_service, _, _, folder_service, _ = _build_services(
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
    _, _, _, folder_service, _ = _build_services(unit_of_work_factory, tmp_path, {})
    batch_root = tmp_path / "batch_root"
    batch_root.mkdir(parents=True)

    with pytest.raises(AutoFactoryFolderContractError, match="scan_depth must be >= 0"):
        folder_service.run_batch_root(batch_root, scan_depth=-1, materialize=False)


def test_folder_service_reads_optional_selection_tags_into_order(unit_of_work_factory, tmp_path) -> None:
    _, _, _, folder_service, _ = _build_services(unit_of_work_factory, tmp_path, {})
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


def test_folder_service_applies_folder_tag_metadata_to_registered_assets(unit_of_work_factory, tmp_path) -> None:
    _, asset_service, _, folder_service, _ = _build_services(
        unit_of_work_factory,
        tmp_path,
        {"voice_a.mp3": 15.0},
    )
    batch_root = tmp_path / "batch_root"
    product_dir = _write_product_folder(
        batch_root,
        folder_name="ProductA",
        product_code="product_a",
        product_name="Product A",
        requested_output_count=1,
    )
    _write_tags_toml(
        product_dir / "foreground",
        global_tags=["role:foreground", "product:product_a"],
        file_tags={"hook_a.mp4": ["message:hook", "mood:exciting"]},
    )

    folder_service.run_batch_root(batch_root, materialize=False)

    assets_by_code = {asset.asset_code: asset for asset in asset_service.list_assets()}
    assert assets_by_code["product_a_fg_hook_a"].tag_labels == (
        "message:hook",
        "mood:exciting",
        "product:product_a",
        "role:foreground",
    )
    assert assets_by_code["product_a_fg_hook_b"].tag_labels == (
        "product:product_a",
        "role:foreground",
    )


def test_folder_service_applies_folder_tag_metadata_to_existing_assets_on_rerun(unit_of_work_factory, tmp_path) -> None:
    _, asset_service, _, folder_service, _ = _build_services(
        unit_of_work_factory,
        tmp_path,
        {"voice_a.mp3": 15.0},
    )
    batch_root = tmp_path / "batch_root"
    product_dir = _write_product_folder(
        batch_root,
        folder_name="ProductA",
        product_code="product_a",
        product_name="Product A",
        requested_output_count=1,
    )

    folder_service.run_batch_root(batch_root, materialize=False)
    _write_tags_toml(
        product_dir / "foreground",
        global_tags=["role:foreground"],
        file_tags={"hook_a.mp4": ["message:hook", "message:hook"]},
    )
    second_report = folder_service.run_batch_root(batch_root, materialize=False)

    assets_by_code = {asset.asset_code: asset for asset in asset_service.list_assets()}
    assert second_report.product_reports[0].registered_asset_count == 0
    assert second_report.product_reports[0].skipped_existing_asset_count == 5
    assert assets_by_code["product_a_fg_hook_a"].tag_labels == (
        "message:hook",
        "role:foreground",
    )


def test_folder_service_rejects_invalid_tags_toml_labels(unit_of_work_factory, tmp_path) -> None:
    _, _, _, folder_service, _ = _build_services(unit_of_work_factory, tmp_path, {})
    batch_root = tmp_path / "batch_root"
    product_dir = _write_product_folder(
        batch_root,
        folder_name="ProductA",
        product_code="product_a",
        product_name="Product A",
        requested_output_count=1,
    )
    (product_dir / "foreground" / "tags.toml").write_text(
        '\n'.join(
            [
                "global_tags = [",
                '  "missing_separator",',
                "]",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(AutoFactoryFolderContractError, match="group:name"):
        folder_service.run_batch_root(batch_root, materialize=False)


def test_folder_service_rejects_invalid_fill_policy_contract(unit_of_work_factory, tmp_path) -> None:
    _, _, _, folder_service, _ = _build_services(unit_of_work_factory, tmp_path, {})
    batch_root = tmp_path / "batch_root"
    product_dir = _write_product_folder(
        batch_root,
        folder_name="ProductA",
        product_code="product_a",
        product_name="Product A",
        requested_output_count=1,
    )
    (product_dir / "pipeline.toml").write_text(
        (product_dir / "pipeline.toml").read_text(encoding="utf-8")
        + '\n[fill_policy.background_music]\nloop_enabled = false\nshortfall_mode = "loop_to_timeline"\n',
        encoding="utf-8",
    )

    with pytest.raises(AutoFactoryFolderContractError):
        folder_service.run_batch_root(batch_root, materialize=False)


def test_folder_service_supports_selection_tags_from_folder_tag_metadata(unit_of_work_factory, tmp_path) -> None:
    _, _, factory_service, folder_service, _ = _build_services(
        unit_of_work_factory,
        tmp_path,
        {"voice_a.mp3": 15.0},
    )
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
                'foreground = ["message:hook"]',
                'background = ["scene:studio"]',
                'voice = ["language:th"]',
            ]
        ),
        encoding="utf-8",
    )
    _write_tags_toml(
        product_dir / "foreground",
        global_tags=["role:foreground"],
        file_tags={"hook_a.mp4": ["message:hook"]},
    )
    _write_tags_toml(
        product_dir / "background",
        global_tags=["scene:studio"],
        file_tags={},
    )
    _write_tags_toml(
        product_dir / "voice",
        global_tags=["language:th"],
        file_tags={},
    )

    report = folder_service.run_batch_root(batch_root)

    assert report.materialization is not None
    recipes = sorted(factory_service.list_recipes(), key=lambda recipe: recipe.recipe_code)
    assert [recipe.recipe_code for recipe in recipes] == ["product_a_batch_root_001"]
