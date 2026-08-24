# 业务知识库 RAG 实现说明

## 1. 功能定位

业务知识库 RAG 为 NL2SQL Agent 提供指标口径、业务规则和数据字典等业务背景。它与 Schema-RAG 的职责严格分离：

- Schema-RAG 是表名、字段名和数据库关系的唯一权威来源；
- 知识库片段是不可信上下文，只能帮助模型理解业务语义；
- 知识库检索失败、无命中或索引不可用时，内部知识问题必须拒答；普通数据查询不依赖知识库，也不会把知识内容放入 SQL Prompt；
- 知识库是全局资源，不按 `database_id` 隔离；文档 ACL 默认 `deny`，只有授权用户可检索，仅 `super_admin` 可上传、删除和修改 ACL。

## 2. 目录与职责

```text
app/
├── knowledge/
│   ├── __init__.py
│   └── service.py             # 文档持久化、解析、异步索引、任务恢复和知识检索
├── api/
│   └── routes.py              # 知识库 GET/POST/DELETE/ACL API 和角色权限边界
├── graph/
│   ├── builder.py             # retrieve_knowledge 节点和 Graph 接线
│   ├── state.py               # knowledge_hits、knowledge_context 和检索错误状态
│   ├── grounded_answer_node.py # 授权知识的引用约束回答
│   ├── general_answer_node.py # 无知识要求时的通用回答
│   ├── generation_node.py     # 仅使用授权 Schema 生成 SQL
│   └── repair_node.py         # 复用固定 Schema 修复 SQL
├── schemas/
│   ├── domain.py              # KnowledgeHit 等领域模型
│   └── response.py            # QueryResponse 和 KnowledgeDocumentResponse
└── config/
    └── settings.py            # KNOWLEDGE_* 配置读取

tests/
└── unit/
    └── test_knowledge.py      # 文件校验、异步索引、检索、删除和失败边界测试

web/src/
├── api/client.ts              # 知识库列表、上传和删除请求
├── types/api.ts               # KnowledgeDocument、KnowledgeHit 和 SSE 类型
├── views/RagView.vue          # 知识库管理、上传、轮询和权限交互
├── views/AgentView.vue        # Agent 知识命中折叠展示
└── tests/ragView.spec.ts      # 页面加载、权限、上传和轮询测试
```

`app/knowledge/service.py` 负责 SQLite 文档、chunk、job 元数据，原文文件保存，TXT/MD/CSV/PDF/DOCX 解析，固定大小线程池，任务重试和启动恢复，以及 FTS5/BM25 检索。API 层只负责认证、角色授权、上传大小读取、状态码和错误映射。Graph 层将知识检索作为增强上下文，不允许知识片段决定表名或字段名。前端只展示文档元数据、状态和短摘要，不渲染原始 HTML 或完整未审核内容。

## 3. 数据流与持久化

```text
multipart 上传
  -> 扩展名、MIME、文件签名、大小和文件名校验
  -> originals/{document_id}.{suffix} 保存原文
  -> SQLite 事务写入 document(uploading) + job(queued)
  -> 立即返回文档元数据
  -> 线程池 claim job
  -> 解析文本、校验空内容和文本长度
  -> 按固定大小和 overlap 切分 chunk
  -> 写入 chunks 和 FTS5 索引
  -> document=indexed、job=done
```

SQLite 数据库默认位于 `KNOWLEDGE_DATABASE_PATH`，包含：

- `knowledge_documents`：文件名、类型、大小、分类、状态、摘要、失败原因和原文路径；
- `knowledge_chunks`：文档片段、顺序和内容；
- `knowledge_jobs`：队列状态、尝试次数、锁定时间和错误；
- `knowledge_chunks_fts`：可用时创建的 SQLite FTS5 虚表，用于 BM25 排序。

原文文件名不会直接作为磁盘路径，服务使用 UUID 文件名避免路径穿越。SQLite 连接启用 WAL、外键和忙等待；删除文档时同步删除 chunk、FTS 记录和原文。

