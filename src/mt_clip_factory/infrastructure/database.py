from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, event

from mt_clip_factory.infrastructure.models import Base


def create_engine_from_path(database_path: Path) -> Engine:
    engine = create_engine(
        f"sqlite:///{database_path}",
        future=True,
        connect_args={"timeout": 30},
    )

    @event.listens_for(engine, "connect")
    def _configure_sqlite_connection(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout = 30000")
        cursor.close()

    return engine


def create_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)
