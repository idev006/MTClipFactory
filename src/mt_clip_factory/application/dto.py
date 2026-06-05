from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CreateProductCommand:
    product_code: str
    product_name: str
    category: str | None = None
    brand_name: str | None = None
    description: str | None = None
    default_platform: str | None = None


@dataclass(slots=True, frozen=True)
class ProductSummaryDTO:
    product_id: int
    product_code: str
    product_name: str
    asset_count: int
    recipe_count: int
    output_count: int

