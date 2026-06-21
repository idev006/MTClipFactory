from __future__ import annotations

from pathlib import Path

from mt_clip_factory.infrastructure.database import create_engine_from_path


def test_create_engine_from_path_configures_sqlite_runtime_pragmas(tmp_path: Path) -> None:
    engine = create_engine_from_path(tmp_path / "app.db")

    with engine.connect() as connection:
        journal_mode = connection.exec_driver_sql("PRAGMA journal_mode").scalar_one()
        busy_timeout = connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one()

    assert str(journal_mode).lower() == "wal"
    assert busy_timeout == 30000
