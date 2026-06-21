from __future__ import annotations

import json
from pathlib import Path

import pytest

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.factory.audio_composition import PreviewAudioMixPlan
from mt_clip_factory.factory.automation_policy import ProductAutomationPolicyService
from mt_clip_factory.factory.caption_runtime import CaptionRuntimeService, ProductAutomationMetadataStore
from mt_clip_factory.factory.dto import AssignAssetToRecipeCommand, CreateRecipeCommand
from mt_clip_factory.factory.preview_artifacts import PreviewManifestBuilder
from mt_clip_factory.factory.preview_composition import PreviewSegmentClip
from mt_clip_factory.factory.product_run_store import ProductRunArtifactStore
from mt_clip_factory.factory.renderers import RenderedPreviewOutput
from mt_clip_factory.factory.services import (
    FactoryJobNotFoundError,
    FinalRenderPrerequisiteError,
    OutputApprovalError,
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


def _build_factory_service(
    unit_of_work_factory,
    preview_root: Path,
    *,
    render_ducking_applied: bool | None = None,
    render_ducking_reason: str = "fake_renderer",
    caption_runtime_service: CaptionRuntimeService | None = None,
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
            resolved_target_path = target_path or (preview_root / product_code / "videos" / f"{output_stem}.mp4")
            resolved_target_path.parent.mkdir(parents=True, exist_ok=True)
            self.calls.append(
                {
                    "output_stem": output_stem,
                    "product_code": product_code,
                    "segment_clips": segment_clips,
                    "source_files": source_files,
                    "audio_mix_plan": audio_mix_plan,
                    "target_ratio": target_ratio,
                    "target_path": resolved_target_path,
                }
            )
            payload = b"".join(segment.source_file.read_bytes() for segment in segment_clips) if segment_clips else source_files[0].read_bytes()
            resolved_target_path.write_bytes(payload)
            duration_sec = round(sum(segment.target_duration_sec for segment in segment_clips), 3) if segment_clips else 3.0
            audio_mix_summary = None
            if audio_mix_plan is not None:
                ducking_applied = (
                    render_ducking_applied
                    if render_ducking_applied is not None
                    else bool(audio_mix_plan.voice_tracks and audio_mix_plan.music_tracks)
                )
                audio_mix_summary = {
                    "mode": "fake_audio_mix",
                    "target_duration_sec": audio_mix_plan.target_duration_sec,
                    "voice_track_count": len(audio_mix_plan.voice_tracks),
                    "music_track_count": len(audio_mix_plan.music_tracks),
                    "mix_balance": {
                        "strategy": "voice_priority_gain_stage",
                        "voice_mix_gain_db": 0,
                        "music_mix_gain_db": -4,
                    },
                    "ducking": {
                        "applied": ducking_applied,
                        "reason": render_ducking_reason,
                    },
                }
            visual_composite_summary = None
            if segment_clips:
                visual_composite_summary = {
                    "mode": "fake_layered_visual_stack",
                    "background_segment_count": sum(1 for segment in segment_clips if segment.background_layer is not None),
                    "keyed_segment_count": 0,
                    "segments": [
                        {
                            "sequence_index": segment.sequence_index,
                            "segment_type": segment.segment_type,
                            "primary_asset_code": segment.asset_code,
                            "primary_layer_name": segment.layer_name,
                            "background_asset_code": None if segment.background_layer is None else segment.background_layer.asset_code,
                            "composite_mode": "single_layer",
                        }
                        for segment in segment_clips
                    ],
                }
            return RenderedPreviewOutput(
                file_path=resolved_target_path,
                duration_sec=duration_sec,
                audio_mix_summary=audio_mix_summary,
                visual_composite_summary=visual_composite_summary,
            )

    renderer = FakePreviewRenderer()
    metadata_store = ProductAutomationMetadataStore(preview_root.parent / "media_library")
    return VideoAssemblyFactoryService(
        unit_of_work_factory=unit_of_work_factory,
        preview_manifest_builder=PreviewManifestBuilder(preview_root),
        preview_renderer=renderer,
        final_renderer=renderer,
        caption_runtime_service=caption_runtime_service,
        automation_policy_service=ProductAutomationPolicyService(metadata_store=metadata_store),
        run_artifact_store=ProductRunArtifactStore(metadata_store=metadata_store),
    )


def _register_ready_asset(
    unit_of_work_factory,
    tmp_path: Path,
    *,
    asset_type: str = "background_video",
    asset_code: str = "hero_asset",
    file_name: str = "hero.mp4",
) -> tuple[int, int]:
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    products = product_service.list_products()
    product_id = (
        products[0].product_id
        if products
        else product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    )
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library")
    source_file = tmp_path / file_name
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


def _write_runtime_caption_contract(
    *,
    media_root: Path,
    product_code: str,
    main_text: str,
    max_lines: int = 3,
    max_chars_per_line: int = 18,
) -> CaptionRuntimeService:
    source_dir = media_root.parent / "product_contract"
    source_dir.mkdir(parents=True, exist_ok=True)
    caption_source = source_dir / "captions.toml"
    caption_source.write_text(
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
                "font_size = 72",
                "min_font_size = 48",
                f"max_lines = {max_lines}",
                f"max_chars_per_line = {max_chars_per_line}",
                'overflow_policy = "wrap_then_scale_then_review"',
                "review_required_if_overflow = true",
                "",
                "[caption_properties.sub]",
                'font_family = "THSarabun"',
                "font_size = 40",
                "min_font_size = 30",
                "max_lines = 2",
                "max_chars_per_line = 24",
                'overflow_policy = "wrap_then_truncate_or_review"',
                "review_required_if_overflow = true",
            ]
        ),
        encoding="utf-8",
    )
    fonts_root = media_root.parent / "fonts"
    fonts_root.mkdir(parents=True, exist_ok=True)
    (fonts_root / "THSarabun.ttf").write_bytes(b"font")
    metadata_store = ProductAutomationMetadataStore(media_root)
    metadata_store.sync_caption_contract(product_code=product_code, source_file=caption_source)
    return CaptionRuntimeService(metadata_store=metadata_store, fonts_root=fonts_root)


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
    assert recipes[0].recipe_score == 0.1
    assert recipes[0].duplicate_risk == 1.0


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
    summary = service.list_recipes()[0]
    assert item_id == 1
    assert len(recipe.items) == 1
    assert recipe.items[0].asset_code == "hero_asset"
    assert recipe.items[0].role == "hero"
    assert recipe.recipe_score == 0.25
    assert recipe.duplicate_risk == 0.0
    assert summary.recipe_score == recipe.recipe_score


