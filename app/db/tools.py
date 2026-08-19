"""Backward-compatible imports for database tools.

The canonical implementation lives in :mod:`app.tool.database_query`.
"""

from app.tool.database_query import QueryDatabaseInput, create_query_database_tool

__all__ = ["QueryDatabaseInput", "create_query_database_tool"]
