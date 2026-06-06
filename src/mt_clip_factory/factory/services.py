from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from mt_clip_factory.domain.decision_events import DecisionEvent
from mt_clip_factory.domain.enums import JobStatus, RecipeStatus
from mt_clip_factory.domain.jobs import Job
from mt_clip_factory.domain.outputs import Output
from mt_clip_factory.domain.recipes import Recipe
from mt_clip_factory.domain.services import UnitOfWork
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
from mt_clip_factory.factory.preview_composition import build_segmented_preview_composition
from mt_clip_factory.factory.renderers import RenderedPreviewOutput
from mt_clip_factory.library.artifacts import build_artifact_job_code, decode_job_input, encode_job_input


class RecipeAlreadyExistsError(ValueError):
    """Raised when a recipe code already exists."""


class RecipeNotFoundError(ValueError):
    """Raised when a recipe does not exist."""


class RecipeAssetMismatchError(ValueError):
    """Raised when an asset belongs to a different product than the recipe."""


class AssetNotReadyForRecipeError(ValueError):
    """Raised when an asset is not ready to be used in a recipe."""


class RecipeItemAlreadyExistsError(ValueError):
    """Raised when the same asset role is already present in a recipe."""


class PreviewBuildInputError(ValueError):
    """Raised when a preview job cannot be built from current recipe state."""


class OutputNotFoundError(ValueError):
    """Raised when an output cannot be found."""


class RecipeApprovalError(ValueError):
    """Raised when a recipe approval decision is invalid."""


class FinalRenderPrerequisiteError(ValueError):
    """Raised when final render requirements are not satisfied."""


class FactoryJobNotFoundError(ValueError):
    """Raised when a factory job cannot be found."""


