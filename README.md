# Chain-NL2SQL

基于 LangGraph 的链式自纠错 NL2SQL 项目，集成 Schema-RAG、SQL 安全治理和可复现实验评测。

## 单账号会话部署

分析会话、执行过程、结果快照、上下文记忆和受控行引用都保存在服务端
`CONVERSATION_DATABASE_PATH` 指定的 SQLite 数据库中，浏览器不保存消息内容。唯一账号由
`APP_AUTH_USERNAME` 和 `APP_AUTH_PASSWORD` 配置，登录后使用 HttpOnly、SameSite Cookie。

跨设备访问时，前端和 `/api` 必须经同一 HTTPS 域名的反向代理提供；不要将开发服务器或
未加密 Cookie 暴露到公网。生产环境必须设置随机的 `APP_SESSION_SECRET` 与非默认密码。

SQLite 使用 WAL 模式。备份请在应用空闲时执行 SQLite 在线备份，例如：

```powershell
sqlite3 data/conversations.sqlite3 ".backup 'backups/conversations-YYYYMMDD.sqlite3'"
```

同时保存 `.sqlite3` 主文件；不要提交会话数据库、`-wal` 或 `-shm` 文件到版本库。

> 项目状态：P0 的基础组件已部分实现，但端到端 NL2SQL 工作流尚未完成。下面的状态以当前仓库代码为准；“目标能力”不代表已上线功能。

## 当前实现状态

状态说明：`V` 为已实现；`X` 为尚未完成或尚未接入完整业务链路。最近一次核对：2026-08-19。

### 服务与 API

| 状态 | 功能 | 当前情况 |
| --- | --- | --- |
| V | 环境配置 | 从 `.env` 读取服务、模型、超时、轮次和数据库白名单配置。 |
| V | 启动配置校验 | 限制本机绑定地址，校验最大轮次、查询超时、结果行数和数据库白名单。 |
| V | FastAPI 应用工厂 | 已创建应用并注册系统路由和业务路由。 |
| V | 健康检查 | `GET /health` 返回服务状态和运行环境。 |
| V | 数据库列表接口 | `GET /api/v1/databases` 仅返回服务端允许的数据库 ID。 |
| V | 请求上下文 | 支持透传或生成 `X-Request-ID`，并加载本地访问策略。 |
| V | 查询请求校验 | 校验问题、数据库 ID 和最大修复轮次的输入范围。 |
| X | 查询接口 | `POST /api/v1/query` 仍固定返回 `501 Not Implemented`。 |
| X | Graph 结果响应映射 | `map_query_state` 仍抛出 `NotImplementedError`。 |
| X | 生产鉴权与权限 | 尚未实现 API Key、RBAC、用户身份和调试 SQL 权限控制。 |

### 数据库与 SQL 安全

| 状态 | 功能 | 当前情况 |
| --- | --- | --- |
| V | SQLite 只读连接 | 使用 `mode=ro` URI 打开数据库，防止驱动层写入。 |
| V | SQLite Schema 读取 | 读取业务表、字段、主键和外键，并排除 SQLite 系统表。 |
| V | Schema 版本指纹 | 基于规范化 Schema 文本计算 SHA-256 版本哈希。 |
| V | SQL AST 解析 | 使用 `sqlglot` 解析 SQL，限制为单条语句。 |
| V | 只读 SQL 校验 | 拒绝写操作、DDL、控制语句、多语句、注释、系统表和危险函数。 |
| V | 表与字段白名单 | 支持按访问策略校验允许访问的表和字段。 |
| V | 受限 SQL 执行 | 支持参数绑定、查询截止时间和 SQLite progress handler 中断。 |
| V | 结果安全格式化 | 支持结果行数上限、截断标记和敏感字段掩码。 |
| X | MySQL 适配器 | 文件仅为占位，尚未实现连接、Schema 读取和只读执行。 |
| X | 多数据库适配器编排 | 尚未根据 `database_id` 构建和复用数据库适配器。 |
| X | 经授权外部数据库连接 | 规划支持服务管理员预先登记的外部 MySQL 数据库；需实现数据库注册表、凭据引用、TLS、连接超时、Schema 读取和只读账号执行。客户端仅可提交已授权的 `database_id`，不得提交任意地址、连接串或密码。 |

