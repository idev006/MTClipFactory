from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot

from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.library.artifact_services import ArtifactGenerationService
from mt_clip_factory.library.dto import AssetSummaryDTO, RegisterAssetCommand, UpdateAssetCommand
from mt_clip_factory.library.services import (
    AssetCodeAlreadyExistsError,
    AssetInUseError,
    AssetIntakeService,
    AssetNotFoundError,
    AssetSourceFileMissingError,
)


class AssetLibraryViewModel(QObject):
    assets_changed = Signal()
    products_changed = Signal()
    status_changed = Signal()
    feedback_changed = Signal()

    def __init__(
        self,
        product_service: ProductApplicationService,
        asset_intake_service: AssetIntakeService,
        artifact_generation_service: ArtifactGenerationService,
    ) -> None:
        super().__init__()
        self._product_service = product_service
        self._asset_intake_service = asset_intake_service
        self._artifact_generation_service = artifact_generation_service
        self._products = []
        self._assets: list[AssetSummaryDTO] = []
        self._status = "idle"
        self._feedback = ""
        self._selected_product_id: int | None = None
        self._selected_asset_type: str | None = None
        self._selected_status: str | None = None

    def _get_status(self) -> str:
        return self._status

    def _set_status(self, value: str) -> None:
        if self._status == value:
            return
        self._status = value
        self.status_changed.emit()

    def _get_feedback(self) -> str:
        return self._feedback

    def _set_feedback(self, value: str) -> None:
        if self._feedback == value:
            return
        self._feedback = value
        self.feedback_changed.emit()

    status = Property(str, _get_status, notify=status_changed)
    feedback = Property(str, _get_feedback, notify=feedback_changed)

    @property
    def products(self):
        return list(self._products)

    @property
    def assets(self) -> list[AssetSummaryDTO]:
        return list(self._assets)

    @Slot()
    def load(self) -> None:
        self._set_status("loading")
        self._products = self._product_service.list_products()
        self._assets = self._asset_intake_service.list_assets(
            product_id=self._selected_product_id,
            asset_type=self._selected_asset_type,
            status=self._selected_status,
        )
        self.products_changed.emit()
        self.assets_changed.emit()
        self._set_status("ready")

    def apply_filters(
        self,
        *,
        product_id: int | None,
        asset_type: str | None,
        status: str | None,
    ) -> None:
        self._selected_product_id = product_id
        self._selected_asset_type = asset_type
        self._selected_status = status
        self.load()

    def register_asset(
        self,
        *,
        product_id: int,
        asset_type: str,
        source_file_path: str,
        asset_code: str | None = None,
    ) -> int:
        self._set_status("submitting")
        try:
            asset_id = self._asset_intake_service.register_asset(
                RegisterAssetCommand(
                    product_id=product_id,
                    asset_type=asset_type,
                    source_file_path=Path(source_file_path),
                    asset_code=asset_code,
                )
            )
        except (AssetCodeAlreadyExistsError, AssetSourceFileMissingError, ValueError) as exc:
            self._set_feedback(str(exc))
            self._set_status("error")
            raise

        self._set_feedback(f"Registered asset #{asset_id}")
        self.load()
        return asset_id

    def update_asset(self, *, asset_id: int, asset_code: str) -> int:
        self._set_status("submitting")
        try:
            updated_asset_id = self._asset_intake_service.update_asset(
                UpdateAssetCommand(asset_id=asset_id, asset_code=asset_code)
            )
        except (AssetCodeAlreadyExistsError, AssetNotFoundError, AssetSourceFileMissingError, FileExistsError, ValueError) as exc:
            self._set_feedback(str(exc))
            self._set_status("error")
            raise

        self._set_feedback(f"Updated asset #{updated_asset_id}")
        self.load()
        return updated_asset_id

    def delete_asset(self, asset_id: int) -> None:
        self._set_status("submitting")
        try:
            self._asset_intake_service.delete_asset(asset_id)
        except (AssetInUseError, AssetNotFoundError, ValueError) as exc:
            self._set_feedback(str(exc))
            self._set_status("error")
            raise

        self._set_feedback(f"Deleted asset #{asset_id}")
        self.load()

    def generate_thumbnail(self, asset_id: int) -> int:
        self._set_status("processing")
        try:
            job_id = self._artifact_generation_service.enqueue_thumbnail_job(asset_id)
            self._artifact_generation_service.run_job(job_id)
        except Exception as exc:  # noqa: BLE001
            self._set_feedback(str(exc))
            self._set_status("error")
            raise

        self._set_feedback(f"Generated thumbnail for asset #{asset_id}")
        self.load()
        return job_id

    def generate_proxy(self, asset_id: int) -> int:
        self._set_status("processing")
        try:
            job_id = self._artifact_generation_service.enqueue_proxy_job(asset_id)
            self._artifact_generation_service.run_job(job_id)
        except Exception as exc:  # noqa: BLE001
            self._set_feedback(str(exc))
            self._set_status("error")
            raise

        self._set_feedback(f"Generated proxy for asset #{asset_id}")
        self.load()
        return job_id
