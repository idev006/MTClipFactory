from __future__ import annotations

import math
import re

from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.factory.auto_factory_dto import (
    AutoFactoryBatchExecutionDTO,
    AutoFactoryBatchMaterializationDTO,
    AutoFactoryBatchOrderDTO,
    AutoFactoryBatchPlanDTO,
    AutoFactoryBatchPreviewProductionDTO,
    AutoFactoryProductRequestDTO,
    AutoFactoryPreviewRecipeResultDTO,
    MaterializedBatchRecipeDTO,
    PlannedBatchAssetAssignmentDTO,
    PlannedBatchRecipeDTO,
    ProductBatchPlanSummaryDTO,
)
from mt_clip_factory.factory.dto import (
    AssignAssetToRecipeCommand,
    CreateRecipeCommand,
    OutputSummaryDTO,
    PreviewJobSummaryDTO,
)
from mt_clip_factory.factory.services import VideoAssemblyFactoryService
from mt_clip_factory.factory.visual_selection import seeded_order
from mt_clip_factory.library.dto import AssetSummaryDTO
from mt_clip_factory.library.services import AssetIntakeService

_DEFAULT_FIXED_DURATION_SEC = 15.0
_SEMANTIC_VISUAL_ROLES = ("hook", "problem", "benefit", "proof", "cta")
_DIVERSITY_DIMENSION_PRIORITY = (
    "voice",
    "foreground_sequence",
    "background",
    "music",
)


class AutoFactoryPlanningError(ValueError):
    """Raised when a production order cannot be planned truthfully."""


class AutoFactoryUnknownProductError(AutoFactoryPlanningError):
    """Raised when a product code in the order does not exist."""


class AutoFactoryCapacityError(AutoFactoryPlanningError):
    """Raised when the planner cannot fulfill an order exactly."""


