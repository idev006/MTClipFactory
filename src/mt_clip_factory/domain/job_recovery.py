from __future__ import annotations

from dataclasses import dataclass
import json

RECOVERY_KEY = "recovery"


@dataclass(slots=True, frozen=True)
class JobRecoveryMetadata:
    retry_count: int = 0
    consecutive_failure_count: int = 0
    last_retry_at: str | None = None
    last_failure_at: str | None = None
    last_success_at: str | None = None
    last_error_message: str | None = None


def decode_job_output_payload(output_json: str | None) -> dict[str, object]:
    if not output_json:
        return {}
    try:
        payload = json.loads(output_json)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def payload_without_recovery(output_json: str | None) -> dict[str, object]:
    payload = decode_job_output_payload(output_json)
    payload.pop(RECOVERY_KEY, None)
    return payload


def recovery_metadata_from_output_json(output_json: str | None) -> JobRecoveryMetadata:
    return recovery_metadata_from_payload(decode_job_output_payload(output_json))


def recovery_metadata_from_payload(payload: dict[str, object]) -> JobRecoveryMetadata:
    raw_recovery = payload.get(RECOVERY_KEY)
    if not isinstance(raw_recovery, dict):
        return JobRecoveryMetadata()
    return JobRecoveryMetadata(
        retry_count=_as_int(raw_recovery.get("retry_count")),
        consecutive_failure_count=_as_int(raw_recovery.get("consecutive_failure_count")),
        last_retry_at=_as_optional_str(raw_recovery.get("last_retry_at")),
        last_failure_at=_as_optional_str(raw_recovery.get("last_failure_at")),
        last_success_at=_as_optional_str(raw_recovery.get("last_success_at")),
        last_error_message=_as_optional_str(raw_recovery.get("last_error_message")),
    )


def prepare_job_output_for_retry(output_json: str | None, *, attempted_at: str) -> str:
    metadata = recovery_metadata_from_output_json(output_json)
    updated = JobRecoveryMetadata(
        retry_count=metadata.retry_count + 1,
        consecutive_failure_count=metadata.consecutive_failure_count,
        last_retry_at=attempted_at,
        last_failure_at=metadata.last_failure_at,
        last_success_at=metadata.last_success_at,
        last_error_message=metadata.last_error_message,
    )
    return encode_job_output_payload({}, recovery=updated)


def apply_job_failure_metadata(output_json: str | None, *, failed_at: str, error_message: str) -> str:
    metadata = recovery_metadata_from_output_json(output_json)
    updated = JobRecoveryMetadata(
        retry_count=metadata.retry_count,
        consecutive_failure_count=metadata.consecutive_failure_count + 1,
        last_retry_at=metadata.last_retry_at,
        last_failure_at=failed_at,
        last_success_at=metadata.last_success_at,
        last_error_message=error_message,
    )
    return encode_job_output_payload(payload_without_recovery(output_json), recovery=updated)


def apply_job_success_metadata(
    output_json: str | None,
    *,
    succeeded_at: str,
    payload_updates: dict[str, object] | None = None,
) -> str:
    metadata = recovery_metadata_from_output_json(output_json)
    updated = JobRecoveryMetadata(
        retry_count=metadata.retry_count,
        consecutive_failure_count=0,
        last_retry_at=metadata.last_retry_at,
        last_failure_at=metadata.last_failure_at,
        last_success_at=succeeded_at,
        last_error_message=None,
    )
    payload = payload_without_recovery(output_json)
    if payload_updates:
        payload.update(payload_updates)
    return encode_job_output_payload(payload, recovery=updated)


def encode_job_output_payload(
    payload: dict[str, object],
    *,
    recovery: JobRecoveryMetadata | None = None,
) -> str:
    normalized = dict(payload)
    if recovery is not None:
        normalized[RECOVERY_KEY] = {
            "retry_count": recovery.retry_count,
            "consecutive_failure_count": recovery.consecutive_failure_count,
            "last_retry_at": recovery.last_retry_at,
            "last_failure_at": recovery.last_failure_at,
            "last_success_at": recovery.last_success_at,
            "last_error_message": recovery.last_error_message,
        }
    return json.dumps(normalized, sort_keys=True)


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)