def test_factory_service_builds_preview_output_job(unit_of_work_factory, tmp_path) -> None:
    product_id, asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(
        CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch", target_ratio="9:16")
    )
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role="hero"))

    job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(job_id)

    jobs = service.list_preview_jobs()
    recipe = service.get_recipe(recipe_id)
    recipe_summary = service.list_recipes()[0]
    outputs = service.list_outputs(recipe_id=recipe_id)
    products = ProductApplicationService(unit_of_work_factory=unit_of_work_factory).list_products()
    assert jobs[0].job_id == job_id
    assert jobs[0].job_type == "render_recipe_preview"
    assert jobs[0].status == "done"
    assert jobs[0].output_path is not None
    assert Path(jobs[0].output_path).exists()
    assert jobs[0].output_path.endswith(".mp4")
    assert recipe.status == "needs_review"
    assert recipe.decision_actor == "system_review_gate"
    assert len(outputs) == 1
    assert outputs[0].approved is False
    assert outputs[0].output_kind == "preview"
    assert outputs[0].manifest_path is not None
    assert outputs[0].rendering_job_code is not None
    assert outputs[0].quality_score is not None
    assert outputs[0].duplicate_risk is not None
    assert recipe.recipe_score == 0.4
    assert recipe.duplicate_risk == outputs[0].duplicate_risk
    assert recipe_summary.recipe_score == recipe.recipe_score
    assert recipe_summary.duplicate_risk == recipe.duplicate_risk
    assert products[0].output_count == 1
    assert service._preview_renderer.calls[0]["target_ratio"] == "9:16"

    manifest_payload = json.loads(Path(outputs[0].manifest_path).read_text(encoding="utf-8"))
    assert manifest_payload["manifest_meta"]["schema_name"] == "mtclipfactory_manifest"
    assert manifest_payload["manifest_meta"]["schema_version"] == "2.0"
    assert manifest_payload["artifact"]["stage_name"] == "preview"
    assert manifest_payload["composition"]["plan"]["resolved_duration_sec"] == 3.0
    assert manifest_payload["quality"]["review_gate"]["required"] is True
    assert manifest_payload["composition_plan"]["resolved_duration_sec"] == 3.0
    assert [segment["segment_type"] for segment in manifest_payload["segments"]] == ["hook", "benefit", "cta"]
    assert all(segment["layer_name"] == "background_visual" for segment in manifest_payload["segments"])
    assert manifest_payload["review_gate"]["required"] is True
    assert manifest_payload["review_gate"]["signals"]


