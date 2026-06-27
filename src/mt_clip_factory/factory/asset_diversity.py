from __future__ import annotations

from functools import lru_cache
import hashlib
from pathlib import Path

from mt_clip_factory.library.dto import AssetSummaryDTO

_ASSET_TYPE_TO_ROLE = {
    "foreground_video": "foreground",
    "background_video": "background",
    "background_music": "music",
    "voiceover": "voice",
}
_ROLE_FAMILY_TAG_GROUPS = {
    "foreground": ("duplicate_family", "presenter", "presenter_family", "visual_family", "family"),
    "background": ("duplicate_family", "scene", "scene_family", "visual_family", "family"),
    "music": ("duplicate_family", "track_family", "music_family", "family"),
    "voice": ("duplicate_family", "speaker_family", "voice_family", "family"),
}


def role_name_from_asset_type(asset_type: str) -> str | None:
    return _ASSET_TYPE_TO_ROLE.get(asset_type.strip().lower())


def build_asset_diversity_key(
    *,
    role_name: str,
    asset_id: int,
    asset_code: str,
    tag_labels: tuple[str, ...],
    file_path: str | None,
) -> str:
    normalized_role = role_name.strip().lower()
    explicit_family = _explicit_family_key(normalized_role, tag_labels)
    if explicit_family is not None:
        return explicit_family
    content_hash = _file_content_hash(file_path)
    if content_hash is not None:
        return f"{normalized_role}_content:{content_hash[:20]}"
    asset_token = asset_code.strip().lower() or str(asset_id)
    return f"{normalized_role}_asset:{asset_token}"


def build_asset_summary_diversity_key(asset: AssetSummaryDTO) -> str | None:
    role_name = role_name_from_asset_type(asset.asset_type)
    if role_name is None:
        return None
    return build_asset_diversity_key(
        role_name=role_name,
        asset_id=asset.asset_id,
        asset_code=asset.asset_code,
        tag_labels=asset.tag_labels,
        file_path=asset.file_path,
    )


def is_collapsed_diversity_key(diversity_key: str | None) -> bool:
    return bool(diversity_key) and "_asset:" not in diversity_key


def _explicit_family_key(role_name: str, tag_labels: tuple[str, ...]) -> str | None:
    allowed_groups = _ROLE_FAMILY_TAG_GROUPS.get(role_name, ("duplicate_family", "family"))
    values: list[str] = []
    for tag_label in tag_labels:
        group_name, family_value = _split_tag_label(tag_label)
        if group_name is None or family_value is None or group_name not in allowed_groups:
            continue
        values.append(f"{group_name}:{family_value}")
    if not values:
        return None
    normalized = "|".join(sorted(dict.fromkeys(values)))
    return f"{role_name}_family:{normalized}"


def _split_tag_label(tag_label: str) -> tuple[str | None, str | None]:
    text = tag_label.strip().lower()
    if ":" not in text:
        return None, None
    group_name, value = text.split(":", maxsplit=1)
    group_name = group_name.strip()
    value = value.strip()
    if not group_name or not value:
        return None, None
    return group_name, value


def _file_content_hash(file_path: str | None) -> str | None:
    if not file_path:
        return None
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return None
    stat = path.stat()
    return _cached_file_content_hash(str(path.resolve()), stat.st_size, stat.st_mtime_ns)


@lru_cache(maxsize=2048)
def _cached_file_content_hash(path_text: str, file_size: int, modified_ns: int) -> str:
    del file_size, modified_ns
    digest = hashlib.sha256()
    with Path(path_text).open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()