### LLM 组件

| 状态 | 功能 | 当前情况 |
| --- | --- | --- |
| V | OpenAI 兼容客户端 | 可创建 `ChatOpenAI` 客户端，并支持自定义兼容 API 地址。 |
| V | 模型配置校验 | 真实调用前校验 `OPENAI_API_KEY` 和 `OPENAI_MODEL`。 |
| V | SQL 生成 Prompt | 已提供约束单条只读 SQL 输出的生成模板。 |
| V | SQL 修复 Prompt | 已提供复用固定 Schema 与脱敏错误信息的修复模板。 |
| V | 模型输出提取 | 可移除 Markdown SQL 围栏并拒绝多语句输出。 |
| V | 超时与重试 | 对短暂模型故障执行有总预算限制的指数退避重试。 |
| V | 真实 NL2SQL 模型调用 | 意图判断、SQL 生成、SQL 修复和通用回答节点均可调用 LLM。 |

### Schema-RAG

| 状态 | 功能 | 当前情况 |
| --- | --- | --- |
| V | Schema 元数据标准化 | 已定义表、字段、外键的方言无关数据模型。 |
| V | Schema 文档构建 | 可将表结构渲染为稳定、适合模型读取的 Schema 文档。 |
| V | 检索接口契约 | 已定义 `SchemaRetriever` 协议和固定 Schema 版本返回模型。 |
| V | Schema 检索 | `SchemaIndexManager` 按问题召回，并在检索前应用数据库、表和字段权限过滤。 |
| V | ChromaDB 向量检索 | 支持按数据库和 Schema 版本持久化的 Chroma collection，embedding 可注入。 |
| V | BM25 关键词检索 | 支持 JSON 文档持久化、加载重建和确定性关键词召回。 |
| V | 混合召回与重排 | 支持 vector/BM25/hybrid 模式、RRF 去重和可注入 CrossEncoder 重排，并可降级到 BM25。 |
| V | 索引构建与版本管理 | 按 database_id 懒构建版本目录，manifest 记录指纹和模型版本，支持并发锁与原子切换。 |

#### RAG 是否必要

Schema-RAG 对本项目有价值，但不是所有规模都必须启用复杂的向量检索：

- 当前 Demo 只有少量表时，完整 Schema 或 BM25 已足够，RAG 的主要价值是保持接口、权限过滤和后续扩展能力。
- 当数据库包含几十到数百张表、表名相似、字段含义依赖中文描述或业务别名时，按问题召回相关表可以减少 Prompt 长度，并降低选错表和字段的概率。
- 当前实际链路是“意图判断 → Schema 检索 → SQL 生成”。检索结果会写入 `schema_context`，随后注入 SQL 生成和 SQL 修复 Prompt；通用问答和澄清分支不会读取 Schema。
- 默认配置为 `SCHEMA_RETRIEVAL_MODE=hybrid`，优先使用向量和 BM25 混合召回；向量模型或重排依赖不可用时降级到 BM25，BM25 也不可用则安全失败，不会未经权限过滤直接把完整 Schema 发送给模型。
- 生产环境应根据表数量和召回评测选择模式。小型数据库可使用 `bm25`，中大型数据库再使用 `hybrid`，并通过 EX Accuracy、选表准确率、Prompt token、延迟和失败率验证收益。

### 业务知识库 RAG（设计中）

业务知识库 RAG 与 Schema-RAG 是两类不同能力：Schema-RAG 检索表、字段和关联关系，服务 SQL 结构生成；知识库 RAG 检索指标口径、业务规则、数据字典和脱敏的问题-SQL 示例，服务业务语义理解。当前项目只完成了前端知识库 Mock 页面和设计规划，尚未实现后端知识库能力。

