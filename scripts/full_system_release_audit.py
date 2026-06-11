from __future__ import annotations

from dataclasses import asdict, replace
import json
from pathlib import Path
import shutil
import tempfile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mt_clip_factory.app_runtime import ApplicationRuntime
from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.config import default_config
from mt_clip_factory.control_center.dto import PathRootsDTO, SystemSettingsDTO
from mt_clip_factory.control_center.services import DashboardService, SystemSettingsService
from mt_clip_factory.factory.audio_composition import PreviewAudioMixPlan
from mt_clip_factory.factory.dto import AssignAssetToRecipeCommand, CreateRecipeCommand
from mt_clip_factory.factory.preview_artifacts import PreviewManifestBuilder
from mt_clip_factory.factory.preview_composition import PreviewSegmentClip
from mt_clip_factory.factory.renderers import RenderedPreviewOutput
from mt_clip_factory.factory.services import RecipeApprovalError, VideoAssemblyFactoryService
from mt_clip_factory.infrastructure.models import Base
from mt_clip_factory.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from mt_clip_factory.library.contracts import AnalyzedMediaMetadata
from mt_clip_factory.library.dto import RegisterAssetCommand
from mt_clip_factory.library.readiness import AssetReadinessEvaluator
from mt_clip_factory.library.services import AssetIntakeService
from mt_clip_factory.library.storage import LocalAssetStorage
from mt_clip_factory.library.tag_dto import AssignTagToAssetCommand, CreateTagCommand
from mt_clip_factory.library.tag_services import TagManagementService


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


class FakePreviewRenderer:
    def __init__(self, output_root: Path, *, ducking_applied: bool | None = None, ducking_reason: str = "fake_renderer") -> None:
        self._output_root = output_root
        self._ducking_applied = ducking_applied
        self._ducking_reason = ducking_reason

    def render_output(
        self,
        *,
        product_code: str,
        output_stem: str,
        source_files: list[Path],
        segment_clips: tuple[PreviewSegmentClip, ...] = (),
        audio_mix_plan: PreviewAudioMixPlan | None = None,
    ) -> RenderedPreviewOutput:
        output_dir = self._output_root / product_code / "videos"
        output_dir.mkdir(parents=True, exist_ok=True)
        target_path = output_dir / f"{output_stem}.mp4"
        payload = (
            b"".join(segment.source_file.read_bytes() for segment in segment_clips)
            if segment_clips
            else source_files[0].read_bytes()
        )
        target_path.write_bytes(payload)
        duration_sec = (
            round(sum(segment.target_duration_sec for segment in segment_clips), 3)
            if segment_clips
            else 3.0
        )
        audio_mix_summary = None
        if audio_mix_plan is not None:
            ducking_applied = (
                self._ducking_applied
                if self._ducking_applied is not None
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
                    "reason": self._ducking_reason,
                },
            }
        return RenderedPreviewOutput(
            file_path=target_path,
            duration_sec=duration_sec,
            audio_mix_summary=audio_mix_summary,
        )


class FakeArtifactJob:
    def __init__(
        self,
        *,
        job_id: int,
        job_code: str,
        job_type: str,
        status: str,
        asset_id: int,
        progress: float = 0.0,
        error_message: str | None = None,
        consecutive_failure_count: int = 0,
    ) -> None:
        self.job_id = job_id
        self.job_code = job_code
        self.job_type = job_type
        self.status = status
        self.asset_id = asset_id
        self.progress = progress
        self.error_message = error_message
        self.recovery_attempt_count = 0
        self.consecutive_failure_count = consecutive_failure_count
        self.last_recovery_attempt_at = None
        self.last_failure_at = None


class FakeArtifactGenerationService:
    def __init__(
        self,
        queued_count: int = 0,
        failed_count: int = 0,
        *,
        failed_failure_streaks: list[int] | None = None,
    ) -> None:
        failed_failure_streaks = failed_failure_streaks or []
        self._queued_jobs = [
            FakeArtifactJob(
                job_id=index + 1,
                job_code=f"queued_{index + 1}",
                job_type="generate_thumbnail",
                status="queued",
                asset_id=1,
            )
            for index in range(queued_count)
        ]
        self._failed_jobs = [
            FakeArtifactJob(
                job_id=queued_count + index + 1,
                job_code=f"failed_{index + 1}",
                job_type="generate_proxy",
                status="failed",
                asset_id=1,
                error_message="job failed",
                consecutive_failure_count=(
                    failed_failure_streaks[index] if index < len(failed_failure_streaks) else 1
                ),
            )
            for index in range(failed_count)
        ]

    def list_jobs(self, *, status: str | None = None) -> list[FakeArtifactJob]:
        if status == "queued":
            return list(self._queued_jobs)
        if status == "failed":
            return list(self._failed_jobs)
        return [*self._queued_jobs, *self._failed_jobs]

    def run_job(self, job_id: int) -> None:
        for index, job in enumerate(self._queued_jobs):
            if job.job_id == job_id:
                self._queued_jobs.pop(index)
                return
        raise ValueError(str(job_id))

    def retry_job(self, job_id: int) -> None:
        for index, job in enumerate(self._failed_jobs):
            if job.job_id == job_id:
                self._failed_jobs.pop(index)
                return
        raise ValueError(str(job_id))


