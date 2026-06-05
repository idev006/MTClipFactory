from __future__ import annotations

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.application.services import ProductApplicationService
from mt_clip_factory.presentation.viewmodels.product_dashboard import ProductDashboardViewModel


def test_view_model_loads_products(unit_of_work_factory) -> None:
    service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    service.create_product(CreateProductCommand(product_code="demo_product", product_name="Demo Product"))
    view_model = ProductDashboardViewModel(product_service=service)

    view_model.load()

    assert view_model.status == "ready"
    assert len(view_model.products) == 1
    assert view_model.products[0].product_code == "demo_product"

