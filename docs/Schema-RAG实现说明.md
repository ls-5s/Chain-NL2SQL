# Schema-RAG 实现说明

## 1. 功能定位

Schema-RAG 是本项目面向数据库结构的检索增强生成能力。它检索的是表、字段、主键和外键等 Schema 元数据，并将与用户问题相关的结构信息提供给 SQL 生成模型。

Schema-RAG 不等同于知识库 RAG：

- Schema-RAG 按 `database_id` 隔离数据库结构，服务于 SQL 生成；
- 知识库 RAG 面向业务规则、指标口径和数据字典等资料；
- Schema-RAG 的结果必须受到表级、字段级访问策略限制，不能把未授权结构发送给模型。

当前实现覆盖本地 SQLite Demo。MySQL、多数据库注册和生产级索引运维仍属于后续扩展。

## 2. 完整数据流

```text
SQLite 元数据
  -> NormalizedTable
  -> SchemaDocument
  -> schema_version
  -> database_id/version 索引目录
  -> 权限过滤
  -> BM25/Chroma 向量召回
  -> Hybrid RRF 合并去重
  -> 可选 Reranker 重排
  -> top-k SchemaDocument
  -> generate_sql Prompt
```

数据查询进入 `retrieve_schema` 节点前，意图闸门已经确认问题属于 `data_query`。非数据问题不会触发 Schema 检索。

## 3. 核心接口

### 3.1 `SchemaRetrievalRequest`

位于 `app/rag/retriever.py`，表示一次经过权限边界约束的检索请求：

```python
SchemaRetrievalRequest(
    question="查询用户数量",
    database_id="demo",
    dialect="sqlite",
    allowed_tables=frozenset({"users"}),
    allowed_columns={"users": frozenset({"id", "name"})},
)
```

### 3.2 `SchemaRetriever`

```python
class SchemaRetriever(Protocol):
    def retrieve(self, request: SchemaRetrievalRequest) -> SchemaRetrieval: ...
```

当前 Graph 通过 `SchemaIndexManager` 实现该协议。P0 兼容路径仍保留 `SQLiteSchemaRetriever`，用于直接读取完整 Schema 和单元测试替身。

### 3.3 `SchemaDocument` 与 `SchemaRetrieval`

`SchemaDocument` 包含：

- `table_name`
- `content`
- `database_id`
- `column_names`
- `dialect`

`SchemaRetrieval` 返回：

- `documents`：最终提供给 SQL 生成的 Schema 文档；
- `schema_version`：规范化 Schema 文本的 SHA-256 指纹；
- `retrieval_mode`：`bm25`、`vector`、`hybrid` 或兼容路径的 `full_schema`；
- `retrieval_scores`：内部召回摘要，不包含原始索引对象。

## 4. 文档构建与版本

`app/rag/introspector.py` 从 SQLite 读取业务表、字段、可空性、主键和外键；`normalizer.py` 将驱动结果转换为方言无关的数据模型；`document_builder.py` 生成稳定文本：

```text
TABLE users
COLUMNS id INTEGER NOT NULL, name TEXT NOT NULL
PRIMARY KEY id
FOREIGN KEYS none
```

当前 SQLite Demo 没有表注释和字段注释，因此实现不会伪造这些信息。每次 Schema 文本变化都会产生新的 `schema_version`。

索引目录为：

```text
data/schema_metadata/{database_id}/{schema_version}/
├── manifest.json
├── bm25.json
└── vector/
```

`manifest.json` 记录数据库 ID、Schema 版本、方言、文档数量、文档指纹、embedding/reranker 模型版本、构建时间和索引可用性。

## 5. 权限过滤

Graph 将 `AccessPolicy` 转换为 `SchemaRetrievalRequest`。检索前执行：

1. 按 `database_id` 隔离文档；
2. 按 `allowed_tables` 过滤表；
3. 按 `allowed_columns` 裁剪字段内容；
4. 裁剪主键和外键摘要，避免被过滤字段通过关系文本重新暴露。

