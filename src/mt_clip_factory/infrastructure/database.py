from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine

from mt_clip_factory.infrastructure.models import Base


def create_engine_from_path(database_path: Path) -> Engine:
    return create_engine(f"sqlite:///{database_path}", future=True)


def create_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)