def test_factory_service_writes_resolved_caption_manifest_and_review_signal(unit_of_work_factory, tmp_path) -> None:
    media_root = tmp_path / "media_library"
    product_id, asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    caption_runtime_service = _write_runtime_caption_contract(
        media_root=media_root,
        product_code="honey",
        main_text="ข้อความยาวมากจนเกินขอบเขต",
        max_lines=1,
        max_chars_per_line=4,
    )
    service = _build_factory_service(
        unit_of_work_factory,
        tmp_path / "previews",
        caption_runtime_service=caption_runtime_service,
    )
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Caption Review"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role="hero"))

    job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(job_id)

    output = service.list_outputs(recipe_id=recipe_id)[0]
    recipe = service.get_recipe(recipe_id)
    manifest_payload = json.loads(Path(output.manifest_path).read_text(encoding="utf-8"))

    assert manifest_payload["composition"]["captions"]["enabled"] is True
    assert manifest_payload["quality"]["review_gate"]["required"] is True
    assert manifest_payload["captions"]["enabled"] is True
    assert manifest_payload["captions"]["review_required_role_count"] == 1
    assert manifest_payload["captions"]["segments"][0]["roles"][0]["font_file"].endswith("THSarabun.ttf")
    assert recipe.status == "needs_review"
    assert any(signal["code"] == "caption_overflow_risk" for signal in manifest_payload["review_gate"]["signals"])


def test_factory_service_writes_runtime_audio_mix_summary_to_manifest(unit_of_work_factory, tmp_path) -> None:
    product_id, visual_asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    _, voice_asset_id = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="voiceover",
        asset_code="voice_asset",
        file_name="voice.mp3",
    )
    _, music_asset_id = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="background_music",
        asset_code="music_asset",
        file_name="music.mp3",
    )
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Audio Mix"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=visual_asset_id, role="hero"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=voice_asset_id, role="voice"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=music_asset_id, role="music"))

    job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(job_id)

    output = service.list_outputs(recipe_id=recipe_id)[0]
    manifest_payload = json.loads(Path(output.manifest_path).read_text(encoding="utf-8"))

    assert manifest_payload["render"]["audio_mix"]["mode"] == "fake_audio_mix"
    assert manifest_payload["audio_mix"]["mode"] == "fake_audio_mix"
    assert manifest_payload["audio_mix"]["voice_track_count"] == 1
    assert manifest_payload["audio_mix"]["music_track_count"] == 1
    assert manifest_payload["audio_mix"]["mix_balance"]["music_mix_gain_db"] == -4
    assert manifest_payload["audio_mix"]["ducking"]["applied"] is True