class AutoFactoryBatchService:
    def __init__(
        self,
        *,
        product_service: ProductApplicationService,
        asset_intake_service: AssetIntakeService,
        video_assembly_factory_service: VideoAssemblyFactoryService,
    ) -> None:
        self._product_service = product_service
        self._asset_intake_service = asset_intake_service
        self._video_assembly_factory_service = video_assembly_factory_service

    def plan_batch(self, order: AutoFactoryBatchOrderDTO) -> AutoFactoryBatchPlanDTO:
        batch_code = _slugify(order.batch_code)
        if not batch_code:
            raise AutoFactoryPlanningError("Batch code is required.")
        if not order.product_requests:
            raise AutoFactoryPlanningError("At least one product request is required.")

        products_by_code = {product.product_code: product for product in self._product_service.list_products()}
        summaries: list[ProductBatchPlanSummaryDTO] = []
        planned_recipes: list[PlannedBatchRecipeDTO] = []

        for product_request in order.product_requests:
            product = products_by_code.get(product_request.product_code)
            if product is None:
                raise AutoFactoryUnknownProductError(product_request.product_code)
            planning = self._plan_product(batch_code=batch_code, product_request=product_request, product=product)
            summaries.append(planning["summary"])
            planned_recipes.extend(planning["recipes"])

        return AutoFactoryBatchPlanDTO(
            batch_code=batch_code,
            summaries=tuple(summaries),
            planned_recipes=tuple(planned_recipes),
        )

    def materialize_batch(self, order: AutoFactoryBatchOrderDTO) -> AutoFactoryBatchMaterializationDTO:
        plan = self.plan_batch(order)
        if order.strict_fulfillment:
            shortfalls = [summary for summary in plan.summaries if not summary.can_fulfill_exactly]
            if shortfalls:
                details = ", ".join(
                    f"{summary.product_code}: requested={summary.requested_output_count}, feasible={summary.planner_feasible_unique_count}"
                    for summary in shortfalls
                )
                raise AutoFactoryCapacityError(f"Batch cannot be fulfilled exactly under current planner policy: {details}")

        created_recipes: list[MaterializedBatchRecipeDTO] = []
        for planned_recipe in plan.planned_recipes:
            recipe_id = self._video_assembly_factory_service.create_recipe(
                CreateRecipeCommand(
                    product_id=planned_recipe.product_id,
                    recipe_code=planned_recipe.recipe_code,
                    target_platform=planned_recipe.target_platform,
                    target_ratio=planned_recipe.target_ratio,
                    duration_sec=planned_recipe.duration_sec,
                )
            )
            for assignment in planned_recipe.assignments:
                self._video_assembly_factory_service.assign_asset_to_recipe(
                    AssignAssetToRecipeCommand(
                        recipe_id=recipe_id,
                        asset_id=assignment.asset_id,
                        role=assignment.role,
                    )
                )
            created_recipes.append(
                MaterializedBatchRecipeDTO(
                    recipe_id=recipe_id,
                    product_id=planned_recipe.product_id,
                    product_code=planned_recipe.product_code,
                    recipe_code=planned_recipe.recipe_code,
                    assignment_count=len(planned_recipe.assignments),
                )
            )

        return AutoFactoryBatchMaterializationDTO(
            batch_code=plan.batch_code,
            created_recipes=tuple(created_recipes),
        )

    def build_previews_for_materialized_batch(
        self,
        materialization: AutoFactoryBatchMaterializationDTO,
    ) -> AutoFactoryBatchPreviewProductionDTO:
        recipe_results: list[AutoFactoryPreviewRecipeResultDTO] = []
        for created_recipe in materialization.created_recipes:
            preview_job_id = self._video_assembly_factory_service.enqueue_preview_job(
                created_recipe.recipe_id,
                batch_code=materialization.batch_code,
                source_mode="auto_factory_folder",
            )
            error_message: str | None = None
            try:
                self._video_assembly_factory_service.run_preview_job(preview_job_id)
            except Exception as exc:
                error_message = str(exc)

            job_summary = self._get_preview_job_summary(preview_job_id)
            recipe = self._video_assembly_factory_service.get_recipe(created_recipe.recipe_id)
            output = self._latest_output_for_recipe(created_recipe.recipe_id) if job_summary.status == "done" else None
            recipe_results.append(
                AutoFactoryPreviewRecipeResultDTO(
                    recipe_id=created_recipe.recipe_id,
                    product_id=created_recipe.product_id,
                    product_code=created_recipe.product_code,
                    recipe_code=created_recipe.recipe_code,
                    preview_job_id=preview_job_id,
                    job_status=job_summary.status,
                    recipe_status=recipe.status,
                    review_required=recipe.status == "needs_review",
                    output_id=None if output is None else output.output_id,
                    output_code=None if output is None else output.output_code,
                    output_path=job_summary.output_path,
                    error_message=job_summary.error_message or error_message,
                )
            )

        succeeded_recipe_count = sum(1 for result in recipe_results if result.job_status == "done")
        return AutoFactoryBatchPreviewProductionDTO(
            batch_code=materialization.batch_code,
            recipe_results=tuple(recipe_results),
            succeeded_recipe_count=succeeded_recipe_count,
            failed_recipe_count=len(recipe_results) - succeeded_recipe_count,
        )

    def materialize_batch_and_build_previews(self, order: AutoFactoryBatchOrderDTO) -> AutoFactoryBatchExecutionDTO:
        materialization = self.materialize_batch(order)
        preview_production = self.build_previews_for_materialized_batch(materialization)
        return AutoFactoryBatchExecutionDTO(
            batch_code=materialization.batch_code,
            materialization=materialization,
            preview_production=preview_production,
        )

    def _plan_product(self, *, batch_code: str, product_request: AutoFactoryProductRequestDTO, product) -> dict[str, object]:
        if product_request.requested_output_count <= 0:
            raise AutoFactoryPlanningError("Requested output count must be greater than zero.")
        if product_request.uniqueness_scope != "batch":
            raise AutoFactoryPlanningError(
                f"Unsupported uniqueness scope: {product_request.uniqueness_scope}. Only 'batch' is currently supported."
            )

        ready_assets = self._asset_intake_service.list_assets(product_id=product.product_id, status="ready")
        all_foreground_assets = tuple(asset for asset in ready_assets if asset.asset_type == "foreground_video")
        all_background_assets = tuple(asset for asset in ready_assets if asset.asset_type == "background_video")
        all_voice_assets = tuple(asset for asset in ready_assets if asset.asset_type == "voiceover")
        all_music_assets = tuple(asset for asset in ready_assets if asset.asset_type == "background_music")
        foreground_assets = _filter_assets_by_required_tags(
            all_foreground_assets,
            product_request.foreground_required_tag_labels,
        )
        background_assets = _filter_assets_by_required_tags(
            all_background_assets,
            product_request.background_required_tag_labels,
        )
        voice_assets = _filter_assets_by_required_tags(
            all_voice_assets,
            product_request.voice_required_tag_labels,
        )
        music_assets = _filter_assets_by_required_tags(
            all_music_assets,
            product_request.music_required_tag_labels,
        )
        foreground_assets = seeded_order(
            foreground_assets,
            seed_key=f"{batch_code}|{product.product_code}|foreground",
            item_key=lambda asset: asset.asset_code or str(asset.asset_id),
        )
        background_assets = seeded_order(
            background_assets,
            seed_key=f"{batch_code}|{product.product_code}|background",
            item_key=lambda asset: asset.asset_code or str(asset.asset_id),
        )
        voice_assets = seeded_order(
            voice_assets,
            seed_key=f"{batch_code}|{product.product_code}|voice",
            item_key=lambda asset: asset.asset_code or str(asset.asset_id),
        )
        music_assets = seeded_order(
            music_assets,
            seed_key=f"{batch_code}|{product.product_code}|music",
            item_key=lambda asset: asset.asset_code or str(asset.asset_id),
        )

        if not foreground_assets and not background_assets:
            limiting_reason = "no ready renderable visual assets"
            if (all_foreground_assets or all_background_assets) and _has_any_required_tag_filters(product_request):
                limiting_reason = "no ready renderable visual assets matched required tag filters"
            summary = ProductBatchPlanSummaryDTO(
                product_id=product.product_id,
                product_code=product.product_code,
                requested_output_count=product_request.requested_output_count,
                planner_feasible_unique_count=0,
                planned_output_count=0,
                can_fulfill_exactly=False,
                shortfall_count=product_request.requested_output_count,
                limiting_reason=limiting_reason,
            )
            return {"summary": summary, "recipes": ()}

        foreground_sequences = _build_foreground_sequences(
            tuple(asset.asset_id for asset in foreground_assets),
            role_count=len(_SEMANTIC_VISUAL_ROLES),
        )
        foreground_sequence_count = len(foreground_sequences) if foreground_sequences else 1
        background_count = len(background_assets) if background_assets else 1
        music_count = len(music_assets) if music_assets else 1
        voice_count = len(voice_assets) if voice_assets else 1
        feasible_count = foreground_sequence_count * background_count * music_count * voice_count
        planned_count = min(product_request.requested_output_count, feasible_count)

        recipes = tuple(
            self._build_planned_recipe(
                batch_code=batch_code,
                product_request=product_request,
                product=product,
                request_index=index + 1,
                foreground_assets=foreground_assets,
                foreground_sequences=foreground_sequences,
                background_assets=background_assets,
                music_assets=music_assets,
                voice_assets=voice_assets,
            )
            for index in range(planned_count)
        )
        summary = ProductBatchPlanSummaryDTO(
            product_id=product.product_id,
            product_code=product.product_code,
            requested_output_count=product_request.requested_output_count,
            planner_feasible_unique_count=feasible_count,
            planned_output_count=planned_count,
            can_fulfill_exactly=planned_count == product_request.requested_output_count,
            shortfall_count=max(0, product_request.requested_output_count - planned_count),
            limiting_reason=None if planned_count == product_request.requested_output_count else "planner capacity exhausted",
        )
        return {"summary": summary, "recipes": recipes}

    def _build_planned_recipe(
        self,
        *,
        batch_code: str,
        product_request: AutoFactoryProductRequestDTO,
        product,
        request_index: int,
        foreground_assets: tuple[AssetSummaryDTO, ...],
        foreground_sequences: tuple[tuple[int, ...], ...],
        background_assets: tuple[AssetSummaryDTO, ...],
        music_assets: tuple[AssetSummaryDTO, ...],
        voice_assets: tuple[AssetSummaryDTO, ...],
    ) -> PlannedBatchRecipeDTO:
        sequence_options = foreground_sequences if foreground_sequences else ((),)
        background_options = background_assets if background_assets else (None,)
        music_options = music_assets if music_assets else (None,)
        voice_options = voice_assets if voice_assets else (None,)
        selected_dimensions = _select_variant_dimensions(
            variant_index=request_index - 1,
            sequence_options=sequence_options,
            background_options=background_options,
            music_options=music_options,
            voice_options=voice_options,
        )
        sequence = selected_dimensions["foreground_sequence"]
        background_asset = selected_dimensions["background"]
        music_asset = selected_dimensions["music"]
        voice_asset = selected_dimensions["voice"]

        assignments: list[PlannedBatchAssetAssignmentDTO] = []
        if background_asset is not None:
            assignments.append(_to_assignment(background_asset, role="background"))
        for role, asset_id in zip(_SEMANTIC_VISUAL_ROLES, sequence, strict=False):
            foreground_asset = _require_asset(foreground_assets, asset_id)
            assignments.append(_to_assignment(foreground_asset, role=role))
        if voice_asset is not None:
            assignments.append(_to_assignment(voice_asset, role="voice"))
        if music_asset is not None:
            assignments.append(_to_assignment(music_asset, role="music"))

        duration_source, duration_sec = _resolve_duration(product_request, voice_asset)
        target_platform = product_request.target_platform or product.default_platform
        fingerprint = _build_fingerprint(
            product_code=product.product_code,
            target_platform=target_platform,
            target_ratio=product_request.target_ratio,
            duration_source=duration_source,
            duration_sec=duration_sec,
            assignments=assignments,
        )
        recipe_code = f"{product.product_code}_{batch_code}_{request_index:03d}"
        return PlannedBatchRecipeDTO(
            product_id=product.product_id,
            product_code=product.product_code,
            recipe_code=recipe_code,
            request_index=request_index,
            target_platform=target_platform,
            target_ratio=product_request.target_ratio,
            duration_sec=duration_sec,
            duration_source=duration_source,
            fingerprint=fingerprint,
            assignments=tuple(assignments),
        )

    def _get_preview_job_summary(self, job_id: int) -> PreviewJobSummaryDTO:
        for summary in self._video_assembly_factory_service.list_preview_jobs():
            if summary.job_id == job_id:
                return summary
        raise AutoFactoryPlanningError(f"Preview job {job_id} was not found after batch execution.")

    def _latest_output_for_recipe(self, recipe_id: int) -> OutputSummaryDTO | None:
        outputs = self._video_assembly_factory_service.list_outputs(recipe_id=recipe_id)
        return max(outputs, key=lambda item: item.output_id, default=None)


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return normalized.strip("_")


