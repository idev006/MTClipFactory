from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import shutil

from mt_clip_factory.app_runtime import ApplicationRuntime
from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.config import default_config
from mt_clip_factory.control_center.dto import PathRootsDTO
from mt_clip_factory.control_center.services import SystemSettingsService
from mt_clip_factory.presentation.control_center.settings import SettingsViewModel


def _runtime_path_roots_from_config(config) -> PathRootsDTO:
    return PathRootsDTO(
        database_path=str(config.paths.database_path),
        media_root=str(config.paths.media_root),
        docs_root=str(config.paths.docs_root),
        outputs_root=str(config.paths.outputs_root),
        preview_root=str(config.paths.preview_root),
    )


def _prepare_workspace(workspace_root: Path) -> None:
    workspace_root.mkdir()
    shutil.copytree(Path.cwd() / "alembic", workspace_root / "alembic")
    shutil.copy2(Path.cwd() / "alembic.ini", workspace_root / "alembic.ini")


def test_system_settings_service_reports_pending_hot_reload_without_restart(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    _prepare_workspace(workspace_root)
    config = default_config(workspace_root)
    service = SystemSettingsService(
        config.paths.app_config_path,
        runtime_path_roots=_runtime_path_roots_from_config(config),
        reload_policy="runtime_hot_reload",
    )

    updated = replace(service.load(), media_root=str(workspace_root / "media_library_v2"))
    service.save(updated)
    status = service.path_root_status()

    assert status.reload_policy == "runtime_hot_reload"
    assert status.restart_required is False
    assert status.changed_path_roots == ("media_root",)


def test_application_runtime_reload_path_roots_swaps_database_and_dashboard_paths(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    _prepare_workspace(workspace_root)
    runtime = ApplicationRuntime(workspace_root)

    runtime.product_service.create_product(
        CreateProductCommand(product_code="honey", product_name="Honey")
    )
    assert len(runtime.product_service.list_products()) == 1

    updated = replace(
        runtime.system_settings_service.load(),
        database_path=str(workspace_root / "data" / "mtclip.db"),
        media_root=str(workspace_root / "media_library_v2"),
        docs_root=str(workspace_root / "doc_v2"),
        outputs_root=str(workspace_root / "outputs_v2"),
        preview_root=str(workspace_root / "outputs_v2" / "preview"),
    )
    runtime.system_settings_service.save(updated)
    pending = runtime.system_settings_service.path_root_status()

    assert pending.reload_policy == "runtime_hot_reload"
    assert pending.restart_required is False
    assert pending.changed_path_roots == (
        "database_path",
        "media_root",
        "docs_root",
        "outputs_root",
        "preview_root",
    )

    applied = runtime.reload_path_roots()
    summary = runtime.dashboard_service.build_summary()

    assert applied.changed_path_roots == ()
    assert applied.runtime_paths.database_path.endswith("mtclip.db")
    assert summary.path_reload_policy == "runtime_hot_reload"
    assert summary.path_restart_required is False
    assert summary.changed_path_roots == ()
    assert summary.runtime_database_path.endswith("mtclip.db")
    assert summary.database_path.endswith("mtclip.db")
    assert summary.runtime_outputs_root.endswith("outputs_v2")
    assert summary.outputs_root.endswith("outputs_v2")
    assert runtime.product_service.list_products() == []


def test_settings_view_model_applies_runtime_hot_reload_and_emits_signal(tmp_path) -> None:
    workspace_root = tmp_path / "workspace"
    _prepare_workspace(workspace_root)
    runtime = ApplicationRuntime(workspace_root)
    view_model = SettingsViewModel(
        runtime.module.system_settings_service,
        runtime_path_reloader=runtime,
    )
    reloaded: list[str] = []
    view_model.runtime_reloaded.connect(lambda: reloaded.append("reloaded"))

    view_model.load()
    assert view_model.settings is not None

    view_model.save(
        replace(
            view_model.settings,
            outputs_root=str(workspace_root / "outputs_v2"),
            preview_root=str(workspace_root / "outputs_v2" / "preview"),
        )
    )
    summary = runtime.dashboard_service.build_summary()

    assert reloaded == ["reloaded"]
    assert "Runtime hot reload applied for path roots" in view_model.feedback
    assert summary.path_reload_policy == "runtime_hot_reload"
    assert summary.path_restart_required is False
    assert summary.changed_path_roots == ()
    assert summary.runtime_outputs_root.endswith("outputs_v2")
    assert summary.outputs_root.endswith("outputs_v2")
