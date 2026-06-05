from __future__ import annotations

from collections.abc import Callable
from types import TracebackType

from sqlalchemy.orm import Session

from mt_clip_factory.infrastructure.repositories import SqlAlchemyProductRepository


class SqlAlchemyUnitOfWork:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        product_repository_type: type[SqlAlchemyProductRepository] = SqlAlchemyProductRepository,
    ) -> None:
        self._session_factory = session_factory
        self._product_repository_type = product_repository_type
        self.session: Session | None = None
        self.products: SqlAlchemyProductRepository

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = self._session_factory()
        self.products = self._product_repository_type(self.session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self.session is None:
            return
        if exc is not None:
            self.session.rollback()
        self.session.close()

    def commit(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of work has not been entered.")
        self.session.commit()

    def rollback(self) -> None:
        if self.session is None:
            raise RuntimeError("Unit of work has not been entered.")
        self.session.rollback()