def _select_variant_dimensions(
    *,
    variant_index: int,
    sequence_options: tuple[tuple[int, ...], ...],
    background_options: tuple[AssetSummaryDTO | None, ...],
    music_options: tuple[AssetSummaryDTO | None, ...],
    voice_options: tuple[AssetSummaryDTO | None, ...],
) -> dict[str, object]:
    dimension_options: dict[str, tuple[object, ...]] = {
        "foreground_sequence": sequence_options,
        "background": background_options,
        "music": music_options,
        "voice": voice_options,
    }
    remaining_index = variant_index
    selected: dict[str, object] = {}
    for dimension_name in _DIVERSITY_DIMENSION_PRIORITY:
        options = dimension_options[dimension_name]
        selected[dimension_name] = options[remaining_index % len(options)]
        remaining_index //= len(options)
    return selected


def _build_foreground_sequences(asset_ids: tuple[int, ...], *, role_count: int) -> tuple[tuple[int, ...], ...]:
    if not asset_ids:
        return ()
    sequences: dict[tuple[int, ...], None] = {}
    total_assets = len(asset_ids)
    for step in range(1, total_assets + 1):
        if math.gcd(step, total_assets) != 1:
            continue
        for start in range(total_assets):
            sequence = tuple(asset_ids[(start + (step * offset)) % total_assets] for offset in range(role_count))
            sequences.setdefault(sequence, None)
    return tuple(sequences)