因此，未授权的表和字段不会进入最终候选，也不会进入 SQL 生成 Prompt、SSE 表名列表或公共 trace。

## 6. 召回与重排

支持三种配置模式：

### `bm25`

使用表名、字段名和 Schema 文本进行关键词召回。索引以 JSON 保存，加载时重建 `rank_bm25` 对象，不使用 pickle。

### `vector`

使用可注入的 `EmbeddingProvider` 生成向量，并存入按数据库和版本隔离的 Chroma collection。默认 embedding 模型为 `BAAI/bge-small-zh-v1.5`。

### `hybrid`

默认模式。向量和 BM25 各取候选后：

1. 按索引文档 ID 去重；
2. 使用 Reciprocal Rank Fusion 合并排名；
3. 使用可注入的 `Reranker` 重排；
4. 最终返回不超过 `SCHEMA_TOP_K` 张表，默认值为 5。

默认 reranker 模型为 `BAAI/bge-reranker-base`。测试使用 fake embedding/reranker，不需要下载真实模型。

## 7. 索引生命周期与降级

`SchemaIndexManager` 按 `database_id` 懒构建索引：首次查询或版本变化时构建，后续复用 manifest 和索引文件。

- 同一数据库使用进程内锁，避免并发重复构建；
- 在临时目录生成 BM25、向量索引和 manifest；
- 通过旧目录备份、临时目录原子替换和失败恢复保护索引完整性；
- Chroma 客户端关闭后再切换目录，兼容 Windows 文件句柄行为。

当 Chroma、embedding 或 reranker 不可用时：

- `SCHEMA_FALLBACK_MODE=bm25`：降级为 BM25；
- `SCHEMA_FALLBACK_MODE=none`：返回 `schema_retrieval_error`；
- BM25 同样不可用时，不会静默退回未经筛选的完整 Schema。

## 8. Graph 接线与 Schema 漂移

`retrieve_schema` 节点写入：

- `schema_version`
- `schema_context`
- `retrieval_mode`
- `retrieval_scores`
- `retrieved_tables`
- 检索节点 trace

首次检索后的 `schema_version` 固定在 `NL2SQLState` 中。`execute_sql` 执行前调用 `DatabaseExecutor.get_schema_version()` 重新读取当前指纹：

- 版本一致：继续执行已通过安全校验的 SQL；
- 版本不一致：返回 `schema_changed`，不执行旧 SQL，也不在同一请求中偷偷替换 Schema 上下文。

SSE 的 `retrieve_schema` 进度事件会报告检索模式、召回数量和已授权表名；召回分数只保留在内部状态，不向客户端暴露原始索引信息。

## 9. 配置

```dotenv
SCHEMA_RETRIEVAL_MODE=hybrid
SCHEMA_TOP_K=5
SCHEMA_INDEX_ROOT=data/schema_metadata
SCHEMA_FALLBACK_MODE=bm25
SCHEMA_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
SCHEMA_RERANKER_MODEL=BAAI/bge-reranker-base
```

配置由 `app/config/settings.py` 读取，并由 `app/config/validation.py` 校验模式、降级策略和 top-k 范围。

真实向量检索需要部署环境安装依赖并预先准备模型。没有模型资源时，推荐使用 BM25 模式或启用 BM25 降级。

## 10. 测试与边界

当前测试覆盖：

- Schema 文档和版本指纹；
- BM25 JSON 持久化与确定性召回；
- RRF 去重、top-k 和 fake reranker；
- fake embedding 的 Chroma 持久化；
- 表/字段权限过滤；
- 向量、重排不可用时的 BM25 降级；
- Schema 漂移阻止 SQL 执行；
- Graph、SSE 和旧 retriever 兼容路径。

当前未覆盖或仍属后续能力：

- MySQL Schema 读取和数据库注册表；
- 多轮会话中的跨请求 Schema 权限继承；
- 独立索引构建 CLI、分布式锁和生产级索引监控；
- SQL 执行失败后的自动修复闭环；
- CSpider/Spider 的完整 RAG 消融评测。

最后一次本地验证：`49 passed`。
