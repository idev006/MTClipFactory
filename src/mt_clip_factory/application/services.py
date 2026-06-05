from __future__ import annotations

from collections.abc import Callable

from mt_clip_factory.application.dto import CreateProductCommand, ProductSummaryDTO
from mt_clip_factory.application.use_cases import build_product_from_command
from mt_clip_factory.domain.services import UnitOfWork


class ProductCodeAlreadyExistsError(ValueError):
    """Raised when a product code is duplicated."""


class ProductApplicationService:
    def __init__(self, unit_of_work_factory: Callable[[], UnitOfWork]) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def create_product(self, command: CreateProductCommand) -> int:
        product = build_product_from_command(command)
        with self._unit_of_work_factory() as uow:
            existing = uow.products.get_by_code(product.product_code)
            if existing is not None:
                raise ProductCodeAlreadyExistsError(product.product_code)

            created = uow.products.add(product)
            uow.commit()
            if created.id is None:
                raise RuntimeError("Product identifier was not assigned.")
            return created.id

    def list_products(self) -> list[ProductSummaryDTO]:
        with self._unit_of_work_factory() as uow:
            return [
                ProductSummaryDTO(
                    product_id=summary.product_id,
                    product_code=summary.product_code,
                    product_name=summary.product_name,
                    asset_count=summary.asset_count,
                    recipe_count=summary.recipe_count,
                    output_count=summary.output_count,
                )
                for summary in uow.products.list_summaries()
            ]