def _require_asset(assets: tuple[AssetSummaryDTO, ...], asset_id: int) -> AssetSummaryDTO:
    for asset in assets:
        if asset.asset_id == asset_id:
            return asset
    raise AutoFactoryPlanningError(f"Asset id {asset_id} was not found in the current planner pool.")


def _to_assignment(asset: AssetSummaryDTO, *, role: str) -> PlannedBatchAssetAssignmentDTO:
    return PlannedBatchAssetAssignmentDTO(
        asset_id=asset.asset_id,
        asset_code=asset.asset_code,
        asset_type=asset.asset_type,
        role=role,
    )


def _resolve_duration(
    product_request: AutoFactoryProductRequestDTO,
    voice_asset: AssetSummaryDTO | None,
) -> tuple[str, float | None]:
    if product_request.duration_mode == "fixed_duration":
        if product_request.fixed_duration_sec is None or product_request.fixed_duration_sec <= 0:
            raise AutoFactoryPlanningError("Fixed duration mode requires a positive fixed_duration_sec value.")
        return "fixed_duration", float(product_request.fixed_duration_sec)

    if product_request.duration_mode != "voice_with_bounds":
        raise AutoFactoryPlanningError(
            f"Unsupported duration mode: {product_request.duration_mode}. Only 'voice_with_bounds' and 'fixed_duration' are supported."
        )

    if voice_asset is None or voice_asset.duration_sec is None:
        fallback_duration = product_request.fixed_duration_sec or _DEFAULT_FIXED_DURATION_SEC
        return "fixed_fallback", float(fallback_duration)

    resolved = max(product_request.min_duration_sec, min(product_request.max_duration_sec, voice_asset.duration_sec))
    return "voice_with_bounds", round(float(resolved), 3)