def test_factory_service_writes_product_local_preview_artifacts_for_batch_context(unit_of_work_factory, tmp_path) -> None:
    product_id, asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    product_root = tmp_path / "product_folder"
    product_root.mkdir(parents=True, exist_ok=True)
    ProductAutomationMetadataStore(tmp_path / "media_library").sync_runtime_context(
        product_code="honey",
        source_product_dir=product_root,
        batch_code="batch_local",
    )
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role="hero"))

    job_id = service.enqueue_preview_job(recipe_id, batch_code="batch_local", source_mode="auto_factory_folder")
    service.run_preview_job(job_id)

    outputs = service.list_outputs(recipe_id=recipe_id)
    assert len(outputs) == 1
    assert "product_folder" in outputs[0].file_path
    assert "runs" in outputs[0].file_path
    journal_path = product_root / "runs" / "batch_local" / "journal.toml"
    assert journal_path.exists()
    assert (product_root / "runs" / "batch_local" / "manifests" / "honey_launch.json").exists()
    journal_text = journal_path.read_text(encoding="utf-8")
    assert 'recorded_at = "' in journal_text
    assert "Z" in journal_text


def test_factory_service_builds_layered_visual_stack_when_background_and_foreground_exist(unit_of_work_factory, tmp_path) -> None:
    product_id, background_asset_id = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="background_video",
        asset_code="bg_asset",
        file_name="bg.mp4",
    )
    _, foreground_asset_id = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="foreground_video",
        asset_code="fg_asset",
        file_name="fg.mp4",
    )
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Layered", target_ratio="9:16"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=background_asset_id, role="background"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=foreground_asset_id, role="hero"))

    job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(job_id)

    recipe = service.get_recipe(recipe_id)
    output = service.list_outputs(recipe_id=recipe_id)[0]
    manifest_payload = json.loads(Path(output.manifest_path).read_text(encoding="utf-8"))
    segment_clips = service._preview_renderer.calls[0]["segment_clips"]

    assert all(segment.layer_name == "product_focus_visual" for segment in segment_clips)
    assert all(segment.background_layer is not None for segment in segment_clips)
    assert recipe.status == "candidate"
    assert manifest_payload["render"]["visual_composite"]["background_segment_count"] == 3
    assert manifest_payload["visual_composite"]["background_segment_count"] == 3
    assert manifest_payload["segments"][0]["background_layer"]["asset_code"] == "bg_asset"


def test_factory_service_uses_semantic_foreground_assignments_per_segment(unit_of_work_factory, tmp_path) -> None:
    product_id, background_asset_id = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="background_video",
        asset_code="bg_asset",
        file_name="bg.mp4",
    )
    semantic_assets = {}
    for role_name in ("hook", "problem", "benefit", "proof", "cta"):
        _, asset_id = _register_ready_asset(
            unit_of_work_factory,
            tmp_path,
            asset_type="foreground_video",
            asset_code=f"fg_{role_name}",
            file_name=f"{role_name}.mp4",
        )
        semantic_assets[role_name] = asset_id
    voice_product_id, voice_asset_id = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="voiceover",
        asset_code="voice_asset",
        file_name="voice.mp3",
    )
    assert voice_product_id == product_id

    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(
        CreateRecipeCommand(
            product_id=product_id,
            recipe_code="Semantic Layer",
            target_ratio="9:16",
            duration_sec=20.0,
        )
    )
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=background_asset_id, role="background"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=voice_asset_id, role="voice"))
    for role_name, asset_id in semantic_assets.items():
        service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role=role_name))

    job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(job_id)

    output = service.list_outputs(recipe_id=recipe_id)[0]
    manifest_payload = json.loads(Path(output.manifest_path).read_text(encoding="utf-8"))
    segment_clips = service._preview_renderer.calls[0]["segment_clips"]

    expected_codes = {
        "hook": "fg_hook",
        "problem": "fg_problem",
        "benefit": "fg_benefit",
        "proof": "fg_proof",
        "cta": "fg_cta",
    }

    assert [segment.segment_type for segment in segment_clips] == ["hook", "problem", "benefit", "proof", "cta"]
    assert [segment.asset_code for segment in segment_clips] == [
        expected_codes[segment.segment_type]
        for segment in segment_clips
    ]
    assert [segment["asset_code"] for segment in manifest_payload["segments"]] == [
        expected_codes[segment["segment_type"]]
        for segment in manifest_payload["segments"]
    ]
    assert all(segment.background_layer is not None for segment in segment_clips)


