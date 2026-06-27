from __future__ import annotations

from mt_clip_factory.domain.enums import JobStatus, RecipeStatus
from mt_clip_factory.domain.job_recovery import apply_job_failure_metadata, apply_job_success_metadata
from mt_clip_factory.domain.outputs import Output
from mt_clip_factory.factory.composition_runtime import persist_composition
from mt_clip_factory.factory.manifest_envelope import build_manifest_envelope
from mt_clip_factory.factory.output_history import (
    USABLE_OUTPUT_HISTORY_SCOPES,
    extract_clip_formula_hash,
    resolve_output_history_scope,
)
from mt_clip_factory.factory.preview_composition import build_segmented_preview_composition
from mt_clip_factory.factory.production_order_detail_support import stage_detail_value
from mt_clip_factory.factory.review_gate import (
    apply_review_gate,
    assess_review_gate,
    review_gate_manifest_payload,
    review_settings_from_provider,
    with_historical_render_duplicate,
)
from mt_clip_factory.factory.recipe_scoring import score_and_persist_recipe
from mt_clip_factory.factory.service_errors import FinalRenderPrerequisiteError, PreviewBuildInputError, RecipeNotFoundError
from mt_clip_factory.factory.service_support import (
    append_run_journal_event as _append_run_journal_event,
    format_optional_timestamp as _format_optional_timestamp,
    format_timestamp as _format_timestamp,
    load_recipe_items_and_assets as _load_recipe_items_and_assets,
    optional_text as _optional_text,
    record_decision_event as _record_decision_event,
    resolve_artifact_paths as _resolve_artifact_paths,
    resolve_caption_frame_size as _resolve_caption_frame_size,
    utc_now as _utc_now,
)
from mt_clip_factory.library.artifacts import build_artifact_job_code, decode_job_input
from mt_clip_factory.time_utils import format_utc_iso_timestamp


