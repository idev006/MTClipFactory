from __future__ import annotations

import pytest

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService, ProductCodeAlreadyExistsError


def test_create_product_assigns_identifier(unit_of_work_factory) -> None:
    service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)

    product_id = service.create_product(
        CreateProductCommand(
            product_code="biiigbee_honey",
            product_name="BIIIGBEE Honey",
            category="food",
            brand_name="BIIIGBEE",
            default_platform="tiktok",
        )
    )

    assert product_id == 1


def test_create_product_rejects_duplicate_code(unit_of_work_factory) -> None:
    service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    command = CreateProductCommand(product_code="biiigbee_honey", product_name="BIIIGBEE Honey")
    service.create_product(command)

    with pytest.raises(ProductCodeAlreadyExistsError):
        service.create_product(command)


def test_list_products_returns_summary(unit_of_work_factory) -> None:
    service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    service.create_product(CreateProductCommand(product_code="biiigbee_honey", product_name="BIIIGBEE Honey"))
    service.create_product(CreateProductCommand(product_code="herb_tea", product_name="Herb Tea"))

    products = service.list_products()

    assert [product.product_code for product in products] == ["biiigbee_honey", "herb_tea"]

