from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractContextManager
from typing import Protocol

from mt_clip_factory.domain.assets import Asset, AssetSummary
from mt_clip_factory.domain.entities import Product, ProductSummary


class ProductRepository(Protocol):
    def add(self, product: Product) -> Product:
        ...

    def get_by_id(self, product_id: int) -> Product | None:
        ...

    def get_by_code(self, product_code: str) -> Product | None:
        ...

    def update(self, product: Product) -> Product:
        ...

    def delete(self, product_id: int) -> None:
        ...

    def has_assets(self, product_id: int) -> bool:
        ...

    def list_summaries(self) -> Sequence[ProductSummary]:
        ...


class AssetRepository(Protocol):
    def add(self, asset: Asset) -> Asset:
        ...

    def get_by_id(self, asset_id: int) -> Asset | None:
        ...

    def get_by_code(self, asset_code: str) -> Asset | None:
        ...

    def list_summaries(self, product_id: int | None = None) -> Sequence[AssetSummary]:
        ...


class UnitOfWork(AbstractContextManager["UnitOfWork"], Protocol):
    products: ProductRepository
    assets: AssetRepository

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...
