"""SQLite 只读数据库适配器。"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Sequence

from app.api.authorization import AccessPolicy
from app.db.base import DatabaseExecutionError
from app.db.connection_manager import open_sqlite_readonly
from app.db.result_formatter import format_query_result
from app.db.security_policy import validate_readonly_sql
from app.rag.introspector import inspect_sqlite_schema
from app.schemas.domain import QueryResult, SchemaRetrieval


class SQLiteAdapter:
    def __init__(self, database_id: str, database_path: str, result_row_limit: int = 100) -> None:
        # 构造时拒绝无效限制，确保每次查询都有安全上限。
        if result_row_limit <= 0:
            raise ValueError("result_row_limit must be positive")
        # 将逻辑 ID 与文件路径分离，用于授权校验。
        self.database_id = database_id
        self.database_path = str(Path(database_path).expanduser().resolve())
        self.result_row_limit = result_row_limit

    def inspect_schema(self, database_id: str) -> SchemaRetrieval:
        # Schema 读取与查询执行使用相同的数据库身份边界。
        self._check_database(database_id)
        connection = self._connect()
        try:
            # introspector 只通过本次操作的连接读取元数据。
            return inspect_sqlite_schema(connection, self.database_id)
        except sqlite3.Error as error:
            raise DatabaseExecutionError("connection_error", "Unable to inspect the database schema.") from error
        finally:
            connection.close()

    def execute_readonly(
        self,
        sql: str,
        deadline: float,
        access_policy: AccessPolicy,
        parameters: Sequence[Any] = (),
    ) -> QueryResult:
        # 创建连接前先校验数据库身份和访问策略。
        self._check_database(self.database_id, access_policy)
        # 只有通过 AST 校验的 SQL 才能到达数据库驱动。
        validation = validate_readonly_sql(sql, "sqlite", access_policy)
        if not validation.allowed:
            raise DatabaseExecutionError("unsafe_sql", validation.reason or "unsafe_sql")
        # 请求已过期时不再创建数据库连接。
        if time.monotonic() >= deadline:
            raise DatabaseExecutionError("connection_error", "Query deadline exceeded.")

        connection = self._connect()

        def progress_handler() -> int:
            # SQLite 会在长时间运行期间周期性调用此回调。
            return int(time.monotonic() >= deadline)

        try:
            # 进度回调间隔用于平衡超时响应速度和回调开销。
            connection.set_progress_handler(progress_handler, 1_000)
            # 参数由 sqlite3 绑定，不通过字符串插值写入 SQL。
            cursor = connection.execute(sql, tuple(parameters))
            # 多读取一行哨兵数据，使 result_formatter 能判断是否截断。
            rows = cursor.fetchmany(self.result_row_limit + 1)
            return format_query_result(
                [description[0] for description in cursor.description or ()],
                rows,
                self.result_row_limit,
                access_policy,
            )
        except sqlite3.OperationalError as error:
            # SQLite 将 progress handler 中断报告为 interrupted 错误。
            if time.monotonic() >= deadline or "interrupted" in str(error).lower():
                raise DatabaseExecutionError("connection_error", "Query deadline exceeded.") from error
            raise DatabaseExecutionError("syntax_error", "The read-only query could not be executed.") from error
        except sqlite3.Error as error:
            raise DatabaseExecutionError("unknown", "The read-only query failed.") from error
        finally:
            # 关闭本次操作连接前先禁用回调。
            connection.set_progress_handler(None, 0)
            connection.close()

    def close(self) -> None:
        # 连接按操作创建，并在 execute/inspect 的 finally 块中关闭。
        return None

    def _connect(self) -> sqlite3.Connection:
        try:
            # 隔离连接创建逻辑，将驱动异常转换为安全领域异常。
            return open_sqlite_readonly(self.database_path)
        except (OSError, sqlite3.Error) as error:
            raise DatabaseExecutionError("connection_error", "Unable to open the database.") from error

    def _check_database(self, database_id: str, policy: AccessPolicy | None = None) -> None:
        # 防止配置为某个数据库的适配器服务其他数据库 ID。
        if database_id != self.database_id:
            raise DatabaseExecutionError("permission_error", "The requested database is not available.")
        # 数据库可见性由服务端策略控制，而不是由请求体声明。
        if policy and database_id not in policy.allowed_database_ids:
            raise DatabaseExecutionError("permission_error", "The requested database is not available.")