class VideoAssemblyFactoryService:
    PREVIEW_JOB_TYPE = "render_recipe_preview"
    FINAL_JOB_TYPE = "render_recipe_final"
    SYSTEM_APPROVAL_ACTOR = "system_final_render"
    SYSTEM_APPROVAL_REASON = "Auto-approved by final render pipeline."
    OUTPUT_APPROVED_EVENT = "output_approved"
    OUTPUT_AUTO_APPROVED_EVENT = "output_auto_approved"
    RECIPE_APPROVED_EVENT = "recipe_approved"
    RECIPE_REJECTED_EVENT = "recipe_rejected"

    def __init__(
        self,
        unit_of_work_factory: Callable[[], UnitOfWork],
        preview_manifest_builder: PreviewManifestBuilder,
        preview_renderer,
        final_renderer,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._preview_manifest_builder = preview_manifest_builder
        self._preview_renderer = preview_renderer
        self._final_renderer = final_renderer

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
            uow.commit()
            if item.id is None:
                raise RuntimeError("Recipe item identifier was not assigned.")
            return item.id

    def list_outputs(
        self,
        *,
        recipe_id: int | None = None,
        approved: bool | None = None,
    ) -> list[OutputSummaryDTO]:
        with self._unit_of_work_factory() as uow:
            requested_outputs = list(uow.outputs.list_summaries(recipe_id=recipe_id, approved=approved))
            lineage_context = _build_output_lineage_context(
                requested_outputs=requested_outputs,
                all_outputs=list(uow.outputs.list_summaries(recipe_id=recipe_id)),
                preview_jobs=[
                    job
                    for job in (
                        uow.jobs.get_by_id(summary.job_id)
                        for summary in uow.jobs.list_summaries(job_type=self.PREVIEW_JOB_TYPE)
                    )
                    if job is not None
                ],
                final_jobs=[
                    job
                    for job in (
                        uow.jobs.get_by_id(summary.job_id)
                        for summary in uow.jobs.list_summaries(job_type=self.FINAL_JOB_TYPE)
                    )
                    if job is not None
                ],
            )
            return [
                OutputSummaryDTO(
                    output_id=summary.output_id,
                    recipe_id=summary.recipe_id,
                    recipe_code=summary.recipe_code,
                    output_code=summary.output_code,
                    file_path=summary.file_path,
                    platform=summary.platform,
                    ratio=summary.ratio,
                    approved=summary.approved,
                    created_at=_format_timestamp(summary.created_at),
                    approved_by=summary.approved_by,
                    approved_at=_format_optional_timestamp(summary.approved_at),
                    approval_reason=summary.approval_reason,
                    output_kind=_resolve_output_kind(summary.output_code, lineage_context.get(summary.output_id)),
                    rendering_job_code=_lineage_value(summary.output_id, lineage_context, "job_code"),
                    manifest_path=_lineage_value(summary.output_id, lineage_context, "preview_manifest_path"),
                    source_output_id=_lineage_value(summary.output_id, lineage_context, "source_output_id"),
                    source_output_code=_lineage_value(summary.output_id, lineage_context, "source_output_code"),
                    source_output_path=_lineage_value(summary.output_id, lineage_context, "source_output_path"),
                )
                for summary in requested_outputs
            ]

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
            items = list(uow.recipes.list_items(recipe.id))
            assets = {
                item.asset_id: asset
                for item in items
                for asset in [uow.assets.get_by_id(item.asset_id)]
                if asset is not None
            }
            persisted = persist_composition(uow, recipe=recipe, items=items, assets=assets)
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
            approved_outputs = list(uow.outputs.list_summaries(recipe_id=recipe_id, approved=True))
            if not approved_outputs:
                raise RecipeApprovalError("Approve at least one output before approving the recipe.")
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

    def enqueue_preview_job(self, recipe_id: int) -> int:
        return self._enqueue_recipe_job(recipe_id=recipe_id, job_type=self.PREVIEW_JOB_TYPE, code_prefix="preview")

    def enqueue_final_render_job(self, recipe_id: int) -> int:
        with self._unit_of_work_factory() as uow:
            recipe = uow.recipes.get_by_id(recipe_id)
            if recipe is None or recipe.id is None:
                raise RecipeNotFoundError(str(recipe_id))
            if recipe.status != RecipeStatus.APPROVED:
                raise FinalRenderPrerequisiteError("Approve the recipe before starting final render.")
        return self._enqueue_recipe_job(recipe_id=recipe_id, job_type=self.FINAL_JOB_TYPE, code_prefix="final")

    def run_preview_job(self, job_id: int) -> None:
        with self._unit_of_work_factory() as uow:
            job = uow.jobs.get_by_id(job_id)
            if job is None or job.id is None:
                raise ValueError(str(job_id))
            if job.job_type != self.PREVIEW_JOB_TYPE:
                raise ValueError(f"Unsupported preview job type: {job.job_type}")

            payload = decode_job_input(job.input_json)
            recipe_id = int(payload.get("recipe_id") or job.recipe_id or 0)
            recipe = uow.recipes.get_by_id(recipe_id)
            if recipe is None or recipe.id is None:
                raise RecipeNotFoundError(str(recipe_id))
            product = uow.products.get_by_id(recipe.product_id)
            if product is None:
                raise ValueError(str(recipe.product_id))
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
                if not items:
                    raise PreviewBuildInputError(f"Recipe {recipe.recipe_code} has no items.")

                persisted = persist_composition(uow, recipe=recipe, items=items, assets=assets)
                composition = build_segmented_preview_composition(
                    recipe=recipe,
                    product_code=product.product_code,
                    items=items,
                    assets=assets,
                    plan=persisted.plan,
                    segments=persisted.segments,
                )
                manifest_path = self._preview_manifest_builder.write_manifest(
                    product_code=product.product_code,
                    recipe_code=recipe.recipe_code,
                    payload=composition.manifest_payload,
                )
                if not composition.source_files:
                    raise PreviewBuildInputError(f"Recipe {recipe.recipe_code} has no renderable video assets.")
                rendered_output = self._preview_renderer.render_output(
                    product_code=product.product_code,
                    output_stem=recipe.recipe_code,
                    source_files=list(composition.source_files),
                    segment_clips=composition.segment_clips,
                )
                output = uow.outputs.add(
                    Output(
                        recipe_id=recipe.id,
                        output_code=build_artifact_job_code("preview_output"),
                        file_path=str(rendered_output.file_path),
                        platform=recipe.target_platform,
                        ratio=recipe.target_ratio,
                        duration_sec=rendered_output.duration_sec,
                        approved=False,
                    )
                )
                job.status = JobStatus.DONE
                job.progress = 1.0
                job.output_json = json.dumps(
                    {
                        "output_id": output.id,
                        "preview_manifest_path": str(manifest_path),
                        "preview_output_path": str(rendered_output.file_path),
                    },
                    sort_keys=True,
                )
                job.error_message = None
                job.finished_at = _utc_now()
                uow.jobs.update(job)
                uow.commit()
            except Exception as exc:
                job.status = JobStatus.FAILED
                job.progress = 0.0
                job.error_message = str(exc)
                job.finished_at = _utc_now()
                uow.jobs.update(job)
                uow.commit()
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
            recipe = uow.recipes.get_by_id(recipe_id)
            if recipe is None or recipe.id is None:
                raise RecipeNotFoundError(str(recipe_id))
            if recipe.status != RecipeStatus.APPROVED:
                raise FinalRenderPrerequisiteError("Approve the recipe before starting final render.")
            product = uow.products.get_by_id(recipe.product_id)
            if product is None:
                raise ValueError(str(recipe.product_id))

            job.status = JobStatus.PROCESSING
            job.started_at = _utc_now()
            job.progress = 0.1
            uow.jobs.update(job)
            uow.commit()

            try:
                approved_outputs = list(uow.outputs.list_summaries(recipe_id=recipe.id, approved=True))
                if not approved_outputs:
                    raise FinalRenderPrerequisiteError("Approve at least one output before final render.")

                source_output = approved_outputs[0]
                rendered_output = self._final_renderer.render_output(
                    product_code=product.product_code,
                    output_stem=f"{recipe.recipe_code}_final",
                    source_files=[Path(source_output.file_path)],
                )
                approved_at = _utc_now()
                output = uow.outputs.add(
                    Output(
                        recipe_id=recipe.id,
                        output_code=build_artifact_job_code("final_output"),
                        file_path=str(rendered_output.file_path),
                        platform=recipe.target_platform,
                        ratio=recipe.target_ratio,
                        duration_sec=rendered_output.duration_sec,
                        approved=True,
                        approved_by=self.SYSTEM_APPROVAL_ACTOR,
                        approved_at=approved_at,
                        approval_reason=self.SYSTEM_APPROVAL_REASON,
                    )
                )
                if output.id is None:
                    raise RuntimeError("Final output identifier was not assigned.")
                _record_decision_event(
                    uow,
                    recipe_id=recipe.id,
                    output_id=output.id,
                    event_type=self.OUTPUT_AUTO_APPROVED_EVENT,
                    actor=self.SYSTEM_APPROVAL_ACTOR,
                    reason=self.SYSTEM_APPROVAL_REASON,
                    created_at=approved_at,
                )
                job.status = JobStatus.DONE
                job.progress = 1.0
                job.output_json = json.dumps(
                    {
                        "output_id": output.id,
                        "source_output_id": source_output.output_id,
                        "final_output_path": str(rendered_output.file_path),
                    },
                    sort_keys=True,
                )
                job.error_message = None
                job.finished_at = _utc_now()
                uow.jobs.update(job)
                uow.commit()
            except Exception as exc:
                job.status = JobStatus.FAILED
                job.progress = 0.0
                job.error_message = str(exc)
                job.finished_at = _utc_now()
                uow.jobs.update(job)
                uow.commit()
                raise

    def list_preview_jobs(self, *, status: str | None = None) -> list[PreviewJobSummaryDTO]:
        return self._list_jobs(job_type=self.PREVIEW_JOB_TYPE, status=status)

    def list_final_render_jobs(self, *, status: str | None = None) -> list[PreviewJobSummaryDTO]:
        return self._list_jobs(job_type=self.FINAL_JOB_TYPE, status=status)

    def list_jobs(self, *, status: str | None = None) -> list[PreviewJobSummaryDTO]:
        jobs = [
            *self.list_preview_jobs(status=status),
            *self.list_final_render_jobs(status=status),
        ]
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
            job.output_json = None
            uow.jobs.update(job)
            uow.commit()

        if job.job_type == self.PREVIEW_JOB_TYPE:
            self.run_preview_job(job_id)
            return
        self.run_final_render_job(job_id)

    def _list_jobs(self, *, job_type: str, status: str | None = None) -> list[PreviewJobSummaryDTO]:
        with self._unit_of_work_factory() as uow:
            jobs = uow.jobs.list_summaries(status=status, job_type=job_type)
            output_map = {
                job.id: job.output_json
                for job in (
                    uow.jobs.get_by_id(summary.job_id)
                    for summary in jobs
                )
                if job is not None and job.id is not None
            }
            return [
                PreviewJobSummaryDTO(
                    job_id=summary.job_id,
                    job_code=summary.job_code,
                    recipe_id=summary.recipe_id,
                    job_type=summary.job_type,
                    status=summary.status.value,
                    progress=summary.progress,
                    output_path=_extract_output_path(output_map.get(summary.job_id)),
                    error_message=summary.error_message,
                )
                for summary in jobs
            ]

    def _enqueue_recipe_job(self, *, recipe_id: int, job_type: str, code_prefix: str) -> int:
        with self._unit_of_work_factory() as uow:
            recipe = uow.recipes.get_by_id(recipe_id)
            if recipe is None or recipe.id is None:
                raise RecipeNotFoundError(str(recipe_id))
            job = Job(
                job_code=build_artifact_job_code(code_prefix),
                job_type=job_type,
                recipe_id=recipe_id,
                status=JobStatus.QUEUED,
                input_json=encode_job_input({"recipe_id": recipe_id}),
            )
            created = uow.jobs.add(job)
            uow.commit()
            if created.id is None:
                raise RuntimeError("Recipe job identifier was not assigned.")
            return created.id


def _slugify_recipe_code(value: str) -> str:
    normalized = "".join(character if character.isalnum() else "_" for character in value.strip().lower())
    return normalized.strip("_")


def _extract_output_path(output_json: str | None) -> str | None:
    if not output_json:
        return None
    payload = json.loads(output_json)
    return payload.get("final_output_path") or payload.get("preview_output_path") or payload.get("preview_manifest_path")


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _build_output_lineage_context(*, requested_outputs, all_outputs, preview_jobs, final_jobs) -> dict[int, dict[str, object | None]]:
    output_lookup = {summary.output_id: summary for summary in all_outputs}
    lineage: dict[int, dict[str, object | None]] = {}
    for job in [*preview_jobs, *final_jobs]:
        payload = _decode_output_payload(job.output_json)
        output_id = payload.get("output_id")
        if not isinstance(output_id, int):
            continue
        source_output_id = payload.get("source_output_id")
        source_summary = output_lookup.get(source_output_id) if isinstance(source_output_id, int) else None
        lineage[output_id] = {
            "job_code": job.job_code,
            "job_type": job.job_type,
            "preview_manifest_path": payload.get("preview_manifest_path"),
            "source_output_id": source_output_id if isinstance(source_output_id, int) else None,
            "source_output_code": source_summary.output_code if source_summary is not None else None,
            "source_output_path": source_summary.file_path if source_summary is not None else None,
        }
    for summary in requested_outputs:
        lineage.setdefault(summary.output_id, {})
    return lineage


def _decode_output_payload(output_json: str | None) -> dict[str, object]:
    if not output_json:
        return {}
    payload = json.loads(output_json)
    if isinstance(payload, dict):
        return payload
    return {}


def _resolve_output_kind(output_code: str, lineage: dict[str, object | None] | None) -> str:
    if lineage is not None and lineage.get("job_type") == VideoAssemblyFactoryService.FINAL_JOB_TYPE:
        return "final"
    if lineage is not None and lineage.get("job_type") == VideoAssemblyFactoryService.PREVIEW_JOB_TYPE:
        return "preview"
    if output_code.startswith("final_output"):
        return "final"
    return "preview"


def _lineage_value(output_id: int, lineage_context: dict[int, dict[str, object | None]], key: str):
    return lineage_context.get(output_id, {}).get(key)


def _format_timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _format_optional_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _format_timestamp(value)


def _normalize_actor(value: str) -> str:
    actor = value.strip()
    if not actor:
        raise ValueError("Decision actor is required.")
    return actor


def _normalize_reason(value: str | None) -> str | None:
    if value is None:
        return None
    reason = value.strip()
    return reason or None


def _record_decision_event(
    uow: UnitOfWork,
    *,
    recipe_id: int,
    event_type: str,
    actor: str,
    created_at: datetime,
    output_id: int | None = None,
    reason: str | None = None,
) -> None:
    uow.decision_events.add(
        DecisionEvent(
            recipe_id=recipe_id,
            output_id=output_id,
            event_type=event_type,
            actor=actor,
            reason=reason,
            created_at=created_at,
        )
    )