| 状态 | 功能 | 当前情况 |
| --- | --- | --- |
| V | 前端知识库页面 | 已有文档列表、分类、上传状态和删除交互，但默认使用 Mock 数据。 |
| X | 文档上传与解析 | 后端尚未提供真实上传、文本提取和内容校验。 |
| X | 文档切分与索引 | 尚未实现 chunk 构建、SQLite 元数据管理、BM25/Chroma 索引和版本发布。 |
| X | 查询流程接入 | 当前 LLM Prompt 不包含业务知识库内容，`data_query` 只使用 Schema-RAG。 |
| X | 命中来源返回 | `knowledge_hits` 已预留前端类型，后端尚未返回文档摘要和来源。 |

目标链路为：

```text
data_query
  -> 业务知识库检索（指标口径、规则、数据字典、示例）
  -> Schema-RAG（表、字段、关系）
  -> Prompt 组装
  -> SQL 生成与安全校验
```

首期设计按 `database_id` 隔离知识库，支持 TXT、Markdown 和 CSV；PDF/DOCX 作为后续扩展。原文存储、SQLite 元数据和 BM25/Chroma Hybrid 索引均属于后续后端实现范围。知识库检索失败或没有命中时继续 Schema-RAG 和 SQL 流程，不因可选知识上下文阻断查询。查询响应只返回标题、分类、摘要和相关度，不返回未经审核的完整原文。

### LangGraph 自纠错工作流

| 状态 | 功能 | 当前情况 |
| --- | --- | --- |
| V | 工作流状态模型 | 已定义请求、Schema、SQL、结果、错误和 Trace 状态字段。 |
| V | 初始状态创建 | 可初始化请求 ID、问题、数据库、方言、轮次和运行状态。 |
| V | 修复路由规则 | 已定义可修复错误类别和最大轮次判断。 |
| V | Graph 构建 | `build_query_graph` 已串联意图判断、Schema 检索、生成、校验、执行、修复和收尾节点。 |
| V | 问题范围判断 | 规则优先判断明确数据查询/通用问题，边界问题由 LLM 以置信度分类，低置信度保守澄清。 |
| V | Schema 检索节点 | 在 SQL 生成前按问题召回授权 Schema，并固定版本和上下文。 |
| V | SQL 生成节点 | 使用 LLM 根据方言、问题和检索到的 Schema 生成只读 SQL。 |
| V | SQL 校验节点 | 使用 AST 和访问策略校验单语句、只读操作及表字段权限。 |
| V | SQL 执行节点 | 在超时、结果行数和 Schema 版本校验下执行只读 SQL。 |
| V | 错误分类节点 | 根据执行或校验结果区分可修复错误与安全、权限、资源错误。 |
| V | SQL 修复节点 | 对允许修复的 SQL 内容错误复用首轮 Schema 上下文进行重试。 |
| V | 收尾节点 | 生成脱敏的最终响应和 Trace。 |
| V | 自纠错闭环 | 已将生成、校验、执行、分类和修复串联为可运行图。 |

### 错误治理与可观测性

| 状态 | 功能 | 当前情况 |
| --- | --- | --- |
| V | 本地访问策略 | 已配置演示数据库、表、字段白名单和邮箱掩码。 |
| V | 基础错误脱敏 | 可脱敏常见数据库连接 URL。 |
| V | 日志入口 | 提供不自动添加 handler 的标准日志获取函数。 |
| X | 错误分类器 | 文件为空壳，尚未映射模型和数据库异常。 |
| X | Trace 记录 | 文件为空壳，尚未持久化或返回节点 Trace。 |
| X | 指标聚合 | 文件为空壳，尚未统计延迟、轮次和修复成功率。 |
| X | 用户安全错误响应 | 尚未完成 Graph 错误到 API 响应的白名单映射。 |

### 前端