class FakeFactoryJob:
    def __init__(
        self,
        *,
        job_id: int,
        job_code: str,
        recipe_id: int,
        job_type: str,
        status: str,
        progress: float,
        output_path: str | None = None,
        error_message: str | None = None,
        consecutive_failure_count: int = 0,
    ) -> None:
        self.job_id = job_id
        self.job_code = job_code
        self.recipe_id = recipe_id
        self.job_type = job_type
        self.status = status
        self.progress = progress
        self.output_path = output_path
        self.error_message = error_message
        self.recovery_attempt_count = 0
        self.consecutive_failure_count = consecutive_failure_count
        self.last_recovery_attempt_at = None
        self.last_failure_at = None


class FakeVideoAssemblyFactoryService:
    def __init__(self, *, failed_failure_streak: int = 1) -> None:
        self._recipes = [
            {"recipe_id": 5, "status": "needs_review"},
            {"recipe_id": 3, "status": "approved"},
        ]
        self._jobs = [
            FakeFactoryJob(
                job_id=11,
                job_code="preview_11",
                recipe_id=5,
                job_type="render_recipe_preview",
                status="queued",
                progress=0.0,
            ),
            FakeFactoryJob(
                job_id=10,
                job_code="final_10",
                recipe_id=3,
                job_type="render_recipe_final",
                status="processing",
                progress=0.4,
            ),
            FakeFactoryJob(
                job_id=9,
                job_code="preview_09",
                recipe_id=2,
                job_type="render_recipe_preview",
                status="done",
                progress=1.0,
                output_path="F:/workspace/outputs/preview/honey.mp4",
            ),
            FakeFactoryJob(
                job_id=8,
                job_code="final_08",
                recipe_id=1,
                job_type="render_recipe_final",
                status="failed",
                progress=0.0,
                error_message="render failed",
                consecutive_failure_count=failed_failure_streak,
            ),
        ]

    def list_jobs(self, *, status: str | None = None) -> list[FakeFactoryJob]:
        if status is None:
            return list(self._jobs)
        return [job for job in self._jobs if job.status == status]

    def list_recipes(self, *, product_id: int | None = None, status: str | None = None) -> list[dict]:
        if status is None:
            return list(self._recipes)
        return [recipe for recipe in self._recipes if recipe["status"] == status]

    def list_preview_jobs(self, *, status: str | None = None) -> list[FakeFactoryJob]:
        jobs = [job for job in self._jobs if job.job_type == "render_recipe_preview"]
        if status is None:
            return jobs
        return [job for job in jobs if job.status == status]

    def list_final_render_jobs(self, *, status: str | None = None) -> list[FakeFactoryJob]:
        jobs = [job for job in self._jobs if job.job_type == "render_recipe_final"]
        if status is None:
            return jobs
        return [job for job in jobs if job.status == status]

    def run_preview_job(self, job_id: int) -> None:
        self._complete_job(job_id, "render_recipe_preview")

    def run_final_render_job(self, job_id: int) -> None:
        self._complete_job(job_id, "render_recipe_final")

    def retry_job(self, job_id: int) -> None:
        for job in self._jobs:
            if job.job_id == job_id:
                job.status = "done"
                job.progress = 1.0
                job.output_path = job.output_path or "F:/workspace/outputs/final/retried.mp4"
                return
        raise ValueError(str(job_id))

    def _complete_job(self, job_id: int, expected_type: str) -> None:
        for job in self._jobs:
            if job.job_id == job_id:
                if job.job_type != expected_type:
                    raise ValueError(job.job_type)
                job.status = "done"
                job.progress = 1.0
                job.output_path = job.output_path or "F:/workspace/outputs/preview/recovered.mp4"
                return
        raise ValueError(str(job_id))


