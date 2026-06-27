from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from mt_clip_factory.factory.caption_runtime import ProductAutomationMetadataStore


@dataclass(slots=True, frozen=True)
class ProductRunArtifactPaths:
    video_path: Path
    manifest_path: Path
    run_root: Path | None
    journal_path: Path | None
    order_snapshot_path: Path | None
    product_local: bool


class ProductRunArtifactStore:
    def __init__(self, *, metadata_store: ProductAutomationMetadataStore) -> None:
        self._metadata_store = metadata_store

    def resolve_render_artifact_paths(
        self,
        *,
        product_code: str,
        batch_code: str | None,
        output_stem: str,
        stage_name: str,
        fallback_video_root: Path,
        fallback_manifest_root: Path,
        video_suffix: str = ".mp4",
        manifest_suffix: str = ".json",
    ) -> ProductRunArtifactPaths:
        context = None if batch_code is None else self._metadata_store.load_runtime_context(product_code)
        if context is None or batch_code is None:
            video_dir = fallback_video_root / product_code / "videos"
            manifest_dir = fallback_manifest_root / product_code
            return ProductRunArtifactPaths(
                video_path=video_dir / f"{output_stem}{video_suffix}",
                manifest_path=manifest_dir / f"{output_stem}{manifest_suffix}",
                run_root=None,
                journal_path=None,
                order_snapshot_path=None,
                product_local=False,
            )
        run_root = context.source_product_dir / "runs" / batch_code
        stage_dir_name = "previews" if stage_name == "preview" else "finals"
        return ProductRunArtifactPaths(
            video_path=run_root / stage_dir_name / "videos" / f"{output_stem}{video_suffix}",
            manifest_path=run_root / "manifests" / f"{output_stem}{manifest_suffix}",
            run_root=run_root,
            journal_path=run_root / "journal.toml",
            order_snapshot_path=run_root / "order_snapshot.toml",
            product_local=True,
        )

    def write_order_snapshot(self, *, product_code: str, batch_code: str, payload: dict[str, object]) -> Path | None:
        paths = self.resolve_render_artifact_paths(
            product_code=product_code,
            batch_code=batch_code,
            output_stem="_snapshot",
            stage_name="preview",
            fallback_video_root=Path("."),
            fallback_manifest_root=Path("."),
        )
        if not paths.product_local or paths.order_snapshot_path is None:
            return None
        paths.order_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "batch_code": batch_code,
            "product_code": product_code,
            **payload,
        }
        paths.order_snapshot_path.write_text(_dump_flat_toml(document) + "\n", encoding="utf-8")
        return paths.order_snapshot_path

    def append_journal_event(
        self,
        *,
        product_code: str,
        batch_code: str,
        event_type: str,
        status: str,
        fields: dict[str, object] | None = None,
    ) -> Path | None:
        paths = self.resolve_render_artifact_paths(
            product_code=product_code,
            batch_code=batch_code,
            output_stem="_journal",
            stage_name="preview",
            fallback_video_root=Path("."),
            fallback_manifest_root=Path("."),
        )
        if not paths.product_local or paths.journal_path is None:
            return None
        existing = {
            "batch_code": batch_code,
            "product_code": product_code,
            "events": [],
        }
        if paths.journal_path.exists():
            with paths.journal_path.open("rb") as file_handle:
                loaded = tomllib.load(file_handle)
            if isinstance(loaded, dict):
                existing["batch_code"] = str(loaded.get("batch_code", batch_code))
                existing["product_code"] = str(loaded.get("product_code", product_code))
                raw_events = loaded.get("events", [])
                if isinstance(raw_events, list):
                    existing["events"] = [event for event in raw_events if isinstance(event, dict)]
        existing["events"].append(
            {
                "event_type": event_type,
                "status": status,
                **({} if fields is None else {key: value for key, value in fields.items() if value is not None}),
            }
        )
        paths.journal_path.parent.mkdir(parents=True, exist_ok=True)
        paths.journal_path.write_text(
            _dump_event_journal(
                batch_code=str(existing["batch_code"]),
                product_code=str(existing["product_code"]),
                events=tuple(existing["events"]),
            )
            + "\n",
            encoding="utf-8",
        )
        return paths.journal_path


def _dump_event_journal(*, batch_code: str, product_code: str, events: tuple[dict[str, object], ...]) -> str:
    lines = [
        f'batch_code = "{_escape_toml(batch_code)}"',
        f'product_code = "{_escape_toml(product_code)}"',
    ]
    for event in events:
        lines.append("")
        lines.append("[[events]]")
        for key, value in event.items():
            lines.append(_toml_line(key, value))
    return "\n".join(lines)


def _dump_flat_toml(data: dict[str, object]) -> str:
    return "\n".join(_toml_line(key, value) for key, value in data.items() if value is not None)


def _toml_line(key: str, value: object) -> str:
    if isinstance(value, (list, tuple)):
        rendered_items = ", ".join(_toml_array_item(item) for item in value)
        return f"{key} = [{rendered_items}]"
    if isinstance(value, bool):
        return f"{key} = {'true' if value else 'false'}"
    if isinstance(value, int):
        return f"{key} = {value}"
    if isinstance(value, float):
        return f"{key} = {value}"
    return f'{key} = "{_escape_toml(str(value))}"'


def _escape_toml(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _toml_array_item(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    return f'"{_escape_toml(str(value))}"'
