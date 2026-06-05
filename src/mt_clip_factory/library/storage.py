from __future__ import annotations

import shutil
from pathlib import Path

from mt_clip_factory.domain.enums import AssetType
from mt_clip_factory.library.contracts import StoredAssetFile


class LocalAssetStorage:
    _folder_names = {
        AssetType.BACKGROUND_VIDEO: "background_videos",
        AssetType.FOREGROUND_VIDEO: "foreground_videos",
        AssetType.VOICEOVER: "voiceovers",
        AssetType.BACKGROUND_MUSIC: "background_music",
        AssetType.SFX: "sfx",
        AssetType.TEMPLATE: "templates",
        AssetType.SCRIPT: "scripts",
    }

    def __init__(self, media_root: Path) -> None:
        self._media_root = media_root

    def store_asset(
        self,
        product_code: str,
        asset_type: AssetType,
        asset_code: str,
        source_file_path: Path,
    ) -> StoredAssetFile:
        target_folder = self._media_root / "products" / product_code / self._folder_names[asset_type]
        target_folder.mkdir(parents=True, exist_ok=True)

        file_suffix = source_file_path.suffix.lower()
        target_path = target_folder / f"{asset_code}{file_suffix}"
        if target_path.exists():
            raise FileExistsError(str(target_path))

        shutil.copy2(source_file_path, target_path)
        return StoredAssetFile(file_path=target_path, file_name=target_path.name)

