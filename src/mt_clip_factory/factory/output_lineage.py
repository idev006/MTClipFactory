from __future__ import annotations

from mt_clip_factory.domain.job_recovery import decode_job_output_payload


def build_output_lineage_context(*, requested_outputs, all_outputs, preview_jobs, final_jobs) -> dict[int, dict[str, object | None]]:
    output_lookup = {summary.output_id: summary for summary in all_outputs}
    lineage: dict[int, dict[str, object | None]] = {}
    for job in [*preview_jobs, *final_jobs]:
        payload = decode_output_payload(job.output_json)
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


def decode_output_payload(output_json: str | None) -> dict[str, object]:
    return decode_job_output_payload(output_json)


def resolve_output_kind(output_code: str, lineage: dict[str, object | None] | None, *, preview_job_type: str, final_job_type: str) -> str:
    if lineage is not None and lineage.get("job_type") == final_job_type:
        return "final"
    if lineage is not None and lineage.get("job_type") == preview_job_type:
        return "preview"
    if output_code.startswith("final_output"):
        return "final"
    return "preview"


def lineage_value(output_id: int, lineage_context: dict[int, dict[str, object | None]], key: str):
    return lineage_context.get(output_id, {}).get(key)
