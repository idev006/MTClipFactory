from __future__ import annotations

from collections.abc import Callable

from mt_clip_factory.domain.enums import JobStatus, RecipeStatus
from mt_clip_factory.domain.job_recovery import prepare_job_output_for_retry
from mt_clip_factory.domain.recipes import Recipe
from mt_clip_factory.domain.services import UnitOfWork
from mt_clip_factory.factory.automation_policy import ProductAutomationPolicyService
from mt_clip_factory.factory.caption_runtime import CaptionRuntimeService
from mt_clip_factory.factory.composition_mapping import to_composition_plan_dto
from mt_clip_factory.factory.composition_runtime import persist_composition
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
from mt_clip_factory.factory.preview_artifacts import PreviewManifestBuilder
from mt_clip_factory.factory.product_run_store import ProductRunArtifactStore
from mt_clip_factory.factory.recipe_scoring import score_and_persist_recipe
from mt_clip_factory.factory.service_render_execution import (
    run_final_render_job as _run_final_render_job,
    run_preview_job as _run_preview_job,
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
    format_optional_timestamp as _format_optional_timestamp,
    format_timestamp as _format_timestamp,
    latest_event_timestamp as _latest_event_timestamp,
    list_output_summaries as _list_output_summaries,
    list_job_summaries as _list_job_summaries,
    load_recipe_items_and_assets as _load_recipe_items_and_assets,
    enqueue_recipe_job as _enqueue_recipe_job_helper,
    record_decision_event as _record_decision_event,
    normalize_actor as _normalize_actor,
    normalize_reason as _normalize_reason,
    slugify_recipe_code as _slugify_recipe_code,
    utc_now as _utc_now,
)


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
        _run_preview_job(self, job_id)

    def run_final_render_job(self, job_id: int) -> None:
        _run_final_render_job(self, job_id)

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