| 状态 | 功能 | 当前情况 |
| --- | --- | --- |
| V | Vue 应用与路由 | 已配置 Vue 3、Element Plus 和 `/knowledge` 路由。 |
| V | 工作区布局 | 已实现桌面侧栏、移动端抽屉和响应式页面框架。 |
| V | 知识库页面 | 已实现文档列表、筛选、上传状态和删除交互。 |
| V | Mock API | 默认 Mock 模式可模拟知识库、查询和审批数据。 |
| V | HTTP 客户端封装 | 已封装数据库列表和查询请求，以及统一错误转换。 |
| X | 查询页面 | 当前无自然语言查询输入、结果表格和执行链路页面。 |
| X | 审批页面 | 当前无审批列表、详情和审批操作页面。 |
| X | 知识库后端接口 | 后端尚未提供列表、上传和删除接口。 |
| X | 查询与审批后端接入 | Mock 查询/审批数据未接入实际后端能力。 |

### 测试、构建与评测

| 状态 | 功能 | 当前情况 |
| --- | --- | --- |
| V | 后端单元测试 | 最近一次 `pytest` 运行共 26 项，全部通过。 |
| V | SQLite Demo fixture | 已提供确定性 SQLite 初始化脚本和测试数据。 |
| V | LLM Fake 测试 | 已使用可注入 Stub/Fake 覆盖模型客户端、Prompt 和重试逻辑。 |
| X | 前端 Vitest 测试 | 当前配置未找到测试文件，`pnpm test` 退出失败。 |
| X | 前端 E2E 测试 | 虽有 Playwright 用例，但当前路由不存在用例所需的查询界面，尚未通过端到端验证。 |
| X | 前端生产构建 | `pnpm build` 受 Vite/Element Plus 类型依赖冲突阻断。 |
| X | CSpider/Spider 评测 | 尚无数据集接入、单轮基线、EX Accuracy 或评测报告。 |

### 当前可用范围

- 可作为后端组件库验证：健康检查、数据库白名单、SQLite Schema 读取、受限只读 SQL 执行、LLM 客户端与 Prompt。
- 不可作为完整 NL2SQL 服务使用：查询接口尚未编排 Graph，因此不会生成、修复或执行自然语言查询。
- 前端默认启用 Mock API，适合查看知识库界面交互；将 `VITE_USE_MOCK_API=false` 后，除已实现的数据库列表外，其余业务接口尚未可用。

## 项目目标

NL2SQL 的难点不只是让模型生成一条 SQL，而是让生成结果能够安全执行、在失败后可解释地修复，并通过执行准确率证明方案有效。

Chain-NL2SQL 将一次查询拆成受控的 Agent 流程：

```mermaid
flowchart LR
    Q[自然语言问题] --> S[首轮 Schema 检索]
    S --> G[SQL 生成]
    G --> V[AST 安全校验]
    V --> E[只读数据库执行]
    E -->|成功| R[结果与 Trace]
    E -->|失败| C[错误分类]
    C -->|可修复且有轮次| F[SQL 修复]
    F --> V
    C -->|不可修复或达到上限| X[失败响应]
```

## 目标能力

- **LangGraph 自纠错闭环**：使用显式 State、条件分支和最大轮次控制，而不是黑盒 SQL Agent。
- **问题范围判断**：在 Schema 检索前以规则优先判断明确数据查询/通用问题，边界问题由 LLM 以置信度分类，低置信度保守澄清，避免无关问题被强行转换为 SQL。
- **Schema-RAG**：首次检索后固定 `schema_context` 和 `schema_version`，修复阶段不重复检索，避免 Schema 漂移。
- **安全执行**：基于 `sqlglot` AST 的只读策略、专用只读数据库账号、超时取消、表/字段白名单与结果脱敏。
- **错误治理**：内部原始异常、持久化 Trace、用户响应三层隔离，避免泄露连接串、路径、堆栈和敏感数据。
- **可评测性**：通过 CSpider/Spider 的 EX Accuracy、修复成功率、平均轮次和失败分类，对比单轮 NL2SQL 基线。