def test_factory_service_keeps_selected_visual_asset_persistent_across_segments(unit_of_work_factory, tmp_path) -> None:
    product_id, background_asset_id = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="background_video",
        asset_code="bg_asset",
        file_name="bg.mp4",
    )
    _, foreground_asset_id_a = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="foreground_video",
        asset_code="fg_asset_a",
        file_name="fg_a.mp4",
    )
    _, foreground_asset_id_b = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="foreground_video",
        asset_code="fg_asset_b",
        file_name="fg_b.mp4",
    )
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Persistent Layer", target_ratio="9:16"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=background_asset_id, role="background"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=foreground_asset_id_a, role="hero_a"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=foreground_asset_id_b, role="hero_b"))

    job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(job_id)

    output = service.list_outputs(recipe_id=recipe_id)[0]
    manifest_payload = json.loads(Path(output.manifest_path).read_text(encoding="utf-8"))
    segment_clips = service._preview_renderer.calls[0]["segment_clips"]
    selected_foreground_codes = {segment.asset_code for segment in segment_clips}
    selected_background_codes = {
        segment.background_layer.asset_code
        for segment in segment_clips
        if segment.background_layer is not None
    }

    assert len(selected_foreground_codes) == 1
    assert selected_foreground_codes <= {"fg_asset_a", "fg_asset_b"}
    assert selected_background_codes == {"bg_asset"}
    assert {segment["asset_code"] for segment in manifest_payload["segments"]} == selected_foreground_codes


def test_factory_service_routes_audio_masking_risk_to_review_manifest(unit_of_work_factory, tmp_path) -> None:
    product_id, visual_asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    _, voice_asset_id = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="voiceover",
        asset_code="voice_asset",
        file_name="voice.mp3",
    )
    _, music_asset_id = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="background_music",
        asset_code="music_asset",
        file_name="music.mp3",
    )
    service = _build_factory_service(
        unit_of_work_factory,
        tmp_path / "previews",
        render_ducking_applied=False,
        render_ducking_reason="duck_disabled_in_settings",
    )
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Audio Review"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=visual_asset_id, role="hero"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=voice_asset_id, role="voice"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=music_asset_id, role="music"))

    job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(job_id)

    output = service.list_outputs(recipe_id=recipe_id)[0]
    recipe = service.get_recipe(recipe_id)
    manifest_payload = json.loads(Path(output.manifest_path).read_text(encoding="utf-8"))
    signal_codes = [signal["code"] for signal in manifest_payload["review_gate"]["signals"]]

    assert recipe.status == "needs_review"
    assert manifest_payload["review_gate"]["required"] is True
    assert "audio_masking_risk" in signal_codes
    assert any(
        signal["code"] == "audio_masking_risk" and signal["metric_value"] == "duck_disabled_in_settings"
        for signal in manifest_payload["review_gate"]["signals"]
    )


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
    assert jobs[0].consecutive_failure_count == 1
    assert jobs[0].recovery_attempt_count == 0


