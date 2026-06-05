from __future__ import annotations

from mt_clip_factory.application.dto import CreateProductCommand, UpdateProductCommand
from mt_clip_factory.domain.entities import Product


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def build_product_from_command(command: CreateProductCommand) -> Product:
    product_code = command.product_code.strip()
    product_name = command.product_name.strip()
    if not product_code:
        raise ValueError("Product code is required.")
    if not product_name:
        raise ValueError("Product name is required.")

    return Product(
        product_code=product_code,
        product_name=product_name,
        category=_normalize_text(command.category),
        brand_name=_normalize_text(command.brand_name),
        description=_normalize_text(command.description),
        default_platform=_normalize_text(command.default_platform),
    )


def build_updated_product_from_command(command: UpdateProductCommand) -> Product:
    product_code = command.product_code.strip()
    product_name = command.product_name.strip()
    if not product_code:
        raise ValueError("Product code is required.")
    if not product_name:
        raise ValueError("Product name is required.")

    return Product(
        id=command.product_id,
        product_code=product_code,
        product_name=product_name,
        category=_normalize_text(command.category),
        brand_name=_normalize_text(command.brand_name),
        description=_normalize_text(command.description),
        default_platform=_normalize_text(command.default_platform),
    )