def _repo_settings_template() -> SystemSettingsDTO:
    return SystemSettingsService(Path.cwd() / "app_config.toml").load()


def _runtime_path_roots_from_config(config) -> PathRootsDTO:
    return PathRootsDTO(
        database_path=str(config.paths.database_path),
        media_root=str(config.paths.media_root),
        docs_root=str(config.paths.docs_root),
        outputs_root=str(config.paths.outputs_root),
        preview_root=str(config.paths.preview_root),
    )


def _settings_for_workspace(workspace_root: Path, template: SystemSettingsDTO) -> SystemSettingsDTO:
    return replace(
        template,
        database_path=str(workspace_root / "audit.db"),
        media_root=str(workspace_root / "media_library"),
        docs_root=str(workspace_root / "doc"),
        outputs_root=str(workspace_root / "outputs"),
        preview_root=str(workspace_root / "outputs" / "preview"),
    )


def _build_file_uow_factory(database_path: Path):
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{database_path.as_posix()}", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory=session_factory)

    return factory


def _build_asset_service(unit_of_work_factory, media_root: Path) -> AssetIntakeService:
    return AssetIntakeService(
        unit_of_work_factory=unit_of_work_factory,
        asset_storage=LocalAssetStorage(media_root),
        metadata_analyzer=FakeMetadataAnalyzer(),
        readiness_evaluator=AssetReadinessEvaluator(),
    )


def _write_media_file(target: Path, label: str) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(f"{label}-bytes".encode("utf-8"))
    return target


def _prepare_runtime_workspace(workspace_root: Path) -> None:
    workspace_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(Path.cwd() / "alembic", workspace_root / "alembic")
    shutil.copy2(Path.cwd() / "alembic.ini", workspace_root / "alembic.ini")


