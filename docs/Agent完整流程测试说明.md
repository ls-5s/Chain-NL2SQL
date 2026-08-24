# Agent 完整流程测试说明

本文档记录 Chain-NL2SQL 当前 V1/V2 Agent 流程、会话恢复、SSE、知识库 ACL 和前端完整流程的实现边界与验收方式。

## 1. 流程总览

请求从 API 进入后，先创建会话 turn，再通过 LangGraph 执行。数据库运行时只在数据查询分支创建；普通回答、澄清和无可靠知识命中分支不会访问 Schema 或执行 SQL。

```text
请求
  -> intent_gate
  -> 分支路由
       -> general_answer -> finalize -> complete
       -> clarification_answer -> finalize -> complete
       -> retrieve_knowledge -> grounded_answer -> finalize -> complete
       -> retrieve_schema -> generate_sql -> validate_sql
          -> execute_sql -> result_guard -> summarize_result
          -> finalize -> complete
```

所有流式请求遵循：

```text
start -> progress... -> complete 或 error
```

`request_id` 会贯穿所有 SSE 事件；终态事件之后不再发送 progress。

## 2. 普通回答

示例问题：`你好`、`帮我写一封邮件`。

执行路径：

```text
intent_gate -> general_answer -> finalize -> complete
```

验收要求：

- 无 `database_id` 也能完成请求；
- 不创建真实数据库 adapter；
- 不读取 Schema；
- 不生成或执行 SQL；
- `answer_source=general_llm`；
- SSE 节点顺序和最终响应一致。

## 3. 澄清流程

问题缺少业务对象、指标、时间范围或数据库时，Agent 返回 `needs_clarification`。

```text
intent_gate -> clarification_answer -> finalize -> complete
```

响应包含：

- `clarification_fields`：需要用户补充的字段；
- `required_actions`：下一步动作，例如 `provide_fields` 或 `select_database`；
- `pending_clarification`：保存于会话数据库，便于刷新和服务重启后恢复。

无数据库的数据问题会要求 `select_database`。选择数据库后，会话只允许绑定一次；并发绑定时只有一个请求成功，其他请求返回 `409`。

## 4. 数据查询流程

数据问题的完整路径为：

```text
intent_gate
  -> 创建数据库运行时
  -> retrieve_schema
  -> generate_sql
  -> validate_sql
  -> execute_sql
  -> result_guard
  -> summarize_result
  -> finalize
  -> complete
```

关键约束：

- Schema 只来自服务端授权范围；
- 业务知识片段不会进入 SQL Prompt 的 Schema 权威上下文；
- 只有通过 AST 只读校验的 SQL 才能执行；
- 结果必须经过 `result_guard`，再交给摘要模型；
- 会话保存最终响应、SQL、结果和 progress；
- 重复 `client_request_id` 会重放已有 turn，不创建重复消息。

## 5. 知识库 V2 与 ACL

知识文档默认 `deny`。管理员可在 RAG 页面为文档设置：

- `deny`：禁止检索；
- `all_authenticated`：所有已登录用户可检索；
- `role`：仅指定角色可检索；
- `user`：仅指定用户可检索。

ACL 在检索时按服务端解析出的用户身份和角色过滤，撤权立即生效。未经授权的文档不会进入 `knowledge_hits`、Grounded Prompt 或最终引用。

内部知识问题要求模型回答包含授权文档 ID 引用；没有命中、知识库不可用、回答没有有效引用或引用校验失败时，返回：

```text
NO_GROUNDED_ANSWER
```

系统不会在该分支调用普通通用回答模型，也不会使用无 ACL 的知识库内容。

## 6. 会话持久化与恢复

会话 Repository 持久化：

- user/assistant message；
- turn 状态和 `client_request_id`；
- SSE progress；
- `QueryResponse`，包括 SQL、结果、知识命中和状态；
- pending clarification；
- 当前 `database_id`。

服务重新初始化时，遗留的 `running` turn 会被安全标记为失败，并提示用户重试，不会保持永久运行状态。

## 7. 前端完整流程

Playwright 用例覆盖以下用户路径：

```text
登录
  -> 创建无数据库会话
  -> 普通回答
  -> 模糊问题并显示澄清
  -> 选择数据库
  -> 重新提交数据问题
  -> 显示 SQL 结果
  -> 刷新并恢复会话
  -> 打开 RAG 资料库
  -> 修改并保存 ACL
```

端到端用例使用浏览器路由模拟稳定的 API/SSE 响应，不依赖真实 LLM、外部数据库或网络服务；后端真实 Graph、SQLite 和 FakeLLM 流程由 Python 测试覆盖。

## 8. 测试命令

后端：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

前端单元测试：

```powershell
cd web
pnpm run test -- --run
```

前端类型检查和生产构建：

```powershell
cd web
pnpm run build
```

Playwright：

```powershell
cd web
pnpm exec playwright install chromium
pnpm run e2e
```

当前验证结果：

- 后端：`103 passed`；
- 前端 Vitest：`21 passed`；
- 前端 `vue-tsc` 和 Vite 构建通过；
- Playwright 完整流程：`1 passed`。

测试通过 `tests/conftest.py` 禁止 LangSmith 外部追踪，保证测试不依赖 `.env` 中的网络凭据。

## 9. 已知边界

当前仍属于后续生产增强的项目：

- Grounded 回答已校验授权文档 ID，但尚未实现逐 claim 的证据覆盖评分；
- 尚未接入 PII/敏感内容自动扫描；
- LLM、Schema、数据库和 SSE 取消路径已有基础错误处理，但尚未建立完整的生产指标和分布式限流；
- Playwright 的 V2 文档上传和普通用户撤权后拒答路径仍可继续扩展，核心 ACL API、检索过滤和管理员控制台已覆盖。
