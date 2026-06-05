from __future__ import annotations

import pytest

from mt_clip_factory.application.dto import CreateProductCommand, UpdateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.presentation.library.product_library import ProductLibraryViewModel


def test_view_model_loads_products(unit_of_work_factory) -> None:
    service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    service.create_product(CreateProductCommand(product_code="demo_product", product_name="Demo Product"))
    view_model = ProductLibraryViewModel(product_service=service)

    view_model.load()

    assert view_model.status == "ready"
    assert len(view_model.products) == 1
    assert view_model.products[0].product_code == "demo_product"


def test_view_model_creates_and_refreshes_products(unit_of_work_factory) -> None:
    service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    view_model = ProductLibraryViewModel(product_service=service)

    product_id = view_model.create_product(CreateProductCommand(product_code="demo_product", product_name="Demo Product"))

    assert product_id == 1
    assert view_model.status == "ready"
    assert "Created product #1" in view_model.feedback
    assert len(view_model.products) == 1


def test_view_model_updates_product(unit_of_work_factory) -> None:
    service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    view_model = ProductLibraryViewModel(product_service=service)
    product_id = view_model.create_product(CreateProductCommand(product_code="demo_product", product_name="Demo Product"))

    view_model.update_product(
        UpdateProductCommand(
            product_id=product_id,
            product_code="demo_product_v2",
            product_name="Demo Product V2",
        )
    )

    assert view_model.status == "ready"
    assert view_model.products[0].product_code == "demo_product_v2"
    assert "Updated product #1" in view_model.feedback


def test_view_model_surfaces_duplicate_errors(unit_of_work_factory) -> None:
    service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    view_model = ProductLibraryViewModel(product_service=service)
    view_model.create_product(CreateProductCommand(product_code="demo_product", product_name="Demo Product"))

    with pytest.raises(ValueError):
        view_model.create_product(CreateProductCommand(product_code="demo_product", product_name="Duplicate"))

    assert view_model.status == "error"
    assert "demo_product" in view_model.feedback