def test_factory_service_marks_preview_job_failed_when_recipe_has_no_renderable_visual_assets(unit_of_work_factory, tmp_path) -> None:
    product_id, voice_asset_id = _register_ready_asset(
        unit_of_work_factory,
        tmp_path,
        asset_type="voiceover",
        asset_code="voice_asset",
        file_name="voice.mp3",
    )
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Voice Only"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=voice_asset_id, role="voice"))
    job_id = service.enqueue_preview_job(recipe_id)

    with pytest.raises(PreviewBuildInputError, match="no renderable video assets"):
        service.run_preview_job(job_id)

    failed_jobs = service.list_preview_jobs(status="failed")
    assert failed_jobs[0].job_id == job_id
    assert failed_jobs[0].consecutive_failure_count == 1


def test_factory_service_retries_failed_preview_job_after_restart(unit_of_work_factory, tmp_path) -> None:
    product_id, asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    preview_root = tmp_path / "previews"
    service = _build_factory_service(unit_of_work_factory, preview_root)
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))
    job_id = service.enqueue_preview_job(recipe_id)

    with pytest.raises(PreviewBuildInputError):
        service.run_preview_job(job_id)

    restarted_service = _build_factory_service(unit_of_work_factory, preview_root)
    restarted_service.assign_asset_to_recipe(
        AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role="hero")
    )
    restarted_service.retry_job(job_id)

    jobs = restarted_service.list_jobs()
    outputs = restarted_service.list_outputs(recipe_id=recipe_id)
    assert jobs[0].job_id == job_id
    assert jobs[0].status == "done"
    assert jobs[0].recovery_attempt_count == 1
    assert jobs[0].consecutive_failure_count == 0
    assert len(outputs) == 1
    assert Path(outputs[0].file_path).exists()


def test_factory_service_requires_approved_output_before_approving_recipe(unit_of_work_factory, tmp_path) -> None:
    product_id, asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role="hero"))
    preview_job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(preview_job_id)

    with pytest.raises(RecipeApprovalError, match="Approve at least one output"):
        service.approve_recipe(recipe_id, actor="qa_lead", reason="creative approved")


def test_factory_service_approves_output_and_recipe(unit_of_work_factory, tmp_path) -> None:
    product_id, asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role="hero"))
    preview_job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(preview_job_id)
    output_id = service.list_outputs(recipe_id=recipe_id)[0].output_id

    service.approve_output(output_id, actor="qa_lead", reason="ready to publish")
    service.approve_recipe(recipe_id, actor="qa_lead", reason="creative approved")

    recipe = service.get_recipe(recipe_id)
    outputs = service.list_outputs(recipe_id=recipe_id, approved=True)
    events = service.list_decision_events(recipe_id)
    assert recipe.status == "approved"
    assert recipe.decision_actor == "qa_lead"
    assert recipe.decision_reason == "creative approved"
    assert outputs[0].approved_by == "qa_lead"
    assert [event.event_type for event in events] == ["recipe_approved", "output_approved", "recipe_review_required"]
    assert len(outputs) == 1


def test_factory_service_requires_review_reason_before_approving_flagged_recipe(unit_of_work_factory, tmp_path) -> None:
    product_id, asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role="hero"))
    preview_job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(preview_job_id)
    output_id = service.list_outputs(recipe_id=recipe_id)[0].output_id
    service.approve_output(output_id, actor="qa_lead", reason="ready to publish")

    with pytest.raises(RecipeApprovalError, match="Provide a review reason"):
        service.approve_recipe(recipe_id, actor="qa_lead")


