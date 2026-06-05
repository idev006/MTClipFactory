from __future__ import annotations

from pathlib import Path
import sqlite3

from sqlalchemy import inspect

from mt_clip_factory.infrastructure.database import create_engine_from_path
from mt_clip_factory.infrastructure.migrations import ensure_schema_current


def test_ensure_schema_current_upgrades_legacy_database(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    database_path = workspace_root / "legacy.db"
    alembic_dir = workspace_root / "alembic"
    versions_dir = alembic_dir / "versions"
    versions_dir.mkdir(parents=True)
    repo_root = Path(__file__).resolve().parents[1]

    (workspace_root / "alembic.ini").write_text(
        "\n".join(
            [
                "[alembic]",
                "script_location = alembic",
                f"sqlalchemy.url = sqlite:///{database_path}",
                "",
                "[loggers]",
                "keys = root,sqlalchemy,alembic",
                "",
                "[handlers]",
                "keys = console",
                "",
                "[formatters]",
                "keys = generic",
                "",
                "[logger_root]",
                "level = WARN",
                "handlers = console",
                "",
                "[logger_sqlalchemy]",
                "level = WARN",
                "handlers =",
                "qualname = sqlalchemy.engine",
                "",
                "[logger_alembic]",
                "level = INFO",
                "handlers =",
                "qualname = alembic",
                "",
                "[handler_console]",
                "class = StreamHandler",
                "args = (sys.stderr,)",
                "level = NOTSET",
                "formatter = generic",
                "",
                "[formatter_generic]",
                "format = %(levelname)-5.5s [%(name)s] %(message)s",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (alembic_dir / "env.py").write_text((repo_root / "alembic" / "env.py").read_text(encoding="utf-8"), encoding="utf-8")
    (alembic_dir / "script.py.mako").write_text(
        (repo_root / "alembic" / "script.py.mako").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    for migration_name in (
        "20260605_0001_initial_schema.py",
        "20260606_0002_approval_audit_fields.py",
        "20260606_0003_decision_event_history.py",
    ):
        source = repo_root / "alembic" / "versions" / migration_name
        target = versions_dir / migration_name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                recipe_code VARCHAR(128) NOT NULL UNIQUE,
                target_platform VARCHAR(64),
                target_ratio VARCHAR(16),
                duration_sec FLOAT,
                mood VARCHAR(64),
                script_angle VARCHAR(128),
                target_audience VARCHAR(128),
                hook_text VARCHAR(512),
                cta_text VARCHAR(512),
                recipe_score FLOAT NOT NULL DEFAULT 0,
                duplicate_risk FLOAT NOT NULL DEFAULT 0,
                status VARCHAR(32) NOT NULL DEFAULT 'candidate',
                created_at DATETIME NOT NULL
            );
            CREATE TABLE outputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                output_code VARCHAR(128) NOT NULL UNIQUE,
                file_path VARCHAR(1024) NOT NULL,
                platform VARCHAR(64),
                ratio VARCHAR(16),
                duration_sec FLOAT,
                quality_score FLOAT,
                duplicate_risk FLOAT,
                approved BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL
            );
            """
        )
        connection.commit()

    ensure_schema_current(workspace_root, database_path)

    engine = create_engine_from_path(database_path)
    inspector = inspect(engine)
    recipe_columns = {column["name"] for column in inspector.get_columns("recipes")}
    output_columns = {column["name"] for column in inspector.get_columns("outputs")}
    decision_event_columns = {column["name"] for column in inspector.get_columns("decision_events")}
    assert "decision_actor" in recipe_columns
    assert "decision_at" in recipe_columns
    assert "decision_reason" in recipe_columns
    assert "approved_by" in output_columns
    assert "approved_at" in output_columns
    assert "approval_reason" in output_columns
    assert {"recipe_id", "output_id", "event_type", "actor", "reason", "created_at"} <= decision_event_columns
    assert "alembic_version" in inspector.get_table_names()
