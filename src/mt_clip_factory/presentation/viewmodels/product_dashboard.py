from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from mt_clip_factory.application.dto import ProductSummaryDTO
from mt_clip_factory.application.services import ProductApplicationService


class ProductDashboardViewModel(QObject):
    products_changed = Signal()
    status_changed = Signal()

    def __init__(self, product_service: ProductApplicationService) -> None:
        super().__init__()
        self._product_service = product_service
        self._products: list[ProductSummaryDTO] = []
        self._status = "idle"

    def _get_status(self) -> str:
        return self._status

    def _set_status(self, value: str) -> None:
        if self._status == value:
            return
        self._status = value
        self.status_changed.emit()

    status = Property(str, _get_status, notify=status_changed)

    @property
    def products(self) -> list[ProductSummaryDTO]:
        return list(self._products)

    @Slot()
    def load(self) -> None:
        self._set_status("loading")
        self._products = self._product_service.list_products()
        self.products_changed.emit()
        self._set_status("ready")

