# LangGraph 查询链路实现说明

## 1. 本次改动概览

本次修改将 P0 阶段原本仅有接口骨架的自然语言查询能力接入最小可运行链路。`POST /api/v1/query` 现在可以针对固定的 SQLite 演示库完成 Schema 读取、模型生成 SQL、安全校验、只读执行和结果响应。

当前链路只支持 `demo` 数据库。真实模型仍需要在 `.env` 中配置 OpenAI 兼容服务的密钥和模型名称。

```text
POST /api/v1/query
  -> 创建 SQLiteAdapter 和 LLMClient
  -> 创建初始 NL2SQLState
  -> LangGraph 执行查询图
  -> 映射为 QueryResponse
```

## 2. 图执行流程

[`app/graph/builder.py`](../app/graph/builder.py) 中的 `build_query_graph` 构建并编译以下固定顺序的图：

```text
retrieve_schema
  -> generate_sql
  -> validate_sql
  -> execute_sql
  -> finalize
  -> END
```

各节点职责如下：

| 节点 | 实现 | 输入/输出 | 失败处理 |
| --- | --- | --- | --- |
| `retrieve_schema` | `SQLiteSchemaRetriever` | 根据问题和数据库 ID 读取 Schema 文档及版本指纹，写入 `schema_context`、`schema_version` | 底层 Schema 读取异常由请求层转换为受控响应 |
| `generate_sql` | `make_generation_node` | 使用 SQL 生成 Prompt、方言、Schema 上下文和用户问题调用 `LLMClient`，提取 SQL，递增 `iteration` | 未得到有效 SQL 时标记为 `failed/invalid_model_output` |
| `validate_sql` | `make_validation_node` | 对生成的 SQL 执行单条只读、表、字段等安全校验，写入 `validated_sql` | 校验不通过时标记为 `blocked`，分类为 `syntax_error` 或 `unsafe_sql` |
| `execute_sql` | `make_execution_node` | 使用 SQLite 只读适配器执行已验证 SQL，写入 `query_result` | `DatabaseExecutionError` 的安全类别和消息写入状态 |
| `finalize` | `make_finalize_node` | 生成不包含原始 SQL 或底层异常的最终说明 | 成功时返回行数；失败时使用安全错误信息或默认文案 |

所有节点都会先检查状态是否仍为 `running`。因此模型输出无效或 SQL 被策略拦截后，后续执行节点不会调用数据库。

## 3. API 接入

[`app/api/routes.py`](../app/api/routes.py) 的 `POST /api/v1/query` 已从固定返回 `501` 改为实际执行图流程。

请求示例：

```json
{
  "question": "查询用户数量",
  "database_id": "demo",
  "max_iterations": 1
}
```

处理规则：

1. 从请求上下文取得服务端访问策略，拒绝不在白名单中的数据库（`403`）。
2. 当前仅配置 `demo` 的 SQLite 适配器，其他已允许但未接入的数据库返回 `404`。
3. 基于 `DEMO_DATABASE_PATH` 创建 `SQLiteAdapter`，并将其作为 Schema 检索和 SQL 执行的唯一数据库边界。
4. 延迟创建 OpenAI 兼容客户端；模型配置缺失时返回 `503`，不会影响健康检查和数据库列表接口。
5. 运行异步 LangGraph，随后由 `map_query_state` 将内部状态白名单映射为 `QueryResponse`。
6. 请求结束后调用适配器的 `close()`；SQLite 连接本身按 Schema 读取或 SQL 执行操作创建并在其内部关闭。

成功响应中的核心字段为：

```json
{
  "request_id": "请求追踪 ID",
  "status": "succeeded",
  "iteration": 1,
  "error_category": null,
  "final_answer": "查询完成，共返回 1 行结果。",
  "result": {
    "columns": ["count"],
    "rows": [[3]],
    "row_count": 1,
    "truncated": false
  },
  "trace": []
}
```

