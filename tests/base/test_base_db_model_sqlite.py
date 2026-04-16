"""SQLite coverage for BaseDBModel table creation."""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import ClassVar
import unittest
from uuid import uuid4

from Base.Repository.base.baseDBModel import BaseDBModel
from Base.Repository.connections.sqliteConnection import SQLiteConnection


class BaseDBModelSQLiteTests(unittest.TestCase):
    def test_create_table_accepts_sqlite_ddl_success(self) -> None:
        """SQLite DDL reports rowcount -1, so success must be verified by table existence."""
        runtime_root = Path(".runtime")
        runtime_root.mkdir(exist_ok=True)
        runtime_dir = runtime_root / f"base-db-model-sqlite-{uuid4().hex}"
        runtime_dir.mkdir()
        try:
            database_path = runtime_dir / "base_model.sqlite3"
            connection = SQLiteConnection(database=str(database_path))

            class SQLiteRecord(BaseDBModel):
                table_alias: ClassVar[str] = "base_sqlite_records"
                create_table_sql: ClassVar[str] = """
                    CREATE TABLE base_sqlite_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL
                    )
                """
                id: int | None = None
                name: str

            SQLiteRecord.set_db_connection(connection)
            SQLiteRecord._table_checked = False

            self.assertTrue(SQLiteRecord.create_table())
            self.assertTrue(SQLiteRecord.table_exists())
        finally:
            shutil.rmtree(runtime_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
