from __future__ import annotations

import json
from pathlib import Path


class PreviewManifestBuilder:
    def __init__(self, preview_root: Path) -> None:
        self._preview_root = preview_root

    def write_manifest(self, *, product_code: str, recipe_code: str, payload: dict) -> Path:
        target_dir = self._preview_root / product_code
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{recipe_code}.json"
        target_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return target_path
