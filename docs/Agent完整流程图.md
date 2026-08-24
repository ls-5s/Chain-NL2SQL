# Agent 输入到输出完整流程图

本文只描述 Agent 从输入到输出的处理链路。登录、HTTP 路由、会话持久化等外围基础设施不放入主图；它们只通过输入上下文和 SSE 结果承载影响 Agent 的行为。

## 1. 输入到输出主流程

```mermaid
flowchart TD
    IN[/用户输入<br/>自然语言问题/] --> CONTEXT[组装 Agent 输入上下文<br/>可选 database_id / 对话上下文 / 参数绑定]
    CONTEXT --> STATE[初始化 NL2SQLState<br/>question / context / iteration / trace]
    STATE --> INTENT[intent_gate<br/>规则优先判断]
    INTENT -->|规则无法确定| INTENT_LLM[LLM 意图分类<br/>intent / confidence / reason]
    INTENT -->|规则已确定| ROUTER{意图路由}
    INTENT_LLM --> CONF{置信度足够且格式有效?}
    CONF -->|否| CLARIFY[澄清回答<br/>补充业务对象、指标、时间范围或数据库]
    CONF -->|是| ROUTER

    ROUTER -->|general_chat| GENERAL[通用回答 LLM<br/>不读取 Schema，不执行 SQL]
    ROUTER -->|知识库问答| KNOW[知识库检索<br/>ACL 过滤 + 相关度阈值]
    ROUTER -->|clarify| CLARIFY
    ROUTER -->|data_query| DB{是否提供 database_id?}

    KNOW --> KNOW_HITS{有可验证资料?}
    KNOW_HITS -->|否| NO_GROUND[暂无可验证知识<br/>安全降级回答]
    KNOW_HITS -->|是| GROUNDED[基于资料生成回答<br/>必须保留可验证引用]

    DB -->|否| CLARIFY_DB[澄清回答<br/>请先选择数据库]
    DB -->|是| SCHEMA[Schema-RAG 检索<br/>数据库/表/字段 ACL 过滤]
    SCHEMA --> SCHEMA_OK{检索到授权 Schema?}
    SCHEMA_OK -->|否/失败| SCHEMA_FAIL[失败终止<br/>未执行 SQL]
    SCHEMA_OK -->|是| FIX_CONTEXT[固定 schema_context 和 schema_version]
    FIX_CONTEXT --> PROMPT[组装 SQL Prompt<br/>问题 + 方言 + Schema + 上下文]
    PROMPT --> GENERATE[LLM 生成 SQL<br/>单条、只读、无未授权字段]
    GENERATE --> VALIDATE[AST 安全校验<br/>sqlglot + 单语句 + 只读 + 白名单 + 参数]
    VALIDATE -->|通过| EXECUTE[只读数据库执行<br/>超时、行数限制、Schema 版本校验]
    VALIDATE -->|SQL 内容错误| RETRY{可修复且未达最大轮次?}
    VALIDATE -->|安全/权限策略拒绝| BLOCK[安全拦截<br/>清空或不返回结果]

    EXECUTE -->|成功| GUARD[result_guard<br/>结果结构、字段映射、脱敏、行数复核]
    EXECUTE -->|SQL 内容错误| RETRY
    EXECUTE -->|连接/超时/权限/Schema 变化| FAIL[不可修复失败<br/>返回安全错误]
    RETRY -->|是| REPAIR[SQL 修复 LLM<br/>复用首轮 Schema 和脱敏错误]
    RETRY -->|否| FAIL
    REPAIR --> VALIDATE

    GUARD -->|通过| SUMMARY[summarize_result<br/>仅基于安全 QueryResult 生成摘要]
    GUARD -->|失败关闭| BLOCK

    GENERAL --> FINALIZE[finalize<br/>整理统一输出]
    CLARIFY --> FINALIZE
    CLARIFY_DB --> FINALIZE
    NO_GROUND --> FINALIZE
    GROUNDED --> FINALIZE
    SUMMARY --> FINALIZE
    SCHEMA_FAIL --> FINALIZE
    BLOCK --> FINALIZE
    FAIL --> FINALIZE
    FINALIZE --> OUT[/最终输出 QueryResponse<br/>final_answer + status + intent<br/>result + generated_sql + trace<br/>knowledge_hits + clarification_fields/]

    classDef input fill:#e8f3ff,stroke:#2878c8,color:#123b63,stroke-width:2px;
    classDef state fill:#f3f4f6,stroke:#6b7280,color:#1f2937;
    classDef llm fill:#fff3d6,stroke:#c07a00,color:#5c3900;
    classDef retrieval fill:#e9f8ef,stroke:#2d8a57,color:#164d30;
    classDef security fill:#fff0f0,stroke:#c23b3b,color:#6f1d1d;
    classDef database fill:#eaf0ff,stroke:#4f63b5,color:#26346e;
    classDef output fill:#e8faef,stroke:#21834b,color:#14532d,stroke-width:2px;
    classDef failure fill:#fce8e8,stroke:#c23b3b,color:#6f1d1d;

    class IN,OUT input;
    class CONTEXT,STATE state;
    class INTENT_LLM,GENERAL,GROUNDED,GENERATE,REPAIR,SUMMARY llm;
    class INTENT,ROUTER,CONF,DB,KNOW_HITS,SCHEMA_OK,RETRY state;
    class KNOW,SCHEMA retrieval;
    class VALIDATE,GUARD,BLOCK security;
    class EXECUTE database;
    class FINALIZE output;
    class CLARIFY,CLARIFY_DB,NO_GROUND,SCHEMA_FAIL,FAIL failure;
```

