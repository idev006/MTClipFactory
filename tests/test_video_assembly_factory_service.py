from __future__ import annotations

import json
from pathlib import Path

import pytest

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.factory.audio_composition import PreviewAudioMixPlan
from mt_clip_factory.factory.dto import AssignAssetToRecipeCommand, CreateRecipeCommand
from mt_clip_factory.factory.preview_artifacts import PreviewManifestBuilder
from mt_clip_factory.factory.preview_composition import PreviewSegmentClip
from mt_clip_factory.factory.renderers import RenderedPreviewOutput
from mt_clip_factory.factory.services import (
    FactoryJobNotFoundError,
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


def _build_factory_service(
    unit_of_work_factory,
    preview_root: Path,
    *,
    render_ducking_applied: bool | None = None,
    render_ducking_reason: str = "fake_renderer",
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
        ) -> RenderedPreviewOutput:
            output_dir = preview_root / product_code / "videos"
            output_dir.mkdir(parents=True, exist_ok=True)
            target_path = output_dir / f"{output_stem}.mp4"
            self.calls.append(
                {
                    "output_stem": output_stem,
                    "product_code": product_code,
                    "segment_clips": segment_clips,
                    "source_files": source_files,
                    "audio_mix_plan": audio_mix_plan,
                }
            )
            payload = b"".join(segment.source_file.read_bytes() for segment in segment_clips) if segment_clips else source_files[0].read_bytes()
            target_path.write_bytes(payload)
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
            return RenderedPreviewOutput(
                file_path=target_path,
                duration_sec=duration_sec,
                audio_mix_summary=audio_mix_summary,
            )

    renderer = FakePreviewRenderer()
    return VideoAssemblyFactoryService(
        unit_of_work_factory=unit_of_work_factory,
        preview_manifest_builder=PreviewManifestBuilder(preview_root),
        preview_renderer=renderer,
        final_renderer=renderer,
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
    recipe_id = service.create_recipe(CreateRecipeCommand(product_id=product_id, recipe_code="Honey Launch"))
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
    assert recipe.recipe_score == 0.35
    assert recipe.duplicate_risk == outputs[0].duplicate_risk
    assert recipe_summary.recipe_score == recipe.recipe_score
    assert recipe_summary.duplicate_risk == recipe.duplicate_risk
    assert products[0].output_count == 1

    manifest_payload = json.loads(Path(outputs[0].manifest_path).read_text(encoding="utf-8"))
    assert manifest_payload["composition_plan"]["resolved_duration_sec"] == 3.0
    assert [segment["segment_type"] for segment in manifest_payload["segments"]] == ["hook", "benefit", "cta"]
    assert all(segment["layer_name"] == "background_visual" for segment in manifest_payload["segments"])
    assert manifest_payload["review_gate"]["required"] is True
    assert manifest_payload["review_gate"]["signals"]


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

    assert manifest_payload["audio_mix"]["mode"] == "fake_audio_mix"
    assert manifest_payload["audio_mix"]["voice_track_count"] == 1
    assert manifest_payload["audio_mix"]["music_track_count"] == 1
    assert manifest_payload["audio_mix"]["mix_balance"]["music_mix_gain_db"] == -4
    assert manifest_payload["audio_mix"]["ducking"]["applied"] is True


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