def run_full_factory_workflow(base_dir: Path, template: SystemSettingsDTO) -> dict[str, object]:
    workspace_root = base_dir / "full_factory"
    workspace_root.mkdir(parents=True, exist_ok=True)
    config = default_config(workspace_root)
    settings_service = SystemSettingsService(
        config.paths.app_config_path,
        runtime_path_roots=_runtime_path_roots_from_config(config),
        reload_policy="runtime_hot_reload",
    )
    settings_service.save(_settings_for_workspace(workspace_root, template))

    unit_of_work_factory = _build_file_uow_factory(workspace_root / "audit.db")
    product_service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    asset_service = _build_asset_service(unit_of_work_factory, workspace_root / "media_library")
    tag_service = TagManagementService(unit_of_work_factory=unit_of_work_factory)
    renderer = FakePreviewRenderer(workspace_root / "outputs" / "preview")
    factory_service = VideoAssemblyFactoryService(
        unit_of_work_factory=unit_of_work_factory,
        preview_manifest_builder=PreviewManifestBuilder(workspace_root / "outputs" / "preview" / "manifests"),
        preview_renderer=renderer,
        final_renderer=FakePreviewRenderer(workspace_root / "outputs" / "final"),
        system_settings_service=settings_service,
    )
    dashboard_service = DashboardService(
        config=config,
        product_service=product_service,
        asset_intake_service=asset_service,
        artifact_generation_service=FakeArtifactGenerationService(),
        video_assembly_factory_service=factory_service,
        tag_management_service=tag_service,
        system_settings_service=settings_service,
    )

    product_id = product_service.create_product(
        CreateProductCommand(product_code="honey", product_name="Honey Launch", default_platform="tiktok")
    )
    visual_asset_id = asset_service.register_asset(
        RegisterAssetCommand(
            product_id=product_id,
            asset_type="background_video",
            source_file_path=_write_media_file(workspace_root / "source" / "hero.mp4", "hero"),
            asset_code="hero_asset",
        )
    )
    voice_asset_id = asset_service.register_asset(
        RegisterAssetCommand(
            product_id=product_id,
            asset_type="voiceover",
            source_file_path=_write_media_file(workspace_root / "source" / "voice.mp3", "voice"),
            asset_code="voice_asset",
        )
    )
    music_asset_id = asset_service.register_asset(
        RegisterAssetCommand(
            product_id=product_id,
            asset_type="background_music",
            source_file_path=_write_media_file(workspace_root / "source" / "music.mp3", "music"),
            asset_code="music_asset",
        )
    )

    tag_id = tag_service.create_tag(CreateTagCommand(tag_name="Warm", tag_group="Mood"))
    tag_service.assign_tag_to_asset(AssignTagToAssetCommand(asset_id=visual_asset_id, tag_id=tag_id))

    recipe_id = factory_service.create_recipe(
        CreateRecipeCommand(
            product_id=product_id,
            recipe_code="Honey Launch",
            target_platform="tiktok",
            target_ratio="9:16",
            hook_text="Fresh honey every day",
            cta_text="Order now",
        )
    )
    factory_service.assign_asset_to_recipe(
        AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=visual_asset_id, role="hero")
    )
    factory_service.assign_asset_to_recipe(
        AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=voice_asset_id, role="voice")
    )
    factory_service.assign_asset_to_recipe(
        AssignAssetToRecipeCommand(recipe_id=recipe_id, asset_id=music_asset_id, role="music")
    )

    preview_job_id = factory_service.enqueue_preview_job(recipe_id)
    factory_service.run_preview_job(preview_job_id)
    preview_output = factory_service.list_outputs(recipe_id=recipe_id)[0]
    manifest_payload = json.loads(Path(preview_output.manifest_path).read_text(encoding="utf-8"))

    approval_guard_triggered = False
    try:
        factory_service.approve_recipe(recipe_id, actor="qa_lead", reason="creative approved")
    except RecipeApprovalError:
        approval_guard_triggered = True

    factory_service.approve_output(preview_output.output_id, actor="qa_lead", reason="ready to publish")
    factory_service.approve_recipe(recipe_id, actor="qa_lead", reason="creative approved")
    final_job_id = factory_service.enqueue_final_render_job(recipe_id)
    factory_service.run_final_render_job(final_job_id)

    recipe = factory_service.get_recipe(recipe_id)
    outputs = factory_service.list_outputs(recipe_id=recipe_id)
    final_output = next(output for output in outputs if output.output_kind == "final")
    events = factory_service.list_decision_events(recipe_id)
    assets = asset_service.list_assets()
    tags = tag_service.list_tags()
    dashboard_summary = dashboard_service.build_summary()

    return {
        "product_count": len(product_service.list_products()),
        "asset_count": len(assets),
        "ready_asset_count": sum(1 for asset in assets if asset.status == "ready"),
        "tag_count": len(tags),
        "hero_tag_labels": list(next(asset for asset in assets if asset.asset_id == visual_asset_id).tag_labels),
        "approval_guard_triggered": approval_guard_triggered,
        "recipe_status": recipe.status,
        "recipe_score": recipe.recipe_score,
        "recipe_duplicate_risk": recipe.duplicate_risk,
        "preview_review_required": bool(manifest_payload["review_gate"]["required"]),
        "preview_review_signals": [signal["code"] for signal in manifest_payload["review_gate"]["signals"]],
        "preview_audio_mode": manifest_payload["audio_mix"]["mode"],
        "output_count": len(outputs),
        "final_output_kind": final_output.output_kind,
        "final_output_auto_approved_by": final_output.approved_by,
        "decision_event_types": [event.event_type for event in events],
        "dashboard_recipe_count": dashboard_summary.recipe_count,
        "dashboard_output_count": dashboard_summary.output_count,
        "dashboard_needs_review_recipe_count": dashboard_summary.needs_review_recipe_count,
    }


