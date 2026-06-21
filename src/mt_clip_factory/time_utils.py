from __future__ import annotations

from datetime import UTC, datetime, tzinfo


def resolve_local_display_timezone() -> tzinfo:
    return datetime.now().astimezone().tzinfo or UTC


def assume_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def to_local_display_datetime(value: datetime, *, local_tz: tzinfo | None = None) -> datetime:
    resolved_local_tz = local_tz or resolve_local_display_timezone()
    return assume_utc(value).astimezone(resolved_local_tz)


def format_local_display_timestamp(value: datetime, *, local_tz: tzinfo | None = None) -> str:
    return to_local_display_datetime(value, local_tz=local_tz).strftime("%Y-%m-%d %H:%M:%S")


def format_optional_local_display_timestamp(
    value: datetime | None,
    *,
    local_tz: tzinfo | None = None,
) -> str | None:
    if value is None:
        return None
    return format_local_display_timestamp(value, local_tz=local_tz)


def format_utc_iso_timestamp(value: datetime) -> str:
    return assume_utc(value).astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_local_timestamp_token(value: datetime | None = None, *, local_tz: tzinfo | None = None) -> str:
    if value is None:
        resolved_local_tz = local_tz or resolve_local_display_timezone()
        local_value = datetime.now(resolved_local_tz)
    else:
        local_value = to_local_display_datetime(value, local_tz=local_tz)
    return local_value.strftime("%Y%m%d_%H%M%S_%f")
