from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractContextManager
from typing import Protocol

from mt_clip_factory.domain.entities import Product, ProductSummary


class ProductRepository(Protocol):
    def add(self, product: Product) -> Product:
        ...

    def get_by_code(self, product_code: str) -> Product | None:
        ...

    def list_summaries(self) -> Sequence[ProductSummary]:
        ...


class UnitOfWork(AbstractContextManager["UnitOfWork"], Protocol):
    products: ProductRepository

    def commit(self) -> None:
        ...

    def rollback(self) -> None:
        ...

