"""Read-only MySQL adapter backed by a server-side credential reference."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import pymysql
from dotenv import load_dotenv

from app.api.authorization import AccessPolicy
from app.db.base import DatabaseExecutionError
from app.db.result_formatter import format_query_result
from app.db.security_policy import validate_readonly_sql
from app.rag.document_builder import build_schema_retrieval
from app.rag.normalizer import NormalizedColumn, NormalizedForeignKey, NormalizedTable
from app.schemas.domain import QueryResult, SchemaRetrieval


class MySQLAdapter:
    def __init__(self, database_id: str, config: Mapping[str, Any], result_row_limit: int = 100) -> None:
        self.database_id = database_id
        self.config = dict(config)
        self.result_row_limit = result_row_limit
        self._connection = None

    def inspect_schema(self, database_id: str) -> SchemaRetrieval:
        self._check_database(database_id)
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY, ORDINAL_POSITION "
                    "FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s ORDER BY TABLE_NAME, ORDINAL_POSITION",
                    (self.config["database"],),
                )
                rows = cursor.fetchall()
                cursor.execute(
                    "SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME "
                    "FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL",
                    (self.config["database"],),
                )
                foreign_key_rows = cursor.fetchall()
            grouped: dict[str, list[NormalizedColumn]] = {}
            for row in rows:
                grouped.setdefault(row[0], []).append(
                    NormalizedColumn(
                        name=row[1],
                        data_type=row[2] or "",
                        nullable=row[3] != "NO",
                        primary_key_position=int(row[5]) if row[4] == "PRI" else 0,
                    )
                )
            foreign_keys_by_table: dict[str, list[NormalizedForeignKey]] = {}
            for row in foreign_key_rows:
                foreign_keys_by_table.setdefault(row[0], []).append(
                    NormalizedForeignKey(column=row[1], referenced_table=row[2], referenced_column=row[3])
                )
            tables = tuple(
                NormalizedTable(
                    name=name,
                    columns=tuple(columns),
                    foreign_keys=tuple(foreign_keys_by_table.get(name, ())),
                )
                for name, columns in grouped.items()
            )
            return build_schema_retrieval(self.database_id, tables, dialect="mysql")
        except pymysql.MySQLError as error:
            raise DatabaseExecutionError("connection_error", "Unable to inspect the database schema.") from error
        finally:
            connection.close()

    def get_schema_version(self, database_id: str) -> str:
        return self.inspect_schema(database_id).schema_version

    def execute_readonly(
        self,
        sql: str,
        deadline: float,
        access_policy: AccessPolicy,
        parameters: Sequence[Any] | Mapping[str, Any] = (),
    ) -> QueryResult:
        self._check_database(self.database_id, access_policy)
        allowed_parameters = set(parameters) if isinstance(parameters, Mapping) else None
        validation = validate_readonly_sql(sql, "mysql", access_policy, allowed_parameters)
        if not validation.allowed:
            raise DatabaseExecutionError("unsafe_sql", validation.reason or "unsafe_sql")
        if time.monotonic() >= deadline:
            raise DatabaseExecutionError("connection_error", "Query deadline exceeded.")
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, parameters if isinstance(parameters, Mapping) else tuple(parameters))
                rows = cursor.fetchmany(self.result_row_limit + 1)
                columns = [item[0] for item in cursor.description or ()]
            return format_query_result(columns, rows, self.result_row_limit, access_policy)
        except pymysql.MySQLError as error:
            category = "connection_error" if time.monotonic() >= deadline else "unknown"
            raise DatabaseExecutionError(category, "The read-only query failed.") from error
        finally:
            connection.close()

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _connect(self):
        password = _credential(self.config["credential_ref"])
        if password is None:
            raise DatabaseExecutionError("connection_error", "The configured database credential is unavailable.")
        ssl = {"check_hostname": True} if self.config.get("tls", True) else None
        try:
            return pymysql.connect(
                host=str(self.config["host"]),
                port=int(self.config["port"]),
                user=str(self.config["username"]),
                password=password,
                database=str(self.config["database"]),
                connect_timeout=5,
                read_timeout=15,
                write_timeout=5,
                ssl=ssl,
                autocommit=True,
                cursorclass=pymysql.cursors.Cursor,
            )
        except pymysql.MySQLError as error:
            raise DatabaseExecutionError("connection_error", "Unable to open the database.") from error

    def _check_database(self, database_id: str, policy: AccessPolicy | None = None) -> None:
        if database_id != self.database_id or (policy and database_id not in policy.allowed_database_ids):
            raise DatabaseExecutionError("permission_error", "The requested database is not available.")


def _credential(reference: object) -> str | None:
    if not isinstance(reference, str) or not reference.strip():
        return None
    # Resolve the repository .env explicitly; the server may be launched from another cwd.
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(dotenv_path=project_root / ".env", override=False)
    key = "DATABASE_SECRET_" + "".join(char if char.isalnum() else "_" for char in reference.upper())
    value = os.getenv(key)
    return value if value else None
