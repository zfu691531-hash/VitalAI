import logging
import sqlite3
from typing import Any, Dict, List, Optional, Union

from Base.Repository.base.baseConnection import BaseConnection

logger = logging.getLogger(__name__)


class SQLiteConnection(BaseConnection):
    """SQLite database connection implementation."""

    def __init__(
        self,
        host: str = "",
        user: str = "",
        password: str = "",
        database: str = ":memory:",
        port: int = 0,
        charset: str = "utf8",
        mincached: int = 0,
        maxcached: int = 0,
        maxconnections: int = 1,
        blocking: bool = False,
    ):
        super().__init__(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            charset=charset,
            mincached=0,
            maxcached=0,
            maxconnections=1,
            blocking=False,
        )
        self.config["type"] = "sqlite"
        self._ensure_database_exists()
        self._create_connection_pool()

    def _ensure_database_exists(self):
        """SQLite creates the database file lazily when the first connection opens."""
        db_path = self.config["database"]
        if db_path == ":memory:":
            logger.debug("Using in-memory SQLite database")
        else:
            logger.debug("Using SQLite database file %s", db_path)

    def _create_connection_pool(self):
        """SQLite does not use a connection pool."""
        self._connection_pool = None
        logger.debug("SQLite uses single direct connections without pooling")

    def _get_raw_connection(self):
        """Create a direct sqlite3 connection."""
        return sqlite3.connect(
            self.config["database"],
            check_same_thread=False,
        )

    def get_connection_url(self) -> str:
        """Return a SQLAlchemy-style SQLite connection URL."""
        database = self.config["database"]
        if database == ":memory:":
            return "sqlite:///:memory:"
        return f"sqlite:///{database}"

    def execute(
        self,
        sql: str,
        params: Optional[tuple] = None,
        operation_type: Optional[str] = None,
        commit: bool = True,
    ) -> Union[List[Dict[str, Any]], int]:
        """Execute one SQL statement and return query rows or affected counts."""
        if operation_type is None:
            operation_type = self._detect_operation_type(sql)

        normalized_sql = sql.replace("%s", "?")
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute(normalized_sql, params or ())

            if operation_type == "query":
                return [dict(row) for row in cur.fetchall()]
            if operation_type == "insert":
                last_id = cur.lastrowid
                if commit:
                    conn.commit()
                return last_id

            affected = cur.rowcount
            if commit:
                conn.commit()
            return affected
        finally:
            conn.close()

    def execute_query(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Backward-compatible query helper."""
        return self.execute(sql, params, "query")

    def execute_update(self, sql: str, params: Optional[tuple] = None, commit: bool = True) -> int:
        """Backward-compatible update helper."""
        return self.execute(sql, params, "update", commit)

    def execute_insert(self, sql: str, params: Optional[tuple] = None, commit: bool = True) -> int:
        """Backward-compatible insert helper."""
        return self.execute(sql, params, "insert", commit)

    def table_exists(self, table_name: str) -> bool:
        """Return whether a given SQLite table already exists."""
        sql = """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """
        result = self.execute_query(sql, (table_name,))
        return len(result) > 0