def test_factory_service_rejects_recipe(unit_of_work_factory, tmp_path) -> None:
    product_id, _ = _register_ready_asset(unit_of_work_factory, tmp_path)
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))

    service.reject_recipe(recipe_id, actor="editor", reason="hook too weak")

    recipe = service.get_recipe(recipe_id)
    events = service.list_decision_events(recipe_id)
    assert recipe.status == "rejected"
    assert recipe.decision_actor == "editor"
    assert recipe.decision_reason == "hook too weak"
    assert events[0].event_type == "recipe_rejected"
    assert events[0].reason == "hook too weak"


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
    service.approve_output(output_id, actor="qa_lead", reason="ready to publish")
    service.approve_recipe(recipe_id, actor="qa_lead", reason="creative approved")

    final_job_id = service.enqueue_final_render_job(recipe_id)
    service.run_final_render_job(final_job_id)

    jobs = service.list_final_render_jobs()
    outputs = service.list_outputs(recipe_id=recipe_id)
    events = service.list_decision_events(recipe_id)
    products = ProductApplicationService(unit_of_work_factory=unit_of_work_factory).list_products()
    assert jobs[0].job_id == final_job_id
    assert jobs[0].job_type == "render_recipe_final"
    assert jobs[0].status == "done"
    assert jobs[0].output_path is not None
    assert jobs[0].output_path.endswith(".mp4")
    assert len(outputs) == 2
    assert outputs[0].approved is True
    assert outputs[0].approved_by == "system_final_render"
    assert outputs[0].output_kind == "final"
    assert outputs[0].manifest_path is not None
    assert outputs[0].source_output_id is not None
    assert outputs[0].source_output_code is not None
    assert events[0].event_type == "output_auto_approved"
    assert events[0].output_id == outputs[0].output_id
    assert products[0].output_count == 2


def test_factory_service_requires_post_replacement_output_before_reapproval(unit_of_work_factory, tmp_path) -> None:
    product_id, source_asset_id = _register_ready_asset(unit_of_work_factory, tmp_path, asset_code="hero_asset")
    _, replacement_asset_id = _register_ready_asset(unit_of_work_factory, tmp_path, asset_code="hero_asset_v2", file_name="hero_v2.mp4")
    asset_service = _build_asset_service(unit_of_work_factory, tmp_path / "media_library")
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=source_asset_id, role="hero"))
    preview_job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(preview_job_id)
    original_output_id = service.list_outputs(recipe_id=recipe_id)[0].output_id
    service.approve_output(original_output_id, actor="qa_lead", reason="ready to publish")
    service.approve_recipe(recipe_id, actor="qa_lead", reason="creative approved")

    asset_service.replace_asset_in_recipes(source_asset_id, replacement_asset_id)

    replaced_recipe = service.get_recipe(recipe_id)
    assert replaced_recipe.status == "candidate"

    with pytest.raises(OutputApprovalError, match="newly rebuilt output"):
        service.approve_output(original_output_id, actor="qa_lead", reason="stale approval")

    with pytest.raises(RecipeApprovalError, match="newly rebuilt output"):
        service.approve_recipe(recipe_id, actor="qa_lead", reason="creative approved")

    rebuilt_preview_job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(rebuilt_preview_job_id)
    rebuilt_output_id = service.list_outputs(recipe_id=recipe_id)[0].output_id
    service.approve_output(rebuilt_output_id, actor="qa_lead", reason="replacement approved")
    service.approve_recipe(recipe_id, actor="qa_lead", reason="creative approved after replacement")

    recipe = service.get_recipe(recipe_id)
    events = service.list_decision_events(recipe_id)
    assert recipe.status == "approved"
    assert any(event.event_type == "recipe_assets_replaced" for event in events)


def test_factory_service_lists_append_only_decision_history(unit_of_work_factory, tmp_path) -> None:
    product_id, asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role="hero"))
    preview_job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(preview_job_id)
    preview_output = service.list_outputs(recipe_id=recipe_id)[0]

    service.approve_output(preview_output.output_id, actor="qa_lead", reason="ready to publish")
    service.reject_recipe(recipe_id, actor="editor", reason="need stronger hook")
    service.approve_recipe(recipe_id, actor="qa_lead", reason="creative approved")

    events = service.list_decision_events(recipe_id)

    assert [event.event_type for event in events] == [
        "recipe_approved",
        "recipe_rejected",
        "output_approved",
        "recipe_review_required",
    ]
    assert events[0].actor == "qa_lead"
    assert events[1].actor == "editor"
    assert events[2].output_code == preview_output.output_code


