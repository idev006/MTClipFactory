from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
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
from mt_clip_factory.factory.auto_factory_fingerprint import (
    build_history_recipe_fingerprint_hash,
    build_planned_recipe_fingerprint,
    build_planned_recipe_fingerprint_hash,
)
from mt_clip_factory.factory.auto_factory_preset_caption_planning import (
    build_caption_planning_signature_lookup,
    resolve_caption_planning_context,
)
from mt_clip_factory.factory.auto_factory_variant_support import (
    _build_persistent_foreground_sequences,
    _enumerate_variant_dimension_selections,
    _order_foreground_sequences_for_diversity_frontier,
    _order_role_assets_for_diversity_frontier,
    _resolve_candidate_scan_limit,
)
from mt_clip_factory.factory.asset_diversity import (
    build_asset_diversity_key,
    build_asset_summary_diversity_key,
    is_collapsed_diversity_key,
)
from mt_clip_factory.factory.caption_runtime import CaptionRuntimeService, ProductAutomationMetadataStore
from mt_clip_factory.factory.caption_selection_support import CaptionSelectionSignature
from mt_clip_factory.factory.creative_preset_runtime import (
    CreativePresetContractError,
    parse_creative_preset_contract_text,
)
from mt_clip_factory.factory.auto_factory_pool_support import (
    _filter_assets_by_required_tags,
    _foreground_sequence_from_recipe_items,
    _resolve_required_visual_shortfall_reason,
)
from mt_clip_factory.factory.auto_factory_planning_support import (
    _PlanningHistory,
    _SEMANTIC_VISUAL_ROLES,
    _VariantBlueprint,
    _select_blueprints_greedily,
)
from mt_clip_factory.factory.dto import (
    AssignAssetToRecipeCommand,
    CreateRecipeCommand,
    OutputSummaryDTO,
    PreviewJobSummaryDTO,
)
from mt_clip_factory.factory.manifest_envelope import read_manifest_section
from mt_clip_factory.factory.output_history import USABLE_OUTPUT_HISTORY_SCOPES
from mt_clip_factory.factory.services import VideoAssemblyFactoryService
from mt_clip_factory.factory.visual_selection import seeded_order
from mt_clip_factory.library.dto import AssetSummaryDTO
from mt_clip_factory.library.services import AssetIntakeService

