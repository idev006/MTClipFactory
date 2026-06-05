from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(slots=True)
class Product:
    product_code: str
    product_name: str
    category: str | None = None
    brand_name: str | None = None
    description: str | None = None
    default_platform: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    id: int | None = None


@dataclass(slots=True)
class ProductSummary:
    product_id: int
    product_code: str
    product_name: str
    category: str | None = None
    brand_name: str | None = None
    default_platform: str | None = None
    asset_count: int = 0
    recipe_count: int = 0
    output_count: int = 0
