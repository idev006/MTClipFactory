from __future__ import annotations

from mt_clip_factory.application.dto import CreateProductCommand
from mt_clip_factory.domain.entities import Product


def build_product_from_command(command: CreateProductCommand) -> Product:
    return Product(
        product_code=command.product_code.strip(),
        product_name=command.product_name.strip(),
        category=command.category,
        brand_name=command.brand_name,
        description=command.description,
        default_platform=command.default_platform,
    )