_DEFAULT_FIXED_DURATION_SEC = 15.0
_HISTORY_RECIPE_LIMIT = 24


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
        caption_runtime_service: CaptionRuntimeService | None = None,
        automation_metadata_store: ProductAutomationMetadataStore | None = None,
    ) -> None:
        self._product_service = product_service
        self._asset_intake_service = asset_intake_service
        self._video_assembly_factory_service = video_assembly_factory_service
        self._caption_runtime_service = caption_runtime_service
        self._automation_metadata_store = automation_metadata_store

    def plan_batch(
        self,
        order: AutoFactoryBatchOrderDTO,
        *,
        history_excluded_recipe_ids: frozenset[int] = frozenset(),
    ) -> AutoFactoryBatchPlanDTO:
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
            planning = self._plan_product(
                batch_code=batch_code,
                product_request=product_request,
                product=product,
                history_excluded_recipe_ids=history_excluded_recipe_ids,
            )
            summaries.append(planning["summary"])
            planned_recipes.extend(planning["recipes"])

        return AutoFactoryBatchPlanDTO(
            batch_code=batch_code,
            summaries=tuple(summaries),
            planned_recipes=tuple(planned_recipes),
        )

    def materialize_batch(
        self,
        order: AutoFactoryBatchOrderDTO,
        *,
        history_excluded_recipe_ids: frozenset[int] = frozenset(),
    ) -> AutoFactoryBatchMaterializationDTO:
        plan = self.plan_batch(order, history_excluded_recipe_ids=history_excluded_recipe_ids)
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
            created_recipes.append(self.materialize_planned_recipe(planned_recipe))

        return AutoFactoryBatchMaterializationDTO(
            batch_code=plan.batch_code,
            created_recipes=tuple(created_recipes),
        )

    def materialize_planned_recipe(self, planned_recipe: PlannedBatchRecipeDTO) -> MaterializedBatchRecipeDTO:
        existing_recipe = self._video_assembly_factory_service.get_recipe_by_code(planned_recipe.recipe_code)
        if existing_recipe is not None:
            return MaterializedBatchRecipeDTO(
                recipe_id=existing_recipe.recipe_id,
                product_id=planned_recipe.product_id,
                product_code=planned_recipe.product_code,
                recipe_code=planned_recipe.recipe_code,
                assignment_count=len(existing_recipe.items),
            )

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
        return MaterializedBatchRecipeDTO(
            recipe_id=recipe_id,
            product_id=planned_recipe.product_id,
            product_code=planned_recipe.product_code,
            recipe_code=planned_recipe.recipe_code,
            assignment_count=len(planned_recipe.assignments),
        )

    def build_previews_for_materialized_batch(
        self,
        materialization: AutoFactoryBatchMaterializationDTO,
    ) -> AutoFactoryBatchPreviewProductionDTO:
        recipe_results: list[AutoFactoryPreviewRecipeResultDTO] = []
        for created_recipe in materialization.created_recipes:
            recipe_results.append(
                self.build_preview_for_materialized_recipe(
                    created_recipe,
                    batch_code=materialization.batch_code,
                    source_mode="auto_factory_folder",
                )
            )

        succeeded_recipe_count = sum(1 for result in recipe_results if result.job_status == "done")
        return AutoFactoryBatchPreviewProductionDTO(
            batch_code=materialization.batch_code,
            recipe_results=tuple(recipe_results),
            succeeded_recipe_count=succeeded_recipe_count,
            failed_recipe_count=len(recipe_results) - succeeded_recipe_count,
        )

    def build_preview_for_materialized_recipe(
        self,
        created_recipe: MaterializedBatchRecipeDTO,
        *,
        batch_code: str,
        source_mode: str = "auto_factory_folder",
    ) -> AutoFactoryPreviewRecipeResultDTO:
        preview_job_id = self._video_assembly_factory_service.enqueue_preview_job(
            created_recipe.recipe_id,
            batch_code=batch_code,
            source_mode=source_mode,
        )
        error_message: str | None = None
        try:
            self._video_assembly_factory_service.run_preview_job(preview_job_id)
        except Exception as exc:
            error_message = str(exc)

        job_summary = self._get_preview_job_summary(preview_job_id)
        recipe = self._video_assembly_factory_service.get_recipe(created_recipe.recipe_id)
        output = self._latest_output_for_recipe(created_recipe.recipe_id) if job_summary.status == "done" else None
        review_signal_codes = () if output is None else _load_review_signal_codes_from_manifest(output.manifest_path)
        return AutoFactoryPreviewRecipeResultDTO(
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
            clip_formula_hash=None if output is None else output.clip_formula_hash,
            history_scope=None if output is None else output.history_scope,
            duplicate_risk=None if output is None else output.duplicate_risk,
            review_signal_codes=review_signal_codes,
            error_message=job_summary.error_message or error_message,
        )

    def materialize_batch_and_build_previews(
        self,
        order: AutoFactoryBatchOrderDTO,
        *,
        history_excluded_recipe_ids: frozenset[int] = frozenset(),
    ) -> AutoFactoryBatchExecutionDTO:
        materialization = self.materialize_batch(order, history_excluded_recipe_ids=history_excluded_recipe_ids)
        preview_production = self.build_previews_for_materialized_batch(materialization)
        return AutoFactoryBatchExecutionDTO(
            batch_code=materialization.batch_code,
            materialization=materialization,
            preview_production=preview_production,
        )

    def _plan_product(
        self,
        *,
        batch_code: str,
        product_request: AutoFactoryProductRequestDTO,
        product,
        history_excluded_recipe_ids: frozenset[int],
    ) -> dict[str, object]:
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
        asset_diversity_keys = {
            asset.asset_id: diversity_key
            for asset in ready_assets
            for diversity_key in [build_asset_summary_diversity_key(asset)]
            if diversity_key is not None
        }
        planning_history = self._load_planning_history(
            product_id=product.product_id,
            product_code=product.product_code,
            asset_diversity_keys=asset_diversity_keys,
            excluded_recipe_ids=history_excluded_recipe_ids,
        )
        creative_preset_definitions = self._load_creative_preset_definitions(product.product_code)

        if not foreground_assets or not background_assets:
            limiting_reason = _resolve_required_visual_shortfall_reason(
                foreground_assets=foreground_assets,
                background_assets=background_assets,
                all_foreground_assets=all_foreground_assets,
                all_background_assets=all_background_assets,
                product_request=product_request,
            )
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

        foreground_sequences = _order_foreground_sequences_for_diversity_frontier(
            _build_persistent_foreground_sequences(
                tuple(asset.asset_id for asset in foreground_assets),
                role_count=len(_SEMANTIC_VISUAL_ROLES),
            ),
            planning_history=planning_history,
        )
        background_assets = _order_role_assets_for_diversity_frontier(
            background_assets,
            role_name="background",
            planning_history=planning_history,
        )
        voice_assets = _order_role_assets_for_diversity_frontier(
            voice_assets,
            role_name="voice",
            planning_history=planning_history,
        )
        music_assets = _order_role_assets_for_diversity_frontier(
            music_assets,
            role_name="music",
            planning_history=planning_history,
        )
        foreground_sequence_count = len(foreground_sequences) if foreground_sequences else 1
        background_count = len(background_assets) if background_assets else 1
        music_count = len(music_assets) if music_assets else 1
        voice_count = len(voice_assets) if voice_assets else 1
        feasible_count = foreground_sequence_count * background_count * music_count * voice_count
        planned_variants = self._select_planned_variants(
            batch_code=batch_code,
            product=product,
            product_request=product_request,
            planned_count=product_request.requested_output_count,
            feasible_count=feasible_count,
            foreground_assets=foreground_assets,
            foreground_sequences=foreground_sequences,
            background_assets=background_assets,
            music_assets=music_assets,
            voice_assets=voice_assets,
            planning_history=planning_history,
            creative_preset_definitions=creative_preset_definitions,
        )
        recipes: list[PlannedBatchRecipeDTO] = []
        for index, blueprint in enumerate(planned_variants):
            recipes.append(
                _blueprint_to_planned_recipe(
                    blueprint,
                    product_id=product.product_id,
                    product_code=product.product_code,
                    batch_code=batch_code,
                    request_index=index + 1,
                )
            )
        recipes = tuple(recipes)
        planned_count = len(recipes)
        can_fulfill_exactly = planned_count == product_request.requested_output_count
        fresh_feasible_count = planned_count if not can_fulfill_exactly else feasible_count
        summary = ProductBatchPlanSummaryDTO(
            product_id=product.product_id,
            product_code=product.product_code,
            requested_output_count=product_request.requested_output_count,
            planner_feasible_unique_count=fresh_feasible_count,
            planned_output_count=planned_count,
            can_fulfill_exactly=can_fulfill_exactly,
            shortfall_count=max(0, product_request.requested_output_count - planned_count),
            limiting_reason=(
                None
                if can_fulfill_exactly
                else _resolve_planner_shortfall_reason(planned_count=planned_count, feasible_count=feasible_count)
            ),
        )
        return {"summary": summary, "recipes": recipes}

    def _select_planned_variants(
        self,
        *,
        batch_code: str,
        product,
        product_request: AutoFactoryProductRequestDTO,
        planned_count: int,
        feasible_count: int,
        foreground_assets: tuple[AssetSummaryDTO, ...],
        foreground_sequences: tuple[tuple[int, ...], ...],
        background_assets: tuple[AssetSummaryDTO, ...],
        music_assets: tuple[AssetSummaryDTO, ...],
        voice_assets: tuple[AssetSummaryDTO, ...],
        planning_history: _PlanningHistory,
        creative_preset_definitions: tuple = (),
    ) -> tuple[_VariantBlueprint, ...]:
        if planned_count <= 0:
            return ()
        candidate_scan_limit = _resolve_candidate_scan_limit(planned_count=planned_count, feasible_count=feasible_count)
        sequence_options = foreground_sequences if foreground_sequences else ((),)
        background_options = background_assets if background_assets else (None,)
        music_options = music_assets if music_assets else (None,)
        voice_options = voice_assets if voice_assets else (None,)
        candidate_dimension_selections = _enumerate_variant_dimension_selections(
            limit=candidate_scan_limit,
            sequence_options=sequence_options,
            background_options=background_options,
            music_options=music_options,
            voice_options=voice_options,
        )
        caption_signature_lookup = build_caption_planning_signature_lookup(
            resolve_signatures_for_slots=self._resolve_caption_signatures_for_slots,
            product_code=product.product_code,
            batch_code=batch_code,
            planned_count=planned_count,
            creative_preset_definitions=creative_preset_definitions,
        )
        candidate_blueprints = tuple(
            self._build_variant_blueprint(
                variant_index=variant_index,
                product=product,
                product_request=product_request,
                foreground_assets=foreground_assets,
                selected_dimensions=selected_dimensions,
                caption_signatures_by_slot=caption_signature_lookup.default_signatures_by_slot,
                pool_profile_caption_signatures=caption_signature_lookup.pool_profile_signatures,
            )
            for variant_index, selected_dimensions in enumerate(candidate_dimension_selections)
        )
        return _select_blueprints_greedily(
            candidate_blueprints,
            planned_count=planned_count,
            planning_history=planning_history,
            planning_context_resolver=lambda blueprint, slot_position, selected_preset_counts, selected_preset_last_slots: (
                (
                    context := resolve_caption_planning_context(
                        blueprint=blueprint,
                        slot_position=slot_position,
                        planned_count=planned_count,
                        product_request=product_request,
                        creative_preset_definitions=creative_preset_definitions,
                        selected_preset_counts=selected_preset_counts,
                        selected_preset_last_slots=selected_preset_last_slots,
                        signature_lookup=caption_signature_lookup,
                    )
                ).slot_signature,
                context.creative_preset_code,
                context.creative_preset_signature,
                context.creative_preset_reasons,
            ),
        )

    def _build_variant_blueprint(
        self,
        *,
        variant_index: int,
        product,
        product_request: AutoFactoryProductRequestDTO,
        foreground_assets: tuple[AssetSummaryDTO, ...],
        selected_dimensions: dict[str, object],
        caption_signatures_by_slot: tuple[CaptionSelectionSignature | None, ...],
        pool_profile_caption_signatures: tuple[CaptionSelectionSignature | None, ...],
    ) -> _VariantBlueprint:
        sequence = tuple(selected_dimensions["foreground_sequence"])
        background_asset = selected_dimensions["background"]
        music_asset = selected_dimensions["music"]
        voice_asset = selected_dimensions["voice"]

        assignments: list[PlannedBatchAssetAssignmentDTO] = []
        if background_asset is not None:
            assignments.append(_to_assignment(background_asset, role="background"))
        if sequence:
            foreground_asset = _require_asset(foreground_assets, sequence[0])
            assignments.append(_to_assignment(foreground_asset, role="foreground"))
        if voice_asset is not None:
            assignments.append(_to_assignment(voice_asset, role="voice"))
        if music_asset is not None:
            assignments.append(_to_assignment(music_asset, role="music"))

        duration_source, duration_sec = _resolve_duration(product_request, voice_asset)
        target_platform = product_request.target_platform or product.default_platform
        fingerprint = build_planned_recipe_fingerprint(
            product_code=product.product_code,
            target_platform=target_platform,
            target_ratio=product_request.target_ratio,
            duration_source=duration_source,
            duration_sec=duration_sec,
            assignments=assignments,
        )
        fingerprint_hash = build_planned_recipe_fingerprint_hash(
            product_code=product.product_code,
            target_platform=target_platform,
            target_ratio=product_request.target_ratio,
            duration_sec=duration_sec,
            assignments=assignments,
        )
        return _VariantBlueprint(
            target_platform=target_platform,
            target_ratio=product_request.target_ratio,
            duration_sec=duration_sec,
            duration_source=duration_source,
            fingerprint=fingerprint,
            fingerprint_hash=fingerprint_hash,
            assignments=tuple(assignments),
            assignment_signature=_assignment_signature_from_assignments(tuple(assignments)),
            foreground_sequence=tuple(sequence),
            variant_index=variant_index,
            caption_signatures_by_slot=caption_signatures_by_slot,
            pool_profile_caption_signatures=pool_profile_caption_signatures,
        )

    def _load_planning_history(
        self,
        *,
        product_id: int,
        product_code: str,
        asset_diversity_keys: dict[int, str],
        excluded_recipe_ids: frozenset[int] = frozenset(),
    ) -> _PlanningHistory:
        output_summaries = self._video_assembly_factory_service.list_outputs(
            product_id=product_id,
            history_scopes=USABLE_OUTPUT_HISTORY_SCOPES,
        )
        recipe_ids_in_history_order: list[int] = []
        seen_recipe_ids: set[int] = set()
        for summary in output_summaries:
            if summary.recipe_id in excluded_recipe_ids or summary.recipe_id in seen_recipe_ids:
                continue
            seen_recipe_ids.add(summary.recipe_id)
            recipe_ids_in_history_order.append(summary.recipe_id)
        if not recipe_ids_in_history_order:
            return _PlanningHistory.empty()

        exact_signature_weights: Counter = Counter()
        exact_fingerprint_hashes: set[str] = set()
        foreground_sequence_weights: Counter = Counter()
        role_asset_weights: Counter = Counter()
        role_family_weights: Counter = Counter()
        for history_index, recipe_id in enumerate(recipe_ids_in_history_order):
            recipe_details = self._video_assembly_factory_service.get_recipe(recipe_id)
            exact_fingerprint_hashes.add(
                build_history_recipe_fingerprint_hash(
                    product_code=product_code,
                    target_platform=recipe_details.target_platform,
                    target_ratio=recipe_details.target_ratio,
                    duration_sec=recipe_details.duration_sec,
                    items=recipe_details.items,
                )
            )
            if history_index >= _HISTORY_RECIPE_LIMIT:
                continue
            history_weight = _history_weight(history_index)
            exact_signature = _assignment_signature_from_recipe_items(recipe_details.items)
            if exact_signature:
                exact_signature_weights[exact_signature] += history_weight
            foreground_sequence = _foreground_sequence_from_recipe_items(recipe_details.items)
            if foreground_sequence:
                foreground_sequence_weights[foreground_sequence] += history_weight
            for item in recipe_details.items:
                normalized_role = item.role.strip().lower()
                if not normalized_role:
                    continue
                role_asset_weights[(normalized_role, item.asset_id)] += history_weight
                diversity_key = asset_diversity_keys.get(item.asset_id)
                if is_collapsed_diversity_key(diversity_key):
                    role_family_weights[(normalized_role, diversity_key)] += history_weight
        return _PlanningHistory(
            exact_signature_weights=exact_signature_weights,
            exact_fingerprint_hashes=frozenset(exact_fingerprint_hashes),
            foreground_sequence_weights=foreground_sequence_weights,
            role_asset_weights=role_asset_weights,
            role_family_weights=role_family_weights,
        )

    def _get_preview_job_summary(self, job_id: int) -> PreviewJobSummaryDTO:
        for summary in self._video_assembly_factory_service.list_preview_jobs():
            if summary.job_id == job_id:
                return summary
        raise AutoFactoryPlanningError(f"Preview job {job_id} was not found after batch execution.")

    def _latest_output_for_recipe(self, recipe_id: int) -> OutputSummaryDTO | None:
        outputs = self._video_assembly_factory_service.list_outputs(recipe_id=recipe_id)
        return max(outputs, key=lambda item: item.output_id, default=None)

    def _resolve_caption_signatures_for_slots(
        self,
        *,
        product_code: str,
        batch_code: str,
        planned_count: int,
        creative_preset_code: str | None = None,
    ) -> tuple[CaptionSelectionSignature | None, ...]:
        if self._caption_runtime_service is None or planned_count <= 0:
            return ()
        return tuple(
            self._caption_runtime_service.resolve_caption_selection_signature(
                product_code=product_code,
                recipe_code=f"{product_code}_{batch_code}_{request_index:03d}",
                creative_preset_code=creative_preset_code,
            )
            for request_index in range(1, planned_count + 1)
        )

    def _load_creative_preset_definitions(self, product_code: str):
        if self._automation_metadata_store is None:
            return ()
        raw_text = self._automation_metadata_store.load_creative_preset_contract_text(product_code)
        if raw_text is None or not raw_text.strip():
            return ()
        try:
            return parse_creative_preset_contract_text(
                raw_text,
                source_name=str(self._automation_metadata_store.creative_preset_contract_path(product_code)),
            )
        except CreativePresetContractError as exc:
            raise AutoFactoryPlanningError(str(exc)) from exc


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return normalized.strip("_")