def _build_fingerprint(
    *,
    product_code: str,
    target_platform: str | None,
    target_ratio: str | None,
    duration_source: str,
    duration_sec: float | None,
    assignments: list[PlannedBatchAssetAssignmentDTO],
) -> str:
    grouped_assignments = [
        f"{assignment.role}:{assignment.asset_id}"
        for assignment in sorted(assignments, key=lambda item: (item.role, item.asset_id, item.asset_code))
    ]
    fingerprint_parts = (
        product_code,
        target_platform or "",
        target_ratio or "",
        duration_source,
        "" if duration_sec is None else f"{duration_sec:.3f}",
        *grouped_assignments,
    )
    return "|".join(fingerprint_parts)


def _filter_assets_by_required_tags(
    assets: tuple[AssetSummaryDTO, ...],
    required_tag_labels: tuple[str, ...],
) -> tuple[AssetSummaryDTO, ...]:
    if not required_tag_labels:
        return assets
    required = {label.strip().casefold() for label in required_tag_labels if label.strip()}
    if not required:
        return assets
    filtered_assets: list[AssetSummaryDTO] = []
    for asset in assets:
        asset_tags = {label.strip().casefold() for label in asset.tag_labels if label.strip()}
        if required.issubset(asset_tags):
            filtered_assets.append(asset)
    return tuple(filtered_assets)


def _has_any_required_tag_filters(product_request: AutoFactoryProductRequestDTO) -> bool:
    return any(
        (
            product_request.foreground_required_tag_labels,
            product_request.background_required_tag_labels,
            product_request.music_required_tag_labels,
            product_request.voice_required_tag_labels,
        )
    )
