from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from mt_clip_factory.infrastructure.database import create_engine_from_path, create_schema

BASELINE_REVISION = "20260605_0001"


def ensure_schema_current(workspace_root: Path, database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine_from_path(database_path)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    if not table_names:
        create_schema(engine)
        _run_alembic(workspace_root, database_path, command_name="stamp", revision="head")
        return

    if "alembic_version" not in table_names:
        _run_alembic(workspace_root, database_path, command_name="stamp", revision=BASELINE_REVISION)

    _run_alembic(workspace_root, database_path, command_name="upgrade", revision="head")


def _run_alembic(workspace_root: Path, database_path: Path, *, command_name: str, revision: str) -> None:
    config = Config(str(workspace_root / "alembic.ini"))
    config.set_main_option("script_location", str(workspace_root / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")

    if command_name == "stamp":
        command.stamp(config, revision)
        return
    if command_name == "upgrade":
        command.upgrade(config, revision)
        return
    raise ValueError(f"Unsupported alembic command: {command_name}")