def run_preview_job(service, job_id: int) -> None:  # noqa: ANN001
    with service._unit_of_work_factory() as uow:
        job = uow.jobs.get_by_id(job_id)
        if job is None or job.id is None:
            raise ValueError(str(job_id))
        if job.job_type != service.PREVIEW_JOB_TYPE:
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
            if service._automation_policy_service is None
            else service._automation_policy_service.load_fill_policies(product.product_code)
        )
        artifact_paths = _resolve_artifact_paths(
            run_artifact_store=service._run_artifact_store,
            preview_renderer=service._preview_renderer,
            final_renderer=service._final_renderer,
            preview_manifest_builder=service._preview_manifest_builder,
            product_code=product.product_code,
            batch_code=batch_code,
            output_stem=recipe.recipe_code,
            stage_name="preview",
        )
        items, assets = _load_recipe_items_and_assets(uow, recipe_id=recipe.id)

        _mark_job_processing(uow, job)

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
            creative_preset_code = _materialize_creative_preset_code(uow, recipe_id=recipe.id)
            composition = build_segmented_preview_composition(
                recipe=recipe,
                product_code=product.product_code,
                items=items,
                assets=assets,
                plan=persisted.plan,
                segments=persisted.segments,
                caption_runtime_service=service._caption_runtime_service,
                automation_policy_service=service._automation_policy_service,
                creative_preset_code=creative_preset_code,
                caption_frame_size=_resolve_caption_frame_size(
                    system_settings_service=service._system_settings_service,
                    target_ratio=recipe.target_ratio,
                    output_resolution_field="preview_output_resolution",
                ),
            )
            if not composition.source_files:
                raise PreviewBuildInputError(f"Recipe {recipe.recipe_code} has no renderable video assets.")
            rendered_output = service._preview_renderer.render_output(
                product_code=product.product_code,
                output_stem=recipe.recipe_code,
                source_files=list(composition.source_files),
                segment_clips=composition.segment_clips,
                audio_mix_plan=composition.audio_mix_plan,
                target_ratio=recipe.target_ratio,
                target_path=artifact_paths.video_path,
                fill_policies=fill_policies,
            )
            review_assessment, manifest_payload, clip_formula_hash, _duplicate_count = _build_render_review_payload(
                service,
                uow,
                recipe=recipe,
                composition=composition,
                persisted_plan=persisted.plan,
                rendered_output=rendered_output,
                exclude_recipe_id=None,
            )
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
            manifest_path = service._preview_manifest_builder.write_manifest(
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
                required_event=service.RECIPE_REVIEW_REQUIRED_EVENT,
                cleared_event=service.RECIPE_REVIEW_CLEARED_EVENT,
                actor=service.SYSTEM_REVIEW_ACTOR,
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
            finished_at = _utc_now()
            job.status = JobStatus.DONE
            job.progress = 1.0
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
                run_artifact_store=service._run_artifact_store,
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
            _fail_render_job(
                service,
                uow,
                job=job,
                product_code=product.product_code,
                batch_code=batch_code,
                event_type="preview_rendered",
                recipe_code=recipe.recipe_code,
                exc=exc,
            )
            raise


def run_final_render_job(service, job_id: int) -> None:  # noqa: ANN001
    with service._unit_of_work_factory() as uow:
        job = uow.jobs.get_by_id(job_id)
        if job is None or job.id is None:
            raise ValueError(str(job_id))
        if job.job_type != service.FINAL_JOB_TYPE:
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
            if service._automation_policy_service is None
            else service._automation_policy_service.load_fill_policies(product.product_code)
        )
        artifact_paths = _resolve_artifact_paths(
            run_artifact_store=service._run_artifact_store,
            preview_renderer=service._preview_renderer,
            final_renderer=service._final_renderer,
            preview_manifest_builder=service._preview_manifest_builder,
            product_code=product.product_code,
            batch_code=batch_code,
            output_stem=f"{recipe.recipe_code}_final",
            stage_name="final",
        )
        items, assets = _load_recipe_items_and_assets(uow, recipe_id=recipe.id)

        _mark_job_processing(uow, job)

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
            creative_preset_code = _materialize_creative_preset_code(uow, recipe_id=recipe.id)
            composition = build_segmented_preview_composition(
                recipe=recipe,
                product_code=product.product_code,
                items=items,
                assets=assets,
                plan=persisted.plan,
                segments=persisted.segments,
                caption_runtime_service=service._caption_runtime_service,
                automation_policy_service=service._automation_policy_service,
                creative_preset_code=creative_preset_code,
                caption_frame_size=_resolve_caption_frame_size(
                    system_settings_service=service._system_settings_service,
                    target_ratio=recipe.target_ratio,
                    output_resolution_field="final_output_resolution",
                ),
            )
            if not composition.source_files:
                raise FinalRenderPrerequisiteError(f"Recipe {recipe.recipe_code} has no renderable video assets.")
            rendered_output = service._final_renderer.render_output(
                product_code=product.product_code,
                output_stem=f"{recipe.recipe_code}_final",
                source_files=list(composition.source_files),
                segment_clips=composition.segment_clips,
                audio_mix_plan=composition.audio_mix_plan,
                target_ratio=recipe.target_ratio,
                target_path=artifact_paths.video_path,
                fill_policies=fill_policies,
            )
            review_assessment, manifest_payload, clip_formula_hash, duplicate_count = _build_render_review_payload(
                service,
                uow,
                recipe=recipe,
                composition=composition,
                persisted_plan=persisted.plan,
                rendered_output=rendered_output,
                exclude_recipe_id=recipe.id,
            )
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
            manifest_path = service._preview_manifest_builder.write_manifest(
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
                    approved_by=service.SYSTEM_APPROVAL_ACTOR if output_approved else None,
                    approved_at=approved_at if output_approved else None,
                    approval_reason=service.SYSTEM_APPROVAL_REASON if output_approved else None,
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
                    event_type=service.OUTPUT_AUTO_APPROVED_EVENT,
                    actor=service.SYSTEM_APPROVAL_ACTOR,
                    reason=service.SYSTEM_APPROVAL_REASON,
                    created_at=approved_at,
                )
            else:
                apply_review_gate(
                    uow,
                    recipe=recipe,
                    assessment=review_assessment,
                    required_event=service.RECIPE_REVIEW_REQUIRED_EVENT,
                    cleared_event=service.RECIPE_REVIEW_CLEARED_EVENT,
                    actor=service.SYSTEM_REVIEW_ACTOR,
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
            finished_at = _utc_now()
            job.status = JobStatus.DONE
            job.progress = 1.0
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
                run_artifact_store=service._run_artifact_store,
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
            _fail_render_job(
                service,
                uow,
                job=job,
                product_code=product.product_code,
                batch_code=batch_code,
                event_type="final_rendered",
                recipe_code=recipe.recipe_code,
                exc=exc,
            )
            raise


def historical_render_duplicate_count(uow, *, product_id: int, clip_formula_hash: str | None, exclude_recipe_id: int | None = None) -> int:  # noqa: ANN001,E501
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


def _mark_job_processing(uow, job) -> None:  # noqa: ANN001
    job.status = JobStatus.PROCESSING
    job.started_at = _utc_now()
    job.progress = 0.1
    uow.jobs.update(job)
    uow.commit()


def _build_render_review_payload(service, uow, *, recipe, composition, persisted_plan, rendered_output, exclude_recipe_id):  # noqa: ANN001,E501
    review_assessment = assess_review_gate(
        plan=persisted_plan,
        composition=composition,
        settings=review_settings_from_provider(service._system_settings_service),
        audio_mix_summary=rendered_output.audio_mix_summary,
    )
    manifest_payload = dict(composition.manifest_payload)
    creative_preset_payload = _materialize_creative_preset_payload(uow, recipe_id=recipe.id)
    if creative_preset_payload is not None:
        manifest_payload["creative_preset"] = creative_preset_payload
    clip_formula_hash = extract_clip_formula_hash(manifest_payload)
    duplicate_count = historical_render_duplicate_count(
        uow,
        product_id=recipe.product_id,
        clip_formula_hash=clip_formula_hash,
        exclude_recipe_id=exclude_recipe_id,
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
    return review_assessment, manifest_payload, clip_formula_hash, duplicate_count


def _materialize_creative_preset_payload(uow, *, recipe_id: int) -> dict[str, object] | None:  # noqa: ANN001
    materialize_stages = uow.production_order_stages.list_by_recipe(recipe_id, stage_name="materialize")
    for stage in reversed(materialize_stages):
        if stage.status.value != "succeeded":
            continue
        preset_code = stage_detail_value(stage.detail_json, "creative_preset_code")
        preset_signature = stage_detail_value(stage.detail_json, "creative_preset_signature")
        preset_reasons = stage_detail_value(stage.detail_json, "creative_preset_reasons")
        reasons = [
            str(reason).strip()
            for reason in preset_reasons
            if isinstance(reason, str) and str(reason).strip()
        ] if isinstance(preset_reasons, list) else []
        if not isinstance(preset_code, str) or not preset_code.strip():
            continue
        return {
            "preset_code": preset_code.strip(),
            "preset_signature": None if not isinstance(preset_signature, str) or not preset_signature.strip() else preset_signature.strip(),
            "selection_reasons": reasons,
        }
    return None


def _materialize_creative_preset_code(uow, *, recipe_id: int) -> str | None:  # noqa: ANN001
    creative_preset_payload = _materialize_creative_preset_payload(uow, recipe_id=recipe_id)
    if creative_preset_payload is None:
        return None
    preset_code = creative_preset_payload.get("preset_code")
    if not isinstance(preset_code, str) or not preset_code.strip():
        return None
    return preset_code.strip()


def _fail_render_job(service, uow, *, job, product_code: str, batch_code: str | None, event_type: str, recipe_code: str, exc: Exception) -> None:  # noqa: ANN001,E501
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
        run_artifact_store=service._run_artifact_store,
        product_code=product_code,
        batch_code=batch_code,
        event_type=event_type,
        status="failed",
        fields={
            "recorded_at": format_utc_iso_timestamp(finished_at),
            "recipe_code": recipe_code,
            "error_message": str(exc),
        },
    )
