from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.core.config import AppConfig, get_config
from app.db.schema import SCHEMA_SQL


def _db_path(config: AppConfig | None = None, db_path: Path | str | None = None) -> Path:
    if db_path is not None:
        return Path(db_path)
    return (config or get_config()).app_db_path


@contextmanager
def get_connection(
    config: AppConfig | None = None,
    db_path: Path | str | None = None,
) -> Iterator[sqlite3.Connection]:
    path = _db_path(config, db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db(config: AppConfig | None = None, db_path: Path | str | None = None) -> None:
    with get_connection(config=config, db_path=db_path) as connection:
        for statement in SCHEMA_SQL:
            connection.execute(statement)
