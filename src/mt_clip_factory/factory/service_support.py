from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from mt_clip_factory.domain.decision_events import DecisionEvent
from mt_clip_factory.domain.job_recovery import decode_job_output_payload, recovery_metadata_from_output_json
from collections.abc import Callable

from mt_clip_factory.domain.services import UnitOfWork
from mt_clip_factory.factory.dto import OutputSummaryDTO, PreviewJobSummaryDTO
from mt_clip_factory.factory.output_lineage import build_output_lineage_context, lineage_value, resolve_output_kind
from mt_clip_factory.factory.product_run_store import ProductRunArtifactPaths, ProductRunArtifactStore


def resolve_artifact_paths(
    *,
    run_artifact_store: ProductRunArtifactStore | None,
    preview_renderer,
    final_renderer,
    preview_manifest_builder,
    product_code: str,
    batch_code: str | None,
    output_stem: str,
    stage_name: str,
) -> ProductRunArtifactPaths:
    fallback_video_root = getattr(
        preview_renderer if stage_name == "preview" else final_renderer,
        "_preview_root",
        Path("."),
    )
    fallback_manifest_root = getattr(preview_manifest_builder, "_preview_root", Path("."))
    if run_artifact_store is None:
        return ProductRunArtifactPaths(
            video_path=Path(fallback_video_root) / product_code / "videos" / f"{output_stem}.mp4",
            manifest_path=Path(fallback_manifest_root) / product_code / f"{output_stem}.json",
            run_root=None,
            journal_path=None,
            order_snapshot_path=None,
            product_local=False,
        )
    return run_artifact_store.resolve_render_artifact_paths(
        product_code=product_code,
        batch_code=batch_code,
        output_stem=output_stem,
        stage_name=stage_name,
        fallback_video_root=Path(fallback_video_root),
        fallback_manifest_root=Path(fallback_manifest_root),
    )


def append_run_journal_event(
    *,
    run_artifact_store: ProductRunArtifactStore | None,
    product_code: str,
    batch_code: str | None,
    event_type: str,
    status: str,
    fields: dict[str, object],
) -> None:
    if run_artifact_store is None or batch_code is None:
        return
    run_artifact_store.append_journal_event(
        product_code=product_code,
        batch_code=batch_code,
        event_type=event_type,
        status=status,
        fields=fields,
    )


def slugify_recipe_code(value: str) -> str:
    normalized = "".join(character if character.isalnum() else "_" for character in value.strip().lower())
    return normalized.strip("_")


def extract_output_path(output_json: str | None) -> str | None:
    payload = decode_job_output_payload(output_json)
    return payload.get("final_output_path") or payload.get("preview_output_path") or payload.get("preview_manifest_path")


def to_preview_job_summary(summary, *, output_json: str | None) -> PreviewJobSummaryDTO:
    recovery = recovery_metadata_from_output_json(output_json)
    return PreviewJobSummaryDTO(
        job_id=summary.job_id,
        job_code=summary.job_code,
        recipe_id=summary.recipe_id,
        job_type=summary.job_type,
        status=summary.status.value,
        progress=summary.progress,
        output_path=extract_output_path(output_json),
        error_message=summary.error_message,
        recovery_attempt_count=recovery.retry_count,
        consecutive_failure_count=recovery.consecutive_failure_count,
        last_recovery_attempt_at=recovery.last_retry_at,
        last_failure_at=recovery.last_failure_at,
    )


def list_job_summaries(
    *,
    unit_of_work_factory: Callable[[], UnitOfWork],
    job_type: str,
    status: str | None = None,
) -> list[PreviewJobSummaryDTO]:
    with unit_of_work_factory() as uow:
        jobs = uow.jobs.list_summaries(status=status, job_type=job_type)
        output_map = {
            job.id: job.output_json
            for job in (uow.jobs.get_by_id(summary.job_id) for summary in jobs)
            if job is not None and job.id is not None
        }
        return [
            to_preview_job_summary(summary=summary, output_json=output_map.get(summary.job_id))
            for summary in jobs
        ]


def list_output_summaries(
    *,
    unit_of_work_factory: Callable[[], UnitOfWork],
    recipe_id: int | None,
    approved: bool | None,
    preview_job_type: str,
    final_job_type: str,
    format_timestamp,
    format_optional_timestamp,
) -> list[OutputSummaryDTO]:
    with unit_of_work_factory() as uow:
        requested_outputs = list(uow.outputs.list_summaries(recipe_id=recipe_id, approved=approved))
        lineage_context = build_output_lineage_context(
            requested_outputs=requested_outputs,
            all_outputs=list(uow.outputs.list_summaries(recipe_id=recipe_id)),
            preview_jobs=[
                job
                for job in (
                    uow.jobs.get_by_id(summary.job_id)
                    for summary in uow.jobs.list_summaries(job_type=preview_job_type)
                )
                if job is not None
            ],
            final_jobs=[
                job
                for job in (
                    uow.jobs.get_by_id(summary.job_id)
                    for summary in uow.jobs.list_summaries(job_type=final_job_type)
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
                created_at=format_timestamp(summary.created_at),
                approved_by=summary.approved_by,
                approved_at=format_optional_timestamp(summary.approved_at),
                approval_reason=summary.approval_reason,
                output_kind=resolve_output_kind(summary.output_code, lineage_context.get(summary.output_id), preview_job_type=preview_job_type, final_job_type=final_job_type),
                rendering_job_code=lineage_value(summary.output_id, lineage_context, "job_code"),
                manifest_path=lineage_value(summary.output_id, lineage_context, "preview_manifest_path"),
                source_output_id=lineage_value(summary.output_id, lineage_context, "source_output_id"),
                source_output_code=lineage_value(summary.output_id, lineage_context, "source_output_code"),
                source_output_path=lineage_value(summary.output_id, lineage_context, "source_output_path"),
                quality_score=summary.quality_score,
                duplicate_risk=summary.duplicate_risk,
            )
            for summary in requested_outputs
        ]


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def format_timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def format_optional_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return format_timestamp(value)


def normalize_actor(value: str) -> str:
    actor = value.strip()
    if not actor:
        raise ValueError("Decision actor is required.")
    return actor


def normalize_reason(value: str | None) -> str | None:
    if value is None:
        return None
    reason = value.strip()
    return reason or None


def optional_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def record_decision_event(
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


def latest_event_timestamp(uow: UnitOfWork, *, recipe_id: int, event_type: str) -> datetime | None:
    for event in uow.decision_events.list_by_recipe(recipe_id):
        if event.event_type == event_type:
            return event.created_at
    return None
