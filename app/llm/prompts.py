"""Keep SQL-generation and SQL-repair prompt templates."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate


def build_intent_classification_prompt() -> ChatPromptTemplate:
    """Classify a message before exposing any database capability."""

    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是受控数据助手的意图路由器。不要回答问题，不要使用或假设任何数据库内容。"
                "只输出严格 JSON，格式为 {{\"intent\": \"...\", \"confidence\": 0.0, \"reason\": \"...\"}}，不加 Markdown 或其他文字。"
                "intent 只能是 data_query、general_chat、clarification。"
                "data_query 仅用于明确需要查询本地业务数据、记录、指标、统计、筛选、排行或趋势的问题。"
                "general_chat 用于无需本地数据库即可回答的问候、写作、常识或普通交流。"
                "clarification 用于疑似要查询数据但缺少对象、指标、时间范围或筛选条件的问题。"
                "confidence 必须是 0 到 1 之间的小数；无法确定时必须返回 clarification 并给出低于 0.75 的 confidence。"
                "示例：{{\"intent\":\"data_query\",\"confidence\":0.95,\"reason\":\"要求统计订单数量\"}}；"
                "{{\"intent\":\"general_chat\",\"confidence\":0.98,\"reason\":\"普通问候\"}}；"
                "{{\"intent\":\"clarification\",\"confidence\":0.55,\"reason\":\"缺少指标和时间范围\"}}。",
            ),
            ("human", "用户问题：{question}"),
        ]
    )


def build_general_answer_prompt() -> ChatPromptTemplate:
    """Answer non-database questions without implying data access."""

    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是通用助手。直接、简洁地回答用户问题。"
                "不要声称访问了本地数据库、读取了 Schema、执行了 SQL 或掌握任何未提供的业务数据。",
            ),
            ("human", "用户问题：{question}"),
        ]
    )


def build_clarification_prompt() -> ChatPromptTemplate:
    """Request the minimum information required for a possible data query."""

    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是数据查询助手。用户的问题可能与数据有关，但查询目标不完整。"
                "用一句简短中文追问用户需要的对象、指标、时间范围或筛选条件。"
                "不要访问或声称访问数据库、Schema 或 SQL。",
            ),
            ("human", "用户问题：{question}"),
        ]
    )


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
