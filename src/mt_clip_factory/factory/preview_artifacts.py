from __future__ import annotations

import json
from pathlib import Path


class PreviewManifestBuilder:
    def __init__(self, preview_root: Path) -> None:
        self._preview_root = preview_root

    def write_manifest(
        self,
        *,
        product_code: str,
        recipe_code: str,
        payload: dict,
        target_path: Path | None = None,
    ) -> Path:
        resolved_target_path = target_path or (self._preview_root / product_code / f"{recipe_code}.json")
        resolved_target_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_target_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return resolved_target_path