def _load_review_signal_codes_from_manifest(manifest_path: str | None) -> tuple[str, ...]:
    if not manifest_path:
        return ()
    manifest_file = Path(manifest_path)
    if not manifest_file.exists():
        return ()
    try:
        payload = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    if not isinstance(payload, dict):
        return ()
    review_gate = read_manifest_section(payload, section_name="quality", legacy_key="review_gate")
    if not isinstance(review_gate, dict):
        return ()
    signals = review_gate.get("signals")
    if not isinstance(signals, list):
        return ()
    return tuple(
        code.strip()
        for code in (signal.get("code") for signal in signals if isinstance(signal, dict))
        if isinstance(code, str) and code.strip()
    )

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
        tag_labels=asset.tag_labels,
        diversity_key=build_asset_diversity_key(
            role_name=role,
            asset_id=asset.asset_id,
            asset_code=asset.asset_code,
            tag_labels=asset.tag_labels,
            file_path=asset.file_path,
        ),
    )


def _blueprint_to_planned_recipe(
    blueprint: _VariantBlueprint,
    *,
    product_id: int,
    product_code: str,
    batch_code: str,
    request_index: int,
) -> PlannedBatchRecipeDTO:
    recipe_code = f"{product_code}_{batch_code}_{request_index:03d}"
    return PlannedBatchRecipeDTO(
        product_id=product_id,
        product_code=product_code,
        recipe_code=recipe_code,
        request_index=request_index,
        target_platform=blueprint.target_platform,
        target_ratio=blueprint.target_ratio,
        duration_sec=blueprint.duration_sec,
        duration_source=blueprint.duration_source,
        fingerprint=blueprint.fingerprint,
        fingerprint_hash=blueprint.fingerprint_hash,
        assignments=blueprint.assignments,
        near_duplicate_score=blueprint.near_duplicate_score,
        near_duplicate_reasons=blueprint.near_duplicate_reasons,
        caption_signature=blueprint.caption_signature,
        main_caption_signature=blueprint.main_caption_signature,
        creative_preset_code=blueprint.creative_preset_code,
        creative_preset_signature=blueprint.creative_preset_signature,
        creative_preset_reasons=blueprint.creative_preset_reasons,
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


def _assignment_signature_from_assignments(
    assignments: tuple[PlannedBatchAssetAssignmentDTO, ...],
) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((assignment.role, assignment.asset_id) for assignment in assignments))


def _assignment_signature_from_recipe_items(recipe_items) -> tuple[tuple[str, int], ...]:
    return tuple(
        sorted(
            (
                item.role.strip().lower(),
                item.asset_id,
            )
            for item in recipe_items
            if item.role.strip()
        )
    )


def _history_weight(history_index: int) -> float:
    if history_index < 3:
        return 4.0
    if history_index < 8:
        return 2.0
    return 1.0


def _resolve_planner_shortfall_reason(*, planned_count: int, feasible_count: int) -> str:
    if planned_count <= 0:
        return "exact fingerprint history exhausted fresh variants"
    if planned_count < feasible_count:
        return "exact fingerprint history reduced fresh variants"
    return "planner capacity exhausted"