def run_recovery_audit(base_dir: Path, template: SystemSettingsDTO) -> dict[str, object]:
    queued_workspace = base_dir / "recovery_queued"
    queued_workspace.mkdir(parents=True, exist_ok=True)
    queued_config = default_config(queued_workspace)
    queued_settings = SystemSettingsService(
        queued_config.paths.app_config_path,
        runtime_path_roots=_runtime_path_roots_from_config(queued_config),
    )
    queued_settings.save(
        replace(
            _settings_for_workspace(queued_workspace, template),
            max_recovery_jobs_per_run=2,
            auto_recover_queued_jobs=False,
            failed_job_escalation_threshold=2,
        )
    )
    queued_dashboard = DashboardService(
        config=queued_config,
        product_service=ProductApplicationService(unit_of_work_factory=_build_file_uow_factory(queued_workspace / "audit.db")),
        asset_intake_service=_build_asset_service(_build_file_uow_factory(queued_workspace / "audit.db"), queued_workspace / "media_library"),
        artifact_generation_service=FakeArtifactGenerationService(queued_count=2, failed_count=0),
        video_assembly_factory_service=FakeVideoAssemblyFactoryService(),
        tag_management_service=TagManagementService(unit_of_work_factory=_build_file_uow_factory(queued_workspace / "audit.db")),
        system_settings_service=queued_settings,
    )
    queued_result = queued_dashboard.recover_queued_jobs(trigger="manual")

    failed_workspace = base_dir / "recovery_failed"
    failed_workspace.mkdir(parents=True, exist_ok=True)
    failed_config = default_config(failed_workspace)
    failed_settings = SystemSettingsService(
        failed_config.paths.app_config_path,
        runtime_path_roots=_runtime_path_roots_from_config(failed_config),
    )
    failed_settings.save(
        replace(
            _settings_for_workspace(failed_workspace, template),
            max_recovery_jobs_per_run=1,
            auto_recover_queued_jobs=False,
            failed_job_escalation_threshold=2,
        )
    )
    failed_dashboard = DashboardService(
        config=failed_config,
        product_service=ProductApplicationService(unit_of_work_factory=_build_file_uow_factory(failed_workspace / "audit.db")),
        asset_intake_service=_build_asset_service(_build_file_uow_factory(failed_workspace / "audit.db"), failed_workspace / "media_library"),
        artifact_generation_service=FakeArtifactGenerationService(
            queued_count=0,
            failed_count=1,
            failed_failure_streaks=[1],
        ),
        video_assembly_factory_service=FakeVideoAssemblyFactoryService(failed_failure_streak=3),
        tag_management_service=TagManagementService(unit_of_work_factory=_build_file_uow_factory(failed_workspace / "audit.db")),
        system_settings_service=failed_settings,
    )
    failed_before = failed_dashboard.build_summary()
    failed_result = failed_dashboard.retry_failed_jobs(trigger="manual")
    failed_after = failed_dashboard.build_summary()

    return {
        "queued_recovery": {
            "matched_job_count": queued_result.matched_job_count,
            "attempted_job_count": queued_result.attempted_job_count,
            "deferred_job_count": queued_result.deferred_job_count,
            "recovered_job_codes": list(queued_result.recovered_job_codes),
            "deferred_job_codes": list(queued_result.deferred_job_codes),
        },
        "failed_recovery": {
            "before_escalated_job_count": failed_before.escalated_job_count,
            "attempted_job_count": failed_result.attempted_job_count,
            "deferred_job_count": failed_result.deferred_job_count,
            "escalated_job_count": failed_result.escalated_job_count,
            "recovered_job_codes": list(failed_result.recovered_job_codes),
            "deferred_job_codes": list(failed_result.deferred_job_codes),
            "escalated_job_codes": list(failed_result.escalated_job_codes),
            "after_failed_job_count": failed_after.failed_job_count,
            "operator_playbook_lines": list(failed_before.operator_playbook_lines),
        },
    }


def run_hot_reload_audit(base_dir: Path) -> dict[str, object]:
    workspace_root = base_dir / "hot_reload"
    _prepare_runtime_workspace(workspace_root)
    runtime = ApplicationRuntime(workspace_root)

    runtime.product_service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    before_count = len(runtime.product_service.list_products())

    updated = replace(
        runtime.system_settings_service.load(),
        database_path=str(workspace_root / "data" / "mtclip.db"),
        media_root=str(workspace_root / "media_library_v2"),
        docs_root=str(workspace_root / "doc_v2"),
        outputs_root=str(workspace_root / "outputs_v2"),
        preview_root=str(workspace_root / "outputs_v2" / "preview"),
    )
    runtime.system_settings_service.save(updated)
    pending = runtime.system_settings_service.path_root_status()
    applied = runtime.reload_path_roots()
    summary = runtime.dashboard_service.build_summary()
    after_count = len(runtime.product_service.list_products())

    return {
        "before_product_count": before_count,
        "pending_changed_path_roots": list(pending.changed_path_roots),
        "applied_changed_path_roots": list(applied.changed_path_roots),
        "summary_reload_policy": summary.path_reload_policy,
        "summary_restart_required": summary.path_restart_required,
        "summary_runtime_database_path": summary.runtime_database_path,
        "summary_database_path": summary.database_path,
        "summary_runtime_outputs_root": summary.runtime_outputs_root,
        "summary_outputs_root": summary.outputs_root,
        "after_product_count": after_count,
    }


def main() -> int:
    template = _repo_settings_template()
    base_dir = Path(tempfile.mkdtemp(prefix="mtcf_release_audit_"))
    try:
        result = {
            "full_factory_workflow": run_full_factory_workflow(base_dir, template),
            "recovery_and_escalation": run_recovery_audit(base_dir, template),
            "runtime_hot_reload": run_hot_reload_audit(base_dir),
        }
        print(json.dumps(result, indent=2))
        return 0
    finally:
        shutil.rmtree(base_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
