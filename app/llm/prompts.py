"""Keep SQL-generation and SQL-repair prompt templates."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate


def build_sql_generation_prompt() -> ChatPromptTemplate:
    """构建首轮 SQL 生成 Prompt，不让模型直接获取数据库访问能力。"""

    # 每次返回新的模板实例，避免调用方修改共享模板影响其他请求。
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是受控 NL2SQL 系统中的 SQL 生成器。只根据提供的 Schema 上下文回答。"
                "仅返回一条只读 SQL，必须是 SELECT 或最终只执行 SELECT 的 WITH 查询。"
                "不得返回 Markdown 围栏、解释文字、注释、分号、多条语句或任何写操作、DDL、"
                "管理命令。不要猜测 Schema 中未出现的表或字段。",
            ),
            (
                "human",
                "数据库方言：{dialect}\n"
                "Schema 上下文：\n{schema_context}\n\n"
                "用户问题：{question}\n\n"
                "只输出 SQL。",
            ),
        ]
    )


def build_sql_repair_prompt() -> ChatPromptTemplate:
    """构建执行失败后的 SQL 修复 Prompt。错误信息必须先由调用方脱敏。"""

    # 修复 Prompt 固定复用首轮 Schema，防止修复循环中发生上下文漂移。
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是受控 NL2SQL 系统中的 SQL 修复器。请根据原问题、固定 Schema、失败 SQL "
                "和已脱敏错误信息修复查询。仅返回一条只读 SQL，必须是 SELECT 或最终只执行 "
                "SELECT 的 WITH 查询。不得返回 Markdown 围栏、解释文字、注释、分号、多条语句，"
                "或任何写操作、DDL、管理命令。不要使用 Schema 中未出现的表或字段。",
            ),
            (
                "human",
                "数据库方言：{dialect}\n"
                "Schema 上下文：\n{schema_context}\n\n"
                "用户问题：{question}\n\n"
                "失败 SQL：\n{failed_sql}\n\n"
                "已脱敏错误信息：\n{error_message}\n\n"
                "只输出修复后的 SQL。",
            ),
        ]
    )