## 4. 文档解析与任务状态

支持的扩展名和解析方式：

| 类型 | 解析方式                     | MIME/签名要求                                              |
| ---- | ---------------------------- | ---------------------------------------------------------- |
| TXT  | UTF-8 文本                   | `text/plain` 或通用二进制 MIME                             |
| MD   | UTF-8 Markdown 文本          | `text/markdown`、`text/plain` 或通用二进制 MIME            |
| CSV  | CSV 行转换为文本片段         | `text/csv`、`text/plain`、Excel CSV MIME 或通用二进制 MIME |
| PDF  | `pypdf` 提取页面文本         | `application/pdf` 和 `%PDF` 签名                           |
| DOCX | `python-docx` 提取段落和表格 | Office MIME、ZIP 签名及 DOCX 必需文件                      |

上传大小默认限制为 20 MiB。空文件、空解析文本、超过 2,000,000 字符的解析结果、非法 MIME、无效 PDF/DOCX 签名和无效文件名都会被拒绝或记录为失败。

文档状态为：

- `uploading`：文件和任务已登记，等待或正在执行任务；
- `parsing`：worker 已 claim 任务并正在解析、切分或写入索引；
- `indexed`：chunk 和索引已完成，可以参与检索；
- `failed`：解析或索引失败，保留失败原因，管理员可删除后重新上传。

任务最多执行 3 次。服务启动时只回收缺失锁、锁超时或无效锁的 `running` 任务；达到最大尝试次数的任务直接标记为 `failed`。删除 `uploading` 或 `parsing` 文档返回 `409`，避免删除与 worker 竞态。

## 5. API 与权限

### `GET /api/v1/knowledge`

需要登录，返回按创建时间倒序排列的文档元数据列表。响应字段包括 `id`、`filename`、`file_type`、`size_bytes`、`category`、`status`、`created_at`、`updated_at`、`chunk_count`、`summary`、`failure_message` 和 `acl`。

### `POST /api/v1/knowledge`

仅 `super_admin` 可调用，使用 `multipart/form-data`：

- `file`：支持的文档文件；
- `category`：可选分类，默认“未分类”，最长 80 个字符。

接口读取大小上限后创建 `uploading` 文档和 `queued` 任务，返回 HTTP `202` 和文档元数据。解析、索引在后台执行，客户端应通过列表接口轮询状态。

非法扩展名、MIME、签名、空文件或超大文件返回 `422`；未登录返回 `401`；非超级管理员返回 `403`。

### `DELETE /api/v1/knowledge/{document_id}`

仅 `super_admin` 可调用。已索引或失败文档删除成功返回 `204`；文档不存在返回 `404`；文档正在处理返回 `409`。删除会移除数据库记录、索引记录和原文文件。

### `PATCH /api/v1/knowledge/{document_id}/acl`

仅 `super_admin` 可调用。请求体为 `{ "policy_type": "deny|all_authenticated|role|user", "role"?: "...", "user_id"?: "..." }`。`role` 策略必须提供角色，`user` 策略必须提供用户 ID；无效策略返回 `422`。ACL 变更立即影响后续检索。

## 6. 检索与 Graph 联动

`build_query_graph()` 在内部知识意图下进入 `retrieve_knowledge` 节点。节点使用已索引 chunk 做 BM25 检索，并将结果写入：

- `knowledge_hits`：标题、分类、短摘要和相关度；
- `knowledge_context`：限制总长度的提示词上下文；
- `knowledge_retrieval_error`：检索失败时的受控错误标记。

SQLite 支持 FTS5 时优先使用 `bm25()` 排序；不可用时退回确定性的 Python 关键词重叠检索。检索异常写入受控错误状态；内部知识问题随后进入拒答分支，不会调用普通通用回答模型，也不会退回无 ACL 的知识库内容。