def test_factory_service_reports_output_lineage(unit_of_work_factory, tmp_path) -> None:
    product_id, asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role="hero"))
    preview_job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(preview_job_id)
    preview_output = service.list_outputs(recipe_id=recipe_id)[0]
    service.approve_output(preview_output.output_id, actor="qa_lead", reason="ready to publish")
    service.approve_recipe(recipe_id, actor="qa_lead", reason="creative approved")
    final_job_id = service.enqueue_final_render_job(recipe_id)
    service.run_final_render_job(final_job_id)

    outputs = service.list_outputs(recipe_id=recipe_id)
    final_output = outputs[0]
    preview_output = outputs[1]

    assert final_output.output_kind == "final"
    assert final_output.rendering_job_code is not None
    assert final_output.manifest_path is not None
    assert final_output.source_output_id == preview_output.output_id
    assert final_output.source_output_code == preview_output.output_code
    assert final_output.source_output_path == preview_output.file_path
    assert preview_output.output_kind == "preview"
    assert preview_output.manifest_path is not None


def test_factory_service_final_render_uses_composition_not_preview_file(unit_of_work_factory, tmp_path) -> None:
    product_id, asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role="hero"))
    preview_job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(preview_job_id)
    preview_output = service.list_outputs(recipe_id=recipe_id)[0]
    Path(preview_output.file_path).write_bytes(b"corrupted-preview")
    service.approve_output(preview_output.output_id, actor="qa_lead", reason="ready to publish")
    service.approve_recipe(recipe_id, actor="qa_lead", reason="creative approved")

    final_job_id = service.enqueue_final_render_job(recipe_id)
    service.run_final_render_job(final_job_id)

    final_output = service.list_outputs(recipe_id=recipe_id)[0]
    final_bytes = Path(final_output.file_path).read_bytes()

    assert final_bytes != b"corrupted-preview"
    assert b"hero_asset-bytes" in final_bytes


def test_factory_service_retries_failed_final_job_after_restart(unit_of_work_factory, tmp_path) -> None:
    product_id, asset_id = _register_ready_asset(unit_of_work_factory, tmp_path)
    preview_root = tmp_path / "previews"
    service = _build_factory_service(unit_of_work_factory, preview_root)
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))
    service.assign_asset_to_recipe(AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=asset_id, role="hero"))
    preview_job_id = service.enqueue_preview_job(recipe_id)
    service.run_preview_job(preview_job_id)
    output_id = service.list_outputs(recipe_id=recipe_id)[0].output_id
    service.approve_output(output_id, actor="qa_lead", reason="ready to publish")
    service.approve_recipe(recipe_id, actor="qa_lead", reason="creative approved")

    with unit_of_work_factory() as uow:
        output = uow.outputs.get_by_id(output_id)
        assert output is not None
        output.approved = False
        uow.outputs.update(output)
        uow.commit()

    final_job_id = service.enqueue_final_render_job(recipe_id)
    with pytest.raises(FinalRenderPrerequisiteError, match="Approve at least one output"):
        service.run_final_render_job(final_job_id)

    restarted_service = _build_factory_service(unit_of_work_factory, preview_root)
    restarted_service.approve_output(output_id, actor="qa_lead", reason="ready to publish")
    restarted_service.retry_job(final_job_id)

    jobs = restarted_service.list_jobs()
    outputs = restarted_service.list_outputs(recipe_id=recipe_id)
    assert jobs[0].job_id == final_job_id
    assert jobs[0].status == "done"
    assert jobs[0].recovery_attempt_count == 1
    assert jobs[0].consecutive_failure_count == 0
    assert len(outputs) == 2
    assert Path(outputs[0].file_path).exists()


def test_factory_service_rejects_retry_for_unknown_job(unit_of_work_factory, tmp_path) -> None:
    service = _build_factory_service(unit_of_work_factory, tmp_path / "previews")

    with pytest.raises(FactoryJobNotFoundError):
        service.retry_job(999)
