"""基于 sqlglot AST 校验实现的 SQL 安全边界。"""

from __future__ import annotations

from dataclasses import dataclass
import re

import sqlglot
from sqlglot import exp

from app.api.authorization import AccessPolicy


@dataclass(frozen=True)
class SQLValidationResult:
    """安全策略的结构化判定结果，拒绝原因可用于安全错误响应。"""

    allowed: bool
    reason: str | None = None


_SYSTEM_TABLES = {
    "sqlite_master",
    "sqlite_schema",
    "sqlite_temp_master",
    "sqlite_temp_schema",
}


def _has_comment_outside_quotes(sql: str) -> bool:
    """检测 SQL 注释，同时避免误判字符串字面量中的注释标记。"""

    # 跟踪引号状态，避免把字面量中的标记误认为注释。
    quote: str | None = None
    index = 0
    while index < len(sql):
        char = sql[index]
        if quote:
            # SQL 通过重复引号进行转义，例如 'it''s'。
            if char == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    index += 2
                    continue
                quote = None
            index += 1
            continue
        if char in {"'", '"', "`"}:
            quote = char
            index += 1
            continue
        if sql.startswith("--", index) or sql.startswith("/*", index):
            return True
        index += 1
    return False


def _iter_nodes(expression: exp.Expression, node_types: tuple[type[exp.Expression], ...]):
    # 遍历完整 AST，使嵌套查询和 CTE 也执行相同校验。
    for node in expression.walk():
        if isinstance(node, node_types):
            yield node


def _column_allowed(column: exp.Column, tables: dict[str, str], policy: AccessPolicy) -> bool:
    # 优先解析表别名；未限定字段需要对所有引用表进行检查。
    table_ref = column.table.lower() if column.table else ""
    table_names = {tables[table_ref]} if table_ref in tables else set(tables.values())
    return any(
        column.name.lower() in policy.allowed_columns.get(table_name, frozenset())
        for table_name in table_names
    )


def validate_readonly_sql(
    sql: str,
    dialect: str,
    access_policy: AccessPolicy | None = None,
    allowed_parameters: set[str] | None = None,
) -> SQLValidationResult:
    """允许一条只读查询，并执行可选的表和字段访问策略。"""

    if not sql or not sql.strip():
        # 空的模型输出永远不能作为可执行 SQL。
        return SQLValidationResult(False, "empty_sql")
    if _has_comment_outside_quotes(sql):
        # 解析前拒绝注释，防止隐藏子句和策略绕过。
        return SQLValidationResult(False, "comments_not_allowed")
    named_parameters = set(re.findall(r"(?<!:):([A-Za-z_][A-Za-z0-9_]*)", sql))
    if named_parameters and allowed_parameters is None:
        return SQLValidationResult(False, "parameters_not_allowed")
    if allowed_parameters is not None and not named_parameters.issubset(allowed_parameters):
        return SQLValidationResult(False, "unknown_parameter")

    try:
        # 按目标方言解析，而不是依赖关键字匹配。
        statements = sqlglot.parse(sql, read=dialect or "sqlite")
    except sqlglot.errors.ParseError:
        return SQLValidationResult(False, "syntax_error")
    if len(statements) != 1 or statements[0] is None:
        # 一次请求只能执行一条语句。
        return SQLValidationResult(False, "multiple_statements")

    statement = statements[0]
    if not isinstance(statement, exp.Select):
        # AST 根节点必须是只读查询。
        return SQLValidationResult(False, "readonly_statement_required")

    forbidden_names = (
        "Insert",
        "Update",
        "Delete",
        "Create",
        "Drop",
        "Alter",
        "Command",
        "Pragma",
        "Truncate",
        "Into",
        "Attach",
    )
    forbidden = tuple(
        node_type
        for name in forbidden_names
        if (node_type := getattr(exp, name, None)) is not None
    )
    if forbidden and any(_iter_nodes(statement, forbidden)):
        # 无论出现在何处，都拒绝写操作、DDL、控制语句和 ATTACH。
        return SQLValidationResult(False, "write_or_control_statement")

    dangerous_functions = {"load_extension", "readfile", "writefile", "eval"}
    for function in _iter_nodes(statement, (exp.Anonymous,)):
        # 这些 SQLite 函数可以访问文件或加载可执行扩展。
        if function.name.lower() in dangerous_functions:
            return SQLValidationResult(False, "dangerous_function_not_allowed")

    tables: dict[str, str] = {}
    for table in _iter_nodes(statement, (exp.Table,)):
        # 构建别名映射，并为每个关系执行表白名单校验。
        table_name = table.name.lower()
        if table_name in _SYSTEM_TABLES:
            return SQLValidationResult(False, "system_table_not_allowed")
        alias = table.alias_or_name.lower()
        tables[alias] = table_name
        if (
            access_policy
            and access_policy.allowed_tables
            and table_name not in access_policy.allowed_tables
        ):
            return SQLValidationResult(False, "table_not_allowed")

    if access_policy and access_policy.allowed_columns:
        for column in _iter_nodes(statement, (exp.Column,)):
            # 显式字段必须存在于服务端字段策略中。
            if not _column_allowed(column, tables, access_policy):
                return SQLValidationResult(False, "column_not_allowed")

    return SQLValidationResult(True)
