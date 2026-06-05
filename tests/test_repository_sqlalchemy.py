from __future__ import annotations

from mt_clip_factory.domain.entities import Product
from mt_clip_factory.infrastructure.repositories import SqlAlchemyProductRepository


def test_repository_round_trips_product(session_factory) -> None:
    session = session_factory()
    repository = SqlAlchemyProductRepository(session)
    created = repository.add(Product(product_code="demo_product", product_name="Demo Product"))
    session.commit()

    loaded = repository.get_by_code("demo_product")

    assert created.id is not None
    assert loaded is not None
    assert loaded.product_name == "Demo Product"


def test_repository_updates_product(session_factory) -> None:
    session = session_factory()
    repository = SqlAlchemyProductRepository(session)
    created = repository.add(Product(product_code="demo_product", product_name="Demo Product"))
    session.commit()

    created.product_name = "Updated Product"
    repository.update(created)
    session.commit()

    loaded = repository.get_by_id(created.id or 0)

    assert loaded is not None
    assert loaded.product_name == "Updated Product"


def test_repository_deletes_product(session_factory) -> None:
    session = session_factory()
    repository = SqlAlchemyProductRepository(session)
    created = repository.add(Product(product_code="demo_product", product_name="Demo Product"))
    session.commit()

    repository.delete(created.id or 0)
    session.commit()

    assert repository.get_by_id(created.id or 0) is None