## 开发阶段

| 阶段 | 范围 | 验收结果 |
| --- | --- | --- |
| P0 | LangGraph 主链路、固定 SQLite Demo、基础 Schema 读取、SQL 安全校验、FastAPI、日志与测试 | 完成成功查询、SQL 修复、安全拦截和受控失败 |
| P1 | ChromaDB + BM25 混合检索、Reranker、MySQL、评测与基线对照 | 可重复输出 EX、轮次、延迟和失败分类 |
| P2 | Human-in-the-Loop、业务知识库 RAG、Example-RAG、Vue3 + Element Plus 前端 | 可审批 SQL、按数据库隔离检索业务知识，并展示命中来源和完整链路 |

## 技术栈

| 模块 | 组件 |
| --- | --- |
| Agent 编排 | LangGraph、LangChain |
| LLM | DeepSeek-Coder、Qwen2-7B-Instruct、GPT-4o-mini（OpenAI 兼容接口） |
| 检索 | ChromaDB、BGE-small-zh、BM25、bge-reranker-small |
| SQL 安全 | sqlglot、SQLite 只读 URI、MySQL 只读账号 |
| 服务与类型 | FastAPI、Pydantic v2、Uvicorn |
| 前端 | Vue 3、TypeScript、Vite、Tailwind CSS、Element Plus、Pinia |
| 评测 | datasets、CSpider、Spider |
| 测试 | pytest、httpx、可编排 `fake_llm` |

## 模块边界

```text
app/
├── api/             # 路由、认证/权限、响应映射
├── config/          # 配置读取和启动校验
├── graph/           # State、节点、路由和 Graph 构建
├── llm/             # 模型适配、Prompt、输出解析和重试
├── rag/             # 元数据、索引、检索和重排
├── db/              # 适配器、连接、SQL 策略和结果格式化
├── services/        # API 与领域组件之间的应用服务
├── tool/            # Graph 可调用的应用工具
├── mcp/             # MCP 工具与外部服务集成边界
├── errors/          # 分类和脱敏
└── observability/   # Trace、日志和指标

evals/               # 基线、批量评测和报告
tests/               # 单元、集成和 fake LLM
data/                # SQLite Demo、Schema 快照和 fixtures
web/                 # P2 前端
```

模块之间通过稳定接口通信：Graph 依赖检索、模型和数据库抽象，不直接依赖具体 SDK 或驱动实现。完整职责拆分见下方开发文档。

## 开发文档

- [项目说明文档](docs/项目说明文档.md)：架构、状态定义、节点路由、API、RAG、安全、评测、目录与测试策略。

## 安全边界

- P0 仅面向本机开发环境，服务绑定 `127.0.0.1`。
- 默认不在 API 响应中返回 SQL；P1 仅允许具备认证和调试角色的调用方查看脱敏 SQL。
- 仅执行通过 AST 校验的单条只读查询，拒绝写入、DDL、多语句和危险系统操作。
- 结果受表/字段白名单、字段掩码和可选行级过滤约束。
- 数据库和模型的真实密钥只通过 `.env` 注入，不提交到仓库。
- 外部数据库仅限所有者授权且由服务端预先登记的目标；使用专用只读账号、主机和端口白名单及 TLS，禁止根据客户端输入直接建立网络连接。

## 计划产物

- 可运行的 SQLite NL2SQL Demo 与固定测试数据。
- `/api/v1/query` 查询接口、健康检查和受控 Trace。
- 单轮基线与链式自纠错方案的评测报告。
- P2 的审批流、业务知识库 RAG、Example-RAG 和可视化链路页面；当前知识库页面仍是 Mock，后端入库和检索尚未实现。
- 经授权外部 MySQL 数据库的注册、只读连接、Schema 读取和安全执行能力。

详细实现规范、接口约束和验收标准请阅读：[docs/项目说明文档.md](docs/项目说明文档.md)。
