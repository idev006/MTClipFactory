from __future__ import annotations

import pytest
from sqlalchemy import text

from mt_clip_factory.application.dto import CreateProductCommand, UpdateProductCommand
from mt_clip_factory.application.services import (
    ProductApplicationService,
    ProductCodeAlreadyExistsError,
    ProductDeleteNotAllowedError,
    ProductNotFoundError,
)


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


def test_get_product_returns_details(unit_of_work_factory) -> None:
    service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = service.create_product(
        CreateProductCommand(
            product_code="biiigbee_honey",
            product_name="BIIIGBEE Honey",
            category="food",
            brand_name="BIIIGBEE",
            description="Wild honey",
            default_platform="tiktok",
        )
    )

    product = service.get_product(product_id)

    assert product.product_id == product_id
    assert product.brand_name == "BIIIGBEE"
    assert product.default_platform == "tiktok"


def test_update_product_changes_existing_record(unit_of_work_factory) -> None:
    service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))

    service.update_product(
        UpdateProductCommand(
            product_id=product_id,
            product_code="honey_v2",
            product_name="Honey Premium",
            category="food",
            brand_name="Bee Farm",
            description="Updated description",
            default_platform="facebook_reels",
        )
    )

    product = service.get_product(product_id)

    assert product.product_code == "honey_v2"
    assert product.product_name == "Honey Premium"
    assert product.default_platform == "facebook_reels"


def test_update_product_rejects_duplicate_code(unit_of_work_factory) -> None:
    service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    first_id = service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    second_id = service.create_product(CreateProductCommand(product_code="tea", product_name="Tea"))

    with pytest.raises(ProductCodeAlreadyExistsError):
        service.update_product(
            UpdateProductCommand(
                product_id=second_id,
                product_code="honey",
                product_name="Tea",
            )
        )

    assert service.get_product(first_id).product_code == "honey"


def test_delete_product_removes_existing_record(unit_of_work_factory) -> None:
    service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))

    service.delete_product(product_id)

    with pytest.raises(ProductNotFoundError):
        service.get_product(product_id)


def test_delete_product_missing_record_raises_error(unit_of_work_factory) -> None:
    service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)

    with pytest.raises(ProductNotFoundError):
        service.delete_product(999)


def test_delete_product_with_assets_is_blocked(unit_of_work_factory, session_factory) -> None:
    service = ProductApplicationService(unit_of_work_factory=unit_of_work_factory)
    product_id = service.create_product(CreateProductCommand(product_code="honey", product_name="Honey"))
    session = session_factory()
    session.execute(
        text(
            """
        INSERT INTO assets (
            product_id,
            asset_code,
            asset_type,
            file_path,
            file_name,
            has_audio,
            quality_score,
            status,
            created_at
        ) VALUES (
            :product_id,
            'asset_001',
            'background_video',
            'media/background.mp4',
            'background.mp4',
            0,
            0,
            'active',
            CURRENT_TIMESTAMP
        )
        """
        ),
        {"product_id": product_id},
    )
    session.commit()
    session.close()

    with pytest.raises(ProductDeleteNotAllowedError):
        service.delete_product(product_id)
