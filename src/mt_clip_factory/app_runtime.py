from __future__ import annotations

from pathlib import Path

from mt_clip_factory.bootstrap import build_resource_library_module
from mt_clip_factory.control_center.dto import PathRootStatusDTO
from mt_clip_factory.library.module import ResourceLibraryModule


class ReloadableServiceProxy:
    def __init__(self, target) -> None:
        self._target = target

    def set_target(self, target) -> None:
        self._target = target

    def __getattr__(self, name: str):
        return getattr(self._target, name)


class ApplicationRuntime:
    def __init__(self, workspace_root: Path) -> None:
        self._workspace_root = workspace_root
        self._module = build_resource_library_module(
            workspace_root,
            run_startup_recovery=True,
            path_reload_policy="runtime_hot_reload",
        )
        self.product_service = ReloadableServiceProxy(self._module.product_service)
        self.asset_intake_service = ReloadableServiceProxy(self._module.asset_intake_service)
        self.artifact_generation_service = ReloadableServiceProxy(self._module.artifact_generation_service)
        self.video_assembly_factory_service = ReloadableServiceProxy(self._module.video_assembly_factory_service)
        self.auto_factory_service = (
            None if self._module.auto_factory_service is None else ReloadableServiceProxy(self._module.auto_factory_service)
        )
        self.auto_factory_folder_service = (
            None
            if self._module.auto_factory_folder_service is None
            else ReloadableServiceProxy(self._module.auto_factory_folder_service)
        )
        self.production_order_service = (
            None
            if self._module.production_order_service is None
            else ReloadableServiceProxy(self._module.production_order_service)
        )
        self.tag_management_service = ReloadableServiceProxy(self._module.tag_management_service)
        self.system_settings_service = ReloadableServiceProxy(self._module.system_settings_service)
        self.dashboard_service = ReloadableServiceProxy(self._module.dashboard_service)

    @property
    def module(self) -> ResourceLibraryModule:
        return ResourceLibraryModule(
            product_service=self.product_service,
            asset_intake_service=self.asset_intake_service,
            artifact_generation_service=self.artifact_generation_service,
            video_assembly_factory_service=self.video_assembly_factory_service,
            tag_management_service=self.tag_management_service,
            system_settings_service=self.system_settings_service,
            dashboard_service=self.dashboard_service,
            auto_factory_service=self.auto_factory_service,
            auto_factory_folder_service=self.auto_factory_folder_service,
            production_order_service=self.production_order_service,
        )

    def reload_path_roots(self) -> PathRootStatusDTO:
        self._module = build_resource_library_module(
            self._workspace_root,
            run_startup_recovery=False,
            path_reload_policy="runtime_hot_reload",
        )
        self.product_service.set_target(self._module.product_service)
        self.asset_intake_service.set_target(self._module.asset_intake_service)
        self.artifact_generation_service.set_target(self._module.artifact_generation_service)
        self.video_assembly_factory_service.set_target(self._module.video_assembly_factory_service)
        if self.auto_factory_service is not None and self._module.auto_factory_service is not None:
            self.auto_factory_service.set_target(self._module.auto_factory_service)
        if self.auto_factory_folder_service is not None and self._module.auto_factory_folder_service is not None:
            self.auto_factory_folder_service.set_target(self._module.auto_factory_folder_service)
        if self.production_order_service is not None and self._module.production_order_service is not None:
            self.production_order_service.set_target(self._module.production_order_service)
        self.tag_management_service.set_target(self._module.tag_management_service)
        self.system_settings_service.set_target(self._module.system_settings_service)
        self.dashboard_service.set_target(self._module.dashboard_service)
        return self.system_settings_service.path_root_status()