知识上下文只进入 Grounded 回答 Prompt，并明确标记为“不可信业务背景”。模型回答必须包含授权 `document_id` 引用；缺少可靠命中或引用校验失败时返回 `NO_GROUNDED_ANSWER`。数据查询的 SQL 生成和修复 Prompt 不包含知识库内容，只使用授权 Schema 和既有安全策略。

公共 `QueryResponse` 增加可选 `knowledge_hits`，默认空列表，因此历史会话响应仍可反序列化。SSE 在 `retrieve_knowledge` 进度中报告命中数量和知识检索可用性；会话持久化保存新增进度和最终响应字段。

## 7. 前端行为

[`RagView.vue`](../web/src/views/RagView.vue) 提供文档总数、已索引数、处理中数量和失败数量统计，并支持文件名/分类/摘要搜索、分类筛选、上传弹窗、失败原因、刷新和删除确认。

- 管理员显示上传、删除和 ACL 控制；普通成员只读；
- 管理员可为每份文档设置禁止、全体已登录用户、指定角色或指定用户 ACL；保存失败会显示文档级错误；
- `uploading` 或 `parsing` 文档每 2 秒刷新一次；组件卸载时清理定时器；
- 客户端先做扩展名和 20 MiB 校验，后端仍执行完整安全校验；
- [`AgentView.vue`](../web/src/views/AgentView.vue) 通过折叠区域展示知识命中标题、分类和摘要。

## 8. 配置

```dotenv
KNOWLEDGE_ROOT=data/knowledge
KNOWLEDGE_DATABASE_PATH=data/knowledge.sqlite3
KNOWLEDGE_TOP_K=5
KNOWLEDGE_MAX_UPLOAD_BYTES=20971520
KNOWLEDGE_CHUNK_SIZE=800
KNOWLEDGE_CHUNK_OVERLAP=120
```

配置由 [`app/config/settings.py`](../app/config/settings.py) 读取。`KNOWLEDGE_TOP_K` 控制每次最多返回的文档命中数；chunk size 和 overlap 影响索引粒度和上下文长度。生产环境应将 `KNOWLEDGE_ROOT` 和数据库路径放在服务账号可读写、且不被静态文件服务暴露的目录中。

## 9. 测试与验收

### Demo 业务知识种子

Demo SQLite 数据库和对应业务知识资料可以重复生成：

```powershell
.venv\Scripts\python.exe scripts\init_demo_db.py
.venv\Scripts\python.exe scripts\seed_demo_knowledge.py
.venv\Scripts\python.exe scripts\build_demo_schema_rag.py
```

种子资料位于 `data/knowledge_sources/`，包括销售指标口径、订单状态规则和 Demo 数据字典；索引完成后资料 ACL 为 `all_authenticated`，可直接用于登录用户的 grounded answer 测试。

后端 [`tests/unit/test_knowledge.py`](../tests/unit/test_knowledge.py) 和 [`tests/unit/test_knowledge_v2.py`](../tests/unit/test_knowledge_v2.py) 覆盖 Markdown 上传、异步索引、BM25 检索、默认拒绝、role/user ACL、撤权、重建失败保留旧索引和 Grounded 引用拒答。前端 [`web/src/tests/ragView.spec.ts`](../web/src/tests/ragView.spec.ts) 覆盖空态、成员只读、管理员上传、轮询收敛和 ACL 保存。

推荐执行：

```bash
python -m pytest tests/unit/test_knowledge.py -q
python -m compileall -q app
cd web
pnpm test
pnpm build
```

Playwright 当前覆盖登录、无数据库会话、普通回答、澄清、数据库选择、数据结果、刷新恢复和 ACL 保存；后端 Graph/SQLite/FakeLLM 覆盖真实节点链路。测试环境使用确定性替身，不依赖生产模型和真实外部服务。完整结果见[Agent完整流程测试说明](Agent完整流程测试说明.md)。
