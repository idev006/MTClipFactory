from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractContextManager
from typing import Protocol

from mt_clip_factory.domain.assets import Asset, AssetSummary
from mt_clip_factory.domain.entities import Product, ProductSummary
from mt_clip_factory.domain.tags import Tag, TagSummary


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

    def list_summaries(
        self,
        product_id: int | None = None,
        asset_type: str | None = None,
        status: str | None = None,
    ) -> Sequence[AssetSummary]:
        ...

    def assign_tag(self, asset_id: int, tag_id: int) -> None:
        ...

    def list_tag_ids(self, asset_id: int) -> Sequence[int]:
        ...


class TagRepository(Protocol):
    def add(self, tag: Tag) -> Tag:
        ...

    def get_by_id(self, tag_id: int) -> Tag | None:
        ...

    def get_by_name_and_group(self, tag_name: str, tag_group: str) -> Tag | None:
        ...

    def list_summaries(self, tag_group: str | None = None) -> Sequence[TagSummary]:
        ...


class UnitOfWork(AbstractContextManager["UnitOfWork"], Protocol):
    products: ProductRepository
    assets: AssetRepository
    tags: TagRepository

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...