`map_query_state` 不会返回内部 SQL、原始异常、数据库路径或模型响应对象。状态和错误类别会被转换为 `QueryStatus`、`ErrorCategory` 枚举，确保响应契约稳定。

## 4. 配置变更

新增环境变量：

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `DEMO_DATABASE_PATH` | `data/demo.sqlite` | 演示 SQLite 数据库文件路径 |

`.env.example` 同时保留以下真实模型配置的占位项：

```dotenv
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=
```

其中 `OPENAI_API_KEY` 和 `OPENAI_MODEL` 是执行查询时创建真实模型客户端的必填项。`OPENAI_BASE_URL` 可为空，或设置为兼容 OpenAI API 的服务地址。

## 5. 错误响应

| 场景 | HTTP 状态码 | 响应说明 |
| --- | --- | --- |
| 数据库不在请求访问策略中 | `403` | `Database is not allowed.` |
| 数据库已允许但没有适配器 | `404` | `Database adapter is not configured.` |
| 缺失模型密钥或模型名称 | `503` | `LLM service is not configured.` |
| 配置或输入参数无效 | `400` | 返回可安全展示的参数错误 |
| 图执行出现未分类异常 | `502` | `The NL2SQL agent could not complete the query.` |

对于已进入图的 SQL 安全拦截和数据库执行错误，接口保持 `200`，并通过响应中的 `status`、`error_category` 与 `final_answer` 表达受控失败结果。

## 6. 测试

新增 [`tests/unit/test_graph.py`](../tests/unit/test_graph.py)，使用 `FakeLLM` 验证最小图的成功路径：

```text
FakeLLM 返回 SELECT COUNT(*) AS count FROM users
  -> Schema 读取
  -> SQL 生成与解析
  -> 安全校验
  -> SQLite 只读执行
  -> 返回 count = 3 和成功提示
```

[`tests/test_health.py`](../tests/test_health.py) 也已更新：当 `OPENAI_API_KEY` 或 `OPENAI_MODEL` 未配置时，查询接口应返回 `503`，取代此前骨架阶段的 `501` 预期。

运行测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 7. 当前边界与后续工作

本次实现的是一次生成、一次校验、一次执行的最小闭环，尚未实现完整的链式自纠错能力：

- 未接入错误分类节点、SQL 修复 Prompt、条件路由和最大轮次重试；`max_iterations` 已在初始状态中保留，但当前图不会据此循环。
- 未写入 `trace` 事件，响应中的 `trace` 当前为空列表。
- `SQLiteSchemaRetriever` 直接返回完整 Schema，尚未按问题进行 RAG 筛选、混合检索或重排。
- 仅支持 `demo` SQLite 数据库，尚未根据其他数据库 ID 选择 MySQL 或其他适配器。
- 路由层将未知图异常统一转换为 `502`；后续应接入更细粒度的异常分类与可观测性。

相关基础能力参见：[SQLite 数据库底座实现说明](SQLite数据库底座实现说明.md) 与 [LLM 组件实现说明](LLM组件实现说明.md)。

## 8. 前端查询视图草稿

工作区还新增了 [`web/src/views/QueryView.vue`](../web/src/views/QueryView.vue)。该视图提供了面向用户的聊天式查询界面，包括：

- 通过 `fetchDatabases()` 加载可选数据源；
- 通过 `submitQuery()` 发送自然语言问题；
- 展示查询状态、结果表格、加载状态和受控失败消息；
- 提供三个示例问题及执行详情抽屉。

该文件目前尚未注册到 [`web/src/router/index.ts`](../web/src/router/index.ts)，默认路由仍指向知识库页面，因此查询视图不能通过现有导航访问。

此外，详情抽屉会读取 `latestResponse.generated_sql`，但后端 `QueryResponse` 的安全响应模型并不包含该字段，实际后端模式下会显示“未生成 SQL”。这是当前前后端契约的已知差异：若后续需要展示 SQL，应先实现受权限保护且经过脱敏的调试 SQL 字段；不能直接将内部生成 SQL 返回给所有调用方。