主链路中的 SQL 自纠错回环是：

```text
生成 SQL -> 安全校验 -> 只读执行 -> 错误判断
                         -> 可修复且有剩余轮次 -> 修复 SQL -> 安全校验
                         -> 不可修复或达到上限 -> 安全失败
```

修复阶段只处理语法、未知字段、未知表、Join 和聚合等 SQL 内容错误；安全、权限、连接、超时、Schema 变化和结果复核失败不会交给模型绕过。

## 2. 输出状态

```mermaid
flowchart LR
    FINALIZE[统一收尾] --> STATUS{最终 status}
    STATUS -->|succeeded| SUCCESS[成功输出<br/>final_answer + QueryResult]
    STATUS -->|needs_clarification| NEEDS[澄清输出<br/>clarification_fields + required_actions]
    STATUS -->|no_grounded_answer| NOGROUND[知识不足输出<br/>不伪造内部资料结论]
    STATUS -->|blocked| BLOCKED[安全拦截输出<br/>不返回不可信结果]
    STATUS -->|failed| FAILED[失败输出<br/>仅返回安全错误信息]

    classDef output fill:#e8faef,stroke:#21834b,color:#14532d,stroke-width:2px;
    classDef warning fill:#fff4df,stroke:#c07a00,color:#5c3900;
    classDef blocked fill:#fce8e8,stroke:#c23b3b,color:#6f1d1d;
    class FINALIZE,SUCCESS output;
    class NEEDS,NOGROUND warning;
    class BLOCKED,FAILED blocked;
```

## 3. 输入与输出字段

| 阶段 | 字段 | 说明 |
| --- | --- | --- |
| 输入 | `question` | 用户自然语言问题 |
| 输入 | `database_id` | 可选数据库标识；数据查询缺失时进入澄清 |
| 输入 | `conversation_context` | 可选历史对话，用于理解省略主语和指代 |
| 输入 | `bound_parameters` | 可选参数绑定，进入 SQL 安全校验和执行 |
| 中间状态 | `intent` / `intent_confidence` | 意图、置信度和分类来源 |
| 中间状态 | `schema_context` / `schema_version` | 授权 Schema 上下文及版本指纹 |
| 中间状态 | `generated_sql` / `validated_sql` | 模型 SQL 和通过安全校验的 SQL |
| 中间状态 | `query_result` | 经过执行和 `result_guard` 复核的结构化结果 |
| 输出 | `final_answer` | 通用回答、澄清、知识库回答或结果摘要 |
| 输出 | `status` | `succeeded`、`needs_clarification`、`no_grounded_answer`、`blocked` 或 `failed` |
| 输出 | `result` / `generated_sql` | 安全结果和 SQL（按接口策略返回） |
| 输出 | `trace` / `knowledge_hits` | 执行轨迹和知识资料命中来源 |

SSE 只负责把 Agent 节点进度和最终结果传给客户端：`start -> progress... -> complete`；发生异常时发送脱敏的 `error`，不改变上述 Agent 输出语义。
