from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from mt_clip_factory.infrastructure.models import Base
from mt_clip_factory.infrastructure.repositories import SqlAlchemyProductRepository
from mt_clip_factory.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture()
def session_factory() -> sessionmaker[Session]:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture()
def unit_of_work_factory(session_factory: sessionmaker[Session]):
    def factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(
            session_factory=session_factory,
            product_repository_type=SqlAlchemyProductRepository,
        )

    return factory
