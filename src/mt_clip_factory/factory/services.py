from __future__ import annotations
from collections.abc import Callable
from mt_clip_factory.domain.enums import JobStatus, RecipeStatus
from mt_clip_factory.domain.job_recovery import (
    apply_job_failure_metadata,
    apply_job_success_metadata,
    prepare_job_output_for_retry,
)
from mt_clip_factory.domain.outputs import Output
from mt_clip_factory.domain.recipes import Recipe
from mt_clip_factory.domain.services import UnitOfWork
from mt_clip_factory.factory.automation_policy import ProductAutomationPolicyService
from mt_clip_factory.factory.composition_mapping import to_composition_plan_dto
from mt_clip_factory.factory.composition_runtime import persist_composition
from mt_clip_factory.factory.caption_runtime import CaptionRuntimeService
from mt_clip_factory.factory.dto import (
    AssignAssetToRecipeCommand,
    CompositionPlanDTO,
    CreateRecipeCommand,
    DecisionEventDTO,
    OutputSummaryDTO,
    PreviewJobSummaryDTO,
    RecipeDetailsDTO,
    RecipeItemDTO,
    RecipeSummaryDTO,
)
from mt_clip_factory.factory.manifest_envelope import build_manifest_envelope
from mt_clip_factory.factory.output_history import USABLE_OUTPUT_HISTORY_SCOPES, extract_clip_formula_hash, resolve_output_history_scope
from mt_clip_factory.factory.preview_artifacts import PreviewManifestBuilder
from mt_clip_factory.factory.preview_composition import build_segmented_preview_composition
from mt_clip_factory.factory.product_run_store import ProductRunArtifactStore
from mt_clip_factory.factory.renderers import RenderedPreviewOutput
from mt_clip_factory.factory.recipe_scoring import score_and_persist_recipe
from mt_clip_factory.factory.review_gate import (
    apply_review_gate,
    assess_review_gate,
    review_gate_manifest_payload,
    review_settings_from_provider,
    with_historical_render_duplicate,
)
from mt_clip_factory.factory.service_errors import (
    AssetNotReadyForRecipeError,
    FactoryJobNotFoundError,
    FinalRenderPrerequisiteError,
    OutputApprovalError,
    OutputNotFoundError,
    PreviewBuildInputError,
    RecipeAlreadyExistsError,
    RecipeApprovalError,
    RecipeAssetMismatchError,
    RecipeItemAlreadyExistsError,
    RecipeNotFoundError,
)
from mt_clip_factory.factory.service_support import (
    append_run_journal_event as _append_run_journal_event,
    format_optional_timestamp as _format_optional_timestamp,
    format_timestamp as _format_timestamp,
    latest_event_timestamp as _latest_event_timestamp,
    list_output_summaries as _list_output_summaries,
    list_job_summaries as _list_job_summaries,
    load_recipe_items_and_assets as _load_recipe_items_and_assets,
    normalize_actor as _normalize_actor,
    normalize_reason as _normalize_reason,
    optional_text as _optional_text,
    enqueue_recipe_job as _enqueue_recipe_job_helper,
    record_decision_event as _record_decision_event,
    resolve_caption_frame_size as _resolve_caption_frame_size,
    resolve_artifact_paths as _resolve_artifact_paths,
    slugify_recipe_code as _slugify_recipe_code,
    to_preview_job_summary as _to_preview_job_summary,
    utc_now as _utc_now,
)
from mt_clip_factory.time_utils import format_utc_iso_timestamp
from mt_clip_factory.library.artifacts import build_artifact_job_code, decode_job_input
class VideoAssemblyFactoryService:
    PREVIEW_JOB_TYPE = "render_recipe_preview"
    FINAL_JOB_TYPE = "render_recipe_final"
    SYSTEM_APPROVAL_ACTOR = "system_final_render"
    SYSTEM_APPROVAL_REASON = "Auto-approved by final render pipeline."
    OUTPUT_APPROVED_EVENT = "output_approved"
    OUTPUT_AUTO_APPROVED_EVENT = "output_auto_approved"
    RECIPE_APPROVED_EVENT = "recipe_approved"
    RECIPE_REJECTED_EVENT = "recipe_rejected"
    RECIPE_REVIEW_REQUIRED_EVENT = "recipe_review_required"
    RECIPE_REVIEW_CLEARED_EVENT = "recipe_review_cleared"
    RECIPE_ASSET_REPLACED_EVENT = "recipe_assets_replaced"
    SYSTEM_REVIEW_ACTOR = "system_review_gate"

    def __init__(
        self,
        unit_of_work_factory: Callable[[], UnitOfWork],
        preview_manifest_builder: PreviewManifestBuilder,
        preview_renderer,
        final_renderer,
        system_settings_service=None,
        caption_runtime_service: CaptionRuntimeService | None = None,
        automation_policy_service: ProductAutomationPolicyService | None = None,
        run_artifact_store: ProductRunArtifactStore | None = None,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._preview_manifest_builder = preview_manifest_builder
        self._preview_renderer = preview_renderer
        self._final_renderer = final_renderer
        self._system_settings_service = system_settings_service
        self._caption_runtime_service = caption_runtime_service
        self._automation_policy_service = automation_policy_service
        self._run_artifact_store = run_artifact_store

    def create_recipe(self, command: CreateRecipeCommand) -> int:
        recipe_code = _slugify_recipe_code(command.recipe_code)
        if not recipe_code:
            raise ValueError("Recipe code is required.")

        with self._unit_of_work_factory() as uow:
            product = uow.products.get_by_id(command.product_id)
            if product is None or product.id is None:
                raise ValueError(str(command.product_id))
            if uow.recipes.get_by_code(recipe_code) is not None:
                raise RecipeAlreadyExistsError(recipe_code)

            recipe = Recipe(
                product_id=command.product_id,
                recipe_code=recipe_code,
                target_platform=command.target_platform,
                target_ratio=command.target_ratio,
                duration_sec=command.duration_sec,
                mood=command.mood,
                script_angle=command.script_angle,
                target_audience=command.target_audience,
                hook_text=command.hook_text,
                cta_text=command.cta_text,
            )
            created = uow.recipes.add(recipe)
            score_and_persist_recipe(uow, recipe=created, items=(), assets={})
            uow.commit()
            if created.id is None:
                raise RuntimeError("Recipe identifier was not assigned.")
            return created.id

    def list_recipes(
        self,
        *,
        product_id: int | None = None,
        status: str | None = None,
    ) -> list[RecipeSummaryDTO]:
        with self._unit_of_work_factory() as uow:
            return [
                RecipeSummaryDTO(
                    recipe_id=summary.recipe_id,
                    product_id=summary.product_id,
                    product_code=summary.product_code,
                    recipe_code=summary.recipe_code,
                    target_platform=summary.target_platform,
                    target_ratio=summary.target_ratio,
                    status=summary.status.value,
                    decision_actor=summary.decision_actor,
                    decision_at=_format_optional_timestamp(summary.decision_at),
                    item_count=summary.item_count,
                    recipe_score=summary.recipe_score,
                    duplicate_risk=summary.duplicate_risk,
                )
                for summary in uow.recipes.list_summaries(product_id=product_id, status=status)
            ]

    def get_recipe(self, recipe_id: int) -> RecipeDetailsDTO:
        with self._unit_of_work_factory() as uow:
            recipe = uow.recipes.get_by_id(recipe_id)
            if recipe is None or recipe.id is None:
                raise RecipeNotFoundError(str(recipe_id))
            items = tuple(
                RecipeItemDTO(
                    recipe_item_id=item.id or 0,
                    asset_id=item.asset_id,
                    asset_code=item.asset_code,
                    asset_type=item.asset_type,
                    role=item.role,
                )
                for item in uow.recipes.list_items(recipe_id)
            )
            return RecipeDetailsDTO(
                recipe_id=recipe.id,
                product_id=recipe.product_id,
                recipe_code=recipe.recipe_code,
                target_platform=recipe.target_platform,
                target_ratio=recipe.target_ratio,
                duration_sec=recipe.duration_sec,
                mood=recipe.mood,
                script_angle=recipe.script_angle,
                target_audience=recipe.target_audience,
                hook_text=recipe.hook_text,
                cta_text=recipe.cta_text,
                status=recipe.status.value,
                decision_actor=recipe.decision_actor,
                decision_at=_format_optional_timestamp(recipe.decision_at),
                decision_reason=recipe.decision_reason,
                items=items,
                recipe_score=recipe.recipe_score,
                duplicate_risk=recipe.duplicate_risk,
            )

    def get_recipe_by_code(self, recipe_code: str) -> RecipeDetailsDTO | None:
        with self._unit_of_work_factory() as uow:
            recipe = uow.recipes.get_by_code(_slugify_recipe_code(recipe_code))
            if recipe is None or recipe.id is None:
                return None
            items = tuple(
                RecipeItemDTO(
                    recipe_item_id=item.id or 0,
                    asset_id=item.asset_id,
                    asset_code=item.asset_code,
                    asset_type=item.asset_type,
                    role=item.role,
                )
                for item in uow.recipes.list_items(recipe.id)
            )
            return RecipeDetailsDTO(
                recipe_id=recipe.id,
                product_id=recipe.product_id,
                recipe_code=recipe.recipe_code,
                target_platform=recipe.target_platform,
                target_ratio=recipe.target_ratio,
                duration_sec=recipe.duration_sec,
                mood=recipe.mood,
                script_angle=recipe.script_angle,
                target_audience=recipe.target_audience,
                hook_text=recipe.hook_text,
                cta_text=recipe.cta_text,
                status=recipe.status.value,
                decision_actor=recipe.decision_actor,
                decision_at=_format_optional_timestamp(recipe.decision_at),
                decision_reason=recipe.decision_reason,
                items=items,
                recipe_score=recipe.recipe_score,
                duplicate_risk=recipe.duplicate_risk,
            )

    def assign_asset_to_recipe(self, command: AssignAssetToRecipeCommand) -> int:
        role = command.role.strip().lower()
        if not role:
            raise ValueError("Recipe role is required.")

        with self._unit_of_work_factory() as uow:
            recipe = uow.recipes.get_by_id(command.recipe_id)
            if recipe is None or recipe.id is None:
                raise RecipeNotFoundError(str(command.recipe_id))
            asset = uow.assets.get_by_id(command.asset_id)
            if asset is None or asset.id is None:
                raise ValueError(str(command.asset_id))
            if asset.product_id != recipe.product_id:
                raise RecipeAssetMismatchError(str(command.asset_id))
            if asset.status != "ready":
                raise AssetNotReadyForRecipeError(asset.asset_code)
            if any(item.asset_id == asset.id and item.role == role for item in uow.recipes.list_items(recipe.id)):
                raise RecipeItemAlreadyExistsError(f"{asset.asset_code}:{role}")

            item = uow.recipes.add_item(recipe.id, asset.id, role)
            score_and_persist_recipe(
                uow,
                recipe=recipe,
                items=list(uow.recipes.list_items(recipe.id)),
                assets={asset.id: asset},
            )
            uow.commit()
            if item.id is None:
                raise RuntimeError("Recipe item identifier was not assigned.")
            return item.id

    def list_outputs(
        self,
        *,
        recipe_id: int | None = None,
        product_id: int | None = None,
        approved: bool | None = None,
        history_scopes: tuple[str, ...] | None = None,
    ) -> list[OutputSummaryDTO]:
        return _list_output_summaries(
            unit_of_work_factory=self._unit_of_work_factory,
            recipe_id=recipe_id,
            product_id=product_id,
            approved=approved,
            history_scopes=history_scopes,
            preview_job_type=self.PREVIEW_JOB_TYPE,
            final_job_type=self.FINAL_JOB_TYPE,
            format_timestamp=_format_timestamp,
            format_optional_timestamp=_format_optional_timestamp,
        )

    def list_decision_events(self, recipe_id: int) -> list[DecisionEventDTO]:
        with self._unit_of_work_factory() as uow:
            recipe = uow.recipes.get_by_id(recipe_id)
            if recipe is None or recipe.id is None:
                raise RecipeNotFoundError(str(recipe_id))
            return [
                DecisionEventDTO(
                    event_id=event.id or 0,
                    recipe_id=event.recipe_id,
                    event_type=event.event_type,
                    actor=event.actor,
                    created_at=_format_timestamp(event.created_at),
                    output_id=event.output_id,
                    output_code=event.output_code,
                    reason=event.reason,
                )
                for event in uow.decision_events.list_by_recipe(recipe_id)
            ]

    def get_composition_plan(self, recipe_id: int) -> CompositionPlanDTO:
        with self._unit_of_work_factory() as uow:
            recipe = uow.recipes.get_by_id(recipe_id)
            if recipe is None or recipe.id is None:
                raise RecipeNotFoundError(str(recipe_id))
            product = uow.products.get_by_id(recipe.product_id)
            if product is None:
                raise ValueError(str(recipe.product_id))
            items, assets = _load_recipe_items_and_assets(uow, recipe_id=recipe.id)
            fill_policies = (
                None
                if self._automation_policy_service is None
                else self._automation_policy_service.load_fill_policies(product.product_code)
            )
            persisted = persist_composition(uow, recipe=recipe, items=items, assets=assets, fill_policies=fill_policies)
            uow.commit()
            return to_composition_plan_dto(
                persisted.plan,
                tuple(uow.timeline_segments.list_by_plan(persisted.plan.id)),
                tuple(uow.render_decisions.list_by_plan(persisted.plan.id)),
                format_timestamp=_format_timestamp,
            )

    def approve_output(self, output_id: int, *, actor: str, reason: str | None = None) -> None:
        actor_name = _normalize_actor(actor)
        approval_reason = _normalize_reason(reason)
        with self._unit_of_work_factory() as uow:
            output = uow.outputs.get_by_id(output_id)
            if output is None or output.id is None:
                raise OutputNotFoundError(str(output_id))
            replacement_event_at = _latest_event_timestamp(
                uow,
                recipe_id=output.recipe_id,
                event_type=self.RECIPE_ASSET_REPLACED_EVENT,
            )
            if replacement_event_at is not None and output.created_at <= replacement_event_at:
                raise OutputApprovalError(
                    "Select a newly rebuilt output after asset replacement before approving output."
                )
            approved_at = _utc_now()
            output.approved = True
            output.approved_by = actor_name
            output.approved_at = approved_at
            output.approval_reason = approval_reason
            uow.outputs.update(output)
            _record_decision_event(
                uow,
                recipe_id=output.recipe_id,
                output_id=output.id,
                event_type=self.OUTPUT_APPROVED_EVENT,
                actor=actor_name,
                reason=approval_reason,
                created_at=approved_at,
            )
            uow.commit()

    def approve_recipe(self, recipe_id: int, *, actor: str, reason: str | None = None) -> None:
        actor_name = _normalize_actor(actor)
        decision_reason = _normalize_reason(reason)
        with self._unit_of_work_factory() as uow:
            recipe = uow.recipes.get_by_id(recipe_id)
            if recipe is None or recipe.id is None:
                raise RecipeNotFoundError(str(recipe_id))
            if recipe.status == RecipeStatus.NEEDS_REVIEW and decision_reason is None:
                raise RecipeApprovalError("Provide a review reason before approving a recipe that needs review.")
            approved_outputs = list(uow.outputs.list_summaries(recipe_id=recipe_id, approved=True))
            if not approved_outputs:
                raise RecipeApprovalError("Approve at least one output before approving the recipe.")
            replacement_event_at = _latest_event_timestamp(
                uow,
                recipe_id=recipe_id,
                event_type=self.RECIPE_ASSET_REPLACED_EVENT,
            )
            if replacement_event_at is not None and not any(
                output.approved_at is not None and output.approved_at > replacement_event_at
                for output in approved_outputs
            ):
                raise RecipeApprovalError(
                    "Approve a newly rebuilt output after asset replacement before approving the recipe."
                )
            decided_at = _utc_now()
            recipe.status = RecipeStatus.APPROVED
            recipe.decision_actor = actor_name
            recipe.decision_at = decided_at
            recipe.decision_reason = decision_reason
            uow.recipes.update(recipe)
            _record_decision_event(
                uow,
                recipe_id=recipe.id,
                event_type=self.RECIPE_APPROVED_EVENT,
                actor=actor_name,
                reason=decision_reason,
                created_at=decided_at,
            )
            uow.commit()

    def reject_recipe(self, recipe_id: int, *, actor: str, reason: str | None = None) -> None:
        actor_name = _normalize_actor(actor)
        decision_reason = _normalize_reason(reason)
        with self._unit_of_work_factory() as uow:
            recipe = uow.recipes.get_by_id(recipe_id)
            if recipe is None or recipe.id is None:
                raise RecipeNotFoundError(str(recipe_id))
            decided_at = _utc_now()
            recipe.status = RecipeStatus.REJECTED
            recipe.decision_actor = actor_name
            recipe.decision_at = decided_at
            recipe.decision_reason = decision_reason
            uow.recipes.update(recipe)
            _record_decision_event(
                uow,
                recipe_id=recipe.id,
                event_type=self.RECIPE_REJECTED_EVENT,
                actor=actor_name,
                reason=decision_reason,
                created_at=decided_at,
            )
            uow.commit()

    def enqueue_preview_job(self, recipe_id: int, *, batch_code: str | None = None, source_mode: str | None = None) -> int:
        return _enqueue_recipe_job_helper(
            unit_of_work_factory=self._unit_of_work_factory,
            recipe_id=recipe_id,
            job_type=self.PREVIEW_JOB_TYPE,
            code_prefix="preview",
            batch_code=batch_code,
            source_mode=source_mode,
            recipe_not_found_error=RecipeNotFoundError,
        )

    def enqueue_final_render_job(self, recipe_id: int, *, batch_code: str | None = None, source_mode: str | None = None) -> int:
        with self._unit_of_work_factory() as uow:
            recipe = uow.recipes.get_by_id(recipe_id)
            if recipe is None or recipe.id is None:
                raise RecipeNotFoundError(str(recipe_id))
            if recipe.status != RecipeStatus.APPROVED:
                raise FinalRenderPrerequisiteError("Approve the recipe before starting final render.")
        return _enqueue_recipe_job_helper(
            unit_of_work_factory=self._unit_of_work_factory,
            recipe_id=recipe_id,
            job_type=self.FINAL_JOB_TYPE,
            code_prefix="final",
            batch_code=batch_code,
            source_mode=source_mode,
            recipe_not_found_error=RecipeNotFoundError,
        )

    def run_preview_job(self, job_id: int) -> None:
        with self._unit_of_work_factory() as uow:
            job = uow.jobs.get_by_id(job_id)
            if job is None or job.id is None:
                raise ValueError(str(job_id))
            if job.job_type != self.PREVIEW_JOB_TYPE:
                raise ValueError(f"Unsupported preview job type: {job.job_type}")

            payload = decode_job_input(job.input_json)
            recipe_id = int(payload.get("recipe_id") or job.recipe_id or 0)
            batch_code = _optional_text(payload.get("batch_code"))
            source_mode = _optional_text(payload.get("source_mode"))
            recipe = uow.recipes.get_by_id(recipe_id)
            if recipe is None or recipe.id is None:
                raise RecipeNotFoundError(str(recipe_id))
            product = uow.products.get_by_id(recipe.product_id)
            if product is None:
                raise ValueError(str(recipe.product_id))
            fill_policies = (
                None
                if self._automation_policy_service is None
                else self._automation_policy_service.load_fill_policies(product.product_code)
            )
            artifact_paths = _resolve_artifact_paths(
                run_artifact_store=self._run_artifact_store,
                preview_renderer=self._preview_renderer,
                final_renderer=self._final_renderer,
                preview_manifest_builder=self._preview_manifest_builder,
                product_code=product.product_code,
                batch_code=batch_code,
                output_stem=recipe.recipe_code,
                stage_name="preview",
            )
            items, assets = _load_recipe_items_and_assets(uow, recipe_id=recipe.id)

            job.status = JobStatus.PROCESSING
            job.started_at = _utc_now()
            job.progress = 0.1
            uow.jobs.update(job)
            uow.commit()

            try:
                if not items:
                    raise PreviewBuildInputError(f"Recipe {recipe.recipe_code} has no items.")

                persisted = persist_composition(
                    uow,
                    recipe=recipe,
                    items=items,
                    assets=assets,
                    fill_policies=fill_policies,
                )
                composition = build_segmented_preview_composition(
                    recipe=recipe,
                    product_code=product.product_code,
                    items=items,
                    assets=assets,
                    plan=persisted.plan,
                    segments=persisted.segments,
                    caption_runtime_service=self._caption_runtime_service,
                    automation_policy_service=self._automation_policy_service,
                    caption_frame_size=_resolve_caption_frame_size(
                        system_settings_service=self._system_settings_service,
                        target_ratio=recipe.target_ratio,
                        output_resolution_field="preview_output_resolution",
                    ),
                )
                if not composition.source_files:
                    raise PreviewBuildInputError(f"Recipe {recipe.recipe_code} has no renderable video assets.")
                rendered_output = self._preview_renderer.render_output(
                    product_code=product.product_code,
                    output_stem=recipe.recipe_code,
                    source_files=list(composition.source_files),
                    segment_clips=composition.segment_clips,
                    audio_mix_plan=composition.audio_mix_plan,
                    target_ratio=recipe.target_ratio,
                    target_path=artifact_paths.video_path,
                    fill_policies=fill_policies,
                )
                review_assessment = assess_review_gate(
                    plan=persisted.plan,
                    composition=composition,
                    settings=review_settings_from_provider(self._system_settings_service),
                    audio_mix_summary=rendered_output.audio_mix_summary,
                )
                manifest_payload = dict(composition.manifest_payload)
                clip_formula_hash = extract_clip_formula_hash(manifest_payload)
                review_assessment = with_historical_render_duplicate(
                    review_assessment,
                    duplicate_count=_historical_render_duplicate_count(
                        uow,
                        product_id=recipe.product_id,
                        clip_formula_hash=clip_formula_hash,
                    ),
                )
                manifest_payload["review_gate"] = review_gate_manifest_payload(review_assessment)
                if rendered_output.audio_mix_summary is not None:
                    manifest_payload["audio_mix"] = rendered_output.audio_mix_summary
                if rendered_output.visual_composite_summary is not None:
                    manifest_payload["visual_composite"] = rendered_output.visual_composite_summary
                manifest_payload = build_manifest_envelope(
                    product_code=product.product_code,
                    recipe_code=recipe.recipe_code,
                    stage_name="preview",
                    target_platform=recipe.target_platform,
                    target_ratio=recipe.target_ratio,
                    output_path=rendered_output.file_path,
                    manifest_path=artifact_paths.manifest_path,
                    batch_code=batch_code,
                    run_root=artifact_paths.run_root,
                    journal_path=artifact_paths.journal_path,
                    order_snapshot_path=artifact_paths.order_snapshot_path,
                    product_local=artifact_paths.product_local,
                    payload=manifest_payload,
                )
                manifest_path = self._preview_manifest_builder.write_manifest(
                    product_code=product.product_code,
                    recipe_code=recipe.recipe_code,
                    payload=manifest_payload,
                    target_path=artifact_paths.manifest_path,
                )
                output = uow.outputs.add(
                    Output(
                        recipe_id=recipe.id,
                        output_code=build_artifact_job_code("preview_output"),
                        file_path=str(rendered_output.file_path),
                        platform=recipe.target_platform,
                        ratio=recipe.target_ratio,
                        duration_sec=rendered_output.duration_sec,
                        quality_score=review_assessment.quality_score,
                        duplicate_risk=review_assessment.duplicate_risk,
                        approved=False,
                        clip_formula_hash=clip_formula_hash,
                        history_scope=resolve_output_history_scope(approved=False, source_mode=source_mode),
                    )
                )
                apply_review_gate(
                    uow,
                    recipe=recipe,
                    assessment=review_assessment,
                    required_event=self.RECIPE_REVIEW_REQUIRED_EVENT,
                    cleared_event=self.RECIPE_REVIEW_CLEARED_EVENT,
                    actor=self.SYSTEM_REVIEW_ACTOR,
                    utc_now=_utc_now,
                    record_decision_event=_record_decision_event,
                )
                score_and_persist_recipe(
                    uow,
                    recipe=recipe,
                    items=items,
                    assets=assets,
                    review_assessment=review_assessment,
                )
                job.status = JobStatus.DONE
                job.progress = 1.0
                finished_at = _utc_now()
                job.output_json = apply_job_success_metadata(
                    job.output_json,
                    succeeded_at=_format_timestamp(finished_at),
                    payload_updates={
                        "output_id": output.id,
                        "preview_manifest_path": str(manifest_path),
                        "preview_output_path": str(rendered_output.file_path),
                    },
                )
                job.error_message = None
                job.finished_at = finished_at
                uow.jobs.update(job)
                uow.commit()
                _append_run_journal_event(
                    run_artifact_store=self._run_artifact_store,
                    product_code=product.product_code,
                    batch_code=batch_code,
                    event_type="preview_rendered",
                    status="review_required" if review_assessment.required else "succeeded",
                    fields={
                        "recorded_at": format_utc_iso_timestamp(finished_at),
                        "recipe_code": recipe.recipe_code,
                        "output_path": str(rendered_output.file_path),
                        "manifest_path": str(manifest_path),
                    },
                )
            except Exception as exc:
                job.status = JobStatus.FAILED
                job.progress = 0.0
                job.error_message = str(exc)
                finished_at = _utc_now()
                job.finished_at = finished_at
                job.output_json = apply_job_failure_metadata(
                    job.output_json,
                    failed_at=_format_timestamp(finished_at),
                    error_message=str(exc),
                )
                uow.jobs.update(job)
                uow.commit()
                _append_run_journal_event(
                    run_artifact_store=self._run_artifact_store,
                    product_code=product.product_code,
                    batch_code=batch_code,
                    event_type="preview_rendered",
                    status="failed",
                    fields={
                        "recorded_at": format_utc_iso_timestamp(finished_at),
                        "recipe_code": recipe.recipe_code,
                        "error_message": str(exc),
                    },
                )
                raise

    def run_final_render_job(self, job_id: int) -> None:
        with self._unit_of_work_factory() as uow:
            job = uow.jobs.get_by_id(job_id)
            if job is None or job.id is None:
                raise ValueError(str(job_id))
            if job.job_type != self.FINAL_JOB_TYPE:
                raise ValueError(f"Unsupported final job type: {job.job_type}")

            payload = decode_job_input(job.input_json)
            recipe_id = int(payload.get("recipe_id") or job.recipe_id or 0)
            batch_code = _optional_text(payload.get("batch_code"))
            source_mode = _optional_text(payload.get("source_mode"))
            recipe = uow.recipes.get_by_id(recipe_id)
            if recipe is None or recipe.id is None:
                raise RecipeNotFoundError(str(recipe_id))
            if recipe.status != RecipeStatus.APPROVED:
                raise FinalRenderPrerequisiteError("Approve the recipe before starting final render.")
            product = uow.products.get_by_id(recipe.product_id)
            if product is None:
                raise ValueError(str(recipe.product_id))
            fill_policies = (
                None
                if self._automation_policy_service is None
                else self._automation_policy_service.load_fill_policies(product.product_code)
            )
            artifact_paths = _resolve_artifact_paths(
                run_artifact_store=self._run_artifact_store,
                preview_renderer=self._preview_renderer,
                final_renderer=self._final_renderer,
                preview_manifest_builder=self._preview_manifest_builder,
                product_code=product.product_code,
                batch_code=batch_code,
                output_stem=f"{recipe.recipe_code}_final",
                stage_name="final",
            )
            items = list(uow.recipes.list_items(recipe.id))
            assets = {
                item.asset_id: asset
                for item in items
                for asset in [uow.assets.get_by_id(item.asset_id)]
                if asset is not None
            }

            job.status = JobStatus.PROCESSING
            job.started_at = _utc_now()
            job.progress = 0.1
            uow.jobs.update(job)
            uow.commit()

            try:
                approved_outputs = list(uow.outputs.list_summaries(recipe_id=recipe.id, approved=True))
                if not approved_outputs:
                    raise FinalRenderPrerequisiteError("Approve at least one output before final render.")
                if not items:
                    raise FinalRenderPrerequisiteError(f"Recipe {recipe.recipe_code} has no items.")

                source_output = approved_outputs[0]
                persisted = persist_composition(
                    uow,
                    recipe=recipe,
                    items=items,
                    assets=assets,
                    fill_policies=fill_policies,
                )
                composition = build_segmented_preview_composition(
                    recipe=recipe,
                    product_code=product.product_code,
                    items=items,
                    assets=assets,
                    plan=persisted.plan,
                    segments=persisted.segments,
                    caption_runtime_service=self._caption_runtime_service,
                    automation_policy_service=self._automation_policy_service,
                    caption_frame_size=_resolve_caption_frame_size(
                        system_settings_service=self._system_settings_service,
                        target_ratio=recipe.target_ratio,
                        output_resolution_field="final_output_resolution",
                    ),
                )
                if not composition.source_files:
                    raise FinalRenderPrerequisiteError(f"Recipe {recipe.recipe_code} has no renderable video assets.")
                rendered_output = self._final_renderer.render_output(
                    product_code=product.product_code,
                    output_stem=f"{recipe.recipe_code}_final",
                    source_files=list(composition.source_files),
                    segment_clips=composition.segment_clips,
                    audio_mix_plan=composition.audio_mix_plan,
                    target_ratio=recipe.target_ratio,
                    target_path=artifact_paths.video_path,
                    fill_policies=fill_policies,
                )
                review_assessment = assess_review_gate(
                    plan=persisted.plan,
                    composition=composition,
                    settings=review_settings_from_provider(self._system_settings_service),
                    audio_mix_summary=rendered_output.audio_mix_summary,
                )
                manifest_payload = dict(composition.manifest_payload)
                clip_formula_hash = extract_clip_formula_hash(manifest_payload)
                duplicate_count = _historical_render_duplicate_count(
                    uow,
                    product_id=recipe.product_id,
                    clip_formula_hash=clip_formula_hash,
                    exclude_recipe_id=recipe.id,
                )
                review_assessment = with_historical_render_duplicate(
                    review_assessment,
                    duplicate_count=duplicate_count,
                )
                manifest_payload["review_gate"] = review_gate_manifest_payload(review_assessment)
                if rendered_output.audio_mix_summary is not None:
                    manifest_payload["audio_mix"] = rendered_output.audio_mix_summary
                if rendered_output.visual_composite_summary is not None:
                    manifest_payload["visual_composite"] = rendered_output.visual_composite_summary
                manifest_payload = build_manifest_envelope(
                    product_code=product.product_code,
                    recipe_code=f"{recipe.recipe_code}_final",
                    stage_name="final",
                    target_platform=recipe.target_platform,
                    target_ratio=recipe.target_ratio,
                    output_path=rendered_output.file_path,
                    manifest_path=artifact_paths.manifest_path,
                    batch_code=batch_code,
                    run_root=artifact_paths.run_root,
                    journal_path=artifact_paths.journal_path,
                    order_snapshot_path=artifact_paths.order_snapshot_path,
                    product_local=artifact_paths.product_local,
                    payload=manifest_payload,
                )
                manifest_path = self._preview_manifest_builder.write_manifest(
                    product_code=product.product_code,
                    recipe_code=f"{recipe.recipe_code}_final",
                    payload=manifest_payload,
                    target_path=artifact_paths.manifest_path,
                )
                approved_at = _utc_now()
                output_approved = duplicate_count <= 0
                output = uow.outputs.add(
                    Output(
                        recipe_id=recipe.id,
                        output_code=build_artifact_job_code("final_output"),
                        file_path=str(rendered_output.file_path),
                        platform=recipe.target_platform,
                        ratio=recipe.target_ratio,
                        duration_sec=rendered_output.duration_sec,
                        quality_score=review_assessment.quality_score,
                        duplicate_risk=review_assessment.duplicate_risk,
                        approved=output_approved,
                        approved_by=self.SYSTEM_APPROVAL_ACTOR if output_approved else None,
                        approved_at=approved_at if output_approved else None,
                        approval_reason=self.SYSTEM_APPROVAL_REASON if output_approved else None,
                        clip_formula_hash=clip_formula_hash,
                        history_scope=resolve_output_history_scope(approved=output_approved, source_mode=source_mode),
                    )
                )
                if output.id is None:
                    raise RuntimeError("Final output identifier was not assigned.")
                if output_approved:
                    _record_decision_event(
                        uow,
                        recipe_id=recipe.id,
                        output_id=output.id,
                        event_type=self.OUTPUT_AUTO_APPROVED_EVENT,
                        actor=self.SYSTEM_APPROVAL_ACTOR,
                        reason=self.SYSTEM_APPROVAL_REASON,
                        created_at=approved_at,
                    )
                else:
                    apply_review_gate(
                        uow,
                        recipe=recipe,
                        assessment=review_assessment,
                        required_event=self.RECIPE_REVIEW_REQUIRED_EVENT,
                        cleared_event=self.RECIPE_REVIEW_CLEARED_EVENT,
                        actor=self.SYSTEM_REVIEW_ACTOR,
                        utc_now=_utc_now,
                        record_decision_event=_record_decision_event,
                    )
                score_and_persist_recipe(
                    uow,
                    recipe=recipe,
                    items=items,
                    assets=assets,
                    review_assessment=review_assessment,
                )
                job.status = JobStatus.DONE
                job.progress = 1.0
                finished_at = _utc_now()
                job.output_json = apply_job_success_metadata(
                    job.output_json,
                    succeeded_at=_format_timestamp(finished_at),
                    payload_updates={
                        "output_id": output.id,
                        "preview_manifest_path": str(manifest_path),
                        "source_output_id": source_output.output_id,
                        "final_output_path": str(rendered_output.file_path),
                    },
                )
                job.error_message = None
                job.finished_at = finished_at
                uow.jobs.update(job)
                uow.commit()
                _append_run_journal_event(
                    run_artifact_store=self._run_artifact_store,
                    product_code=product.product_code,
                    batch_code=batch_code,
                    event_type="final_rendered",
                    status="succeeded",
                    fields={
                        "recorded_at": format_utc_iso_timestamp(finished_at),
                        "recipe_code": recipe.recipe_code,
                        "output_path": str(rendered_output.file_path),
                        "manifest_path": str(manifest_path),
                    },
                )
            except Exception as exc:
                job.status = JobStatus.FAILED
                job.progress = 0.0
                job.error_message = str(exc)
                finished_at = _utc_now()
                job.finished_at = finished_at
                job.output_json = apply_job_failure_metadata(
                    job.output_json,
                    failed_at=_format_timestamp(finished_at),
                    error_message=str(exc),
                )
                uow.jobs.update(job)
                uow.commit()
                _append_run_journal_event(
                    run_artifact_store=self._run_artifact_store,
                    product_code=product.product_code,
                    batch_code=batch_code,
                    event_type="final_rendered",
                    status="failed",
                    fields={
                        "recorded_at": format_utc_iso_timestamp(finished_at),
                        "recipe_code": recipe.recipe_code,
                        "error_message": str(exc),
                    },
                )
                raise

    def list_preview_jobs(self, *, status: str | None = None) -> list[PreviewJobSummaryDTO]:
        return _list_job_summaries(unit_of_work_factory=self._unit_of_work_factory, job_type=self.PREVIEW_JOB_TYPE, status=status)

    def list_final_render_jobs(self, *, status: str | None = None) -> list[PreviewJobSummaryDTO]:
        return _list_job_summaries(unit_of_work_factory=self._unit_of_work_factory, job_type=self.FINAL_JOB_TYPE, status=status)

    def list_jobs(self, *, status: str | None = None) -> list[PreviewJobSummaryDTO]:
        jobs = [*self.list_preview_jobs(status=status), *self.list_final_render_jobs(status=status)]
        return sorted(jobs, key=lambda job: job.job_id, reverse=True)

    def retry_job(self, job_id: int) -> None:
        with self._unit_of_work_factory() as uow:
            job = uow.jobs.get_by_id(job_id)
            if job is None or job.id is None:
                raise FactoryJobNotFoundError(str(job_id))
            if job.job_type not in {self.PREVIEW_JOB_TYPE, self.FINAL_JOB_TYPE}:
                raise ValueError(f"Unsupported factory job type: {job.job_type}")
            job.status = JobStatus.QUEUED
            job.progress = 0.0
            job.error_message = None
            job.started_at = None
            job.finished_at = None
            job.output_json = prepare_job_output_for_retry(
                job.output_json,
                attempted_at=_format_timestamp(_utc_now()),
            )
            uow.jobs.update(job)
            uow.commit()

        if job.job_type == self.PREVIEW_JOB_TYPE:
            self.run_preview_job(job_id)
            return
        self.run_final_render_job(job_id)


def _historical_render_duplicate_count(
    uow: UnitOfWork,
    *,
    product_id: int,
    clip_formula_hash: str | None,
    exclude_recipe_id: int | None = None,
) -> int:
    if not clip_formula_hash:
        return 0
    history_outputs = uow.outputs.list_summaries(
        product_id=product_id,
        history_scopes=USABLE_OUTPUT_HISTORY_SCOPES,
    )
    return sum(
        1
        for summary in history_outputs
        if summary.clip_formula_hash == clip_formula_hash
        and (exclude_recipe_id is None or summary.recipe_id != exclude_recipe_id)
    )
