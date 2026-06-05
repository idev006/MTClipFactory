from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

from mt_clip_factory.application.dto import CreateProductCommand, ProductDetailsDTO, ProductSummaryDTO, UpdateProductCommand
from mt_clip_factory.application.services import (
    ProductApplicationService,
    ProductCodeAlreadyExistsError,
    ProductDeleteNotAllowedError,
    ProductNotFoundError,
)


class ProductLibraryViewModel(QObject):
    products_changed = Signal()
    status_changed = Signal()
    feedback_changed = Signal()

    def __init__(self, product_service: ProductApplicationService) -> None:
        super().__init__()
        self._product_service = product_service
        self._products: list[ProductSummaryDTO] = []
        self._status = "idle"
        self._feedback = ""

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
    def products(self) -> list[ProductSummaryDTO]:
        return list(self._products)

    @Slot()
    def load(self) -> None:
        self._set_status("loading")
        self._products = self._product_service.list_products()
        self.products_changed.emit()
        self._set_status("ready")

    def create_product(self, command: CreateProductCommand) -> int:
        self._set_status("submitting")
        try:
            product_id = self._product_service.create_product(command)
        except (ProductCodeAlreadyExistsError, ValueError) as exc:
            self._set_feedback(str(exc))
            self._set_status("error")
            raise

        self._set_feedback(f"Created product #{product_id}")
        self.load()
        return product_id

    def get_product(self, product_id: int) -> ProductDetailsDTO:
        return self._product_service.get_product(product_id)

    def update_product(self, command: UpdateProductCommand) -> None:
        self._set_status("updating")
        try:
            self._product_service.update_product(command)
        except (ProductCodeAlreadyExistsError, ProductNotFoundError, ValueError) as exc:
            self._set_feedback(str(exc))
            self._set_status("error")
            raise

        self._set_feedback(f"Updated product #{command.product_id}")
        self.load()

    def delete_product(self, product_id: int) -> None:
        self._set_status("deleting")
        try:
            self._product_service.delete_product(product_id)
        except (ProductDeleteNotAllowedError, ProductNotFoundError) as exc:
            self._set_feedback(str(exc))
            self._set_status("error")
            raise

        self._set_feedback(f"Deleted product #{product_id}")
        self.load()

