# LLM 组件实现说明

## 目标

`app/llm` 将 LangChain ChatModel 适配为项目内部稳定的 `LLMClient` 协议。Graph 节点只依赖统一的 Prompt 输入与 `ModelResponse` 输出，不直接依赖 OpenAI、DeepSeek 或 Qwen 的 SDK。

当前组件只负责模型调用、Prompt 构建、重试和响应归一化。它不会连接数据库、执行 SQL、修改 LangGraph State，也不会改变 `/api/v1/query` 现有的 `501` 行为。

## 配置

在项目根目录创建 `.env`，填写真实服务配置：

```dotenv
OPENAI_API_KEY=your-provider-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=your-model-name
```

| 变量 | 是否必填 | 说明 |
| --- | --- | --- |
| `OPENAI_API_KEY` | 是 | OpenAI 或兼容服务的 API 密钥。不得提交到仓库。 |
| `OPENAI_BASE_URL` | 否 | 空值时使用 OpenAI 默认地址；可配置为 DeepSeek、Qwen 等兼容服务地址。 |
| `OPENAI_MODEL` | 是 | 由服务商支持的模型名称；不提供默认值，避免意外调用和成本。 |

`Settings` 将空字符串视为未配置。服务启动和健康检查不要求模型凭证；只有创建真实 `OpenAIChatClient` 时才会验证 `OPENAI_API_KEY` 与 `OPENAI_MODEL`。

## 统一接口

[`app/llm/client.py`](../app/llm/client.py) 定义以下稳定边界：

```python
class LLMClient(Protocol):
    def generate(self, prompt: PromptValue, timeout_seconds: float) -> ModelResponse: ...
```

- `PromptValue` 来自 LangChain，保留 system 与 human 消息边界。
- `ModelResponse` 只包含模型返回文本与模型标识，不暴露供应商响应对象或原始元数据。
- 测试可使用 `tests/fakes/fake_llm.py` 中的 `FakeLLM`，不需要网络或真实密钥。

## Prompt

[`app/llm/prompts.py`](../app/llm/prompts.py) 提供两个 `ChatPromptTemplate`：

- `build_sql_generation_prompt()`：首次根据问题、数据库方言与 Schema 上下文生成 SQL。
- `build_sql_repair_prompt()`：根据原问题、固定 Schema、失败 SQL 与已脱敏错误信息修复 SQL。

两个模板都要求模型只输出一条只读 SQL，不包含 Markdown 围栏、解释、注释、分号、多语句、写操作、DDL 或管理命令。Prompt 约束不是安全边界，模型输出仍必须经过 `output_parser.py` 和后续 SQL AST 安全校验。

## 调用与重试

[`app/llm/factory.py`](../app/llm/factory.py) 使用 `ChatOpenAI` 创建 OpenAI 兼容客户端：

- `temperature=0`，提高 NL2SQL 输出稳定性。
- `max_retries=0`，禁用 SDK 内部重试。
- 调用传入的 `timeout_seconds` 作为单次请求的时间预算。
- 供应商实际返回模型名时优先使用；未返回时回退为 `OPENAI_MODEL`。

[`app/llm/retry_policy.py`](../app/llm/retry_policy.py) 统一处理重试：

- 仅重试连接错误、请求超时、限流和服务端临时错误。
- 最多 3 次尝试，即首次调用后最多重试 2 次。
- 退避时间为 `0.25s`、`0.5s`，且不会超出调用总时间预算。
- 认证、请求参数、模型名称和模型输出错误不会重试，交由上层错误分类处理。

## 集成方式

后续 Graph 节点应先填充 Prompt，再调用客户端：

```python
prompt = build_sql_generation_prompt().invoke(
    {
        "dialect": state["dialect"],
        "schema_context": schema_context_text,
        "question": state["question"],
    }
)
response = client.generate(prompt, timeout_seconds=settings.query_timeout_seconds)
```

修复节点应使用 `build_sql_repair_prompt()`，并且只传入已经脱敏的数据库错误信息。节点收到 `response.content` 后必须调用 `extract_sql`，再交给 SQL 安全策略校验；不得绕过只读校验直接执行模型输出。

## 测试

[`tests/unit/test_llm.py`](../tests/unit/test_llm.py) 覆盖：

- 缺失模型配置时的可读错误；
- `ChatOpenAI` 的模型、Base URL、温度、超时和重试参数；
- 文本与模型名称归一化；
- 临时错误重试、非临时错误直返和重试耗尽；
- SQL 生成与修复 Prompt 的约束及变量填充。

运行全部 Python 测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
