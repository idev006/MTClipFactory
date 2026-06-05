from __future__ import annotations

from collections.abc import Callable

from mt_clip_factory.application.dto import CreateProductCommand, ProductDetailsDTO, ProductSummaryDTO, UpdateProductCommand
from mt_clip_factory.application.use_cases import build_product_from_command, build_updated_product_from_command
from mt_clip_factory.domain.services import UnitOfWork


class ProductCodeAlreadyExistsError(ValueError):
    """Raised when a product code is duplicated."""


class ProductNotFoundError(ValueError):
    """Raised when a product cannot be found."""


class ProductDeleteNotAllowedError(ValueError):
    """Raised when a product cannot be deleted safely."""


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

    def get_product(self, product_id: int) -> ProductDetailsDTO:
        with self._unit_of_work_factory() as uow:
            product = uow.products.get_by_id(product_id)
            if product is None or product.id is None:
                raise ProductNotFoundError(str(product_id))

            return ProductDetailsDTO(
                product_id=product.id,
                product_code=product.product_code,
                product_name=product.product_name,
                category=product.category,
                brand_name=product.brand_name,
                description=product.description,
                default_platform=product.default_platform,
            )

    def update_product(self, command: UpdateProductCommand) -> None:
        product = build_updated_product_from_command(command)
        with self._unit_of_work_factory() as uow:
            current = uow.products.get_by_id(command.product_id)
            if current is None:
                raise ProductNotFoundError(str(command.product_id))

            existing = uow.products.get_by_code(product.product_code)
            if existing is not None and existing.id != command.product_id:
                raise ProductCodeAlreadyExistsError(product.product_code)

            uow.products.update(product)
            uow.commit()

    def delete_product(self, product_id: int) -> None:
        with self._unit_of_work_factory() as uow:
            current = uow.products.get_by_id(product_id)
            if current is None:
                raise ProductNotFoundError(str(product_id))
            if uow.products.has_assets(product_id):
                raise ProductDeleteNotAllowedError(str(product_id))

            uow.products.delete(product_id)
            uow.commit()

    def list_products(self) -> list[ProductSummaryDTO]:
        with self._unit_of_work_factory() as uow:
            return [
                ProductSummaryDTO(
                    product_id=summary.product_id,
                    product_code=summary.product_code,
                    product_name=summary.product_name,
                    category=summary.category,
                    brand_name=summary.brand_name,
                    default_platform=summary.default_platform,
                    asset_count=summary.asset_count,
                    recipe_count=summary.recipe_count,
                    output_count=summary.output_count,
                )
                for summary in uow.products.list_summaries()
            ]
