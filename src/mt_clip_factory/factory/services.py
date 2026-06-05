from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime

from mt_clip_factory.domain.enums import JobStatus
from mt_clip_factory.domain.jobs import Job
from mt_clip_factory.domain.recipes import Recipe
from mt_clip_factory.domain.services import UnitOfWork
from mt_clip_factory.factory.dto import (
    AssignAssetToRecipeCommand,
    CreateRecipeCommand,
    PreviewJobSummaryDTO,
    RecipeDetailsDTO,
    RecipeItemDTO,
    RecipeSummaryDTO,
)
from mt_clip_factory.factory.preview_artifacts import PreviewManifestBuilder
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


class VideoAssemblyFactoryService:
    PREVIEW_JOB_TYPE = "render_recipe_preview"

    def __init__(
        self,
        unit_of_work_factory: Callable[[], UnitOfWork],
        preview_manifest_builder: PreviewManifestBuilder,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._preview_manifest_builder = preview_manifest_builder

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

    def enqueue_preview_job(self, recipe_id: int) -> int:
        with self._unit_of_work_factory() as uow:
            recipe = uow.recipes.get_by_id(recipe_id)
            if recipe is None or recipe.id is None:
                raise RecipeNotFoundError(str(recipe_id))
            job = Job(
                job_code=build_artifact_job_code("preview"),
                job_type=self.PREVIEW_JOB_TYPE,
                recipe_id=recipe_id,
                status=JobStatus.QUEUED,
                input_json=encode_job_input({"recipe_id": recipe_id}),
            )
            created = uow.jobs.add(job)
            uow.commit()
            if created.id is None:
                raise RuntimeError("Preview job identifier was not assigned.")
            return created.id

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

            job.status = JobStatus.PROCESSING
            job.started_at = _utc_now()
            job.progress = 0.1
            uow.jobs.update(job)
            uow.commit()

            try:
                if not items:
                    raise PreviewBuildInputError(f"Recipe {recipe.recipe_code} has no items.")

                manifest_path = self._preview_manifest_builder.write_manifest(
                    product_code=product.product_code,
                    recipe_code=recipe.recipe_code,
                    payload={
                        "recipe_code": recipe.recipe_code,
                        "product_code": product.product_code,
                        "target_platform": recipe.target_platform,
                        "target_ratio": recipe.target_ratio,
                        "duration_sec": recipe.duration_sec,
                        "status": recipe.status.value,
                        "items": [
                            {
                                "asset_id": item.asset_id,
                                "asset_code": item.asset_code,
                                "asset_type": item.asset_type,
                                "role": item.role,
                            }
                            for item in items
                        ],
                    },
                )
                job.status = JobStatus.DONE
                job.progress = 1.0
                job.output_json = json.dumps({"preview_manifest_path": str(manifest_path)}, sort_keys=True)
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
        with self._unit_of_work_factory() as uow:
            jobs = uow.jobs.list_summaries(status=status, job_type=self.PREVIEW_JOB_TYPE)
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
                    status=summary.status.value,
                    progress=summary.progress,
                    output_path=_extract_output_path(output_map.get(summary.job_id)),
                    error_message=summary.error_message,
                )
                for summary in jobs
            ]


def _slugify_recipe_code(value: str) -> str:
    normalized = "".join(character if character.isalnum() else "_" for character in value.strip().lower())
    return normalized.strip("_")


def _extract_output_path(output_json: str | None) -> str | None:
    if not output_json:
        return None
    payload = json.loads(output_json)
    return payload.get("preview_manifest_path")


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
